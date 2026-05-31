"""
gen_libraries.py
================
One Python entry point that:

  1. Walks the icc/ folder at the repo root,
  2. For every CMYK profile found, samples colors in CIE LCh,
  3. Round-trips each through the ICC (sRGB -> CMYK -> sRGB),
  4. Keeps only colors that survive with ΔE₀₀ <= --delta-e,
  5. Appends a K-only neutral ramp (separate from the chromatic set),
  6. Assigns unique descriptive names (Option A naming),
  7. Writes per-profile JSON to  data/libraries/<profile>.json,
     ASE + GPL siblings if --full,
  8. Writes data/libraries/library_index.json so the HTML tools can list
     available libraries with counts + LUT paths.

This script absorbs everything the old `swatches.py` did (color math,
naming, palette format writers, round-trip gate). `swatches.py` is gone;
this is the single library generator.

Optional ArgyllCMS xicclu: if installed and on PATH, it is used as an
extra geometric in-gamut filter (intersect with ΔE gate). If not, only
the ΔE gate is used. We do not prompt the user to install Argyll; it is
an opt-in if it happens to already be there.

Usage
-----
    python scripts/gen_libraries.py
    python scripts/gen_libraries.py --delta-e 1.5
    python scripts/gen_libraries.py --only CoatedFOGRA39.icc
    python scripts/gen_libraries.py --force        # rebuild even if fresh
    python scripts/gen_libraries.py --full         # also write .ase + .gpl
"""

import argparse
import csv
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import warnings
from pathlib import Path

from PIL import Image, ImageCms

# Reuse the CMYK detection + tier labelling that lives in gen_luts.py so
# both scripts agree on what's a CMYK profile and how to label tiers.
sys.path.insert(0, str(Path(__file__).parent))
try:
    from gen_luts import is_cmyk, label_for  # type: ignore
except ImportError as e:
    sys.exit(f"need gen_luts.py next to this script: {e}")


# ---------------------------------------------------------------------------
# Paths (everything resolved relative to repo root, not CWD)
# ---------------------------------------------------------------------------

ROOT     = Path(__file__).resolve().parent.parent
ICC_DIR  = ROOT / "icc"
LIB_DIR  = ROOT / "data" / "libraries"
LUT_DIR  = ROOT / "data" / "luts"
INDEX    = LIB_DIR / "library_index.json"


# ---------------------------------------------------------------------------
# Sampling + acceptance defaults
# ---------------------------------------------------------------------------

# LCh candidate density. These shape the *test set*, not what passes.
LIGHTNESS_STEPS = 8
CHROMA_STEPS    = 8
HUE_STEPS       = 24

# Max chroma sampled in CIELCh. sRGB tops out near C* = 132 (pure red);
# CMYK gamuts cap much lower. 110 is generous; lower it for stricter sets.
CHROMA_MAX = 110

# K-only ramp resolution (steps from white to black).
K_RAMP_STEPS = 7

# Round-trip rendering intent. RELATIVE_COLORIMETRIC clips out-of-gamut
# colors to the boundary, which is exactly what we want to measure.
INTENT = ImageCms.Intent.RELATIVE_COLORIMETRIC

# Black point compensation: OFF during gamut testing. BPC rescales L* on
# both legs of a round-trip and inflates ΔE near the black point in ways
# unrelated to gamut membership (El Asaleh / Sharma).
USE_BPC_FOR_TEST = False


# ---------------------------------------------------------------------------
# Color math: CIE LCh -> Lab -> XYZ -> sRGB, plus CIEDE2000
# ---------------------------------------------------------------------------

def lch_to_lab(L, C, h_deg):
    h = math.radians(h_deg)
    return (L, C * math.cos(h), C * math.sin(h))


def lab_to_xyz(L, a, b, ref=(0.95047, 1.0, 1.08883)):
    fy = (L + 16) / 116
    fx = a / 500 + fy
    fz = fy - b / 200
    inv = lambda t: t**3 if t**3 > 0.008856 else (t - 16/116) / 7.787
    return ref[0]*inv(fx), ref[1]*inv(fy), ref[2]*inv(fz)


def xyz_to_linear(X, Y, Z):
    return ( 3.2404542*X - 1.5371385*Y - 0.4985314*Z,
            -0.9692660*X + 1.8760108*Y + 0.0415560*Z,
             0.0556434*X - 0.2040259*Y + 1.0572252*Z)


def linear_to_srgb(c):
    return 12.92*c if c <= 0.0031308 else 1.055*(c**(1/2.4)) - 0.055


def lch_to_srgb8(L, C, h):
    r, g, b = xyz_to_linear(*lab_to_xyz(*lch_to_lab(L, C, h)))
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
    if abs(dhp) > 180:
        dhp -= 360 * (1 if dhp > 0 else -1)
    dHp = 2*math.sqrt(C1p*C2p)*math.sin(math.radians(dhp/2)) if (C1p and C2p) else 0
    avg_L = (L1 + L2) / 2
    avg_hp = (h1p + h2p) / 2
    if abs(h1p - h2p) > 180:
        avg_hp += 180
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

HUE_NAMES = ["red", "vermilion", "orange", "amber", "yellow", "lime",
             "green", "jade", "teal", "cyan", "blue", "indigo",
             "violet", "magenta"]


def hue_bin(lab_h_deg):
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
    C = math.hypot(a, b)
    if C < 6:
        return neutral_name(L)
    h_deg = math.degrees(math.atan2(b, a)) % 360
    return f"{lightness_bin(L)}-{chroma_bin(C)}-{hue_bin(h_deg)}"


def assign_unique_names(swatches):
    """Mutate swatches in place: name is base_name with -02, -03, ...
    appended within collision groups (lowest ΔE keeps the bare name)."""
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
    """GIMP Palette plain text. Used by GIMP, Inkscape, Krita, Blender."""
    with open(path, "w", encoding="utf-8") as f:
        f.write("GIMP Palette\n")
        f.write(f"Name: {palette_title}\n")
        f.write("Columns: 8\n")
        f.write("# Generated by gen_libraries.py\n")
        for s in swatches:
            r, g, b = s["rgb"]
            f.write(f"{r:3d} {g:3d} {b:3d}\t{s['name']}\n")


def write_ase(path, swatches, palette_title="palette"):
    """Adobe Swatch Exchange binary BE. Photoshop / Illustrator / Affinity /
    Substance Painter all import this."""
    def encode_name(name):
        s = (name + "\x00").encode("utf-16-be")
        return struct.pack(">H", len(s) // 2) + s

    blocks = [(0xC001, encode_name(palette_title))]
    for s in swatches:
        body  = encode_name(s["name"])
        body += b"RGB "
        r, g, b = (c / 255.0 for c in s["rgb"])
        body += struct.pack(">fff", r, g, b)
        body += struct.pack(">H", 2)   # color type: normal
        blocks.append((0x0001, body))
    blocks.append((0xC002, b""))

    with open(path, "wb") as f:
        f.write(b"ASEF")
        f.write(struct.pack(">HH", 1, 0))
        f.write(struct.pack(">I", len(blocks)))
        for btype, body in blocks:
            f.write(struct.pack(">H", btype))
            f.write(struct.pack(">I", len(body)))
            f.write(body)


# ---------------------------------------------------------------------------
# Optional ArgyllCMS xicclu (geometric in-gamut)
# ---------------------------------------------------------------------------

def find_xicclu():
    """Return xicclu binary path if installed and on PATH, else None.
    No install prompt, no auto-install. Pure detect-and-use."""
    p = shutil.which("xicclu")
    if p:
        return p
    if sys.platform == "win32":
        for d in [r"C:\Program Files\ArgyllCMS\bin",
                  r"C:\Program Files (x86)\ArgyllCMS\bin"]:
            exe = Path(d) / "xicclu.exe"
            if exe.exists():
                return str(exe)
    return None


def argyll_in_gamut(icc_path, lab_values, xicclu_path):
    """Run xicclu to detect (clip) markers on each Lab value.
    Returns list[bool] or None on failure."""
    stdin_text = "\n".join(f"{L} {a} {b}" for L, a, b in lab_values) + "\n"
    cmd = [xicclu_path, "-fb", "-ir", "-pl", "-s", "100", str(icc_path)]
    try:
        result = subprocess.run(cmd, input=stdin_text, capture_output=True,
                                text=True, timeout=120)
    except (subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0 and not result.stdout.strip():
        return None
    out = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        out.append("(clip)" not in line.lower())
    return out if len(out) == len(lab_values) else None


# ---------------------------------------------------------------------------
# Sanity check (warn user if reverse table is broken)
# ---------------------------------------------------------------------------

def sanity_check(icc_path, to_cmyk, to_rgb, to_lab):
    """Round-trip 6 reference colors; flag profiles with broken B2A tables."""
    refs = [((255, 128,   0), "mid orange"),
            ((128, 200,   0), "lime green"),
            ((  0, 180,  90), "mid green"),
            ((180,   0, 180), "muted magenta"),
            ((255, 220,   0), "yellow"),
            ((100,  60,  30), "brown")]
    src = Image.new("RGB", (1, len(refs)))
    src.putdata([c[0] for c in refs])
    bk  = ImageCms.applyTransform(ImageCms.applyTransform(src, to_cmyk), to_rgb)
    ls  = ImageCms.applyTransform(src, to_lab)
    lb  = ImageCms.applyTransform(bk,  to_lab)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ls, lb = list(ls.getdata()), list(lb.getdata())
    dec = lambda p: (p[0]*100/255, p[1]-128, p[2]-128)
    dEs = [delta_e_2000(dec(ls[i]), dec(lb[i])) for i in range(len(refs))]
    if max(dEs) > 5.0:
        print(f"    !! warn: profile reverse table looks weak (worst ΔE = {max(dEs):.2f})")
        for (rgb, name), de in zip(refs, dEs):
            tag = " <-- bad" if de > 5.0 else ""
            print(f"       {name:18s} RGB{rgb}  ΔE={de:.2f}{tag}")


# ---------------------------------------------------------------------------
# Core: build one library from one ICC
# ---------------------------------------------------------------------------

def build_one_library(icc_path: Path, delta_e: float, use_argyll: bool):
    """Return (swatches_dict, summary_dict) for a single ICC profile.
    Caller writes the JSON / ASE / GPL files."""
    srgb_p  = ImageCms.createProfile("sRGB")
    lab_p   = ImageCms.createProfile("LAB")
    print_p = ImageCms.getOpenProfile(str(icc_path))
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

    sanity_check(icc_path, to_cmyk, to_rgb, to_lab)

    # 1. LCh candidates -> unique sRGB
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

    # 2. Round-trip through the profile, measure ΔE
    src   = Image.new("RGB", (1, len(cand_list)))
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
    dec = lambda p: (p[0]*100/255, p[1]-128, p[2]-128)

    results = []
    for i, rgb in enumerate(cand_list):
        lab1 = dec(lab_s[i])
        lab2 = dec(lab_b[i])
        de   = delta_e_2000(lab1, lab2)
        results.append({
            "rgb":  rgb,
            "hex":  f"{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}",
            "cmyk": tuple(int(round(v * 100 / 255)) for v in cmyk_px[i]),
            "lab":  lab1,
            "delta_e":   round(de, 3),
            "base_name": base_name(*lab1),
        })

    # 3. Optional Argyll geometric in-gamut filter
    xicclu = find_xicclu() if use_argyll else None
    if xicclu:
        ig = argyll_in_gamut(icc_path, [r["lab"] for r in results], xicclu)
        if ig is not None:
            for r, v in zip(results, ig):
                r["argyll_in_gamut"] = v

    def is_safe(r):
        if r["delta_e"] > delta_e:
            return False
        if "argyll_in_gamut" in r and not r["argyll_in_gamut"]:
            return False
        return True
    safe = [r for r in results if is_safe(r)]

    # 4. K-ramp (pure neutrals through the CMYK profile)
    k_vals = []
    for i in range(K_RAMP_STEPS):
        v = round((1 - i/(K_RAMP_STEPS-1)) * 255)
        k_vals.append((v, v, v))
    k_src   = Image.new("RGB", (1, K_RAMP_STEPS))
    k_src.putdata(k_vals)
    k_cmyk  = ImageCms.applyTransform(k_src, to_cmyk)
    k_back  = ImageCms.applyTransform(k_cmyk, to_rgb)
    k_lab_s = ImageCms.applyTransform(k_src,  to_lab)
    k_lab_b = ImageCms.applyTransform(k_back, to_lab)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        k_cmyk_px  = list(k_cmyk.getdata())
        k_lab_s_px = list(k_lab_s.getdata())
        k_lab_b_px = list(k_lab_b.getdata())

    safe_hexes = {s["hex"] for s in safe}
    k_ramp = []
    for i, rgb in enumerate(k_vals):
        hx = f"{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        if hx in safe_hexes:
            continue
        lab1 = dec(k_lab_s_px[i])
        lab2 = dec(k_lab_b_px[i])
        de   = delta_e_2000(lab1, lab2)
        k_pct = round(i * 100 / (K_RAMP_STEPS - 1))
        k_ramp.append({
            "rgb":  rgb,
            "hex":  hx,
            "cmyk": tuple(int(round(v*100/255)) for v in k_cmyk_px[i]),
            "lab":  lab1,
            "delta_e":   round(de, 3),
            "base_name": f"k-{k_pct:03d}",
            "is_k_ramp": True,
            "k_percent": k_pct,
        })

    # 5. Names + uniqueness pass on the chromatic set only
    assign_unique_names(safe)
    for s in k_ramp:
        s["name"] = s["base_name"]

    all_sw = safe + k_ramp
    summary = {
        "count_safe":   len(safe),
        "count_k_ramp": len(k_ramp),
        "count_total":  len(all_sw),
        "argyll_used":  bool(xicclu),
    }
    return all_sw, summary


def sort_by_hue(swatches):
    def lab_chroma(lab): _, a, b = lab; return math.hypot(a, b)
    def lab_h(lab):      _, a, b = lab; return math.degrees(math.atan2(b, a)) % 360
    def key(s):
        if s.get("is_k_ramp") or lab_chroma(s["lab"]) < 6:
            return (2, s["lab"][0])
        return (0, lab_h(s["lab"]), s["lab"][0])
    return sorted(swatches, key=key)


def write_library_json(path: Path, icc_filename: str, delta_e: float,
                       swatches, summary):
    payload = {
        "icc_profile":       icc_filename,
        "delta_e_threshold": delta_e,
        **summary,
        "swatches": [{k: v for k, v in s.items() if k != "is_k_ramp"}
                     for s in swatches],
    }
    path.write_text(
        json.dumps(payload, indent=2,
                   default=lambda x: list(x) if isinstance(x, tuple) else x),
        encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Build a curated print-safe swatch library from every "
                    "CMYK ICC in icc/. Writes data/libraries/<profile>.json "
                    "and data/libraries/library_index.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--delta-e", type=float, default=2.0,
                    help="Delta-E 2000 acceptance threshold (default 2.0). "
                         "The 3D explorer's dE-max slider scales DOWN from "
                         "this; anything above this is filtered out entirely.")
    ap.add_argument("--only",
                    help="Rebuild a single ICC filename (e.g. "
                         "CoatedFOGRA39.icc). Default: all CMYK profiles.")
    ap.add_argument("--force", action="store_true",
                    help="Rebuild even when the library JSON is newer "
                         "than its ICC.")
    ap.add_argument("--full", action="store_true",
                    help="Also write .ase + .gpl palette files alongside "
                         "each library JSON.")
    ap.add_argument("--argyll", action="store_true",
                    help="If ArgyllCMS xicclu is on PATH, run it as an "
                         "extra geometric in-gamut filter (intersect "
                         "with the dE gate). Default: off.")
    args = ap.parse_args()

    if not ICC_DIR.exists():
        sys.exit(f"icc/ folder not found at {ICC_DIR}\n"
                 f"Put .icc/.icm files in {ICC_DIR} and re-run.")

    LIB_DIR.mkdir(parents=True, exist_ok=True)

    iccs = sorted(p for p in ICC_DIR.glob("*.[iI][cC][cCmM]"))
    if args.only:
        iccs = [ICC_DIR / args.only]

    entries = []
    built = 0
    skipped_rgb = 0
    skipped_fresh = 0

    for icc in iccs:
        if not icc.exists():
            print(f"  missing: {icc}")
            continue
        if not is_cmyk(icc):
            skipped_rgb += 1
            print(f"  skip RGB-only: {icc.name}")
            continue

        label, tier = label_for(icc.name)
        json_path = LIB_DIR / (icc.stem + ".json")

        if not args.force and json_path.exists() \
                and json_path.stat().st_mtime > icc.stat().st_mtime:
            skipped_fresh += 1
            print(f"  skip up-to-date: data/libraries/{json_path.name}")
        else:
            print(f"  build  {icc.name}  ({label})")
            swatches, summary = build_one_library(icc, args.delta_e, args.argyll)
            swatches = sort_by_hue(swatches)
            write_library_json(json_path, icc.name, args.delta_e,
                               swatches, summary)
            if args.full:
                title = icc.stem + " print-safe"
                write_ase(LIB_DIR / (icc.stem + ".ase"), swatches, title)
                write_gpl(LIB_DIR / (icc.stem + ".gpl"), swatches, title)
            print(f"    safe={summary['count_safe']}  "
                  f"k-ramp={summary['count_k_ramp']}  "
                  f"total={summary['count_total']}  "
                  f"argyll={'on' if summary['argyll_used'] else 'off'}")
            built += 1

        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            ct = data.get("count_total")
            cs = data.get("count_safe")
            ck = data.get("count_k_ramp")
            de = data.get("delta_e_threshold")
        except (OSError, json.JSONDecodeError):
            ct = cs = ck = de = None

        entries.append({
            "profile_filename": icc.name,
            "profile_label":    label,
            "profile_tier":     tier,
            "library_file":     f"data/libraries/{json_path.name}",
            "forward_lut":      f"data/luts/{icc.stem}.lut",
            "reverse_lut":      f"data/luts/{icc.stem}.rcmyk.lut",
            "delta_e_threshold": de,
            "count_total":      ct,
            "count_safe":       cs,
            "count_k_ramp":     ck,
            "bytes":            json_path.stat().st_size,
        })

    entries.sort(key=lambda e: (e["profile_tier"], e["profile_label"]))
    INDEX.write_text(json.dumps({
        "format": "swatch.library_index/v1",
        "delta_e_threshold_used": args.delta_e,
        "libraries": entries,
    }, indent=2), encoding="utf-8")

    print(f"\nindex: data/libraries/{INDEX.name}")
    print(f"built: {built}   up-to-date: {skipped_fresh}   "
          f"rgb-only skipped: {skipped_rgb}   libraries indexed: {len(entries)}")


if __name__ == "__main__":
    main()
