"""Generate ground-truth Lab_D50 + Lab_D65 values for 10 known sRGB hex colors.

D50 ground truth: Pillow + LittleCMS ICC pipeline (sRGB -> LAB D50 PCS).
  This is the primary regression target - we want rgb2lab_d50 to match ICC.

D65 ground truth: analytic formula with WP_D65 whitepoint.
  Pillow's createProfile('LAB') always uses D50 as the PCS whitepoint
  regardless of colorTemp, so it cannot provide independent D65 Lab values.
  Instead, D65 ground truth is generated analytically here; the browser test
  verifies the JS implementation matches bit-for-bit (floating-point identity).

Output JSON is consumed by _verify/test_color_math.html for
browser-side regression testing of the Bradford fix.
"""
from __future__ import annotations
import json, math
from pathlib import Path
from PIL import Image, ImageCms

TEST_HEXES = [
    "#FF0000", "#00FF00", "#0000FF",  # primaries
    "#FFFFFF", "#7F7F7F", "#000000",  # neutrals
    "#FEDFE1",  # sakura-iro (jp-trad)
    "#1C3563",  # japanese blue
    "#CD071E",  # chinese red
    "#6495ED",  # cornflowerblue (CSS)
]

# --- analytic helpers (mirrors JS implementation exactly) --------------------
def srgb2lin(u: float) -> float:
    u /= 255.0
    return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4

def rgb2xyz(r: int, g: int, b: int) -> tuple[float, float, float]:
    R, G, B = srgb2lin(r), srgb2lin(g), srgb2lin(b)
    return (
        0.4124564*R + 0.3575761*G + 0.1804375*B,
        0.2126729*R + 0.7151522*G + 0.0721750*B,
        0.0193339*R + 0.1191920*G + 0.9503041*B,
    )

WP_D65 = (0.95047, 1.0, 1.08883)

# ICC linear Bradford CAT D65 -> D50 (ISO 15076-1 Annex E.3)
M_BRAD = [
    [ 1.0478112,  0.0228866, -0.0501270],
    [ 0.0295424,  0.9904844, -0.0170491],
    [-0.0092345,  0.0150436,  0.7521316],
]
WP_D50 = (0.96422, 1.0, 0.82521)

def f_(t: float) -> float:
    return t ** (1/3) if t > 0.008856 else 7.787 * t + 16/116

def xyz_to_lab(X: float, Y: float, Z: float, wp: tuple) -> tuple[float, float, float]:
    Xn, Yn, Zn = wp
    fx, fy, fz = f_(X/Xn), f_(Y/Yn), f_(Z/Zn)
    return (116*fy - 16, 500*(fx - fy), 200*(fy - fz))

def analytic_lab_d65(r: int, g: int, b: int) -> tuple[float, float, float]:
    return xyz_to_lab(*rgb2xyz(r, g, b), WP_D65)

# --- ICC D50 via Pillow (primary ground truth) --------------------------------
def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

def pillow_lab_d50(r: int, g: int, b: int) -> tuple[float, float, float]:
    """sRGB -> Lab D50 PCS via ImageCms (Pillow always returns D50 Lab)."""
    srgb_prof = ImageCms.createProfile("sRGB")
    lab_prof  = ImageCms.createProfile("LAB", colorTemp=5000)
    img = Image.new("RGB", (1, 1), (r, g, b))
    xform = ImageCms.buildTransformFromOpenProfiles(srgb_prof, lab_prof, "RGB", "LAB")
    lab_img = ImageCms.applyTransform(img, xform)
    L_byte, a_byte, b_byte = lab_img.getpixel((0, 0))
    # Pillow encodes Lab: L in [0,255] -> [0,100]; a/b in [0,255] -> [-128,127]
    L  = L_byte * 100.0 / 255.0
    a  = a_byte - 128.0
    bv = b_byte - 128.0
    return (L, a, bv)

# -----------------------------------------------------------------------------

def main():
    rows = []
    for hx in TEST_HEXES:
        r, g, b = hex_to_rgb(hx)
        L50, a50, b50 = pillow_lab_d50(r, g, b)
        L65, a65, b65 = analytic_lab_d65(r, g, b)
        rows.append({
            "hex": hx,
            "rgb": [r, g, b],
            "lab_d50": [round(L50, 3), round(a50, 3), round(b50, 3)],
            "lab_d65": [round(L65, 6), round(a65, 6), round(b65, 6)],
        })
    out = Path("_verify/color_math_truth.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "source": "D50: ImageCms (LittleCMS D50 PCS); D65: analytic WP_D65",
        "rows": rows,
    }, indent=2))
    print(f"Wrote {out} with {len(rows)} test rows")

if __name__ == "__main__":
    main()
