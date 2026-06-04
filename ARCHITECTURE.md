# CMYK Swatch System: Architecture & Rebuild Guide

> Treat this file as authoritative. Everything in the project should be
> reproducible by reading this document. Code is the implementation;
> this doc is the contract.

---

## 0. System purpose

A browser tool backed by a small Python toolchain that helps a designer
pick CMYK colors and palettes that will print faithfully on a chosen press
profile (FOGRA39, Japan Color, SWOP, Mimaki 3DUJ, etc.), and produce
design-app-ready palette files (.ase / .gpl) plus per-swatch PNG manifests.

The single tool is `app/mixo-swatch.html` (Mixo Swatch). It explores the full CMYK
uniform grid through a chosen ICC profile so the user can hand-pick swatches.
Data is generated at runtime: CMYK lattice, LUT lookup, derived fields.

3D-print color matching is a supported use case via the same pipeline. The
Mimaki 3DUJ ICC profile sits alongside the offset profiles. The tool's ΔE
max filter (§7.5) provides round-trip safety for any selected profile,
including 3DUJ.

A zen landing at `index.html` links to the explorer. One Python script in
`scripts/` sits between the ICC binaries and the HTML.

---

## 1. Folder layout

```
cmyk/
|-- index.html                     Zen landing page
|-- app/
|   `-- mixo-swatch.html           Mixo Swatch (LUT-driven Mixo Swatch)
|-- scripts/
|   `-- gen_luts.py                Build CMYK->sRGB + sRGB->CMYK LUTs from ICCs
|-- data/                          Generated, mostly gitignored
|   |-- corpora/
|   |   `-- name_corpora.json      jp-trad + html + zh-trad named color corpora (committed, schema v3)
|   `-- luts/
|       |-- index.json             Profile manifest (consumed by the HTML)
|       |-- <profile>.lut          Forward LUT: CMYK->sRGB (17^4 x 3 bytes ~= 245 KB)
|       `-- <profile>.rcmyk.lut    Reverse LUT: sRGB->CMYK (17^3 x 4 bytes ~= 20 KB)
|-- icc/                           Gitignored: user supplies their own
|   |-- *.icc / *.icm              Source ICC profiles
|   `-- README.md                  Drop-zone explanation
|-- run.bat / run.sh               Local HTTP server launcher
|-- README.md                      Setup + usage
|-- ARCHITECTURE.md                This file
`-- .gitignore
```

`.git/`, `icc/*.icc`, and `data/luts/*.lut` are gitignored.
ICC profile binaries are not redistributable; the LUTs are derived from
them and can be either committed (for GitHub Pages hosting) or kept local.

---

## 2. Color theory used in this system

### 2.1 Color spaces

- **CMYK**: device-dependent. Four ink channels: Cyan, Magenta, Yellow, K (black). Each channel 0-100%. There is no "true" CMYK. The meaning of `(100, 0, 0, 0)` depends entirely on the press, paper, and ink. ICC profiles encode that meaning.
- **sRGB**: device-independent for the web. The displayed color. Two-decade-old standard, virtually all browsers and monitors map to it.
- **CIE Lab**: perceptually uniform color space. L*=lightness 0-100, a*=green vs red, b*=blue vs yellow. Used as the lingua franca for color math. Distances in Lab approximate perceived color difference. Two reference whites are in active use; see §2.7.
- **CIE LCh**: polar form of Lab. L*=lightness, C*=chroma (saturation), h=hue angle.

### 2.7 Color mode: D50 vs D65 (Bradford CAT)

ICC profiles natively use D50 as their Profile Connection Space (PCS) white point. sRGB is defined under D65. The tool ships two Lab conversion paths and a global `LAB_MODE` toggle (`'d50'` | `'d65'`) in the HTML:

- **`rgb2lab_d65`** (default for screen comparison): sRGB gamma expand -> XYZ D65 matrix -> adapt to D65 white. Used for corpora matching and ΔE comparisons where the reference is a screen-rendered hex value.
- **`rgb2lab_d50`** (print mode): the same XYZ D65 result is chromatically adapted to D50 via the Bradford 3x3 CAT before entering the Lab formula. Matches what a color management engine sees when it reads the LUT output into an ICC PCS.

Bradford CAT matrix (D65 to D50, applied to linear XYZ):

```
[Xd50]   [ 1.0478112  0.0228866 -0.0501270] [Xd65]
[Yd50] = [ 0.0295424  0.9904844 -0.0170491] [Yd65]
[Zd50]   [-0.0092345  0.0150436  0.7521316] [Zd65]
```

Every swatch and every corpus entry maintains two Lab caches: `lab_d65` and `lab_d50`. ΔE comparisons always use matching modes on both sides. The UI `LAB_MODE` control switches which cache feeds the ΔE and closest-name math. Switching mode triggers a full rematch pass.

When `LAB_MODE = 'd50'`, the tool mirrors the numeric Lab values that ICC-aware prepress software reports, making ΔE readings directly comparable to Photoshop Info panel values measured under relative colorimetric intent.

### 2.2 ΔE (Delta-E) variants used

- **ΔE 1976**: old, deprecated. Simple Euclidean in Lab.
- **ΔE 2000**: the standard. Corrects perceptual non-uniformity, especially in saturated and dark regions. We use it everywhere.

Reference thresholds:
| ΔE 2000 | Meaning |
|---|---|
| < 1.0 | Imperceptible to most viewers |
| 1.0-2.0 | Perceptible on close inspection; below ISO 12647-7 contract proof tolerance |
| ~2.0 | ISO 12647-7:2016 average contract-proof tolerance |
| ~3.0 | Commonly cited "just noticeable difference" for general viewers |
| > 5.0 | Clearly different colors |

### 2.3 ICC profiles

An ICC profile is a measured table mapping device coordinates (CMYK) to a
device-independent color space (Lab or XYZ) and back. It encodes:

- **A2B0**: Device to PCS (Profile Connection Space). For CMYK profiles, this is what 4-channel ink combinations actually look like under D50 light.
- **B2A0**: PCS to Device, the reverse. Used to compute "what CMYK to send to get this Lab".
- **Tone reproduction curves (TRC)** per channel.
- **Gray component replacement (GCR) / Under color removal (UCR)** rules embedded in the B2A table.

Two rendering intents matter for us:
- **Relative colorimetric**: out-of-gamut colors are clipped to the gamut boundary. Used for proofing, accurate color match. This is our default.
- **Perceptual**: entire gamut compressed proportionally. Used for photography.

GCR is the rule for how grayscale gets built. Pure-K means K-ink only.
Heavy GCR means K dominates the neutral axis. Light GCR means CMY mixes
form the neutrals. Different profiles take different stances. That is why
our two greyscale strips (see §5.3) look different.

### 2.4 Total Area Coverage (TAC)

`TAC = C + M + Y + K` as percentages. Maximum ink load.
Real presses limit:
| Press type | Typical TAC limit |
|---|---|
| Newsprint / uncoated | 220-260% |
| Coated commercial offset | 300-340% |
| Sheetfed coated | 320-360% |
| Mimaki 3DUJ (3D color print) | profile-dependent, usually <=300% |

Exceeding TAC causes ink not to dry, smudges, paper warping. We expose
TAC as a UI filter in the Mixo Swatch.

**Per-profile TAC defaults.** `data/luts/index.json` carries `tac_recommended` and `tac_max` per profile entry. Values are sourced from public specifications (proof.de press standards, Cummings Printing data). When the user switches profiles the tool snaps the TAC slider to `tac_recommended` for the new profile unless the user has already adjusted it manually. The sidebar also ships five quick preset buttons:

| Preset | tac_recommended | Notes |
|---|---|---|
| Newspaper / Uncoated | 220% | ISO newsprint |
| Uncoated coated | 260% | General uncoated offset |
| USWebCoatedSWOP | 300% | US web press |
| FOGRA39 / Coated | 330% | European sheetfed coated |
| JapanColor | 320% | Japanese offset coated |
| 3D-print (Mimaki 3DUJ) | 300% | Profile-specific; checkbox in UI |

The **3D-print preset** checkbox is a two-way toggle. It auto-checks itself whenever the live state already satisfies every 3D-print constraint (TAC <= 240%, dE max <= 2.0, profile filename matches `Uncoated | Newspaper | 3DUJ | Mimaki`). A manual click flips state:
- **Click on** (when conditions are not met): snapshot the current TAC / dE / profile, then force-fit the constraints (cap TAC, tighten dE, switch to a 3DUJ-safe proxy profile).
- **Click off** (when conditions are met): if a snapshot exists from a prior click-on, restore it. Otherwise the user reached the satisfied state organically by adjusting sliders and has no snapshot; in that case the toggle forces the inverse - switch to a coated offset profile (FOGRA39 / SWOP / JapanColor), open TAC to ~330%, and relax dE max to ~3.0 - so the toggle is always a meaningful two-way control.

### 2.5 K-tier philosophy (project-specific)

K-tier classification by black-ink percentage, used in the CMYK
explorer to label swatches:
| Tier | K range | Use case |
|---|---|---|
| 1 . Brand | K 0-25 | Clean, premium, reproducible. Default zone for logos and brand colors. |
| 2 . Support | K 26-50 | Secondary darks for depth. |
| 3 . Deep | K 51-100 | True charcoals, espresso, deep wine. When richness is intentional. |

Originally a UI default-filter (start at Tier 1, user widens). Was
removed as auto-default because it is a stylistic preference, not a
print-safety rule.

The HTML defaults to Tier 3 (show all). User clicks pills to narrow.

### 2.6 Gamut and "safe" swatches

A CMYK value is in-gamut if it survives a round-trip through the ICC:
1. CMYK to sRGB via A2B0
2. sRGB to CMYK via B2A0
3. CMYK to sRGB again
4. Compare Lab of step 1 output vs step 3 output via ΔE 2000

If step 1 was already at the gamut boundary, step 2's reverse-lookup
will clip, step 3 won't recover the original Lab, ΔE > 0. Higher ΔE
means deeper into out-of-gamut territory.

The explorer exposes this round-trip ΔE as `delta_e_print` on every swatch
and as the **ΔE max** filter slider (see §7.5). Setting the slider tight
(e.g. 2.0) hides swatches the chosen press cannot hold confidently. This
slider is the surviving safety mechanism for round-trip gamut control.
Pure neutrals (K-ramp) are always achievable on essentially every CMYK
press and are not gated by this slider.

---

## 3. Color math kernels

These are ported between Python (LUT generator) and JavaScript (the HTML).
Identical math both sides. Critical that they stay in sync.

### 3.1 sRGB to linear RGB

```
srgb_to_linear(u):
    u_norm = u / 255
    if u_norm <= 0.04045:
        return u_norm / 12.92
    return ((u_norm + 0.055) / 1.055) ** 2.4
```

### 3.2 linear RGB to CIE XYZ (D65)

```
[X] = [0.4124564 0.3575761 0.1804375] [R]
[Y]   [0.2126729 0.7151522 0.0721750] [G]
[Z]   [0.0193339 0.1191920 0.9503041] [B]
```

### 3.3 XYZ to Lab (dual white points)

The tool implements two variants (see §2.7):

**`rgb2lab_d65`**: D65 reference white (Xn=0.95047, Yn=1, Zn=1.08883)

```
f(t) = t^(1/3)            if t > 0.008856
       7.787 * t + 16/116  otherwise

L = 116 * f(Y/Yn) - 16
a = 500 * (f(X/Xn) - f(Y/Yn))
b = 200 * (f(Y/Yn) - f(Z/Zn))
```

**`rgb2lab_d50`**: apply Bradford CAT (§2.7) to the linear XYZ first, then feed D50 reference white (Xn=0.96422, Yn=1, Zn=0.82521) into the same f(t) formula above.

### 3.4 WCAG relative luminance + contrast

```
L_rel = 0.2126*srgb_to_linear(R) + 0.7152*srgb_to_linear(G) + 0.0722*srgb_to_linear(B)
contrast(L1, L2) = (max + 0.05) / (min + 0.05)
```

Used to pick text color (black vs white) for each swatch and tag WCAG
AA (>= 4.5:1) / AAA (>= 7.0:1) compliance.

### 3.5 ΔE 2000

The CIEDE2000 formula. Implemented identically in Python and JavaScript
(`deltaE2000` in the HTML). Both use degrees for hue angles and the
standard 14 correction terms. Inputs are always the same Lab space on
both sides of the comparison (D65 vs D65, or D50 vs D50, governed by
`LAB_MODE` - see §2.7).

### 3.6 Naive CMYK to RGB (DO NOT USE for color decisions)

```
R = 255 * (1 - C/100) * (1 - K/100)
G = 255 * (1 - M/100) * (1 - K/100)
B = 255 * (1 - Y/100) * (1 - K/100)
```

This is the formula early embedded RAW data used. **It is wrong for any
press.** It is included here only to document why the project moved off
it. The formula assumes ideal subtractive pigments; real ink behaves
differently. Use the ICC pipeline (§4) instead.

---

## 4. ICC pipeline: LUT generation

### 4.1 Why LUTs and not WASM ICC

Investigated `lcms-wasm` and similar. No clean prebuilt browser build
exists as of the build date. Compiling LittleCMS via Emscripten is
viable but adds a 30-60 minute build chain and ~1 MB wasm.

We chose **precomputed lookup tables** built by Python's Pillow (which
internally uses LittleCMS):
- Smaller payload (~250 KB forward + 20 KB reverse per profile)
- No browser-side ICC engine needed
- Identical color math to Pillow / LittleCMS, no approximation drift
- Limitation: only integer grid resolutions; we use 17 nodes per axis
  (interpolation error ~ΔE 0.3, perceptually invisible)

### 4.2 LUT binary format

**Forward (CMYK to sRGB)**: `*.lut`:
```
offset  size  content
0       4     ASCII "LUT4"
4       1     uint8 grid size (currently 17)
5       11    reserved zero padding (16-byte header total)
16      ...   row-major RGB triplets:
              for K in 0..16:
                for Y in 0..16:
                  for M in 0..16:
                    for C in 0..16:
                      uint8 R, uint8 G, uint8 B
              total = 17^4 * 3 = 250,563 bytes
```

Index formula: `idx = K * 17^3 + Y * 17^2 + M * 17 + C`

**Reverse (sRGB to CMYK)**: `*.rcmyk.lut`:
```
offset  size  content
0       4     ASCII "CMK4"
4       1     uint8 grid size (17)
5       11    reserved zero padding
16      ...   row-major CMYK quadruples:
              for R in 0..16:
                for G in 0..16:
                  for B in 0..16:
                    uint8 C, uint8 M, uint8 Y, uint8 K
              total = 17^3 * 4 = 19,652 bytes
```

Index: `idx = R * 17^2 + G * 17 + B`. Pillow returns 0-255 byte CMYK
which JS code rescales to 0-100% percent.

### 4.3 Quadrilinear interpolation

For arbitrary input CMYK(c, m, y, k) where each is in 0-100:

```javascript
N = 17; step = 100 / (N - 1)
fc = c/step; fm = m/step; fy = y/step; fk = k/step
c0 = floor(fc); c1 = c0 + 1 (clamped to N-1)
m0, m1, y0, y1, k0, k1: same
dc = fc - c0; dm, dy, dk: same

R = G = B = 0
for each of 16 corners (c_i,m_i,y_i,k_i):
    weight = wk * wy * wm * wc  (each ws = ds if upper else 1-ds)
    idx = k_corner * N^3 + y_corner * N^2 + m_corner * N + c_corner
    R += lut[idx*3 + 0] * weight
    G += lut[idx*3 + 1] * weight
    B += lut[idx*3 + 2] * weight

return [round(R), round(G), round(B)]
```

Reverse LUT uses trilinear (3D not 4D) since input is RGB. Same logic.

### 4.4 `gen_luts.py` responsibilities

For each `icc/*.icc` / `*.icm` found:
1. Test if it's a CMYK output profile (`is_cmyk`)
2. Skip RGB-only working spaces (AdobeRGB, sRGB)
3. Build forward LUT: sample CMYK grid, push through ImageCms transform with Relative Colorimetric intent, write binary
4. Build reverse LUT: sample sRGB grid, push through ImageCms transform, write binary
5. Write `data/luts/index.json` manifest:
   ```json
   {
     "format": "icc.index/v1",
     "grid": 17,
     "lut_header_bytes": 16,
     "profiles": [
       {
         "filename": "CoatedFOGRA39.icc",
         "label": "Tier 3 . Coated FOGRA39",
         "kind": "cmyk",
         "lut": "luts/CoatedFOGRA39.lut",
         "lut_bytes": 250579
       }
     ]
   }
   ```

The display label comes from `TIERS` patterns in `gen_luts.py`. Order
matters because `fnmatch` is greedy. Uncoated patterns must come before
Coated patterns to avoid the substring "Uncoated...Coated" being matched
as Coated.

`--force` rebuilds even when timestamps say up-to-date.
`gen_luts.py SINGLE.icc` builds just one.

---

## 5. Greyscale rendering (in-browser)

The Mixo Swatch renders two greyscale strips below the main grid using
the live LUTs. No precomputed library is needed; both strips are derived
at runtime from the active profile's forward and reverse LUTs.

### 5.1 Neutral ramp (ICC-routed)

For pct = 0, 10, ..., 100, target gray = sRGB(255-pct%, ...). Reverse-LUT
to CMYK, forward-LUT back to RGB. This shows what the press actually
hits when asked to render gray via its GCR rules.

### 5.2 Pure K-only sweep

For K = 0, 10, ..., 100, look up CMYK(0, 0, 0, K) via the forward LUT.
This shows K-channel-only behavior.

### 5.3 Why two strips

The two visibly diverge. Most profiles' neutral path mixes some CMY,
their pure-K path drifts warm or cool. This divergence is the reason
print-color work should look at both: the choice of which gray model to
use influences how shadows and dark tones print. The same divergence
appears in 3D-print profiles such as Mimaki 3DUJ.

---

## 6. Name corpora (`data/corpora/name_corpora.json`)

### 6.1 Schema v3 (current)

Per-library the JSON declares an `id`, a tri-lingual `label` object
(`{en, ja, zh}`), an ordered `fields[]` array (each entry's displayable
name fields), a `default_display`, an `anchor` (`hex` or `cmyk`), and an
`entries[]` list. Each entry carries tri-lingual name fields plus optional
transliteration.

```json
{
  "version": 3,
  "schema_rev": "3.0",
  "corpora": [
    {
      "id": "jp-trad",
      "label": { "en": "Japanese traditional", "ja": "日本の伝統色", "zh": "日本傳統色" },
      "fields": [
        { "id": "name_ja",  "label": { "en": "kanji",  "ja": "漢字", "zh": "漢字" } },
        { "id": "romaji",   "label": { "en": "romaji", "ja": "ローマ字", "zh": "羅馬字" } },
        { "id": "name_en",  "label": { "en": "english","ja": "英語", "zh": "英語" } }
      ],
      "default_display": "name_ja",
      "anchor": "hex",
      "entries": [
        {
          "name_ja": "桜色", "name_en": "Sakura Pink", "name_zh": "櫻花色",
          "romaji": "sakura-iro", "hex": "#FCC9D2"
        }
      ]
    }
  ]
}
```

**Tri-lingual fields per entry.** Each entry carries `name_en`, `name_ja`,
and `name_zh`. Entries that originally had only one language leave the
other two as empty strings `""`. The loader fills empty strings with
fallback rules:
- If `name_zh` is `""`, fall back to `name_en` for Chinese display.
- If `name_en` is `""`, fall back to `name_ja` for English display.
- `name_ja` is never empty in the Japanese and Chinese corpora; it may be
  empty for the html corpus (which uses `name_en` as primary).

**Transliteration fields.** Japanese entries carry `romaji`; Chinese entries
carry `pinyin`. Both are optional.

Per-entry attributes:
- `hex`: sRGB anchor (`#RRGGBB`). Used directly: hex to Lab (in the active
  `LAB_MODE`) to ΔE.
- `cmyk`: 4 ints 0..100. Routed through the active forward ICC LUT
  (CMYK to sRGB to Lab) before matching.
- Any declared `fields[]` member (`name_en`, `name_ja`, `name_zh`,
  `romaji`, `pinyin`, etc.).

The displayed swatch color always comes from the swatch's own
LUT-computed sRGB. The corpus `hex` / `cmyk` values are match anchors
only.

**Active corpora (v3 ship):**

| ID | Source | Anchor | Entries |
|---|---|---|---|
| `jp-trad` | NipponColors.com (250 traditional Japanese colors) | hex | 250 |
| `html` | W3C CSS Color Module Level 4 canonical hex | hex | 148 |
| `zh-trad` | Chinese traditional color corpus | hex | 526 |

Backward compatibility: the loader accepts v2 / v2.1 corpora (with
`primary` / `secondary` fields and the legacy `{ "jpn": [...], "html": [...] }`
shape) and auto-promotes them to v3 on read.

### 6.2 Matching algorithm

For each loaded library, each swatch gets a match:

```js
sw.matches[lib.id] = {
  entry,      // ref to the winning corpus entry
  deltaE,     // ΔE 2000 between sw and the entry's Lab (in active LAB_MODE)
  anchor,     // 'hex' or 'cmyk': which attribute drove the match
};
```

The rendered text for any field is `m.entry[fieldId]`, looked up at
draw time via `_libDisplayField(libId)` (which honors the user's per-
library radio selection).

**Dynamic library IDs.** Swatch records store match data under
`s[\`${lib.id}__name\`]`, `s[\`${lib.id}__closest\`]`, and
`s[\`${lib.id}__deltaE\`]`. No hardcoded `jpn_*` or `html_*` field names
exist; all paths are derived from `lib.id` at runtime.

**Per-(lib, entry) uniqueness with tiebreak.** When multiple swatches
tie on ΔE to the same corpus entry, the `_markClosest` pass uses a
deterministic tiebreak: lower TAC wins; if still tied, lower K wins; if
still tied, lower array index wins. This replaces the old `system_name` /
`HUE_NAMES` / bin-threshold approach entirely.

### 6.3 Per-library UI

Two sidebar sections, both built dynamically from `CORPORA.libraries`:

**"Named swatches - filter"**: independent of the display setting.
Master "All libraries" checkbox plus one checkbox per library. When the
filter pill is set to "Any named", a swatch passes the filter if and
only if it matches a name in at least one checked library.

**"Naming - per library"**: one row per library:
- A radio group with one button per declared field in `lib.fields[]` plus
  a `hide` option. The selected radio is the field rendered on the cell.
- An anchor `<select>` (`hex` / `cmyk`) when the library has at least one
  entry carrying both attributes. Flipping the anchor triggers a full
  rematch (heavy but acceptable on explicit user action).

State is part of `cmykUIState_v2` under `corpora_prefs[lib.id]` with
keys `display`, `anchor`, and `filter_enabled`. The "Reset UI to
defaults" button (§6.5) clears these along with the rest of UI state.

The detail card chip pass is independent of the cell display radio: it
shows every field of the matched entry for every library (no hiding),
so the user can always see the full corpus context for a swatch.

**Global anchor + dE tolerance.** A link badge in the header allows the
user to lock the anchor mode globally (applies to all libraries) or set
a global dE tolerance that relaxes the named-filter threshold without
opening individual library dialogs.

### 6.4 Edit workflow

1. Open `data/corpora/name_corpora.json` in any text editor (save UTF-8).
2. Add a new corpus to the `corpora` array, or append entries to an
   existing one. Follow the v3 schema: tri-lingual `label` object,
   tri-lingual `name_en`/`name_ja`/`name_zh` per entry.
3. Save and refresh the browser. No Python rebuild needed. Lab is
   computed in the browser on load (in both D50 and D65 modes).

### 6.5 UI defaults + reset (`data/ui_defaults.json`)

The HTML ships with a single `data/ui_defaults.json` that controls
the factory defaults applied on first run. Current shipped values:

```json
{
  "cmyk_explorer": {
    "step": 20, "cell_size": 80, "view_mode": "grid",
    "sort_mode": "hue", "k_tier": 3, "named_filter": "any",
    "wcag_aa": false, "wcag_aaa": false,
    "white_text_only": false, "black_text_only": false,
    "search": "",
    "cmyk_range": { "c": [0,100], "m": [0,100], "y": [0,100], "k": [0,80] },
    "tac_max": 240,
    "delta_e_max": 0.6,
    "default_profile_match": "UncoatedFOGRA29",
    "active_palette_id": null,
    "lab_mode": "d50",
    "gamut_safe_only": false,
    "palette_panel_open": false,
    "ui_lang": "auto",
    "corpora_prefs": {
      "_global": { "anchor": "cmyk", "tolerance": 5.5 },
      "jp-trad": { "display": "name_ja" },
      "html":    { "display": "name_en" },
      "zh-trad": { "display": "name_zh" }
    }
  }
}
```

**Default-state intent.** Factory defaults are tuned for the print-first
workflow on a coated press:

- `step: 20` and `cell_size: 80` keep the first paint fast (<1300 swatches)
  and labels legible.
- `tac_max: 240` snaps to a conservative coated-uncoated bracket; the
  per-profile presets (260 / 300 / 330 / 350) override.
- `delta_e_max: 0.6` hides any swatch the active profile cannot round-trip
  within 0.6 dE - tight by intent, so the user immediately sees only
  press-safe swatches and widens the slider as needed.
- `cmyk_range.k: [0,80]` discards K=85-100 which are functionally identical
  to pure black on most coated presses and rarely useful for brand work.
- `named_filter: "any"` plus the per-library checkboxes (all on by default)
  surface only swatches that hit a named entry in at least one corpus -
  paired with `tolerance: 5.5` this keeps the grid useful out of the box.
- `lab_mode: "d50"` mirrors the ICC Profile Connection Space whitepoint
  used by Photoshop / InDesign Info panel readings.
- `default_profile_match: "UncoatedFOGRA29"` is the closest bundled
  proxy for Mimaki 3DUJ when no genuine 3DUJ ICC is supplied. Gamut
  approximately 78 % of FOGRA39 coated (within ~5 % of measured 3DUJ
  gamut), TAC recommended 260 % sits inside the Mimaki safe zone
  (240-280), and the warm-neutral axis tracks resin yellow-cast better
  than any coated profile. ECI cross-media workflows reach for
  UncoatedFOGRA29 in the same sample-then-tune role.
  `populateProfileSelect()` searches the manifest with this string
  (case-insensitive) and falls back to FOGRA39 then the first profile
  if the match is absent.

**Two Mimaki workflows, two right answers.** Mimaki's own RasterLink /
MPM3 RIP documentation recommends sRGB IEC61966-2.1 input for
**texture-map / 3D-asset** authoring (Substance Painter, ZBrush
PolyPaint, Blender, Maya - everything that produces sRGB-tagged
texture maps). The RIP's proprietary multi-channel engine (CMYK +
White + Clear, optionally Lc / Lm) compresses sRGB into 3DUJ ink
space intelligently and avoids the double-conversion you'd get from
user-CMYK input. Mixo Swatch does **not** serve that workflow - it
is not a texture authoring tool.

Mixo Swatch serves the **spot-color / brand-palette** workflow:
choosing a small set of named or branded colors that need explicit
gamut decisions and visibility. For spot colors the sRGB path is
wrong because the RIP's perceptual intent compresses brand colors
silently. The correct path is CMYK pre-routed through a 3DUJ-like
ICC + the round-trip dE gate, which is what Mixo Swatch does.
- `ui_lang: "auto"` reads `navigator.language` on first run: `ja*` -> ja,
  `zh*` -> zh-Hant, anything else -> en. Persisted under
  `localStorage['ui_lang']` once the user picks from the topbar menu.

**localStorage key: `cmykUIState_v2`.** The tool writes all UI state
to this key. On first load (key absent), defaults from `ui_defaults.json`
are applied. A v1-to-v2 migration runs at startup: if `cmykUIState_v1`
is present and `cmykUIState_v2` is absent, the v1 object is read,
`corpora_prefs` is reshaped from the old flat structure (keyed by
`jpn`/`html`) to the new structure (keyed by `jp-trad`/`html`/`zh-trad`),
and written under `cmykUIState_v2`. The `cmykUIState_v1` key is left
intact for downgrade safety.

Runtime layering:
1. Load `data/ui_defaults.json`.
2. Run v1->v2 migration if needed.
3. Load `localStorage[cmykUIState_v2]` (everything the user
   changed since last visit).
4. Merge: defaults < user state. User state wins per-key.
5. Apply to live vars + DOM controls + `CORPORA_PREFS` before first
   render.
6. Sidebar-wide delegated listener (`change` + `input`) persists the
   snapshot on every control flip.

The **"Reset UI to defaults"** sidebar button:
- Removes the `cmykUIState_v2` localStorage key.
- Re-applies the JSON defaults.
- Rebuilds the Naming UI.
- Triggers a full rebuild / rematch.

Palette localStorage keys (`cmykPalettes_v1`) are **never** touched by
the reset.

### 6.6 UI internationalisation (en / ja / zh-Hant)

The tool ships a built-in i18n layer covering every sidebar label,
top-bar button, palette-panel string, and dynamic mode badge.

**Languages supported:** English (`en`), Japanese (`ja`), Traditional
Chinese (`zh`, rendered with `<html lang="zh-Hant">`).

**Auto-detect rule.** On first run the page reads
`navigator.languages` (falls back to `navigator.language`) and matches
the prefix: `ja*` -> `ja`, `zh*` (any variant) -> `zh`, anything else ->
`en`. The detected value is what the UI displays; the user's explicit
choice in the top-right dropdown (`#langPickerBtn`) overrides and
persists under `localStorage['ui_lang']`. Selecting "Auto" restores the
detection.

**Markup contract.** Every translatable element carries a
`data-i18n="<key>"` attribute. `applyI18n()` walks every such element on
language switch and replaces its `textContent` with `t(key)`. Elements
with state-dependent text (the Lab mode badge, the palette open/close
button) are updated by hand inside `applyI18n` after the walk.

**Translation table.** `I18N` is an in-script object keyed by lang code,
with one entry per `data-i18n` key. Adding a translation = adding the
key + string to all three languages. Keys are namespaced
(`sec.tac`, `sort.huelight`, `tier.t1.name`, etc.). Untranslated keys
fall back to the `en` value, then to the original `textContent` -
nothing ever renders blank.

**Re-render on switch.** `applyI18n` calls `buildNamingUI()` and
`buildFilterUI()` so dynamically-built corpus rows (which bake corpus
`label.{en|ja|zh}` into strings at build time) refresh in the new
language. The currently-active language is read from `UI_LANG` whenever
those builders run.

### 6.7 Null-active palette

`activeId === null` is a first-class state in the HTML. The palette
dropdown carries a "no palette selected" placeholder. Select-mode
clicks with no active palette prompt the user to create one or pick
one before adding swatches. Deleting the last palette leaves
`activeId === null` rather than auto-creating a replacement.

---

## 7. HTML data pipeline (Mixo Swatch)

### 7.1 Lifecycle

1. **Page load**: bootstrap `window.addEventListener('load', ...)`:
   - Detect `file://` protocol; if so, show error pointing to `run.bat`
   - `loadPalettes()`: pull saved palettes from `localStorage['cmykPalettes_v1']`
   - `loadIndex()`: fetch `data/luts/index.json`, populate profile dropdown
   - `loadCorpora()`: fetch `data/corpora/name_corpora.json`, precompute Lab for each entry
   - `populateProfileSelect()`: fill the dropdown, default to FOGRA39
   - `rebuildAll()`: generate lattice, fetch LUTs, derive per-swatch fields, render

2. **`rebuildAll()`** (called on profile change OR step change):
   - `genLattice(curStep)`: produce CMYK lattice (step 10 gives 14,641 entries; step 5 gives 1.3M, only feasible if K-tier filter narrows)
   - `loadLUT(forward)` + `loadRLUT(reverse)`: fetch + cache binary
   - `deriveSwatch(s, lut)` per swatch:
     - `lutLookup(lut, C, M, Y, K)` to R, G, B
     - hex via standard
     - `rgb2lab` to L_star, a_star, b_star
     - WCAG luminance, contrast against black + white, pick the higher
     - `kTier(K)` to tier 1/2/3 + name
     - `tac = C + M + Y + K`
     - `grayscale = (C==0 && M==0 && Y==0)`
   - `delta_e_print`: `deltaERoundTrip(s, fwdLut, revLut)` (round-trip ΔE)
   - `matchNearest(s)`: find closest entry in each active library;
     populates `s.matches[lib.id]` for every lib in `CORPORA.libraries`
   - Dedupe by `C|M|Y|K` (defensive; lattice shouldn't dup)
   - Split into `MAIN_DATA` (non-K-only) + `GS_DATA` (K-only)
   - `_markClosest(lib.id)` for each active library (TAC/K/index tiebreak)
   - `render()`

3. **`render()`**: pick view mode:
   - `grid`: call the virtualized grid renderer
   - `huelight`: `renderHueLightMap()`
   - `palettes`: `renderPaletteMode()`

### 7.2 Virtualized grid renderer

DOM size in step-10 would be ~11,000 cells if naive. Browser dies.
Virtualization:
- Compute `rows = ceil(data.length / cols)` and `rowH = cellSize + gap`
- Container = `position:relative`, fixed height = `rows * rowH`
- Only paint cells in `viewportScrollTop +/- 6 rows`
- Use absolute positioning per cell (`left:col*step px; top:row*step px`)
- Bind one rAF-throttled scroll listener
- Cache `_lastWindow` to skip repaint when window unchanged

Shared cell-build helper `_makeSwatchCell(sw, ctx)` is used by:
- Main virtualized renderer
- Hue x Light map renderer (so info labels also appear there)

### 7.3 Two greyscale strips

Below the main grid. See §5 for the renderer details.

### 7.4 View modes

- **Grid**: virtualized swatch grid (default)
- **Palettes**: list of saved palette panels with per-palette actions
  (rename, duplicate, clear, delete, PNG, ASE, GPL, JSON, ZIP)

2-button group at the top: `[Grid] [Palettes]`.

**Hue x Light** is not a separate view mode. It is a sort option in the
**Sort by** row: selecting "Hue x Light" renders the 18 hue x 10 light
bucket map inline into the main swatch grid area (`#swatchGrid`), using
the full available width of `#gridScroll`. The renderer overrides the
default `.swatch-grid` padding / justify so the bucket grid fills the
container; columns are `repeat(10, minmax(0, 1fr))` and inner padding
collapses on narrow viewports (4 px under 768 px, 10 px otherwise).
Cells use `aspect-ratio: 1/1`, so they shrink-to-fit responsively as
the viewport changes; the resize listener (§7.5) debounces re-render
to 120 ms.

**Palettes panel.** The Palettes block and the palette-manager (`pm-wrap`)
are merged into a single collapsable panel that sits above the grid. The
panel is collapsed by default. The header is a clear button row: title on
the left, a high-contrast accent button (`#ppAction`) on the right
labelled "Open palettes" / "Close palettes" - the legacy disclosure
triangle (`.chev`) was removed because the affordance was too subtle.

**Hue x Light lives inside the main swatch grid area.** The Hue x Light
sort option renders into `#swatchGrid` (full grid-area width). When the
sort is active, `gsWrap` (the two greyscale strips block) is hidden so
the bucket map gets the entire vertical real estate. The Palettes panel
above the grid is left in whatever state the user last set it - there
is no auto-open coupling between Hue x Light and the Palettes panel.

### 7.5 Filters

Applied in `filtered()`:
- CMYK range sliders (4 channels x min/max). K factory default
  `[0, 80]`; the other three default `[0, 100]`.
- TAC limit slider (factory default 240%; per-profile presets snap)
- K-tier (factory default Tier 3 = all)
- **dE max** slider: hides swatches whose round-trip `delta_e_print`
  exceeds the threshold. Factory default 0.6 dE (tight, surfaces only
  press-safe swatches on the active profile - including Mimaki 3DUJ).
  This is the surviving round-trip safety mechanism.
- Named source pills (factory default `Any named`; per-library checkboxes
  all on by default)
- Name tolerance slider (dE allowance for non-closest swatches to also
  display the name; factory default 5.5)
- WCAG AA / AAA toggles (all OFF by default)
- White-text-only / Black-text-only toggles (all OFF by default)
- Search box (case-insensitive substring against all name fields + hex;
  140 ms debounced to avoid per-keystroke render churn)

Sort: hue (default), light, TAC, cyan-only, chroma, safety (round-trip
dE), Hue x Light.

**Panel-input lag mitigation.**
- `_debouncedSearch()` collapses keystroke bursts (140 ms).
- `_scheduleRender()` rAF-coalesces multiple `onFilter`/sort/checkbox
  events into one paint per frame.
- `_schedulePersist()` rAF-coalesces sidebar `input`+`change` events
  into one `localStorage` write per frame.
- Heavy rematch on anchor / Lab-mode flip is chunked at 1500
  swatches/batch with a progress overlay (`_showProgress`).
- `setStep` debounces `rebuildAll` (180 ms) so rapid step-pill clicks
  collapse to a single rebuild on the final value.
- The window `resize` listener debounces `render` (120 ms) so a single
  drag never queues N renders.
- `_clampDual(id, movedEl)` only snaps the moved thumb against the
  stationary thumb (passes `this` from the `oninput` attribute) -
  previously both thumbs collapsed to a single value when the user
  crossed them.
- `togglePaletteMode` cycles `grid <-> palettes` only; the obsolete
  `huelight` token (a sort option, not a view mode) was removed from
  the cycle.

### 7.6 Palettes

localStorage key: `cmykPalettes_v1`.

JSON shape:
```json
{
  "format": "cmyk.palettes/v1",
  "exported": "2026-...",
  "palettes": [
    {
      "id": "abc123",
      "name": "Brand 2026",
      "created": 17000000,
      "updated": 17000000,
      "swatches": [
        {"C": 20, "M": 10, "Y": 0, "K": 5, "hex": "#C0D9F2", "R": 192,
         "jp-trad__name": "水色", "jp-trad__closest": true, "jp-trad__deltaE": 1.4,
         "html__name": "lightsteelblue", "html__closest": false, "html__deltaE": 3.1}
      ]
    }
  ]
}
```

Import: file picker, parse, merge (existing kept) or replace (active
palette overwritten).

### 7.7 Exports

| Button | Function | Output |
|---|---|---|
| CSV | `exportCSV()` | UTF-8 BOM CSV of filtered swatches |
| PNG (topbar) | `exportPNG()` | Square fit-square PNG of filtered set with title band + per-cell labels |
| PNG pure (topbar) | `exportFilteredPurePNG()` | 4096 x 4096 pure-color PNG of filtered set. No title band, no labels, no borders, no gap |
| PNG (labelled) | `exportActivePalettePNGSized()` | Palette PNG at 1024/2048/4096, full labels |
| PNG (pure) | `exportActivePalettePNGPure()` | Palette PNG at chosen size, swatches only |
| ZIP (palette) | `exportActivePaletteZIP()` | Per-swatch 128x128 PNGs + manifest.txt/csv/json |
| ZIP (swatch) | `exportSwatchZIP(sw)` | Single swatch: 128x128 PNG + name card, from the detail popover |
| ASE | `exportActivePaletteASE()` | Adobe Swatch Exchange |
| GPL | `exportActivePaletteGPL()` | GIMP Palette |

ZIP writer is pure JS, STORE-only (no compression), ~150 LOC including
CRC-32 table. PNG data is already deflate-compressed internally so
STORE is fine.

### 7.8 ASE binary format (`buildASE`)

Adobe Swatch Exchange. Reverse-engineered (no official public spec).
Big-endian throughout:

```
"ASEF"                            4 bytes  magic
0x0001 0x0000                     4 bytes  version 1.0
uint32                            block count
repeat: blocks
  uint16  block type
            0xC001 group start
            0xC002 group end
            0x0001 color
  uint32  block length (body bytes)
  body:
    for group start:
      uint16 name length (chars incl null)
      UTF-16BE name + null terminator
    for color:
      uint16 name length (chars incl null)
      UTF-16BE name + null terminator
      "RGB "                       4 bytes
      float32 BE                   R [0..1]
      float32 BE                   G [0..1]
      float32 BE                   B [0..1]
      uint16  color type (0=global, 1=spot, 2=normal)
```

The JS implementation uses `DataView` for big-endian writes and a manual
UTF-16BE encoder.

### 7.9 GPL format

GIMP Palette. Plain text. Forgiving format:

```
GIMP Palette
Name: <title>
Columns: 8
# Generated by ...
# Profile: ...
255 255 255	white
200 100  50	burnt-orange
```

Whitespace-separated R G B integers, tab, name.

---

## 8. UI / UX rationale (decisions, not just facts)

### 8.1 Why a single tool

The system used to ship two HTMLs: an open Mixo Swatch and a curated
print-safe library viewer. The library viewer was deprecated once the
explorer grew a ΔE max slider (§7.5) that delivers the same round-trip
safety on the live LUT pipeline. One tool removes the mental model
split between "explore everything" and "show me safe colors".

### 8.2 Why a virtualized DOM grid (vs canvas)

Canvas wins on raw paint speed but loses:
- Per-cell hover transform animation (CSS effect)
- Per-cell click outlines (`in-palette` ring)
- Native a11y (screen readers see DOM cells)
- Easy palette-marker swap via classList

Virtualization gives near-canvas paint perf while keeping DOM ergonomics
for the typical step-10 workload (~14k swatches, ~500 cells in DOM).

### 8.3 Why content-visibility:auto AND virtualization

`content-visibility:auto` is a defense-in-depth for the in-DOM cells:
even within the visible viewport, paint cost stays low. Cells getting
scrolled into view paint at the last possible moment.

### 8.4 Why the K-tier filter defaults to "all"

Originally defaulted to Tier 1 (Brand, K <= 25) as an anti-AI-purple
"low K by default" heuristic. Confusing for a tool whose purpose is open
exploration. Now: filter is a user choice, defaults open, narrow via UI
pills if you want a low-K subset.

### 8.5 Why two greyscale strips

A single strip labelled "K-only" was the wrong abstraction. Real CMYK
presses can hit the neutral axis two completely different ways
(GCR-mixed CMY+K vs literal K-only). Both are valid; their behavior
diverges visibly; users designing for 3D-print specifically need both
for reference.

### 8.6 Why responsive cell sizing in Hue x Light

The map is fixed at 18 hue x 10 light buckets. At large cell sizes
(say 160 px) the map's natural width is 2,880+ px, easily wider than
most viewports. Rather than horizontal-scroll (frustrating UX) we
shrink-to-fit while preserving labels where they fit.

### 8.7 Why no DIC / Pantone upload

DIC and Pantone are trademarked color systems. Their hex equivalents
are not freely redistributable. The previous UI had a CSV upload path
which was useful but also a server-side abuse surface if hosted. We
removed the upload path entirely; the JSON corpus can be hand-edited
to add private color systems offline.

### 8.8 Why no ICC upload via UI

Same reason: server-side file upload is an abuse surface. The whole
ICC pipeline runs locally via Python anyway. Drop the .icc file in,
run one script, refresh. That is the workflow.

### 8.9 Why button-group mode switcher

Two modes (Grid / Palettes) use a segmented button group. Hue x Light
moved to Sort by (§7.4), so a three-button group was no longer necessary.
The two-button group is more compact and the Hue x Light option is now
adjacent to the other sort options where it belongs semantically.

### 8.10 UI consolidation rationale (Spec 6)

Several UI changes were bundled in Spec 6 to reduce sidebar surface area:

- **Hue x Light -> Sort by**: bringing a layout-style view into the sort
  row eliminates a mode-switch and makes it composable with filters.
- **Palettes collapsable panel**: the split between the palette dropdown
  and the palette-manager panel was confusing. One collapsable panel with
  a clear header reduces the mental model.
- **Per-swatch ZIP**: previously export required selecting a palette. The
  per-swatch ZIP lets the user export a single color directly from its
  detail card without creating a palette.
- **Light + dark theme with topbar toggle**: the app ships both themes and
  honors `prefers-color-scheme` on first run; an explicit topbar toggle
  (`#themeToggleBtn`) overrides and persists under
  `localStorage['ui_theme']`. The light palette mirrors `index.html` token
  for token (warm paper / brand-tan accent / espresso text). The topbar
  logo swaps between `img/logo.svg` (white-on-dark) and `img/logo-black.svg`
  (black-on-light) so the mark stays legible across themes.
- **Responsive breakpoints (1024 / 768 / 480)**: sidebar becomes a
  drawer at 1024px, triggered by a hamburger button. At 768px the grid
  columns narrow. At 480px single-column layout with full-width controls.

---

## 9. Performance budget

| Operation | Target | Method |
|---|---|---|
| Initial page load | < 200 ms | LUT lazy-fetched, corpora ~3 KB |
| Profile switch (step 10) | < 200 ms | LUT fetch + derive 14k swatches |
| Profile switch (step 5) | < 1.5 s | Chunked w/ rAF |
| Filter slider drag | rAF-batched | `render()` only repaints viewport |
| Scroll | 60 fps | rAF-throttled paint, _lastWindow cache |
| PNG export 4096^2 | ~2 s | One-shot canvas, no virtualization |
| ZIP build (50 swatches) | < 200 ms | Pure JS, STORE-only |

If step 5 ever feels too slow at default profile, raise initial
TAC limit lower or cap K-tier to bring count down before profile
recompute.

---

## 10. How to rebuild the project from scratch

Assume a fresh empty folder.

### 10.1 Install dependencies

```bash
pip install pillow      # ImageCms (LittleCMS Python binding)
```

### 10.2 Get ICC profiles

Drop CMYK profiles into `icc/`. Free sources:
- Adobe ICC Profiles end-user license: includes CoatedFOGRA39.icc, JapanColor2001Coated.icc, USWebCoatedSWOP.icc
- ECI ISOcoated_v2_eci.icc: modern Fogra-derived, www.eci.org
- Mimaki 3DUJ profile: from RasterLink / MPM3 with hardware

### 10.3 Build LUTs

```bash
python scripts/gen_luts.py
```

Reads every `.icc`/`.icm` in `icc/`, builds forward + reverse LUTs,
writes `data/luts/index.json`. Skips RGB-only working spaces.

### 10.4 Build name corpora

`data/corpora/name_corpora.json` is committed and ready to use. It
ships with three active corpora in schema v3 format (see §6.1):

- `jp-trad`: 250 NipponColors.com Japanese traditional colors
- `html`: 148 W3C CSS Color Module Level 4 canonical named colors
- `zh-trad`: 526 Chinese traditional colors

To add a corpus, edit the JSON per the v3 schema in §6.1 and refresh the
browser. Even an empty corpora array lets the HTML load; it just won't
have nearest-name matches.

### 10.5 Build the HTML

The HTML is self-contained, no build step. Compose:

1. **Color math** (§3.1-3.5) ported to JS once
2. **LUT engine** (§4.3): `loadLUT`, `lutLookup`, `loadRLUT`, `rlutLookup`
3. **Lattice generator + per-swatch derivation** (§7.1)
4. **Name matcher** (§6): `matchNearest`, `_markClosest` (dynamic lib IDs)
5. **Filters + sort** (§7.5), including ΔE max and the Hue x Light sort
6. **Virtualized grid + cell builder** (§7.2)
7. **Two greyscale strips** (§5): neutral via reverse+forward
   round-trip; pure-K via forward only
8. **Hue x Light sort** (§7.4) rendered inline, responsive cell sizing (§8.6)
9. **Palette CRUD + collapsable panel** (§7.6) with localStorage persistence
10. **Exports** (§7.7): CSV, PNG sized, PNG pure, ZIP (palette + per-swatch), ASE, GPL
11. **Tooltips** on every control (laymen friendly, not jargon)
12. **2-button mode switcher** (§8.9)

### 10.6 Run the stack locally

```bash
# Windows
run.bat
# Mac / Linux
bash run.sh
```

Starts `python -m http.server 8765` and opens `index.html` (the zen
landing) in the default browser. The HTML fetches its config via HTTP
so `file://` won't work (security restriction).

### 10.7 Deploy

Drop the folder onto GitHub Pages or any static host. ICCs stay
`.gitignore`d (license reasons); LUTs can be committed with `git add -f`
if you want them served alongside the HTML.

For password protection on a self-hosted Apache box, use cPanel
Directory Privacy (`.htaccess` / `.htpasswd`). No HTML changes needed.

---

## 11. Failure modes and recovery

| Symptom | Likely cause | Fix |
|---|---|---|
| Browser hangs on load | Embedded RAW data | Drop the embedded const, refetch profiles + corpora |
| Cyan / magenta look pure RGB | Naive math, no ICC | Confirm LUTs exist + index.json fetched |
| All counts wrong | K-tier filter on | Set Tier pill to 3 (all) |
| ΔE max slider hides everything | Threshold too tight for profile | Raise the slider; check the profile's typical round-trip ΔE distribution |
| ZIP corrupt | CRC-32 buggy | Verify table-based impl, EOCD offsets |
| ASE rejected by Photoshop | UTF-16BE name length wrong | Ensure char count INCLUDES null terminator |
| Hue x Light overflows | Fixed `cs px` columns | Compute `fitCs = floor((avail - gaps)/18)`, use min |
| `file://` blocks fetch | Wrong launch path | Use `run.bat` / `run.sh` |
| Console: "palSet already declared" | Same `const` twice in `renderGS` | Reuse the outer declaration; don't redeclare in the pure-K block |

---

## 12. Conscious omissions and future work

- **No Mimaki 3DUJ ICC** is bundled. The pipeline supports it when the
  user supplies one. Without it, FOGRA39 is the closest proxy and will
  behave noticeably different on neutrals.
- **No WASM ICC engine**. LUT interpolation is ~ΔE 0.3 vs full ICC.
  Future: vendor `lcms2.wasm` if a clean browser build appears.
- **No proper visualization of TAC limit zone**. Currently a filter
  only. Could highlight at-risk swatches in the grid.
- **No Mac Catalyst / iPad palette sync**. localStorage is per-browser.
- **No diff view across profiles**. Could show a swatch's behavior
  side-by-side under 2-3 profiles at once.
- **LAB_MODE toggle is global**. A per-library or per-corpus mode
  (some corpora authored under D65, others under D50) is not supported.
  All corpora use the same LAB_MODE for matching.

---

## 13. Glossary

| Term | Meaning |
|---|---|
| A2B0 | ICC device to PCS LUT |
| B2A0 | ICC PCS to device LUT |
| GCR | Gray Component Replacement |
| UCR | Under Color Removal |
| TAC | Total Area Coverage |
| TRC | Tone Reproduction Curve |
| ΔE | Color difference, perceptually weighted |
| PCS | Profile Connection Space (Lab or XYZ) |
| Round-trip | Forward + reverse transform applied to measure gamut |
| Safe | Within ΔE acceptance gate after round-trip |
| K-tier | Project-specific K-percentage classification (Brand/Support/Deep) |
| Lattice | Uniform CMYK grid sampled at step 5 or 10 |
| Bucket | Grid cell in the Hue x Light map (one of 180) |
| Virtualization | DOM only contains visible cells |
| LUT | Lookup table (forward CMYK to RGB or reverse RGB to CMYK) |
| Quadrilinear | 4-D interpolation between 16 LUT corners |
| Bradford CAT | Chromatic adaptation transform D65->D50 used in rgb2lab_d50 |
| LAB_MODE | Global toggle: 'd65' for screen comparison, 'd50' for print/ICC match |
| D50 | ICC PCS white point (Xn=0.96422, Yn=1, Zn=0.82521) |
| D65 | sRGB white point (Xn=0.95047, Yn=1, Zn=1.08883) |
| jp-trad | Japanese traditional color corpus (250 NipponColors entries) |
| zh-trad | Chinese traditional color corpus (526 entries) |
| Corpus v3 | Schema with tri-lingual label + per-entry name_en/name_ja/name_zh |
| Dynamic lib ID | Swatch fields keyed as `lib.id + "__name"` etc., no hardcoded IDs |
| tac_recommended | Per-profile suggested TAC cap, sourced from press spec data |
| tac_max | Per-profile hard maximum TAC, used when 3D-print preset is active |
| cmykUIState_v2 | Current localStorage key for all UI state (migrated from v1) |

---

*End of architecture document.*
