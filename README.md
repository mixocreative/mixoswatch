
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="app/img/logo.svg">
  <img src="app/img/logo-black.svg" alt="mixoswatch" width="72">
</picture>

# Mixo Swatch

Cross-media color swatches for **commercial print**, **screen workflows**, and **3D color printing** (Mimaki 3DUJ, Stratasys J55, Cura material libraries). Every swatch is routed through a real CMYK ICC profile — not naive subtractive math.

**[→ Open Mixo Swatch](https://mixocreative.github.io/mixoswatch/app/mixo-swatch.html)**

> Screen color is not a contract proof. Uncontrolled color translation creates slow approvals, repeated tests, and avoidable production risk. Mixo Swatch is a color reliability system for selecting ICC-aware CMYK swatches, checking round-trip stability, building palettes, and exporting files that production tools can read.
>
> 沒有任何螢幕能完全精確地呈現印刷結果。為了省去生產端的反覆盲測，明上堂自主研發了 Mixo Swatch 色彩可靠性系統。
>
> 印刷結果を完全に再現できる画面は存在しません。製造現場での手探りの試作を省くため、明上堂は色彩安定化システム「Mixo Swatch」を自社開発しました。

---

## What's included

- **`app/mixo-swatch.html`** — live ICC-routed CMYK explorer with TAC, round-trip ΔE, K-tier, accessibility, search, naming-corpus, and sort filters. Build palettes, manage them in Palettes view, and export CSV, PNG, CMYK TIFF, ZIP, ASE, GPL, and JSON.
- **Production hand-off formats** — CMYK ASE and CMYK TIFF preserve ink values for RIP/prepress; RGB ASE and PNG serve Adobe, Affinity, Substance, Figma, web, and mockup workflows. ZIP exports include ordered per-swatch PNG/TIFF siblings plus manifests.
- **Print / screen / 3D workflow controls** — D50/D65 Lab mode, per-profile TAC defaults, 3D-print preset, Hue × Light map, full-canvas PNG/TIFF export, safer filenames, and EN / 日本語 / 繁體中文 UI with a light/dark theme toggle.
- **`index.html`** — tri-lingual project landing page with interactive demos and setup guidance.

---

## Quickstart

```bash
# 1. Install the only Python dependency.
python -m pip install --upgrade Pillow

# 2. Drop one or more CMYK ICC profiles into icc/.

# 3. Build the lookup tables the HTML uses to render CMYK ↔ sRGB.
python scripts/gen_luts.py

# 4. Serve locally (browsers block fetch() from file://).
python -m http.server 8765
# then open http://localhost:8765/
```

Windows: double-click `run.bat`. Any static file server works (`npx serve`, nginx, etc.).

---

## Why ICC-derived LUTs?

Most web CMYK pickers use `R = 255 × (1 − C/100) × (1 − K/100)`. That is not how presses, papers, inks, or 3D color printers behave. The same CMYK mix produces visibly different results on FOGRA39 coated stock, Japan Color, SWOP, or a Mimaki 3DUJ profile. Mixo Swatch routes colors through ICC-derived lookup tables so every swatch is tied to the intended production profile from the start.

---

## Pick the right export

| Receiver | Export | Why |
|---|---|---|
| Photoshop / InDesign / Affinity prepress | **TIFF (CMYK)** | 8-bit CMYK, ICC profile embedded — self-describing |
| Mimaki RasterLink / MPM3 | **TIFF (CMYK)** + assign 3DUJ ICC in the RIP | RIP reads CMYK directly, no perceptual compression on brand colors |
| Prepress / RIP swatch import | **ASE (CMYK)** | Exact ink values, no sRGB intermediate |
| Adobe / Affinity / Substance / Figma | **ASE (RGB)** + PNG | Screen tools expect sRGB |
| Web / mockup / preview | **PNG** | Standard sRGB raster |
| Texture-map authoring for 3DUJ | Not this tool — send sRGB-tagged textures into RasterLink directly | Mimaki RIP handles sRGB → 3DUJ-ink mapping for texture work |

---

## Export filenames and ZIP contents

Exports use short ASCII-safe filenames. Underscores separate metadata fields; hyphens separate words within a field. Full metadata stays in the manifests.

```text
mixo-pal_hong-kong-credit-cards-gold_9_pd50_coated-fogra39_de1.8_s10_na3.0_rgb_4096px_labelled.png
mixo-swatches_filtered_128_pd50_coated-fogra39_de1.8_s10_na3.0_cmyk_zip.zip
```

ZIP internals:

```text
png/001_ccbbaa_C000-M012-Y024-K000.png
tiff/001_ccbbaa_C000-M012-Y024-K000.tif
manifest.txt
manifest.csv
manifest.json
```

Grid side = `ceil(sqrt(count))`; empty cells are allowed at the end, no right/bottom margin.

---

## Repository layout

```
mixoswatch/
├── index.html                   Landing page (tri-lingual, live demos)
├── app/
│   └── mixo-swatch.html         Mixo Swatch (live CMYK explorer)
├── scripts/
│   └── gen_luts.py              Build CMYK↔sRGB lookup tables from ICCs
├── data/
│   ├── corpora/
│   │   └── name_corpora.json    Named-color dictionaries
│   ├── ui_defaults.json         Factory defaults
│   └── luts/                    Generated, gitignored
│       ├── index.json           Profile manifest
│       ├── *.lut                Forward CMYK → sRGB (17⁴, ~250 KB each)
│       └── *.rcmyk.lut          Reverse sRGB → CMYK (17³, ~20 KB each)
├── icc/                         Gitignored — bring your own .icc / .icm
├── README.md
├── ARCHITECTURE.md              Full pipeline + rationale
└── _config.yml                  Jekyll / Slate theme config
```

---

## ICC profiles are not bundled

Adobe / ECI / Mimaki / Fogra distribute CMYK ICC profiles under licenses that prohibit redistribution. `icc/` is gitignored — bring your own.


---

## Python pipeline — `scripts/gen_luts.py`

Uses Pillow's `ImageCms` binding to LittleCMS — the same color engine many prepress tools and FOSS RIPs share. Walks `icc/`, skips RGB-only working spaces, and emits two binary LUTs per profile:

| File | Direction | Grid | Size |
|---|---|---|---|
| `data/luts/<profile>.lut` | CMYK → sRGB | 17⁴ = 83,521 nodes | ~250 KB |
| `data/luts/<profile>.rcmyk.lut` | sRGB → CMYK | 17³ = 4,913 nodes | ~20 KB |

Plus `data/luts/index.json` — the profile manifest the HTML reads to populate its dropdown.

**Flags**

| Flag | Effect |
|---|---|
| `--force` | Rebuild every LUT regardless of timestamp |
| `<filename.icc>` | Build one profile by name |

**Common operations**

```bash
# Add a new profile:
cp ~/Downloads/MyMimaki3DUJ.icc icc/
python scripts/gen_luts.py

# Full rebuild:
python scripts/gen_luts.py --force

# Single profile:
python scripts/gen_luts.py CoatedFOGRA39.icc
```

LUT binary format (magic `LUT4` / `CMK4`, 16-byte header, little-endian, quadrilinear interpolation) is documented in `ARCHITECTURE.md §4.2`.

---

## Named-color corpora

`data/corpora/name_corpora.json` ships with three libraries. Add more by editing the JSON and refreshing the browser — no Python step needed.

| ID | Source | Entries |
|---|---|---|
| `jp-trad` | NipponColors.com Japanese traditional | 250 |
| `html` | W3C CSS Color Module Level 4 | 148 |
| `zh-trad` | Chinese traditional color corpus | 526 |

Schema v3 reference in `ARCHITECTURE.md §6.1`. Each entry supports `name_en`, `name_ja`, `name_zh`, and `hex` / `cmyk` match anchors. The UI lets users switch the per-library anchor live.

---

## Factory UI defaults — `data/ui_defaults.json`

Read on load and on "Reset to defaults". Session state layers on top via `localStorage` (`cmykUIState_v2`); reset restores JSON values while leaving saved palettes intact.

| Setting | Default | Why |
|---|---|---|
| Step | 20 | Stays under ~1300 swatches on first paint |
| Cell size | 80 px | CMYK + hex + corpus labels all legible |
| Lab mode | `d50` (Print) | Matches ICC PCS whitepoint + Photoshop Info panel |
| Profile | UncoatedFOGRA29 | Closest bundled proxy for Mimaki 3DUJ; TAC 260 % is in the Mimaki safe zone |
| TAC max | 240 % | Conservative coated-uncoated bracket |
| Round-trip ΔE max | 0.6 | Only press-safe swatches shown by default |
| K range | `[0, 80]` | K 85–100 collapses to pure black on most presses |
| Named-swatch filter | Any named (all libraries on) | Useful grid out of the box |
| Naming accuracy (ΔE) | 5.0 | Permissive enough to surface names, still meaningful |
| Sort | Hue | Best general overview |
| Accessibility toggles | All OFF | No hidden filters at first run |
| UI language | `auto` | `navigator.language` → `ja` / `zh-Hant` / `en` |

Full key reference in `ARCHITECTURE.md §6.5`.

---

## Hosting on GitHub Pages

The repo is GitHub Pages–ready once `data/luts/` is built. Two options:

**Commit the LUT artifacts:**

```bash
git add -f data/luts/*.lut data/luts/*.rcmyk.lut data/luts/index.json
git commit -m "ship LUT artifacts for GitHub Pages"
git push
```

ICC files stay out — LUTs are derived sampling results, not source profiles.

**Self-host:** run `python -m http.server 8765` locally and never push the data folder.

---

## Performance

| Operation | Target |
|---|---|
| Initial page load | < 200 ms |
| Profile switch, step 10 | < 200 ms |
| Profile switch, step 5 | < 1.5 s |
| Slider drag | rAF-coalesced |
| Scroll | 60 fps (virtualized, ~500 cells in DOM) |
| PNG export 4096² | ~2 s |
| TIFF pure 4096² (CMYK) | < 200 ms |
| TIFF labelled 4096² (CMYK) | ~0.8–1.2 s |
| ZIP export (50 swatches) | < 300 ms |

Detailed budget and lag-prevention rationale in `ARCHITECTURE.md §11`.

---

## Architecture

[`ARCHITECTURE.md`](ARCHITECTURE.md) is the full pipeline contract — color theory (CMYK / Lab / LCh, ΔE variants, GCR/UCR, K-tier, gamut, Bradford D50/D65 CAT), LUT binary format, round-trip safety gate, corpora schema v3, HTML pipeline lifecycle, virtualization, export rendering core, filename grammar, per-profile TAC defaults, i18n contract, and rebuild guide.

---

## About Mixo Creative

> **Create. Make. Innovate.** _Designing joy in every layer: custom toys and 3D-printed art that spark imagination._

Mixo Creative is a Taiwan-based professional design studio specializing in brand-identity geometry, 3D form design, and print production. Founded by **Adrian Li** — lecturer in the Department of Cultural and Creative Arts at The Education University of Hong Kong, and First-Class Honours Master's graduate in Design Management from the Birmingham Institute of Art and Design, UK. Works recognized by Adobe Behance and featured by Cults3D (France).

明上堂 Mixo Creative 是一家扎根於台灣、兼具國際視野的專業設計公司。深耕品牌識別幾何學、3D 造型設計與印刷。

明上堂（Mixo Creative）は、台湾に拠点を置くプロフェッショナルなデザイン会社です。ブランドアイデンティティの幾何学、3Dモデリング、印刷技術を深く追求しています。

<p>
  <img width="48" src="app/img/logo3d.png" alt="Mixo Creative 3D mark" />
  &nbsp;
  <img width="48" src="app/img/logotype.svg" alt="Mixo Creative logotype" />
  &nbsp;&nbsp;
  <img width="100" src="app/img/cults-cert-gold.png" alt="Cults3D Selected Designer" />
  &nbsp;
  <img width="100" src="app/img/behance-cert-gold.png" alt="Adobe Behance featured designer" />
</p>

[Instagram](https://www.instagram.com/mixocreative) · [Behance](https://www.behance.net/mixocreative) · [GitHub](https://github.com/mixocreative) · [About us](https://mixocreative.com/about/)

---

## License

Code: [GPL-3.0](LICENSE.txt). ICC profiles, DIC color guides, and Pantone are not redistributed.
