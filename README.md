# CMYK Swatch Tools

Two browser tools for designing print-safe colors against real ICC profiles, plus a small Python toolchain that prepares the data they consume.

- **`app/cmyk-explorer.html`** — live grid of every CMYK value at a chosen step, rendered through a CMYK ICC profile of your choice. Filter by total area coverage, by named-color closeness (Japanese traditional + W3C CSS names), build palettes, export ASE / GPL / PNG / JSON.
- **`app/3d-explorer.html`** — curated, pre-filtered library per profile. Every swatch has already passed a sRGB → CMYK → sRGB round-trip with ΔE ≤ threshold. Default sort is "safety" (lowest ΔE first). Pure-K neutral ramp included for 3D-print K-only printing.

A short zen landing at `index.html` links to both.

## Why

LLM color tools default to naive `R = 255 (1 − C/100)(1 − K/100)` math, which is what every web "CMYK picker" does. That math is fiction: the same CMYK ink mix prints differently on a Japanese coated press, a US web coated, a FOGRA39 sheet, and a Mimaki 3DUJ. These tools call real ICC profiles via a precomputed LUT pipeline so the displayed sRGB actually matches what the press would output.

## Repository layout

```
.
├── index.html                    zen landing
├── app/
│   ├── cmyk-explorer.html        live CMYK explorer
│   └── 3d-explorer.html          curated library viewer
├── data/
│   ├── corpora/
│   │   └── name_corpora.json     Japanese + W3C named-color dictionary (committed)
│   ├── luts/                     generated, gitignored
│   │   ├── index.json            profile manifest
│   │   ├── *.lut                 forward CMYK → sRGB (17⁴, ~250 KB each)
│   │   └── *.rcmyk.lut           reverse sRGB → CMYK (17³, ~20 KB each)
│   └── libraries/                generated, gitignored
│       ├── library_index.json    library manifest
│       └── *.json                per-profile curated library
├── icc/                          gitignored: user supplies their own .icc / .icm
├── scripts/
│   ├── gen_luts.py               build the LUTs and luts/index.json
│   └── gen_libraries.py          build the curated libraries and library_index.json
├── ARCHITECTURE.md               full color theory + pipeline rationale
├── run.bat                       Windows local server launcher
└── run.sh                        macOS / Linux local server launcher
```

## ICC profiles are not included

Adobe / ECI / Mimaki / Fogra all distribute their CMYK ICC profiles under licenses that do not allow redistribution. So `icc/` is `.gitignore`d and you bring your own.

Free, common options:

| Profile | Where to get it |
|---|---|
| `CoatedFOGRA39.icc` (recommended baseline) | [Adobe ICC Profiles bundle](https://www.adobe.com/support/downloads/iccprofiles/) — extract, find `CMYK Profiles/CoatedFOGRA39.icc` |
| `ISOcoated_v2_eci.icc` | [ECI offset profiles](https://www.eci.org/doku.php?id=en:colourstandards:offset) |
| `JapanColor2001Coated.icc` | Adobe ICC Profiles bundle |
| `USWebCoatedSWOP.icc` | Adobe ICC Profiles bundle |
| Mimaki 3DUJ profile | Mimaki Profile Master 3 (MPM3), or request from Mimaki technical support |

Drop them into `icc/` and run the build commands below.

## Setup

```bash
# 1. Install Python dependency (Pillow ships LittleCMS bindings).
python -m pip install --upgrade Pillow

# 2. Drop one or more CMYK ICC profiles into icc/.

# 3. Build the lookup tables the HTML uses to render CMYK → sRGB.
python scripts/gen_luts.py

# 4. Build the curated print-safe libraries the 3D explorer browses.
python scripts/gen_libraries.py

# 5. Serve the folder locally. Browsers block fetch() from file:// .
./run.sh        # macOS / Linux
run.bat         # Windows
```

Then open <http://localhost:8000/> in a browser.

## Common tasks

**Add a profile.** Drop the `.icc` into `icc/`. Re-run `python scripts/gen_luts.py` and `python scripts/gen_libraries.py`. Refresh the page.

**Add a named color, or a whole new corpus.** Edit `data/corpora/name_corpora.json` (v2 schema — see `ARCHITECTURE.md §7`). Append an entry to an existing corpus, or add a new corpus block under `corpora`. Each entry may carry `hex` and/or `cmyk` as match *anchors* (not display values — the displayed color always comes from the ICC-routed sRGB). Refresh the browser; no Python rebuild needed. The sidebar's per-library "Naming" controls let you pick which name field to show on swatches and which attribute drives the match.

**Change the factory defaults.** `data/ui_defaults.json` carries the values both tools apply on first run and on **↺ Reset UI to defaults**. The tools layer the user's last-session state from browser localStorage on top — so the reset button restores the JSON defaults while leaving your saved palettes untouched. The "no palette selected" state is also persisted.

**Rebuild everything from scratch.** `python scripts/gen_luts.py --force && python scripts/gen_libraries.py --force`.

**Loosen / tighten the curated library.** `python scripts/gen_libraries.py --delta-e 1.5`. Smaller ΔE = stricter, fewer swatches. Default 2.0.

**Use ArgyllCMS xicclu as an extra in-gamut filter.** Install ArgyllCMS, ensure `xicclu` is on `PATH`, then `python scripts/gen_libraries.py --argyll`.

## Hosting on GitHub Pages

The HTML tools are static and use only `fetch()` from disk-relative paths, so the entire repo is GitHub-Pages-ready as-is once you have built `data/luts/` and `data/libraries/`. Because both are gitignored, you have two choices:

1. **Public LUTs, public libraries.** Build locally, then commit `data/luts/*.lut`, `data/luts/index.json`, `data/libraries/*.json`, `data/libraries/library_index.json` with an explicit `git add -f` so they ship to GH Pages. ICC files stay out.
2. **Self-host instead.** Run `./run.sh` or `run.bat` locally; never push the data folder.

Option (1) is fine because LUTs and libraries do not contain the ICC profile binary, only sampled output points.

## Architecture

`ARCHITECTURE.md` carries the full rationale: color theory (CMYK / Lab / LCh, ΔE variants, GCR/UCR, K-tier philosophy, gamut), the LUT binary format (magic header, quadrilinear interpolation pseudocode), the round-trip safety gate, the descriptive naming system, the HTML pipeline (lifecycle, virtualization, two greyscale strips, view modes, palette format), the performance budget, and a step-by-step rebuild guide. Read it if you want to reproduce, extend, or audit the toolchain.

## License

Code: MIT. ICC profiles are not redistributed.
