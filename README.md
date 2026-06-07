<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="app/img/logo.svg">
  <img src="app/img/logo-black.svg" alt="mixoswatch" width="112">
</picture>

# mixoswatch
</div>
<div>
Cross-media color swatches for **commercial print**, **screen workflows**, and **3D color printing** (Mimaki 3DUJ, Stratasys J55, Cura material libraries). Every swatch is routed through a real CMYK ICC profile rather than naive subtractive math.

Screen color is not a contract proof. For brand, print, and 3D production work, uncontrolled color translation creates slow approvals, repeated tests, and avoidable production risk. **Mixo Swatch** is a color reliability system for selecting ICC-aware CMYK swatches, checking round-trip stability, building palettes, and exporting files that production tools can read.

[真相] 沒有任何螢幕能完全精確地呈現印刷結果。在平面或紙品印刷上，沒有使用昂貴專色的品牌設計，設計師與客户溝通時總得面對選色導致校對螢幕色與列印色版相當耗時的問題。在跨足平面與立體設計的過程中，3D建模軟體不支援實體色彩管理，列印成 3D 實體模型往往難以控制色差。為了一定程度省去生產端的反覆盲測，明上堂自主研發了 Mixo Swatch 色彩可靠性系統。

【真実】印刷結果を完全に再現できる画面は存在しません。グラフィック印刷では、高価な特色を使わない限り、画面と印刷サンプルの色合わせに多大な時間がかかります。さらに、平面から立体デザインへの展開において、3Dソフトは実物のカラーマネジメントに対応していないため、3Dプリント模型の色ブレ管理は極めて困難です。製造現場での手探りの試作を省くため、明上堂は色彩安定化システム「Mixo Swatch」を自社開発しました。
</div>
<div align="center">

### [→ Open Mixo Swatch 立刻使用 詳細を見る](https://mixocreative.github.io/mixoswatch/)

</div>

---

## Contents

- [What's included](#whats-included)
- [Quickstart](#quickstart)
- [Why](#why)
- [Pick the right export](#pick-the-right-export-for-the-receiver)
- [Export filenames and ZIP contents](#export-filenames-and-zip-contents)
- [ICC profiles](#icc-profiles-are-not-bundled)
- [Python pipeline](#python-pipeline-in-detail)
- [UI defaults](#factory-ui-defaults-dataui_defaultsjson)
- [Performance notes](#performance-notes)
- [Architecture](#architecture)

## What's included

- **`app/mixo-swatch.html`** (Mixo Swatch) · live ICC-routed CMYK explorer with TAC, round-trip dE, K-tier, accessibility, search, naming-corpus, and sort filters. Build palettes, manage them in Palettes view, and export CSV, PNG, CMYK TIFF, ZIP, ASE, GPL, and JSON.
- **Production hand-off formats** · CMYK ASE and CMYK TIFF preserve the selected ink values for RIP/prepress workflows; RGB ASE and PNG serve Adobe, Affinity, Substance, Figma, web, and mockup workflows. ZIP exports include ordered per-swatch PNG/TIFF siblings plus manifests.
- **Print/screen/3D workflow controls** · D50/D65 Lab mode, per-profile TAC defaults, 3D-print preset, Hue x Light map, full-canvas PNG/TIFF export fitting, safer filenames, and English / 日本語 / 繁體中文 UI with a light/dark theme toggle.
- **`index.html`** · tri-lingual project landing page with interactive demos and setup guidance.

## Quickstart

```bash
# 1. Install the only Python dependency.
python -m pip install --upgrade Pillow

# 2. Drop one or more CMYK ICC profiles into icc/.

# 3. Build the lookup tables the HTML uses to render CMYK ↔ sRGB.
python scripts/gen_luts.py

# 4. Serve the folder locally (browsers block fetch() from file://).
# Windows: double-click run.bat, or:
python -m http.server 8765
# then open http://localhost:8765/ in a browser
```

Any static file server works (`npx serve`, nginx, etc.). Ctrl+C stops `http.server`.

## Why

Most web CMYK pickers use simplified subtractive formulas such as `R = 255 × (1 − C/100) × (1 − K/100)`. That is not how presses, papers, inks, or 3D color printers behave. The same CMYK mix can produce visibly different results on FOGRA39 coated stock, Japan Color, SWOP, or a Mimaki 3DUJ profile. Mixo Swatch routes colors through ICC-derived lookup tables so the working swatch is tied to the intended production profile from the beginning.

## Pick the right export for the receiver

| Receiver | Export | Why |
|---|---|---|
| Photoshop / InDesign / Affinity prepress | **TIFF (CMYK, labelled or pure)** | 8-bit CMYK, ICC profile embedded when `icc/<filename>` is reachable - file is self-describing |
| Mimaki RasterLink / MPM3 (spot-color) | **TIFF (CMYK)** + assign 3DUJ ICC in the RIP | RIP reads CMYK directly, no perceptual compression on brand colors |
| Prepress / RIP swatch import (no raster) | **ASE (CMYK)** | Same CMYK values that the picker locked in, no sRGB intermediate |
| Adobe / Affinity / Substance / Figma | **ASE (RGB)** + PNG | Screen tools expect sRGB |
| Web / mockup / preview | **PNG** (labelled or pure) | Standard sRGB raster |
| Texture-map authoring for 3DUJ (Substance, ZBrush, Blender) | Not this tool - send sRGB-tagged textures into RasterLink directly | Mimaki RIP handles the sRGB → 3DUJ-ink mapping intelligently for texture work |

## Export filenames and ZIP contents

Exports use short, ASCII-safe filenames so they survive Adobe apps, RIP hot folders, shared drives, shell scripts, and ZIP tools. Underscores separate metadata fields; hyphens separate words inside one field. Full metadata remains in the manifests.

Canvas exports include canvas size:

```text
mixo-pal_hong-kong-credit-cards-gold_9_pd50_coated-fogra39_de1.8_s10_na3.0_rgb_4096px_labelled.png
mixo-swatches_filtered_128_pd50_coated-fogra39_de1.8_s10_na3.0_cmyk_4096px_pure.tif
```

Data exports omit canvas size:

```text
mixo-pal_hong-kong-credit-cards-gold_9_pd50_coated-fogra39_de1.8_s10_na3.0_cmyk_zip.zip
mixo-swatches_filtered_128_pd50_coated-fogra39_de1.8_s10_na3.0_rgb_ase.ase
```

ZIP internals keep order and color identity:

```text
png/001_ccbbaa_C000-M012-Y024-K000.png
tiff/001_ccbbaa_C000-M012-Y024-K000.tif
manifest.txt
manifest.csv
manifest.json
```

Fixed-size PNG/TIFF exports use a full-canvas grid. The grid side is `ceil(sqrt(count))`; empty cells are allowed at the end, but there is no right/bottom white margin.

For full color theory + pipeline rationale see **`ARCHITECTURE.md`** (the contract document).

## Repository layout

```
mixoswatch/
├── index.html                      Zen landing (tri-lingual, live demos)
├── app/
│   └── mixo-swatch.html            Mixo Swatch (live CMYK explorer)
├── scripts/
│   └── gen_luts.py                 Build CMYK↔sRGB lookup tables from ICCs
├── data/
│   ├── corpora/
│   │   └── name_corpora.json       Named-color dictionaries (committed)
│   ├── ui_defaults.json            Factory defaults (committed)
│   └── luts/                       Generated, gitignored
│       ├── index.json              Profile manifest
│       ├── *.lut                   Forward CMYK → sRGB (17⁴, ~250 KB each)
│       └── *.rcmyk.lut             Reverse sRGB → CMYK (17³, ~20 KB each)
├── icc/                            Gitignored: you supply your own .icc / .icm
├── README.md                       This file
├── ARCHITECTURE.md                 Full pipeline + rationale
└── .gitignore
```

## ICC profiles are not bundled

Adobe / ECI / Mimaki / Fogra all distribute their CMYK ICC profiles under licenses that do not allow redistribution. `icc/` is `.gitignore`d and you bring your own.

Free, common sources:

| Profile | Where to get it |
|---|---|
| `CoatedFOGRA39.icc` (recommended baseline) | [Adobe ICC Profiles bundle](https://www.adobe.com/support/downloads/iccprofiles/) → extract → `CMYK Profiles/CoatedFOGRA39.icc` |
| `ISOcoated_v2_eci.icc` | [ECI offset profiles](https://www.eci.org/doku.php?id=en:colourstandards:offset) |
| `JapanColor2001Coated.icc` | Adobe ICC Profiles bundle |
| `USWebCoatedSWOP.icc` | Adobe ICC Profiles bundle |
| `Mimaki 3DUJ` profile | Mimaki Profile Master 3 (MPM3), or by request from Mimaki support |

Drop them into `icc/` and run the Quickstart commands above.

---

## Python pipeline in detail

One script. Uses Pillow's `ImageCms` binding to LittleCMS. Same color engine many prepress tools and FOSS RIPs share, so the numbers we sample match what a real RIP would emit at the same intent.

### `scripts/gen_luts.py` · lookup-table generator

**What it does.** Walks `icc/`, finds every CMYK profile (RGB-only working spaces like AdobeRGB are auto-skipped), and emits two binary lookup tables per profile:

| File | Direction | Grid | Size | Used by |
|---|---|---|---|---|
| `data/luts/<profile>.lut` | CMYK → sRGB | 17⁴ = 83,521 nodes | ~250 KB | Mixo Swatch (cell rendering) |
| `data/luts/<profile>.rcmyk.lut` | sRGB → CMYK | 17³ = 4,913 nodes | ~20 KB | Mixo Swatch (round-trip safety / ΔE max filter) |

Plus a manifest the HTML reads to populate its profile dropdown:

```json
// data/luts/index.json
{
  "format": "icc.index/v1",
  "grid": 17,
  "lut_header_bytes": 16,
  "profiles": [
    { "filename": "CoatedFOGRA39.icc",
      "label": "Tier 3 · Coated FOGRA39",
      "kind": "cmyk",
      "lut": "luts/CoatedFOGRA39.lut",
      "lut_bytes": 250579 }
  ]
}
```

**Flags.**

| Flag | Effect |
|---|---|
| `--force` | Rebuild every LUT even when its timestamp is newer than the source ICC |
| `<filename.icc>` | Build just one profile by name (positional argument) |

**LUT binary format.** Documented in `ARCHITECTURE.md §4.2`. Magic `LUT4` for forward, `CMK4` for reverse, 16-byte header, little-endian, row-major RGB / CMYK triples. The browser tool interpolates the 16 surrounding LUT corners quadrilinearly for arbitrary CMYK inputs.

### Common operations

```bash
# Add a new profile end-to-end:
cp ~/Downloads/MyMimaki3DUJ.icc icc/
python scripts/gen_luts.py

# Rebuild everything from scratch (after a project pull or schema bump):
python scripts/gen_luts.py --force

# Build only one profile (after editing just one ICC):
python scripts/gen_luts.py CoatedFOGRA39.icc
```

---

## Editing the named-color corpora (no rebuild needed)

`data/corpora/name_corpora.json` ships with three corpora. Add more by editing the JSON; refresh the browser; done. No Python step.

| ID | Source | Anchor | Entries |
|---|---|---|---|
| `jp-trad` | NipponColors.com Japanese traditional colors | hex | 250 |
| `html` | W3C CSS Color Module Level 4 canonical named colors | hex | 148 |
| `zh-trad` | Chinese traditional color corpus | hex | 526 |

Schema (v3) lives in `ARCHITECTURE.md §6.1`. The short version:

```json
{
  "version": 3,
  "schema_rev": "3.0",
  "corpora": [
    {
      "id": "jp-trad",
      "label": { "en": "Japanese traditional", "ja": "日本の伝統色", "zh": "日本傳統色" },
      "fields": [
        { "id": "name_ja", "label": { "en": "kanji",  "ja": "漢字", "zh": "漢字" } },
        { "id": "romaji",  "label": { "en": "romaji", "ja": "ローマ字", "zh": "羅馬字" } },
        { "id": "name_en", "label": { "en": "english","ja": "英語", "zh": "英語" } }
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

Each entry carries `name_en`, `name_ja`, and `name_zh`. Empty slots fall back gracefully (see `ARCHITECTURE.md §6.1`). Each entry can also carry `hex` and/or `cmyk` as match anchors (not display values). The browser UI lets the user flip the per-library anchor between `hex` and `cmyk` live.

---

## Factory UI defaults (`data/ui_defaults.json`)

First-run UI state lives in this JSON. The tool reads it on load and on "Reset to defaults". User session state layers on top via `localStorage` (key: `cmykUIState_v2`), so the reset restores the JSON values while leaving saved palettes intact.

The shipped defaults are tuned for the print-first workflow on a coated press:

| Setting | Default | Why |
|---|---|---|
| Step | 20 | First paint stays under ~1300 swatches |
| Cell size | 80 px | Labels (CMYK + hex + corpus name) all legible |
| Lab mode | `d50` (Print) | Matches ICC PCS whitepoint + Photoshop Info panel |
| Profile | UncoatedFOGRA29 | Closest bundled proxy for Mimaki 3DUJ. Gamut ≈ 78 % FOGRA39 coated (within ~5 % of measured 3DUJ), TAC recommended 260 % sits in the Mimaki safe zone (240-280), warm-neutral axis tracks resin yellow-cast. Falls back to FOGRA39 then the first profile if the match string is missing. |
| TAC max | 240 % | Conservative coated-uncoated bracket |
| Round-trip dE max | 0.6 | Tight - only press-safe swatches show by default |
| K range | `[0, 80]` | K 85-100 collapses to pure black on most presses |
| Named-swatch filter | `Any named` (all libraries on) | Useful grid out of the box |
| Naming accuracy (dE) | 5.0 | Permissive enough to surface names but still meaningful |
| Sort | Hue | Best general overview |
| Accessibility toggles | All OFF | No hidden filters at first run |
| UI language | `auto` | `navigator.language` → `ja` / `zh` (-Hant) / `en` |

Edit this file when you want your team to start with non-default values (default profile, default cell size, default sort, default dE max, per-corpus display + anchor, default UI language, etc.). Full key reference in `ARCHITECTURE.md §6.5`.

**v1 migration.** If a browser has a `cmykUIState_v1` key from a pre-Spec-6 session, the tool migrates it to v2 on first load (reshaping `corpora_prefs` keys from `jpn`/`html` to `jp-trad`/`html`/`zh-trad`, bumping default tolerance from 3.0 to 5.5). The v1 key is preserved for downgrade.

---

## Running locally

```bash
# Windows: double-click run.bat, or:
python -m http.server 8765
# then open http://localhost:8765/
```

The HTML fetches JSON and LUT files via `fetch()`, so `file://` will not work (browser CORS/security). Any plain static-file host works (`npx serve`, nginx, etc.).

The landing is `/`, the explorer is `/app/mixo-swatch.html`. Same paths apply on the live site.

---

## Hosting on GitHub Pages

The HTML tool is static and references data via disk-relative `fetch()` paths, so the entire repo is GitHub-Pages-ready as-is once you have built `data/luts/`. The folder is gitignored by default; pick one:

1. **Commit the LUT folder.** Build locally, then force-add the artifacts:
   ```bash
   git add -f data/luts/*.lut data/luts/*.rcmyk.lut data/luts/index.json
   git commit -m "ship LUT artifacts for GitHub Pages"
   git push
   ```
   ICC files stay out. LUTs are derived sampling results, not the source profile.
2. **Self-host.** Run `python -m http.server 8765` locally; never push the data folder.

---

## Performance notes

| Operation | Target | How |
|---|---|---|
| Initial page load | < 200 ms | LUT lazy-fetched, corpora ~36 KB |
| Profile switch, step 10 | < 200 ms | LUT fetch + derive 14k swatches in chunks |
| Profile switch, step 5 | < 1.5 s | rAF-batched derive + visible progress bar |
| Slider drag | rAF-coalesced | One `render()` per animation frame max |
| Scroll | 60 fps | Virtualized grid (~500 cells in DOM at a time) |
| PNG export 4096² | ~2 s | Shared canvas renderer, full-canvas grid, no virtualization |
| TIFF pure 4096² (CMYK) | < 200 ms | Direct C/M/Y/K bytes, chunked progress, no rLUT round-trip |
| TIFF labelled 4096² (CMYK) | ~0.8-1.2 s | Shared labelled canvas → reverse LUT pixel walk, white/black short-circuit |
| ZIP export (50 swatches, png + tiff) | < 300 ms | Pure JS, STORE-only; ordered PNG/TIFF siblings + manifests |

Detailed budget + the lag-prevention rationale (rAF-coalesced render scheduler, chunked match passes, etc.) in `ARCHITECTURE.md §11`.

---

## Architecture

`ARCHITECTURE.md` is the full pipeline contract: color theory (CMYK / Lab / LCh, dE variants, GCR / UCR, K-tier philosophy, gamut, Bradford D50/D65 CAT), the LUT binary format (magic header, quadrilinear interpolation pseudocode), the round-trip safety gate, the corpora schema v3 (tri-lingual fields, dynamic library IDs, per-(lib,entry) tiebreak), the HTML pipeline (lifecycle, virtualization, ICC neutral ramp + Pure RGB reference strips, Grid/Palettes view modes, Hue x Light placement, palette format), export rendering core, safer filename grammar, per-profile TAC defaults, the i18n contract (en / ja / zh-Hant, `data-i18n` keys, auto-detect rule), and a step-by-step rebuild guide. Read it if you want to reproduce, extend, or audit the toolchain.

## About the studio

> **Create. Make. Innovate.** _Designing joy in every layer: custom toys and 3D-printed art that spark imagination._

<div style="font-size:small;">
Mixo Creative is a Taiwan-based professional design studio with an international outlook, specializing in brand-identity geometry, 3D form design, and print production. Founded by **Adrian Li**, lecturer in the Department of Cultural and Creative Arts at The Education University of Hong Kong, and First-Class Honours Master's graduate in Design Management from the Birmingham Institute of Art and Design, UK. The studio's works have been officially recognized by Adobe Behance and featured by Cults3D in France.

Whether your company is planning a new brand identity system or exploring ambitious frontiers in physical 3D art, we look forward to partnering with you, transforming ideas into reality with confidence, clarity, and technical reliability. We sincerely look forward to hearing about your next project.

明上堂 Mixo Creative 是一家扎根於台灣、兼具國際視野的專業設計公司。香港教育大學文化及創新設計系講師、英國伯明罕藝術設計學院設計管理學一級榮譽碩士 Adrian Li 的工作室。明上堂歷年作品榮獲 Adobe Behance 官方平台認證、法國 Cults3D 精選推薦。深耕品牌識別幾何學、 3D 造型設計與印刷。

明上堂（Mixo Creative）は、台湾に拠点を置きながら国際的な視野を併せ持つプロフェッショナルなデザイン会社です。香港教育大学の文化・イノベーションデザイン学科講師であり、英国バーミンガム芸術デザイン大学院にてデザインマネジメント学の一級栄誉修士（First Class Honours）を取得した Adrian Li のスタジオでもあります。明上堂のこれまでの作品は、Adobe Behanceの公式プラットフォームでの認定や、フランスのCults3Dでの厳選推奨を獲得しています。ブランドアイデンティティの幾何学、3Dモデリングデザイン、そして印刷技術の分野を深く追求しています。
</div>

<div align="center">
<p>
  <img width="60" src="app/img/logo3d.png" alt="Mixo Creative 3D mark" />
  &nbsp;
  <img width="60" src="app/img/logotype.svg" alt="Mixo Creative logotype" />
  &nbsp;&nbsp;
  <img width="120" src="app/img/cults-cert-gold.png" alt="Cults3D Selected Designer" title="Cults3D Selected Designer (France)" />
  &nbsp;
  <img width="120" src="app/img/behance-cert-gold.png" alt="Adobe Behance featured designer" title="Adobe Behance featured designer" />
</p>
</div>

**Find us:** [Instagram](https://www.instagram.com/mixocreative) · [Facebook](https://www.facebook.com/mixocreative) · [Behance](https://www.behance.net/mixocreative) · [GitHub](https://github.com/mixocreative) · [TEAM TAIWAN Open Source Initiative · 台灣尚勇開源計劃)](https://github.com/mixocreative/twsy) · [About us →](https://mixocreative.com/about/)

## License

Code: GPL-3.0 (see `LICENSE.txt`). ICC profiles, DIC color guides, and Pantone are not redistributed.
