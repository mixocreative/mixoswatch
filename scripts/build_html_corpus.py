"""Build html corpus block (148 W3C named colors, schema v3).

Source: https://www.w3.org/TR/css-color-4/#named-colors
The W3C CSS Color Level 4 spec defines 148 named color keywords
(including alias pairs such as gray/grey, cyan/aqua, fuchsia/magenta).
Each entry gets a unique name_en; alias pairs are distinguished in
name_ja / name_zh to satisfy per-language uniqueness.

Anchor is 'hex' (W3C names are sRGB-native).
CMYK is derived via Pillow + CoatedFOGRA39 when the ICC profile is
present in icc/CoatedFOGRA39.icc; falls back to naive math otherwise.
"""
from __future__ import annotations
import json
from pathlib import Path
from PIL import Image, ImageCms

RAW      = Path("scripts/source_data/css_named_colors.json")
TRANSLIT = Path("scripts/source_data/html_translit.json")
ICC      = Path("icc/CoatedFOGRA39.icc")
OUT      = Path("scripts/source_data/html_v3.json")

_XFORM = None


def get_xform():
    global _XFORM
    if _XFORM is not None:
        return _XFORM
    if not ICC.exists():
        return None
    srgb      = ImageCms.createProfile("sRGB")
    cmyk_prof = ImageCms.getOpenProfile(str(ICC))
    _XFORM    = ImageCms.buildTransformFromOpenProfiles(
        srgb, cmyk_prof, "RGB", "CMYK"
    )
    return _XFORM


def hex_to_cmyk_fogra39(hex_v: str) -> list[int]:
    xf = get_xform()
    if xf is None:
        return hex_to_cmyk_naive(hex_v)
    h        = hex_v.lstrip("#")
    r, g, b  = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    img      = Image.new("RGB", (1, 1), (r, g, b))
    out      = ImageCms.applyTransform(img, xf)
    C, M, Y, K = [round(v * 100 / 255) for v in out.getpixel((0, 0))]
    return [C, M, Y, K]


def hex_to_cmyk_naive(hex_v: str) -> list[int]:
    h        = hex_v.lstrip("#")
    r, g, b  = int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0
    k        = 1 - max(r, g, b)
    if k >= 1:
        return [0, 0, 0, 100]
    c = (1 - r - k) / (1 - k)
    m = (1 - g - k) / (1 - k)
    y = (1 - b - k) / (1 - k)
    return [round(c * 100), round(m * 100), round(y * 100), round(k * 100)]


def main() -> None:
    raw      = json.loads(RAW.read_text(encoding="utf-8"))
    translit = (
        json.loads(TRANSLIT.read_text(encoding="utf-8"))
        if TRANSLIT.exists()
        else {}
    )

    xform_source = "fogra39" if ICC.exists() else "naive"
    print(f"CMYK source: {xform_source}")

    entries = []
    for r in raw:
        name  = r["name"]
        hex_v = r["hex"].upper()
        t     = translit.get(name, {})
        entry = {
            "name_en": name,
            "name_ja": t.get("ja") or name,
            "name_zh": t.get("zh") or name,
            "hex":     hex_v,
            "cmyk":    hex_to_cmyk_fogra39(hex_v),
        }
        entries.append(entry)

    out_data = {
        "id":      "html",
        "label":   {
            "en": "W3C named colors (148)",
            "ja": "W3C 名前付き色",
            "zh": "W3C 命名色",
        },
        "fields": [
            {"id": "name_en", "label": {"en": "English",  "ja": "英語",   "zh": "英文"}},
            {"id": "name_ja", "label": {"en": "Japanese", "ja": "日本語", "zh": "日文"}},
            {"id": "name_zh", "label": {"en": "Chinese",  "ja": "中国語", "zh": "中文"}},
        ],
        "default_display": "name_en",
        "anchor":          "hex",
        "source":          "https://www.w3.org/TR/css-color-4/#named-colors",
        "entries":         entries,
    }

    OUT.write_text(
        json.dumps(out_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {OUT} with {len(entries)} entries")


if __name__ == "__main__":
    main()
