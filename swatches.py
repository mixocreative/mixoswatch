"""
Mimaki 3DUJ-safe swatch pipeline (v3)
======================================

Produces (all flat in swatches/):
  swatch-{hex}-{name}.png     individual 128x128 swatches
  master-by-hue.png           square grid sorted by hue
  master-by-lightness.png     square grid sorted by L*
  master-by-chroma.png        square grid sorted by C*
  master-by-safety.png        square grid sorted by deltaE (most reliable first)
  master-hue-lightness.png    2D hue x lightness map
  manifest.txt                human-readable list
  manifest.csv                spreadsheet-friendly
  swatches.json               programmatic consumers
  swatches.ase                Adobe Swatch Exchange (Photoshop / Illustrator /
                              Substance Painter / Affinity)
  swatches.gpl                GIMP Palette (GIMP / Inkscape / Krita / Blender
                              via the GPL Palette Importer addon)

Naming (Option A):
  Chromatic: {lightness}-{chroma}-{hue}[-NN]
    lightness: ink, deep, mid, soft, pale     (5 bins by L*)
    chroma   : gray, dusty, fair, vivid       (4 bins by C*)
    hue      : 14 bins (red, vermilion, orange, amber, yellow, lime, green,
               jade, teal, cyan, blue, indigo, violet, magenta)
  Neutrals (incl. K-ramp): black, dark-gray, medium-gray, light-gray, white
  Collision suffix -02, -03, ... assigned by deltaE rank
  (cleanest name goes to the most reliable color in a collision group).

Gamut filter:
  sRGB -> CMYK ICC -> sRGB round-trip with black point compensation,
  keep if deltaE_2000 <= DELTA_E_MAX.

  Default profile: CoatedFOGRA39 (auto-discovered) acts as a CONSERVATIVE
  LOWEST-COMMON-DENOMINATOR for typical print gamuts. Note: Mimaki's spec
  claims the 3DUJ covers ~84% of Fogra39L, meaning the 3DUJ has its OWN
  gamut shape that partially overlaps Fogra39 — the 3DUJ can reach some
  saturated yellows/oranges/cyans that Fogra39 cannot, while Fogra39
  reaches some shadow areas the 3DUJ cannot. So filtering through Fogra39
  is conservative on average but loses some 3DUJ-only saturated colors.
  For best results, point this at Mimaki's actual 3DUJ ICC (shipped with
  RasterLink) via --profile PATH or MIMAKI_ICC_PATH env var.

Requirements: Pillow >= 9.2 (for ImageDraw.textlength / Font.getlength).
"""

import os
import csv
import json
import math
import shutil
import argparse
import platform
import subprocess
import colorsys
import warnings
from pathlib import Path
from PIL import Image, ImageCms, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path("swatches")

# Candidate sampling density in CIE LCh. These define how many colors we test,
# not which ones pass — see DELTA_E_MAX for the acceptance gate.
# default:
# LIGHTNESS_STEPS = 12
# CHROMA_STEPS    = 8
# HUE_STEPS       = 24


LIGHTNESS_STEPS = 8
CHROMA_STEPS    = 8
HUE_STEPS       = 24

# Maximum chroma sampled. CIELCh has no hard upper bound, but sRGB tops out
# near C* = 132 (pure red) and CMYK gamuts cap much lower. We sample to 76
# (was 90 in earlier versions). The reduction is a deliberate ~15% radial
# inset to partially compensate for the FOGRA39-vs-3DUJ shape mismatch
# documented in the research report: FOGRA39 is *not* a conservative subset
# of the 3DUJ gamut, so accepting saturated FOGRA39 colors over-promises
# what the 3DUJ can actually print. Raise this if you have a measured 3DUJ
# profile and want to recover real-world Mimaki saturation; lower it for
# even more conservative output.
# default:
# CHROMA_MAX = 76
CHROMA_MAX = 110

# Acceptance threshold for the round-trip gamut check, measured in CIEDE2000.
# ΔE₀₀ ≤ 1.0 is the current value. Reference points:
#   ~0.5  : LAB2000HL grid step used by Fraunhofer IGD for printer profiling
#   ~1.0  : current setting, well inside ISO 12647-7 proof tolerance (2.0)
#   ~1.5  : previous setting, still below Paravina dental perceptibility (1.7)
#   ~2.0  : ISO 12647-7:2016 average ΔE₀₀ contract-proof tolerance
#   ~3.0  : commonly cited "just noticeable difference" for general viewers
# Note: ΔE₀₀ ≤ 1.0 is NOT "imperceptible." It is "below dental-grade
# perceptibility threshold." Honest framing matters.
DELTA_E_MAX = .75

# default:
# K_RAMP_STEPS = 11
K_RAMP_STEPS = 7

# Rendering intent for the round-trip. RELATIVE_COLORIMETRIC is correct for
# gamut-testing: it clips out-of-gamut colors to the nearest boundary point,
# which is what we want to measure.
INTENT = ImageCms.Intent.RELATIVE_COLORIMETRIC

# Black point compensation: ON for production output, but the El Asaleh/Sharma
# research recommends OFF for gamut testing because BPC rescales the L* axis
# on both legs and inflates ΔE near the black point unrelated to gamut.
USE_BPC_FOR_TEST = False

# ---------------------------------------------------------------------------
# ICC profile discovery (ranked from most accurate -> least accurate proxy)
# ---------------------------------------------------------------------------

# Filename patterns matched in priority order. First match wins. The ranking
# reflects how well each profile approximates the actual Mimaki 3DUJ gamut.
#
# Tier 1 (best): Mimaki's own 3DUJ profile. Not publicly distributed by Mimaki
#                — only available through Profile Master 3 (MPM3) with hardware
#                access, or by request from Mimaki technical support.
# Tier 2: ECI ISOcoated_v2 — modern, well-built, widely used in European print.
#         Free download from www.eci.org.
# Tier 3: CoatedFOGRA39 — the report's reference proxy. Free from Adobe.
# Tier 4: JapanColor2001Coated — similar volume to Fogra39, different shape.
# Tier 5: USWebCoatedSWOP / RSWOP — Mimaki spec also references SWOP coverage.
# Tier 6: Anything else CMYK we can find. Wide variance in quality.
ICC_PROFILE_TIERS = [
    ("Mimaki 3DUJ (measured)",  ["*3DUJ*", "*Mimaki*3D*", "*MPM3*"]),
    ("ECI ISOcoated v2",        ["ISOcoated_v2_eci*", "ISOcoated_v2_300_eci*",
                                 "ISOcoated_v2*", "ISO Coated v2*"]),
    ("Coated FOGRA39",          ["CoatedFOGRA39*", "FOGRA39*", "ISOcoated_FOGRA39*"]),
    ("Japan Color 2001 Coated", ["JapanColor2001Coated*", "JapanColor*Coated*"]),
    ("US Web Coated SWOP",      ["USWebCoatedSWOP*", "RSWOP*", "SWOP*"]),
]


def _icc_search_locations():
    """Yield (location_label, directory_path) pairs to scan for .icc/.icm files,
    in priority order from most-likely-to-be-user-chosen to most generic."""
    here = Path(__file__).parent
    cwd  = Path.cwd()
    yield ("script folder", here)
    if cwd != here:
        yield ("current directory", cwd)
    system = platform.system()
    if system == "Windows":
        yield ("Windows system color folder", Path(r"C:\Windows\System32\spool\drivers\color"))
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            yield ("Windows user color folder", Path(local) / "Microsoft" / "Windows" / "Color")
        # Mimaki RasterLink installs sometimes drop ICCs here
        for p in [r"C:\Program Files\Mimaki", r"C:\Program Files (x86)\Mimaki",
                  r"C:\MimakiTools"]:
            if os.path.exists(p):
                yield ("Mimaki install folder", Path(p))
    elif system == "Darwin":
        yield ("macOS user ColorSync",   Path.home() / "Library/ColorSync/Profiles")
        yield ("macOS system ColorSync", Path("/Library/ColorSync/Profiles"))
        yield ("macOS bundled ColorSync",Path("/System/Library/ColorSync/Profiles"))
    else:  # Linux and friends
        yield ("system color/icc",       Path("/usr/share/color/icc"))
        yield ("texlive colorprofiles",
               Path("/usr/share/texlive/texmf-dist/tex/generic/colorprofiles"))
        yield ("user .color/icc",        Path.home() / ".color/icc")


def _all_icc_candidates():
    """Walk search locations and return [(path, location_label), ...] for every
    .icc/.icm file found. Deduplicates by real path."""
    seen = set()
    out = []
    for label, d in _icc_search_locations():
        if not d.exists():
            continue
        try:
            files = list(d.glob("*.icc")) + list(d.glob("*.icm")) + list(d.glob("*.ICC")) + list(d.glob("*.ICM"))
        except OSError:
            continue
        for f in files:
            try:
                rp = f.resolve()
            except OSError:
                rp = f
            if rp in seen:
                continue
            seen.add(rp)
            out.append((f, label))
    return out


def _is_cmyk_profile(path):
    """True if path opens as a CMYK ICC profile usable as a print destination."""
    try:
        prof = ImageCms.getOpenProfile(str(path))
        srgb = ImageCms.createProfile("sRGB")
        ImageCms.buildTransform(srgb, prof, "RGB", "CMYK")
        return True
    except (ImageCms.PyCMSError, OSError):
        return False


def find_icc_profile(verbose=True):
    """Pick the best available CMYK ICC profile by tiered priority.

    Returns (path_str, tier_label) or (None, None). When verbose, prints the
    candidates considered and explains the choice."""
    # 1. Explicit env override beats everything
    override = os.environ.get("MIMAKI_ICC_PATH")
    if override and os.path.exists(override) and _is_cmyk_profile(override):
        return override, "MIMAKI_ICC_PATH override"

    candidates = _all_icc_candidates()
    if verbose and candidates:
        print(f"Scanning {len(candidates)} ICC file(s) across the system...")

    # 2. Walk tiers in priority order
    for tier_label, patterns in ICC_PROFILE_TIERS:
        for path, location_label in candidates:
            name = path.name
            for pat in patterns:
                if path.match(pat) or path.match(pat.lower()) or _glob_match_ci(name, pat):
                    if _is_cmyk_profile(path):
                        if verbose:
                            print(f"  matched tier: {tier_label}")
                            print(f"  profile     : {path}  (from {location_label})")
                        return str(path), tier_label
    # 3. Last resort: any CMYK profile we can find
    for path, location_label in candidates:
        if _is_cmyk_profile(path):
            if verbose:
                print(f"  no preferred profile found; falling back to: {path}")
            return str(path), "fallback (unranked CMYK profile)"
    return None, None


def _glob_match_ci(name, pattern):
    """Case-insensitive glob match for a single filename."""
    import fnmatch
    return fnmatch.fnmatch(name.lower(), pattern.lower())


# ---------------------------------------------------------------------------
# ArgyllCMS detection + optional auto-install
# ---------------------------------------------------------------------------
# ArgyllCMS is the gold-standard open-source color tool. When available, we
# use `xicclu` for a true geometric gamut test instead of round-trip ΔE.
# The script works fine without it (PIL-only fallback); ArgyllCMS just makes
# the result more accurate.

def _find_argyll_binary(name="xicclu"):
    """Look for an ArgyllCMS binary on PATH or in common install locations."""
    # PATH first
    p = shutil.which(name)
    if p: return p
    # Common Windows installs
    if platform.system() == "Windows":
        for d in [r"C:\Program Files\ArgyllCMS\bin",
                  r"C:\Program Files (x86)\ArgyllCMS\bin",
                  r"C:\Argyll\bin",
                  r"C:\Tools\ArgyllCMS\bin"]:
            exe = Path(d) / f"{name}.exe"
            if exe.exists(): return str(exe)
        # Sometimes installed as Argyll_V*
        pf = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        if pf.exists():
            for sub in pf.glob("Argyll_V*"):
                exe = sub / "bin" / f"{name}.exe"
                if exe.exists(): return str(exe)
    elif platform.system() == "Darwin":
        for d in ["/usr/local/bin", "/opt/homebrew/bin"]:
            exe = Path(d) / name
            if exe.exists(): return str(exe)
        # Sometimes installed as /Applications/Argyll_V*/bin/
        for sub in Path("/Applications").glob("Argyll_V*"):
            exe = sub / "bin" / name
            if exe.exists(): return str(exe)
    else:  # Linux
        for d in ["/usr/bin", "/usr/local/bin", "/opt/argyll/bin"]:
            exe = Path(d) / name
            if exe.exists(): return str(exe)
    return None


def install_argyll(force=False):
    """Attempt to install ArgyllCMS via the system package manager.
    NEVER called silently — only on explicit --install-argyll opt-in.
    Returns True if install succeeded, False otherwise."""
    system = platform.system()
    print(f"Attempting to install ArgyllCMS on {system}...")
    try:
        if system == "Windows":
            # winget is bundled with Windows 11 and recent Windows 10. Falls
            # back to chocolatey if winget unavailable.
            if shutil.which("winget"):
                cmd = ["winget", "install", "--id", "ArgyllCMS.ArgyllCMS", "-e",
                       "--accept-source-agreements", "--accept-package-agreements"]
            elif shutil.which("choco"):
                cmd = ["choco", "install", "argyllcms", "-y"]
            else:
                print("  Neither winget nor choco found.")
                print("  Manual install: download from https://www.argyllcms.com/")
                return False
        elif system == "Darwin":
            if shutil.which("brew"):
                cmd = ["brew", "install", "argyll"]
            else:
                print("  Homebrew not found.")
                print("  Install Homebrew first: https://brew.sh/")
                print("  Or manual install: https://www.argyllcms.com/")
                return False
        else:  # Linux
            if shutil.which("apt-get"):
                cmd = ["sudo", "apt-get", "install", "-y", "argyll"]
            elif shutil.which("dnf"):
                cmd = ["sudo", "dnf", "install", "-y", "argyllcms"]
            elif shutil.which("pacman"):
                cmd = ["sudo", "pacman", "-S", "--noconfirm", "argyll"]
            else:
                print("  No supported package manager found.")
                print("  Manual install: https://www.argyllcms.com/")
                return False
        print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode == 0:
            print("  ArgyllCMS installed.")
            return True
        print(f"  Install command exited with code {result.returncode}.")
        return False
    except (subprocess.SubprocessError, OSError) as e:
        print(f"  Install failed: {e}")
        return False


def argyll_in_gamut(icc_path, lab_values, xicclu_path):
    """Run ArgyllCMS xicclu to test if Lab points are in gamut.
    Returns a list of bools, same length as lab_values.
    lab_values: list of (L, a, b) tuples.

    xicclu -fb -ir -pl -s 100 <profile> reads Lab triples on stdin, writes
    the round-trip back to Lab and a (clip) suffix if the value was out
    of gamut at the destination."""
    # Build stdin: one "L a b" line per value
    stdin_text = "\n".join(f"{L} {a} {b}" for L, a, b in lab_values) + "\n"
    # -fb: backward, -ir: relative colorimetric, -pl: Lab input/output, -s 100: scale Lab
    cmd = [xicclu_path, "-fb", "-ir", "-pl", "-s", "100", icc_path]
    try:
        result = subprocess.run(cmd, input=stdin_text, capture_output=True,
                                text=True, timeout=120)
    except (subprocess.SubprocessError, OSError) as e:
        print(f"  xicclu failed: {e}; falling back to round-trip ΔE")
        return None
    if result.returncode != 0:
        # xicclu sometimes emits warnings but still produces output
        if not result.stdout.strip():
            print(f"  xicclu returned {result.returncode}; falling back")
            return None
    in_gamut = []
    for line in result.stdout.strip().splitlines():
        # Lines look like: "L a b -> C M Y K [ DE2K = 0.000 ] (clip)"
        # We just need to know if "(clip)" is present.
        if not line.strip(): continue
        in_gamut.append("(clip)" not in line.lower())
    if len(in_gamut) != len(lab_values):
        # Output didn't match expected count; bail
        return None
    return in_gamut


def sanity_check_profile(icc_path, to_cmyk, to_rgb, to_lab):
    """Run a few known-good colors through the profile and check round-trip ΔE.
    Any CMYK profile worth using should round-trip these colors with ΔE well
    below 5. If they don't, the profile's reverse (B2A) table is broken — we
    warn the user before producing a garbage result like 8 'safe' colors."""
    test_colors = [
        ((255, 128, 0),  "mid orange"),
        ((128, 200, 0),  "lime green"),
        ((0, 180, 90),   "mid green"),
        ((180, 0, 180),  "muted magenta"),
        ((255, 220, 0),  "yellow"),
        ((100, 60, 30),  "brown"),
    ]
    src = Image.new("RGB", (1, len(test_colors)))
    src.putdata([c[0] for c in test_colors])
    cmyk    = ImageCms.applyTransform(src, to_cmyk)
    back    = ImageCms.applyTransform(cmyk, to_rgb)
    lab_src = ImageCms.applyTransform(src,  to_lab)
    lab_bk  = ImageCms.applyTransform(back, to_lab)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ls = list(lab_src.getdata())
        lb = list(lab_bk.getdata())
    def dec(p): return (p[0]*100/255, p[1]-128, p[2]-128)
    dEs = [delta_e_2000(dec(ls[i]), dec(lb[i])) for i in range(len(test_colors))]
    worst = max(dEs)
    if worst > 5.0:
        print()
        print(f"!!! WARNING: this ICC profile may have a broken reverse table.")
        print(f"    Test round-trip ΔE values:")
        for (rgb, name), de in zip(test_colors, dEs):
            flag = " <-- bad" if de > 5.0 else ""
            print(f"      {name:20s} RGB{rgb}  ΔE={de:.2f}{flag}")
        print(f"    A correctly-built profile should keep all of these under ΔE ~3.")
        print(f"    Your result will likely have very few 'safe' colors.")
        print(f"    Recommended fix: download Adobe's free CoatedFOGRA39.icc:")
        print(f"      https://www.adobe.com/support/downloads/iccprofiles/")
        print(f"    Drop it next to this script and re-run.")
        print()
        return False
    return True


# These are set by main() at runtime — keep as module-level placeholders for
# type clarity and so functions called pre-main don't NameError.
ICC_PATH = None
XICCLU_PATH = None

INDIVIDUAL_PX = 128
TILE_PX       = 240
BORDER_PX     = 0     # no separator between swatches
TITLE_BAND    = 90

# ---------------------------------------------------------------------------
# Color math: CIE LCh -> sRGB, deltaE 2000
# ---------------------------------------------------------------------------

def lch_to_lab(L, C, h_deg):
    h = math.radians(h_deg)
    return (L, C * math.cos(h), C * math.sin(h))

def lab_to_xyz(L, a, b, ref=(0.95047, 1.0, 1.08883)):
    fy = (L + 16) / 116
    fx = a / 500 + fy
    fz = fy - b / 200
    inv = lambda t: t**3 if t**3 > 0.008856 else (t - 16/116) / 7.787
    return ref[0] * inv(fx), ref[1] * inv(fy), ref[2] * inv(fz)

def xyz_to_linear(X, Y, Z):
    return ( 3.2404542*X - 1.5371385*Y - 0.4985314*Z,
            -0.9692660*X + 1.8760108*Y + 0.0415560*Z,
             0.0556434*X - 0.2040259*Y + 1.0572252*Z)

def linear_to_srgb(c):
    return 12.92*c if c <= 0.0031308 else 1.055*(c**(1/2.4)) - 0.055

def lch_to_srgb8(L, C, h):
    r, g, b = xyz_to_linear(*lab_to_xyz(*lch_to_lab(L, C, h)))
    # Allow a small tolerance for float rounding (a candidate at r=1.00003
    # is a perfectly valid sRGB color, just on the edge). We clamp into [0,1]
    # below. The induced hue shift at this magnitude is sub-perceptual.
    if min(r, g, b) < -0.01 or max(r, g, b) > 1.01:
        return None
    clamp = lambda x: max(0.0, min(1.0, x))
    return (round(linear_to_srgb(clamp(r))*255),
            round(linear_to_srgb(clamp(g))*255),
            round(linear_to_srgb(clamp(b))*255))

def delta_e_2000(lab1, lab2):
    L1, a1, b1 = lab1; L2, a2, b2 = lab2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    avg_C = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(avg_C**7/(avg_C**7 + 25**7))) if avg_C else 0
    a1p, a2p = (1+G)*a1, (1+G)*a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    avg_Cp = (C1p + C2p) / 2
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if (a1p or b1) else 0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if (a2p or b2) else 0
    dLp = L2 - L1
    dCp = C2p - C1p
    dhp = h2p - h1p
    if abs(dhp) > 180: dhp -= 360 * (1 if dhp > 0 else -1)
    dHp = 2*math.sqrt(C1p*C2p)*math.sin(math.radians(dhp/2)) if (C1p and C2p) else 0
    avg_L = (L1 + L2) / 2
    avg_hp = (h1p + h2p) / 2
    if abs(h1p - h2p) > 180: avg_hp += 180
    avg_hp %= 360
    T = (1 - 0.17*math.cos(math.radians(avg_hp - 30))
           + 0.24*math.cos(math.radians(2*avg_hp))
           + 0.32*math.cos(math.radians(3*avg_hp + 6))
           - 0.20*math.cos(math.radians(4*avg_hp - 63)))
    SL = 1 + (0.015*(avg_L-50)**2) / math.sqrt(20 + (avg_L-50)**2)
    SC = 1 + 0.045*avg_Cp
    SH = 1 + 0.015*avg_Cp*T
    dtheta = 30*math.exp(-((avg_hp - 275)/25)**2)
    RC = 2*math.sqrt(avg_Cp**7/(avg_Cp**7 + 25**7))
    RT = -math.sin(math.radians(2*dtheta))*RC
    return math.sqrt((dLp/SL)**2 + (dCp/SC)**2 + (dHp/SH)**2
                     + RT*(dCp/SC)*(dHp/SH))

# ---------------------------------------------------------------------------
# Naming (Option A)
# ---------------------------------------------------------------------------

# 14 hue bins, each ~25.7 degrees wide in Lab hue angle space.
HUE_NAMES = ["red", "vermilion", "orange", "amber", "yellow", "lime",
             "green", "jade", "teal", "cyan", "blue", "indigo",
             "violet", "magenta"]

def hue_bin(lab_h_deg):
    """Lab hue angle (atan2(b,a) in degrees, 0..360) -> hue name.
    Red sits near 30 deg in Lab, so we rotate the bins to align."""
    # Shift so 'red' starts at -13 deg (i.e. spans ~17 to 43 in Lab hue)
    shifted = (lab_h_deg + 13) % 360
    idx = int(shifted / (360 / len(HUE_NAMES)))
    return HUE_NAMES[idx]

def lightness_bin(L):
    if L < 20:  return "ink"
    if L < 40:  return "deep"
    if L < 60:  return "mid"
    if L < 80:  return "soft"
    return "pale"

def chroma_bin(C):
    if C < 15:  return "gray"
    if C < 35:  return "dusty"
    if C < 60:  return "fair"
    return "vivid"

def neutral_name(L):
    if L < 15:  return "black"
    if L < 38:  return "dark-gray"
    if L < 62:  return "medium-gray"
    if L < 85:  return "light-gray"
    return "white"

def base_name(L, a, b):
    """Build the base literal name from Lab coordinates."""
    C = math.hypot(a, b)
    if C < 6:
        return neutral_name(L)
    h_deg = math.degrees(math.atan2(b, a)) % 360
    return f"{lightness_bin(L)}-{chroma_bin(C)}-{hue_bin(h_deg)}"

# NOTE: previous versions of this script injected canonical RGB-primary anchors
# (#FF0000, #00FF00, etc.) so they would be named "red", "green", etc. if they
# passed the gamut filter. The research review correctly flagged this as broken:
# the pure sRGB primaries sit far outside any CMYK gamut (ΔE > 10 from the
# FOGRA39 boundary), so either they always fail the filter (useless) or they
# bypass it and silently weaken the safety guarantee on the most named colors
# in the deliverable. Removed. Names now come purely from the descriptive
# system on Lab-of-the-actually-printable-color. Cleaner, no false promises.

def assign_unique_names(swatches):
    """Mutates swatches in place: ensures every 'name' is globally unique.
    Within a collision group, the lowest-ΔE member keeps the bare base name;
    subsequent duplicates get -02, -03, ..."""
    by_base = {}
    for s in swatches:
        by_base.setdefault(s["base_name"], []).append(s)
    for base, group in by_base.items():
        group.sort(key=lambda s: s["delta_e"])
        for i, s in enumerate(group):
            s["name"] = base if i == 0 else f"{base}-{i+1:02d}"

# ---------------------------------------------------------------------------
# Palette format writers (.ase, .gpl)
# ---------------------------------------------------------------------------

def write_gpl(path, swatches, palette_title="palette"):
    """GIMP Palette format. Used by GIMP, Inkscape, Krita, and Blender (via
    the GPL Palette Importer add-on). Plain text, very forgiving.

    Format:
        GIMP Palette
        Name: <title>
        Columns: 8
        #
        R   G   B   Name
        ...
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write("GIMP Palette\n")
        f.write(f"Name: {palette_title}\n")
        f.write("Columns: 8\n")
        f.write("# Generated by mimaki_swatches.py\n")
        f.write("# https://github.com/(your repo here)\n")
        for s in swatches:
            r, g, b = s["rgb"]
            f.write(f"{r:3d} {g:3d} {b:3d}\t{s['name']}\n")


def write_ase(path, swatches, palette_title="palette"):
    """Adobe Swatch Exchange (.ase) — binary big-endian format used by
    Photoshop, Illustrator, InDesign, Affinity Suite, Substance Painter,
    and many others. Specification reverse-engineered from public sources
    (carl.camera/sereal/aseutil, the format has no official public spec).

    Layout:
      Magic        "ASEF"                              4 bytes
      Version      0x0001 0x0000                       4 bytes
      Block count  uint32 big-endian                   4 bytes
      Repeat: blocks
        Block type   uint16 (0xC001=group start, 0xC002=group end, 0x0001=color)
        Block length uint32 (size of remaining block data in bytes)
        Block body:
          For group-start: utf-16be name (len uint16, then name+null)
          For color:       utf-16be name, color model "RGB ", 3 float32 BE,
                           color type uint16 (0=global 1=spot 2=normal)
    """
    import struct
    def encode_name(name):
        # UTF-16 BE, null-terminated. Length field is char-count INCLUDING null.
        s = (name + "\x00").encode("utf-16-be")
        n_chars = len(s) // 2
        return struct.pack(">H", n_chars) + s

    blocks = []
    # Optional: group start
    grp_name = encode_name(palette_title)
    blocks.append((0xC001, grp_name))
    # Color blocks
    for s in swatches:
        body = encode_name(s["name"])
        body += b"RGB "
        r, g, b = (c / 255.0 for c in s["rgb"])
        body += struct.pack(">fff", r, g, b)
        body += struct.pack(">H", 2)   # color type: normal
        blocks.append((0x0001, body))
    # Group end
    blocks.append((0xC002, b""))

    with open(path, "wb") as f:
        f.write(b"ASEF")
        f.write(struct.pack(">HH", 1, 0))           # version 1.0
        f.write(struct.pack(">I", len(blocks)))     # block count
        for btype, body in blocks:
            f.write(struct.pack(">H", btype))
            f.write(struct.pack(">I", len(body)))
            f.write(body)


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def get_font(size):
    for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "C:/Windows/Fonts/consola.ttf",       # Windows monospace
                 "C:/Windows/Fonts/consolab.ttf",      # Windows mono-bold
                 "/Library/Fonts/Menlo.ttc",           # macOS monospace
                 "/Library/Fonts/Arial.ttf",
                 "C:/Windows/Fonts/arial.ttf"]:
        if os.path.exists(path):
            try: return ImageFont.truetype(path, size)
            except OSError: continue
    return ImageFont.load_default()

def text_color_for(rgb):
    Y = 0.2126*rgb[0] + 0.7152*rgb[1] + 0.0722*rgb[2]
    return (15, 15, 18) if Y > 140 else (245, 245, 248)

def draw_cell(draw, x, y, w, h, swatch, name_font, mono_font):
    # color fill
    draw.rectangle([x, y, x + w - 1, y + h - 1], fill=swatch["rgb"])
    tc = text_color_for(swatch["rgb"])
    r, g, b = swatch["rgb"]
    c, m, ye, k = swatch["cmyk"]
    pad = 10
    line1 = swatch["name"]
    line2 = f"#{swatch['hex'].upper()}"
    line3 = f"RGB {r:3d} {g:3d} {b:3d}"
    line4 = f"CMYK {c:3d} {m:3d} {ye:3d} {k:3d}"
    max_w = w - 2*pad
    while line1 and name_font.getlength(line1) > max_w:
        line1 = line1[:-1]
    if line1 != swatch["name"] and len(line1) > 1:
        line1 = line1[:-1] + "..."
    draw.text((x + pad, y + pad),                 line1, fill=tc, font=name_font)
    draw.text((x + pad, y + pad + 26),            line2, fill=tc, font=mono_font)
    draw.text((x + pad, y + h - pad - 38),        line3, fill=tc, font=mono_font)
    draw.text((x + pad, y + h - pad - 20),        line4, fill=tc, font=mono_font)

def draw_square_master(swatches, path, title, fonts):
    """Square grid of cells (ceil(sqrt(N)) per side), no canvas padding.
    Final image: grid_w wide, (title_band + grid_w) tall."""
    n = len(swatches)
    if n == 0: return
    side = math.ceil(math.sqrt(n))
    grid_w = side * TILE_PX + (side + 1) * BORDER_PX
    img_w  = grid_w
    img_h  = TITLE_BAND + grid_w
    img = Image.new("RGB", (img_w, img_h), (32, 32, 38))
    draw = ImageDraw.Draw(img)
    title_font, name_font, mono_font = fonts
    draw.text((20, 24), f"{title}  ({n} colors)",
              fill=(245, 245, 248), font=title_font)
    draw.text((20, 60),
              f"profile: {os.path.basename(ICC_PATH)}   threshold: dE <= {DELTA_E_MAX}",
              fill=(170, 170, 180), font=mono_font)
    for i, s in enumerate(swatches):
        col = i % side
        row = i // side
        x = BORDER_PX + col * (TILE_PX + BORDER_PX)
        y = TITLE_BAND + BORDER_PX + row * (TILE_PX + BORDER_PX)
        draw_cell(draw, x, y, TILE_PX, TILE_PX, s, name_font, mono_font)
    img.save(path, optimize=True)

def draw_hue_lightness_master(swatches, path, title, fonts):
    """2D layout: hue across, lightness down. One swatch per bucket (lowest
    deltaE wins ties). Uses Lab coordinates for consistency with naming."""
    HB, LB = 18, 10
    grid = {}
    for s in swatches:
        L, a, b = s["lab"]
        chroma = math.hypot(a, b)
        if chroma < 6:
            # Near-neutrals don't have a meaningful hue; park them in the
            # leftmost column where the sort lands them naturally.
            hb = 0
        else:
            h_deg = math.degrees(math.atan2(b, a)) % 360
            hb = min(int(h_deg / 360 * HB), HB - 1)
        lb = min(int(L / 100 * LB), LB - 1)
        key = (hb, lb)
        if key not in grid or s["delta_e"] < grid[key]["delta_e"]:
            grid[key] = s
    title_font, name_font, mono_font = fonts
    grid_w = HB * TILE_PX + (HB + 1) * BORDER_PX
    grid_h = LB * TILE_PX + (LB + 1) * BORDER_PX
    img_w = grid_w
    img_h = TITLE_BAND + grid_h
    img = Image.new("RGB", (img_w, img_h), (32, 32, 38))
    draw = ImageDraw.Draw(img)
    draw.text((20, 24), f"{title}  (hue -> across, lightness -> down)",
              fill=(245, 245, 248), font=title_font)
    draw.text((20, 60),
              f"profile: {os.path.basename(ICC_PATH)}   threshold: dE <= {DELTA_E_MAX}",
              fill=(170, 170, 180), font=mono_font)
    for (hb, lb), s in grid.items():
        x = BORDER_PX + hb * (TILE_PX + BORDER_PX)
        y = TITLE_BAND + BORDER_PX + (LB - 1 - lb) * (TILE_PX + BORDER_PX)
        draw_cell(draw, x, y, TILE_PX, TILE_PX, s, name_font, mono_font)
    img.save(path, optimize=True)

# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    global ICC_PATH, DELTA_E_MAX, OUTPUT_DIR, XICCLU_PATH
    ICC_PATH = None
    XICCLU_PATH = None

    ap = argparse.ArgumentParser(
        description="Generate a Mimaki 3DUJ-safe RGB swatch library.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Profile fallback order (most accurate -> least):\n"
            "  1. --profile PATH or MIMAKI_ICC_PATH env var\n"
            "  2. Mimaki 3DUJ profile (if found by name)\n"
            "  3. ECI ISOcoated v2  4. Coated FOGRA39  5. Japan Color 2001\n"
            "  6. US Web Coated SWOP / RSWOP\n"
            "  7. Any other CMYK profile available\n"))
    ap.add_argument("--profile", metavar="PATH",
                    help="ICC profile to use (overrides auto-discovery).")
    ap.add_argument("--delta-e", type=float, metavar="N",
                    help=f"ΔE₀₀ acceptance threshold (default {DELTA_E_MAX}).")
    ap.add_argument("--chroma-max", type=float, metavar="N",
                    help=f"Maximum CIELCh chroma to sample (default {CHROMA_MAX}).")
    ap.add_argument("--out", metavar="DIR",
                    help=f"Output directory (default '{OUTPUT_DIR}').")
    ap.add_argument("--no-argyll", action="store_true",
                    help="Skip ArgyllCMS entirely, use PIL-only round-trip ΔE.")
    ap.add_argument("--yes", "-y", action="store_true",
                    help="Auto-answer 'yes' to the ArgyllCMS install prompt "
                         "(useful for scripted/CI runs).")
    args = ap.parse_args()

    # 1. Pick ICC profile
    if args.profile:
        if not os.path.exists(args.profile):
            raise SystemExit(f"ERROR: --profile path does not exist: {args.profile}")
        if not _is_cmyk_profile(args.profile):
            raise SystemExit(f"ERROR: --profile is not a CMYK profile: {args.profile}")
        ICC_PATH = args.profile
        tier_label = "--profile CLI override"
    else:
        ICC_PATH, tier_label = find_icc_profile(verbose=True)

    if args.delta_e is not None:
        DELTA_E_MAX = args.delta_e
    if args.chroma_max is not None:
        globals()["CHROMA_MAX"] = args.chroma_max
    if args.out:
        OUTPUT_DIR = Path(args.out)
    OUTPUT_DIR.mkdir(exist_ok=True)
    # Remove stale swatch files from previous runs — a name might change between
    # runs (different profile, different threshold), and we don't want orphans.
    for p in OUTPUT_DIR.glob("swatch-*.png"):
        try: p.unlink()
        except OSError: pass

    if not ICC_PATH:
        print("ERROR: No CMYK ICC profile found on this system.")
        print()
        print("Free options to install one (any of these will work):")
        print()
        print("  Option 1 (recommended): Adobe ICC Profiles — free, includes")
        print("  CoatedFOGRA39.icc which is what this script's research uses")
        print("  as the reference proxy.")
        print("    https://www.adobe.com/support/downloads/iccprofiles/")
        print("    Extract the .zip, find 'CMYK Profiles/CoatedFOGRA39.icc',")
        print("    drop it next to this script.")
        print()
        print("  Option 2: ECI ISOcoated_v2_eci.icc — modern Fogra-derived,")
        print("  used widely in European print.")
        print("    https://www.eci.org/doku.php?id=en:colourstandards:offset")
        print()
        print("  Option 3: Locate a Mimaki ICC if you have RasterLink/MPM3.")
        if platform.system() == "Windows":
            print("    Check: C:\\Windows\\System32\\spool\\drivers\\color\\")
            print("           C:\\Program Files\\Mimaki\\")
        elif platform.system() == "Darwin":
            print("    Check: /Library/ColorSync/Profiles/")
            print("           ~/Library/ColorSync/Profiles/")
        else:
            print("    Check: /usr/share/color/icc/")
        print()
        print("  Option 4: Point MIMAKI_ICC_PATH env var at a .icc/.icm you have.")
        raise SystemExit(1)

    # 2. Find ArgyllCMS — used for a true geometric in-gamut test alongside
    # the PIL round-trip ΔE. If not found, prompt once to install it.
    if not args.no_argyll:
        XICCLU_PATH = _find_argyll_binary("xicclu")
        if XICCLU_PATH:
            print(f"ArgyllCMS xicclu  : {XICCLU_PATH}")
        else:
            # Not installed — ask the user once, interactively.
            sys_name = platform.system()
            install_cmds = {
                "Windows": "winget install --id ArgyllCMS.ArgyllCMS",
                "Darwin":  "brew install argyll",
            }
            if sys_name not in install_cmds:
                if shutil.which("apt-get"):
                    install_cmds[sys_name] = "sudo apt-get install -y argyll"
                elif shutil.which("dnf"):
                    install_cmds[sys_name] = "sudo dnf install -y argyllcms"
                elif shutil.which("pacman"):
                    install_cmds[sys_name] = "sudo pacman -S --noconfirm argyll"
                else:
                    install_cmds[sys_name] = None

            cmd_hint = install_cmds.get(sys_name)
            print()
            print("ArgyllCMS not found. It provides a more accurate geometric")
            print("in-gamut test alongside the PIL round-trip ΔE check.")
            if cmd_hint:
                print(f"Install command   : {cmd_hint}")
            else:
                print("Manual download   : https://www.argyllcms.com/")
            print()

            # Use --yes flag for non-interactive (scripted) runs.
            if args.yes:
                answer = "y"
                print("--yes flag set, proceeding with install.")
            else:
                try:
                    answer = input("Install ArgyllCMS now? [Y/n] ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    answer = "n"
                    print()

            if answer in ("", "y", "yes"):
                if install_argyll():
                    XICCLU_PATH = _find_argyll_binary("xicclu")
                    if XICCLU_PATH:
                        print(f"ArgyllCMS ready   : {XICCLU_PATH}")
                    else:
                        print("ArgyllCMS installed but xicclu not found on PATH.")
                        print("You may need to open a new terminal so PATH updates.")
                        print("Continuing with PIL-only mode for this run.")
                else:
                    print("ArgyllCMS install did not complete. Continuing PIL-only.")
            else:
                print("Skipping ArgyllCMS. Using PIL-only round-trip ΔE.")
                print("Re-run without --no-argyll after installing to enable it.")

        if not XICCLU_PATH:
            print("ArgyllCMS         : PIL-only mode (round-trip ΔE)")
        print()

    print(f"ICC profile       : {ICC_PATH}")
    print(f"Profile tier      : {tier_label}")
    print(f"ΔE₀₀ threshold    : {DELTA_E_MAX}")
    print(f"Chroma cap        : {CHROMA_MAX}")
    print(f"BPC during test   : {'on' if USE_BPC_FOR_TEST else 'off (recommended)'}")

    srgb_p  = ImageCms.createProfile("sRGB")
    lab_p   = ImageCms.createProfile("LAB")
    print_p = ImageCms.getOpenProfile(ICC_PATH)
    # Black point compensation: ON for production output, OFF for gamut testing.
    # BPC rescales the L* axis on both legs of a round-trip and inflates ΔE
    # near the black point in ways unrelated to gamut membership. The El Asaleh
    # & Sharma research on in-gamut methodology recommends disabling BPC for
    # this specific use. See USE_BPC_FOR_TEST in the config block.
    flags = 0
    if USE_BPC_FOR_TEST:
        try:
            flags = int(ImageCms.Flags.BLACKPOINTCOMPENSATION)
        except AttributeError:
            flags = ImageCms.FLAGS["BLACKPOINTCOMPENSATION"]
    to_cmyk = ImageCms.buildTransform(srgb_p,  print_p, "RGB",  "CMYK",
                                      renderingIntent=INTENT, flags=flags)
    to_rgb  = ImageCms.buildTransform(print_p, srgb_p,  "CMYK", "RGB",
                                      renderingIntent=INTENT, flags=flags)
    to_lab  = ImageCms.buildTransform(srgb_p,  lab_p,   "RGB",  "LAB")

    # 1. Sample candidates in LCh
    print("Sampling LCh candidates...")
    cand = set()
    for li in range(LIGHTNESS_STEPS):
        L = 10 + 80 * li / (LIGHTNESS_STEPS - 1)
        for ci in range(CHROMA_STEPS):
            C = CHROMA_MAX * ci / (CHROMA_STEPS - 1)
            for hi in range(HUE_STEPS):
                rgb = lch_to_srgb8(L, C, 360 * hi / HUE_STEPS)
                if rgb: cand.add(rgb)
                if C == 0: break

    cand_list = sorted(cand)
    print(f"  {len(cand_list)} unique sRGB candidates")

    # 2. Round-trip through CMYK and measure ΔE₀₀.
    # The round-trip ΔE is one of three recognized in-gamut tests. It is not
    # a strict in/out boolean — it's a "robust interior" filter: low ΔE means
    # the color sits comfortably inside the destination gamut, high ΔE means
    # the color is at or beyond the boundary. We use ΔE ≤ DELTA_E_MAX as the
    # acceptance gate. When ArgyllCMS is available, we ALSO run xicclu for
    # a true geometric in-gamut test and intersect the two results.
    print("Round-tripping and measuring deltaE...")
    src      = Image.new("RGB", (1, len(cand_list)))
    src.putdata(cand_list)
    cmyk_img = ImageCms.applyTransform(src, to_cmyk)
    back_img = ImageCms.applyTransform(cmyk_img, to_rgb)
    lab_s_img = ImageCms.applyTransform(src,      to_lab)
    lab_b_img = ImageCms.applyTransform(back_img, to_lab)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        cmyk_px = list(cmyk_img.getdata())
        lab_s   = list(lab_s_img.getdata())
        lab_b   = list(lab_b_img.getdata())

    def dec_lab(p): return (p[0]*100/255, p[1]-128, p[2]-128)

    results = []
    for i, rgb in enumerate(cand_list):
        lab1 = dec_lab(lab_s[i])
        lab2 = dec_lab(lab_b[i])
        de = delta_e_2000(lab1, lab2)
        results.append({
            "rgb": rgb,
            "hex": f"{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}",
            "cmyk": tuple(int(round(v * 100 / 255)) for v in cmyk_px[i]),
            "lab":  lab1,
            "delta_e": round(de, 3),
            "base_name": base_name(*lab1),
        })

    # Optional second filter: ArgyllCMS geometric in-gamut test.
    if XICCLU_PATH:
        print(f"  cross-checking with ArgyllCMS xicclu ({XICCLU_PATH})...")
        in_gamut = argyll_in_gamut(ICC_PATH, [r["lab"] for r in results], XICCLU_PATH)
        if in_gamut is not None:
            for r, ig in zip(results, in_gamut):
                r["argyll_in_gamut"] = ig
            argyll_pass = sum(1 for r in results if r.get("argyll_in_gamut"))
            print(f"  ArgyllCMS in-gamut: {argyll_pass}/{len(results)}")

    # Acceptance gate: ΔE ≤ DELTA_E_MAX AND (if available) ArgyllCMS agrees.
    # Both signals are noisy in different ways; the intersection is conservative.
    def is_safe(r):
        if r["delta_e"] > DELTA_E_MAX:
            return False
        if "argyll_in_gamut" in r and not r["argyll_in_gamut"]:
            return False
        return True
    safe = [r for r in results if is_safe(r)]
    print(f"  safe: {len(safe)}    rejected: {len(results)-len(safe)}")

    # 3. K-ramp — pure grays through the CMYK profile. Round-trip ΔE is NOT
    # zero in general: warm/cool drift along the gray axis is real, especially
    # at quarter-tones. We measure it the same way as chromatic colors.
    print("Building K-ramp...")
    k_values = []
    for i in range(K_RAMP_STEPS):
        v = round((1 - i/(K_RAMP_STEPS-1)) * 255)
        k_values.append((v, v, v))
    k_src = Image.new("RGB", (1, K_RAMP_STEPS))
    k_src.putdata(k_values)
    k_cmyk = ImageCms.applyTransform(k_src, to_cmyk)
    k_back = ImageCms.applyTransform(k_cmyk, to_rgb)
    k_lab_s = ImageCms.applyTransform(k_src,  to_lab)
    k_lab_b = ImageCms.applyTransform(k_back, to_lab)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        k_cmyk_px  = list(k_cmyk.getdata())
        k_lab_s_px = list(k_lab_s.getdata())
        k_lab_b_px = list(k_lab_b.getdata())
    safe_hexes = {s["hex"] for s in safe}
    k_ramp = []
    for i, rgb in enumerate(k_values):
        hx = f"{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        if hx in safe_hexes:
            continue   # already represented in the safe set
        lab1 = dec_lab(k_lab_s_px[i])
        lab2 = dec_lab(k_lab_b_px[i])
        de = delta_e_2000(lab1, lab2)
        k_pct = round(i * 100 / (K_RAMP_STEPS - 1))
        k_ramp.append({
            "rgb": rgb,
            "hex": hx,
            "cmyk": tuple(int(round(v*100/255)) for v in k_cmyk_px[i]),
            "lab":  lab1,
            "delta_e": round(de, 3),
            "base_name": f"k-{k_pct:03d}",
            "is_k_ramp": True,
            "k_percent": k_pct,
        })
    print(f"  k-ramp entries added (not duplicates of safe set): {len(k_ramp)}")

    all_sw = safe + k_ramp
    print(f"  total swatches: {len(all_sw)}")

    # 4. Assign unique names
    print("Assigning unique names...")
    # K-ramp names like 'k-000' already unique; only collisions are within safe set
    # Run unique-name pass on safe; K-ramp already unique by k_pct
    assign_unique_names(safe)
    for s in k_ramp:
        s["name"] = s["base_name"]
    # Sanity check
    names = [s["name"] for s in all_sw]
    assert len(names) == len(set(names)), "Name collision after uniqueness pass"

    # 5. Sort keys. Hue sort uses Lab hue (atan2(b,a)) so that the visual
    # ordering matches the hue bins used in naming. Lightness sort uses Lab L*
    # for the same reason. We only fall back to HLS for the "is this gray?"
    # gate (chroma threshold) since it's just a binary categorization.
    def hls(rgb): return colorsys.rgb_to_hls(rgb[0]/255, rgb[1]/255, rgb[2]/255)
    def lab_hue_deg(lab):
        _, a, b = lab
        return math.degrees(math.atan2(b, a)) % 360
    def lab_chroma(lab):
        _, a, b = lab
        return math.hypot(a, b)
    def hue_key(s):
        # K-ramp and near-neutrals trail at the end of the hue sort
        if s.get("is_k_ramp") or lab_chroma(s["lab"]) < 6:
            return (2, s["lab"][0])   # sort by L*
        return (0, lab_hue_deg(s["lab"]), s["lab"][0])
    def light_key(s):
        return (s["lab"][0], lab_hue_deg(s["lab"]))
    def chroma_key(s):
        return (lab_chroma(s["lab"]), s["lab"][0])
    def safety_key(s):
        return (s["delta_e"], -s["lab"][0])

    sorts = {
        "by-hue":       sorted(all_sw, key=hue_key),
        "by-lightness": sorted(all_sw, key=light_key),
        "by-chroma":    sorted(all_sw, key=chroma_key),
        "by-safety":    sorted(all_sw, key=safety_key),
    }

    # 6. Manifests
    print("Writing manifests...")
    with open(OUTPUT_DIR / "manifest.txt", "w", encoding="utf-8") as f:
        f.write("# Mimaki 3DUJ-safe color manifest\n")
        f.write(f"# ICC profile     : {ICC_PATH}\n")
        f.write(f"# deltaE threshold: {DELTA_E_MAX}\n")
        f.write(f"# Safe chromatic  : {len(safe)}\n")
        f.write(f"# K-ramp added    : {len(k_ramp)}\n")
        f.write(f"# Total swatches  : {len(all_sw)}\n")
        f.write("# Sorted by hue.\n")
        f.write("# Columns: NAME | #HEX | RGB | CMYK% | dE\n")
        f.write("#" + "-"*92 + "\n")
        for s in sorts["by-hue"]:
            r, g, b = s["rgb"]; c, m, y, k = s["cmyk"]
            f.write(f"{s['name']:<26} | #{s['hex'].upper()} | "
                    f"RGB({r:3d},{g:3d},{b:3d}) | "
                    f"CMYK({c:3d},{m:3d},{y:3d},{k:3d})% | "
                    f"dE={s['delta_e']:.2f}\n")

    with open(OUTPUT_DIR / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name","hex","r","g","b","c","m","y","k","delta_e","filename"])
        for s in sorts["by-hue"]:
            r, g, b = s["rgb"]; c, m, y, k = s["cmyk"]
            fn = f"swatch-{s['hex']}-{s['name']}.png"
            w.writerow([s["name"], f"#{s['hex'].upper()}", r, g, b,
                        c, m, y, k, f"{s['delta_e']:.3f}", fn])

    with open(OUTPUT_DIR / "swatches.json", "w") as f:
        json.dump({
            "icc_profile": ICC_PATH,
            "delta_e_threshold": DELTA_E_MAX,
            "count_safe": len(safe),
            "count_k_ramp": len(k_ramp),
            "count_total": len(all_sw),
            "swatches": [{k: v for k, v in s.items() if k != "is_k_ramp"} for s in all_sw],
        }, f, indent=2, default=lambda x: list(x) if isinstance(x, tuple) else x)

    # Export as Adobe Swatch Exchange (.ase) and GIMP Palette (.gpl). These
    # drop straight into Photoshop, Illustrator, Substance, Affinity, Krita,
    # Inkscape, GIMP, and Blender (via add-on). Sorted by hue for usability.
    write_ase(OUTPUT_DIR / "swatches.ase",
              sorts["by-hue"],
              palette_title="Mimaki 3DUJ-safe")
    write_gpl(OUTPUT_DIR / "swatches.gpl",
              sorts["by-hue"],
              palette_title="Mimaki 3DUJ-safe")

    # 7. Master grids
    print("Drawing master grids...")
    fonts = (get_font(32), get_font(15), get_font(13))
    titles = {
        "by-hue":       "Mimaki 3DUJ-safe palette - sorted by HUE",
        "by-lightness": "Mimaki 3DUJ-safe palette - sorted by LIGHTNESS",
        "by-chroma":    "Mimaki 3DUJ-safe palette - sorted by CHROMA",
        "by-safety":    "Mimaki 3DUJ-safe palette - sorted by SAFETY (lowest dE first)",
    }
    for key, swatches in sorts.items():
        out = OUTPUT_DIR / f"master-{key}.png"
        draw_square_master(swatches, out, titles[key], fonts)
        print(f"  {out.name}")
    draw_hue_lightness_master(
        all_sw, OUTPUT_DIR / "master-hue-lightness.png",
        "Mimaki 3DUJ-safe palette - hue x lightness map", fonts)
    print("  master-hue-lightness.png")

    # 8. Individual swatches
    print(f"Writing {len(all_sw)} individual 128x128 swatches...")
    for s in all_sw:
        fn = f"swatch-{s['hex']}-{s['name']}.png"
        Image.new("RGB", (INDIVIDUAL_PX, INDIVIDUAL_PX), s["rgb"]).save(
            OUTPUT_DIR / fn, optimize=True)

    print()
    print(f"Done. Output: {OUTPUT_DIR.resolve()}")
    print(f"  safe chromatic : {len(safe)}")
    print(f"  k-ramp added   : {len(k_ramp)}")
    print(f"  total swatches : {len(all_sw)}")
    print(f"  files written  : {len(all_sw)} swatches + 5 masters + 3 manifests")

if __name__ == "__main__":
    main()
