# mixoswatch

One browser tool for designing print-safe colors against real ICC profiles, plus a small Python script that prepares the lookup tables it consumes. Built for designers who work across **2D commercial print** and **3D color printing** (Mimaki 3DUJ, Stratasys J55, Cura material libraries, etc.).

- **`app/mixo-swatch.html`** (Mixo Swatch) · live grid of every CMYK value at a chosen step, rendered through a CMYK ICC profile of your choice. Filter by total area coverage, by named-color closeness (Japanese traditional + W3C CSS + DIC Japanese + DIC Chinese), by **ΔE max** for round-trip safety, build palettes, export ASE / GPL / PNG / JSON.
- **`index.html`** · zen landing with live interactive demos for every sidebar control, tri-lingual (EN / 日本語 / 繁中).

## Why

LLM color tools default to naive `R = 255 × (1 − C/100) × (1 − K/100)` math, which is what every web "CMYK picker" does. That math is fiction. The same CMYK ink mix prints differently on a Japanese coated press, a US web coated, a FOGRA39 sheet, and a Mimaki 3DUJ. mixoswatch routes every color through a real ICC profile (the same files prepress tools and FOSS RIPs load), so what you see on screen matches what the press will actually produce. No surprises at the proof stage.

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
├── run.bat / run.sh                Local HTTP server launcher
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

Drop them into `icc/` and run the build commands below.

---

## Quickstart

```bash
# 1. Install the only Python dependency.
python -m pip install --upgrade Pillow

# 2. Drop one or more CMYK ICC profiles into icc/.

# 3. Build the lookup tables the HTML uses to render CMYK ↔ sRGB.
python scripts/gen_luts.py

# 4. Serve the folder locally (browsers block fetch() from file://).
./run.sh        # macOS / Linux
run.bat         # Windows
```

Open <http://localhost:8765/> in a browser.

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

`data/corpora/name_corpora.json` ships with four corpora out of the box. Add more by editing the JSON; refresh the browser; done. No Python step.

| ID | Source | Anchor | Entries |
|---|---|---|---|
| `jpn` | Japanese traditional palette (Wikipedia) | hex | 111 |
| `html` | W3C CSS Color Module Level 4 named colors | hex | 141 |
| `jpn-dic` | DIC Japanese Traditional (matte), seed N801..N810 | cmyk | 10 |
| `zh-dic` | DIC Chinese Traditional, seed reds + yellows + blues | cmyk | 24 |

Schema (v2.1) lives in `ARCHITECTURE.md §7.1`. The short version:

```json
{
  "version": 2,
  "schema_rev": "2.1",
  "corpora": [
    {
      "id": "jpn-dic",
      "label": "DIC Japanese Traditional (matte)",
      "fields": [
        { "id": "name",     "label": "kanji" },
        { "id": "romaji",   "label": "romaji" },
        { "id": "english",  "label": "english" },
        { "id": "dic_code", "label": "DIC code" }
      ],
      "default_display": "name",
      "anchor": "cmyk",
      "entries": [
        { "name": "苅安色", "romaji": "kariyasu-iro",
          "english": "Kariyasu Yellow", "dic_code": "DIC-N804",
          "hex": "#FDC600", "cmyk": [0, 19, 100, 0] }
      ]
    }
  ]
}
```

Each entry can carry `hex` and/or `cmyk` as *match anchors* (not display values). Per-library anchor (`hex` vs `cmyk`) decides which attribute drives the nearest-match math. The browser UI lets the user flip the anchor live.

**Why CMYK anchoring matters for DIC corpora.** DIC sample books are authored as ink values. Hex equivalents in third-party tables are often back-converted from those CMYK values under one specific profile. If the user's profile is different, hex anchoring picks a slightly wrong target. CMYK anchoring routes the corpus's CMYK through the user's active profile first, giving a more honest match.

---

## Factory UI defaults (`data/ui_defaults.json`)

First-run UI state lives in this JSON. The tool reads it on load and on "↺ Reset to defaults". User session state layers on top via `localStorage`, so the reset restores the JSON values while leaving saved palettes intact.

Edit this file when you want your team to start with non-default values (default profile, default cell size, default sort, default ΔE max, per-corpus display + anchor, etc.). Full key reference in `ARCHITECTURE.md §6.5`.

---

## Running locally

```bash
./run.sh        # macOS / Linux
run.bat         # Windows
```

Both call `python -m http.server 8765` from the project root and open the landing page in your default browser. The HTML fetches JSON and LUT files via `fetch()`, so `file://` will not work (browser CORS/security). If you prefer a different server (`npx serve`, nginx, etc.) any plain static-file host works.

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
2. **Self-host.** Run `./run.sh` / `run.bat` locally; never push the data folder.

---

## Performance notes

| Operation | Target | How |
|---|---|---|
| Initial page load | < 200 ms | LUT lazy-fetched, corpora ~36 KB |
| Profile switch, step 10 | < 200 ms | LUT fetch + derive 14k swatches in chunks |
| Profile switch, step 5 | < 1.5 s | rAF-batched derive + visible progress bar |
| Slider drag | rAF-coalesced | One `render()` per animation frame max |
| Scroll | 60 fps | Virtualized grid (~500 cells in DOM at a time) |
| PNG export 4096² | ~2 s | One-shot canvas, no virtualization |
| ZIP export (50 swatches) | < 200 ms | Pure JS, STORE-only |

Detailed budget + the lag-prevention rationale (rAF-coalesced render scheduler, chunked match passes, etc.) in `ARCHITECTURE.md §11`.

---

## Architecture

`ARCHITECTURE.md` is the full pipeline contract: color theory (CMYK / Lab / LCh, ΔE variants, GCR / UCR, K-tier philosophy, gamut), the LUT binary format (magic header, quadrilinear interpolation pseudocode), the round-trip safety gate, the descriptive naming system, the HTML pipeline (lifecycle, virtualization, two greyscale strips, view modes, palette format), and a step-by-step rebuild guide. Read it if you want to reproduce, extend, or audit the toolchain.

## License

Code: MIT. ICC profiles, DIC color guides, and Pantone are not redistributed.
