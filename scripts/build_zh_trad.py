"""Build zh-trad corpus block from raw Chinese traditional list.

Input:  scripts/source_data/zh_trad_raw.json
Output: scripts/source_data/zh_trad_v3.json (consumed by build_corpora.py in Task 10)

Each raw entry has: {name (hanzi), pinyin, hex}.
CMYK is derived from hex via naive sRGB->CMYK (icc/ is gitignored; if CoatedFOGRA39.icc
is present at icc/CoatedFOGRA39.icc, Pillow+ImageCms is used instead for profile-accurate
conversion matching gen_luts.py).

English + Japanese gloss come from scripts/source_data/zh_trad_glosses.json.
Entries without a gloss fall back to pinyin for both name_en and name_ja.

Source: color-term.com/traditional-color-of-china/ (526 entries, 14 pages),
        sourced from the Chinese Academy of Sciences color name dictionary (1957).
"""
from __future__ import annotations
import json
from pathlib import Path

RAW   = Path("scripts/source_data/zh_trad_raw.json")
GLOSS = Path("scripts/source_data/zh_trad_glosses.json")
OUT   = Path("scripts/source_data/zh_trad_v3.json")
ICC   = Path("icc/CoatedFOGRA39.icc")


def _build_icc_xform():
    """Return a Pillow ImageCms transform (sRGB -> CMYK) if ICC file exists."""
    try:
        from PIL import ImageCms
        if not ICC.exists():
            return None
        srgb      = ImageCms.createProfile("sRGB")
        cmyk_prof = ImageCms.getOpenProfile(str(ICC))
        xform     = ImageCms.buildTransformFromOpenProfiles(
            srgb, cmyk_prof, "RGB", "CMYK"
        )
        return xform
    except Exception:
        return None


def hex_to_cmyk_icc(hex_v: str, xform) -> list[int]:
    """Convert hex -> CMYK using Pillow + CoatedFOGRA39 profile."""
    from PIL import Image, ImageCms
    h = hex_v.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    img = Image.new("RGB", (1, 1), (r, g, b))
    out = ImageCms.applyTransform(img, xform)
    return [round(v * 100 / 255) for v in out.getpixel((0, 0))]


def hex_to_cmyk_naive(hex_v: str) -> list[int]:
    """Naive sRGB -> CMYK without ICC profile (no gamut mapping)."""
    h = hex_v.lstrip("#")
    r, g, b = int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0
    k = 1.0 - max(r, g, b)
    if k >= 1.0:
        return [0, 0, 0, 100]
    c = (1.0 - r - k) / (1.0 - k)
    m = (1.0 - g - k) / (1.0 - k)
    y = (1.0 - b - k) / (1.0 - k)
    return [round(c * 100), round(m * 100), round(y * 100), round(k * 100)]


def main() -> None:
    raw    = json.loads(RAW.read_text(encoding="utf-8"))
    gloss  = json.loads(GLOSS.read_text(encoding="utf-8")) if GLOSS.exists() else {}

    # Attempt ICC-accurate conversion; fall back to naive
    xform = _build_icc_xform()
    cmyk_method = "Pillow+CoatedFOGRA39" if xform else "naive sRGB->CMYK"
    print(f"CMYK method: {cmyk_method}")

    entries: list[dict] = []
    seen_names: dict[str, int] = {}
    dropped = 0

    for r in raw:
        hanzi  = r["name"]
        pinyin = (r.get("pinyin") or "").strip().lower()
        hex_v  = r.get("hex", "").upper()
        if not hex_v.startswith("#"):
            hex_v = "#" + hex_v

        # Deduplicate by hanzi name - keep first occurrence
        if hanzi in seen_names:
            dropped += 1
            continue
        seen_names[hanzi] = len(entries)

        # CMYK: use value from raw if present and valid, else derive
        cmyk = r.get("cmyk")
        if not (isinstance(cmyk, list) and len(cmyk) == 4):
            if xform:
                cmyk = hex_to_cmyk_icc(hex_v, xform)
            else:
                cmyk = hex_to_cmyk_naive(hex_v)

        g = gloss.get(hanzi, {})
        entries.append({
            "name_zh": hanzi,
            "pinyin":  pinyin,
            "name_en": g.get("en") or pinyin,
            "name_ja": g.get("ja") or pinyin,
            "hex":     hex_v,
            "cmyk":    cmyk,
        })

    if dropped:
        print(f"Dropped {dropped} duplicate hanzi entries (kept first occurrence)")

    corpus = {
        "id": "zh-trad",
        "label": {
            "en": "Chinese traditional",
            "ja": "中国の伝統色",
            "zh": "中國傳統色",
        },
        "fields": [
            {"id": "name_zh", "label": {"en": "Chinese",  "ja": "漢字",       "zh": "漢字"}},
            {"id": "pinyin",  "label": {"en": "pinyin",   "ja": "ピンイン",   "zh": "拼音"}},
            {"id": "name_en", "label": {"en": "English",  "ja": "英語",       "zh": "英文"}},
            {"id": "name_ja", "label": {"en": "Japanese", "ja": "日本語",     "zh": "日文"}},
        ],
        "default_display": "name_zh",
        "anchor": "cmyk",
        "source": (
            "https://color-term.com/traditional-color-of-china/ "
            "(526 colors, Chinese Academy of Sciences color name dictionary, 1957)"
        ),
        "entries": entries,
    }

    OUT.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {OUT} with {len(entries)} entries")


if __name__ == "__main__":
    main()
