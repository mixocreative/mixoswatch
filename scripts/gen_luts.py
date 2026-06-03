"""
gen_luts.py — Build per-ICC CMYK→sRGB lookup tables for the swatch explorer HTMLs.

For each CMYK ICC profile in icc/, samples a 17×17×17×17 CMYK grid (83,521 points),
pushes it through Pillow's LittleCMS binding into sRGB, and writes the result as a
compact binary .lut file the HTML can fetch and quadrilinearly interpolate.

Output layout (binary, little-endian):
    bytes 0-3   : magic "LUT4"
    byte  4     : grid size N (uint8, currently 17)
    bytes 5-15  : reserved zero padding (16-byte header total)
    bytes 16-…  : raw RGB triplets, N⁴ entries, index = k*N³ + y*N² + m*N + c
                  each triplet = R, G, B (uint8)

Also writes data/luts/index.json listing every CMYK profile with display label
+ tier and the LUT filename. The HTML reads this manifest to populate its
profile dropdown.

Usage:
    python scripts/gen_luts.py            # rebuild all .lut + data/luts/index.json
    python scripts/gen_luts.py FILE.icc   # rebuild a single profile
    python scripts/gen_luts.py --force    # rebuild even if .lut is newer than the .icc
"""

import argparse
import fnmatch
import json
import os
import struct
import sys
import warnings
from pathlib import Path

from PIL import Image, ImageCms

ROOT     = Path(__file__).resolve().parent.parent
ICC_DIR  = ROOT / "icc"
LUT_DIR  = ROOT / "data" / "luts"
INDEX    = LUT_DIR / "index.json"
GRID     = 17                              # 17 steps per axis -> 83,521 nodes
MAGIC    = b"LUT4"
HEADER   = 16                              # bytes
INTENT   = ImageCms.Intent.RELATIVE_COLORIMETRIC

# Tiered display labels — mirrors swatches.py ICC_PROFILE_TIERS, extended to
# cover everything currently sitting in icc/. Order matters: more specific
# patterns first because fnmatch.fnmatch("UnCoatedX","*Coated*") would otherwise
# greedy-match Uncoated as Coated.
TIERS = [
    ("Tier 1 · Mimaki 3DUJ (measured)",  ["*3DUJ*", "*Mimaki*3D*", "*MPM3*"]),
    ("Tier 2 · ECI ISOcoated v2",        ["ISOcoated_v2*", "ISO Coated v2*"]),
    ("Tier 3 · Coated FOGRA39",          ["CoatedFOGRA39*", "FOGRA39*"]),
    # Japan family — Uncoated/Newspaper/Web BEFORE Coated to avoid substring greed
    ("Tier 4 · Japan Color Uncoated",    ["JapanColor*Uncoated*"]),
    ("Tier 4 · Japan Color Newspaper",   ["JapanColor*Newspaper*"]),
    ("Tier 4 · Japan Web Coated",        ["JapanWeb*"]),
    ("Tier 4 · Japan Color Coated",      ["JapanColor*Coated*"]),
    # US family — Uncoated variants BEFORE Coated; SWOP-specific BEFORE generic
    ("Tier 5 · US Web Uncoated",         ["USWebUncoated*"]),
    ("Tier 5 · US Sheetfed Uncoated",    ["USSheetfedUncoated*"]),
    ("Tier 5 · US Web Coated SWOP",      ["USWebCoatedSWOP*", "SWOP*"]),
    ("Tier 5 · US Sheetfed Coated",      ["USSheetfedCoated*"]),
    # FOGRA family — specific numbers
    ("Tier 5 · Coated FOGRA27",          ["CoatedFOGRA27*"]),
    ("Tier 5 · Web Coated FOGRA28",      ["WebCoatedFOGRA28*"]),
    ("Tier 5 · Uncoated FOGRA29",        ["UncoatedFOGRA29*"]),
]


def is_cmyk(path: Path) -> bool:
    """True when the profile can act as a CMYK destination from sRGB."""
    try:
        prof = ImageCms.getOpenProfile(str(path))
        srgb = ImageCms.createProfile("sRGB")
        ImageCms.buildTransform(srgb, prof, "RGB", "CMYK")
        return True
    except (ImageCms.PyCMSError, OSError):
        return False


def label_for(name: str) -> tuple[str, int]:
    """Return (display_label, tier_index). Falls back to filename + Tier 99."""
    for i, (label, patterns) in enumerate(TIERS):
        for pat in patterns:
            if fnmatch.fnmatch(name.lower(), pat.lower()):
                return label, i
    return f"Tier 99 · {Path(name).stem}", 99


def build_lut(icc_path: Path, out_path: Path) -> None:
    """Sample the 17⁴ CMYK grid, push through ICC → sRGB, write the binary."""
    srgb_p  = ImageCms.createProfile("sRGB")
    print_p = ImageCms.getOpenProfile(str(icc_path))
    to_rgb  = ImageCms.buildTransform(
        print_p, srgb_p, "CMYK", "RGB", renderingIntent=INTENT)

    n = GRID
    step = 255 / (n - 1)                 # Pillow CMYK image uses 0-255 bytes
    cmyk_pixels = bytearray(n * n * n * n * 4)
    idx = 0
    for k in range(n):
        for y in range(n):
            for m in range(n):
                for c in range(n):
                    cmyk_pixels[idx]     = round(c * step)
                    cmyk_pixels[idx + 1] = round(m * step)
                    cmyk_pixels[idx + 2] = round(y * step)
                    cmyk_pixels[idx + 3] = round(k * step)
                    idx += 4

    n4 = n * n * n * n
    cmyk_img = Image.frombytes("CMYK", (n4, 1), bytes(cmyk_pixels))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        rgb_img = ImageCms.applyTransform(cmyk_img, to_rgb)
    rgb_bytes = rgb_img.tobytes()        # 3 bytes per pixel, total = n4 * 3

    assert len(rgb_bytes) == n4 * 3, f"unexpected output size: {len(rgb_bytes)}"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<B", n))
        f.write(b"\x00" * (HEADER - 5))  # pad to 16 bytes
        f.write(rgb_bytes)


def build_rcmyk_lut(icc_path: Path, out_path: Path) -> None:
    """Reverse LUT for safety/round-trip math. Samples sRGB at GRID³ nodes,
    pushes through sRGB → ICC CMYK, writes a binary with the same header
    layout. Magic CMK4 to distinguish from forward LUT4. Body = n³ × 4 bytes
    CMYK per node, index = r*n² + g*n + b."""
    srgb_p  = ImageCms.createProfile("sRGB")
    print_p = ImageCms.getOpenProfile(str(icc_path))
    to_cmyk = ImageCms.buildTransform(
        srgb_p, print_p, "RGB", "CMYK", renderingIntent=INTENT)

    n = GRID
    step = 255 / (n - 1)
    rgb_pixels = bytearray(n * n * n * 3)
    idx = 0
    for r in range(n):
        for g in range(n):
            for b in range(n):
                rgb_pixels[idx]     = round(r * step)
                rgb_pixels[idx + 1] = round(g * step)
                rgb_pixels[idx + 2] = round(b * step)
                idx += 3

    n3 = n * n * n
    rgb_img = Image.frombytes("RGB", (n3, 1), bytes(rgb_pixels))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        cmyk_img = ImageCms.applyTransform(rgb_img, to_cmyk)
    cmyk_bytes = cmyk_img.tobytes()      # 4 bytes per pixel

    assert len(cmyk_bytes) == n3 * 4, f"unexpected output size: {len(cmyk_bytes)}"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(b"CMK4")
        f.write(struct.pack("<B", n))
        f.write(b"\x00" * (HEADER - 5))
        f.write(cmyk_bytes)


def needs_rebuild(icc_path: Path, lut_path: Path, force: bool) -> bool:
    if force or not lut_path.exists():
        return True
    return lut_path.stat().st_mtime < icc_path.stat().st_mtime


def write_index(entries: list[dict]) -> None:
    """Write icc/index.json sorted by tier then label."""
    entries.sort(key=lambda e: (e["tier_index"], e["label"]))
    INDEX.write_text(
        json.dumps({
            "format": "icc.index/v1",
            "grid": GRID,
            "lut_header_bytes": HEADER,
            "profiles": [
                {k: v for k, v in e.items() if k != "tier_index"} for e in entries
            ],
        }, indent=2),
        encoding="utf-8",
    )


def main():
    TAC_TABLE = {
        "CoatedFOGRA39":           {"rec": 330, "max": 350, "paper": "coated"},
        "CoatedFOGRA27":           {"rec": 320, "max": 340, "paper": "coated"},
        "UncoatedFOGRA29":         {"rec": 260, "max": 290, "paper": "uncoated"},
        "WebCoatedFOGRA28":        {"rec": 300, "max": 320, "paper": "coated-web"},
        "JapanColor2001Coated":    {"rec": 350, "max": 350, "paper": "coated"},
        "JapanColor2001Uncoated":  {"rec": 260, "max": 290, "paper": "uncoated"},
        "JapanColor2002Newspaper": {"rec": 240, "max": 260, "paper": "newsprint"},
        "JapanWebCoated":          {"rec": 300, "max": 320, "paper": "coated-web"},
        "USSheetfedCoated":        {"rec": 320, "max": 340, "paper": "coated"},
        "USSheetfedUncoated":      {"rec": 260, "max": 290, "paper": "uncoated"},
        "USWebCoatedSWOP":         {"rec": 300, "max": 320, "paper": "coated-web"},
        "USWebUncoated":           {"rec": 260, "max": 290, "paper": "uncoated"},
    }

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?",
                    help="single .icc/.icm path; default rebuilds all in icc/")
    ap.add_argument("--force", action="store_true",
                    help="rebuild LUTs even if newer than the .icc")
    args = ap.parse_args()

    if not ICC_DIR.exists():
        sys.exit(f"icc/ folder not found at {ICC_DIR}")

    all_iccs = sorted(p for p in ICC_DIR.glob("*.[iI][cC][cCmM]") if p.is_file())
    # We always scan EVERY CMYK profile to rebuild the index, but only
    # rebuild the LUT binary for the ones requested.
    rebuild_set = {Path(args.file).name} if args.file else None
    if rebuild_set is not None and not any(p.name in rebuild_set for p in all_iccs):
        sys.exit(f"{args.file} not found in icc/")
    if not all_iccs:
        sys.exit("no .icc/.icm files found")

    LUT_DIR.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []
    built = 0
    skipped_rgb = 0
    skipped_fresh = 0

    for icc in all_iccs:
        do_build = (rebuild_set is None) or (icc.name in rebuild_set)
        if not do_build:
            # Still want this profile in the index, but skip the binary build.
            pass
        if not is_cmyk(icc):
            skipped_rgb += 1
            print(f"  skip RGB-only: {icc.name}")
            continue
        label, tier_index = label_for(icc.name)
        lut_name  = icc.stem + ".lut"
        rlut_name = icc.stem + ".rcmyk.lut"
        lut_path  = LUT_DIR / lut_name
        rlut_path = LUT_DIR / rlut_name

        if do_build and needs_rebuild(icc, lut_path, args.force):
            print(f"  build {icc.name} -> data/luts/{lut_name}  ({label})")
            try:
                build_lut(icc, lut_path)
                built += 1
            except (ImageCms.PyCMSError, OSError) as e:
                print(f"    !! forward LUT failed: {e}")
                continue
        else:
            if do_build:
                skipped_fresh += 1
                print(f"  skip up-to-date: data/luts/{lut_name}")

        if do_build and needs_rebuild(icc, rlut_path, args.force):
            print(f"  build {icc.name} -> data/luts/{rlut_name}  (reverse RGB->CMYK)")
            try:
                build_rcmyk_lut(icc, rlut_path)
            except (ImageCms.PyCMSError, OSError) as e:
                print(f"    !! reverse LUT failed: {e}")
                rlut_path = None
        elif do_build:
            print(f"  skip up-to-date: data/luts/{rlut_name}")

        stem_key = icc.stem  # e.g. "CoatedFOGRA39"
        tac_info = TAC_TABLE.get(stem_key, {"rec": 300, "max": 320, "paper": "unknown"})

        entries.append({
            "filename":   icc.name,
            "label":      label,
            "tier_index": tier_index,
            "kind":       "cmyk",
            "lut":        f"data/luts/{lut_name}",
            "rlut":       f"data/luts/{rlut_name}" if rlut_path and rlut_path.exists() else None,
            "lut_bytes":  lut_path.stat().st_size if lut_path.exists() else None,
            "rlut_bytes": rlut_path.stat().st_size if rlut_path and rlut_path.exists() else None,
            "tac_recommended": tac_info["rec"],
            "tac_max":         tac_info["max"],
            "paper":           tac_info["paper"],
        })

    if entries:
        write_index(entries)
        print(f"\nindex written: {INDEX}")

    print(f"\nbuilt: {built}   up-to-date: {skipped_fresh}   "
          f"rgb-only skipped: {skipped_rgb}   profiles indexed: {len(entries)}")


if __name__ == "__main__":
    main()
