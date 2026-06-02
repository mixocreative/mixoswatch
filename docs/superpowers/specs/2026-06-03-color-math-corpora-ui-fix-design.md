# Spec 6 - Color math + corpora + UI overhaul

Date: 2026-06-03
Branch: spec5-cmyk-only (continues from)
Status: draft pending user review

## Problem

Three independent correctness/coverage gaps surfaced in research:

1. **Lab math uses D65 whitepoint, no Bradford D65->D50 chromatic adaptation.** ICC PCS Lab is D50. Every closest-corpus match and tolerance gate inherits a 0.5-2 dE drift vs ICC reference tools. Affects naming accuracy, especially near deep blues/yellows.
2. **Corpora coverage is thin and DIC is licensed.** Current jpn=111 of ~250-465 references. DIC seed corpora (jpn-dic=10, zh-dic=24) are tiny fractions of licensed swatch books with grey-area provenance. html=141 vs W3C canonical 147.
3. **Hardcoded values block customization.** HUE_NAMES wheel, lightness/chroma bin thresholds, single global tolerance, no per-profile TAC default, no print/screen Lab toggle, no 3D-print preset, no responsive layout, hardcoded library IDs in swatch fields block dynamic corpus addition.

Goal: ship best swatches that work on digital + 2D press + 3D print outputs.

## Decisions (locked via brainstorm)

| Decision | Choice | Rationale |
|---|---|---|
| Work bundling | All-at-once (single commit set) | localStorage v1->v2 migration is one event; corpora + math + UI touch overlapping code paths |
| DIC sourcing | Drop DIC entirely | License grey area; replace with clean-provenance sources |
| Replacement corpora | NipponColors 250 (jp-trad) + Chinese trad 526 (zh-trad) + W3C canonical 147 (html) | Public datasets, clean provenance |
| Bradford fix | Precompute both D50 + D65 Lab at preload, UI toggle swaps active, status badge always shown | No recompute lag; user can pick print or screen orientation |
| Default Lab mode | D50 (print-first) | Aligns with project goal (digital + 2D + 3D print) |
| system_name synthesis | Drop entirely | Algorithmic name had no cross-app meaning; ~93% of swatches will show hex only when no corpus matches; tradeoff accepted |
| Name uniqueness | Per-library, closest swatch only wears name within tolerance | Eliminates name duplication across grid |
| Global controls | One anchor (cmyk/hex) + one dE tolerance for all libraries, link icon always shown | Simpler mental model |
| Per-library controls | Display field radio only (which translit/gloss to show) | Per-library tuning of display, not match logic |
| TAC presets | Per-profile recommended TAC in luts/index.json + quick-preset buttons | Profile-aware defaults; quick switching |
| 3D-print preset | Single checkbox snaps TAC <=240, dE max <=3 | One-click safe palette |
| Dark mode | Always dark, drop light fallback | Surrounding luminance bias affects color picking accuracy |
| Mobile | Responsive breakpoints at 1024/768/480 + sidebar drawer | Touch targets >=44px |
| Dynamic corpora | Drop hardcoded library IDs (jpn, html) from swatch fields, use ${lib.id}__name pattern | Add corpus to JSON -> UI auto-builds, zero code |
| Tri-lingual fill | Field-per-language (name_en, name_ja, name_zh) + translit (romaji/pinyin); no empty strings; loader fills with fallback | Memory rule compliance, dictionary integrity |

## Architecture

### Color math (Section 1)

New constants:
```js
const M_BRAD_D65_D50 = [
  [ 1.0478112,  0.0228866, -0.0501270],
  [ 0.0295424,  0.9904844, -0.0170491],
  [-0.0092345,  0.0150436,  0.7521316]
];
const D50 = { Xn: 0.96422, Yn: 1.0, Zn: 0.82521 };
const D65 = { Xn: 0.95047, Yn: 1.0, Zn: 1.08883 };
```

Functions:
- `rgb2lab_d65(r,g,b)` - current rgb2lab body, renamed
- `rgb2lab_d50(r,g,b)` - rgb2xyz -> Bradford 3x3 -> XYZ_D50 -> Lab
- `activeLab(s)` - reads LAB_MODE global, returns s.lab_d50 or s.lab_d65

Per-swatch cache:
- `s.lab_d50 = [L,a,b]` precomputed in deriveSwatch
- `s.lab_d65 = [L,a,b]` precomputed in deriveSwatch
- `s.L_star/s.a_star/s.b_star` become aliases to active mode

Per-corpus-entry cache:
- `entry._lab_d50_hex`, `entry._lab_d65_hex`
- `entry._lab_d50_cmyk`, `entry._lab_d65_cmyk` (when cmyk anchor present)

LAB_MODE global, default `'d50'`. Toggle in settings panel:
- Radio: "Color mode: (.) Print (D50)  ( ) Screen (D65)"
- Persistent status badge near top: "Mode: Print (D50)" or "Mode: Screen (D65)"
- Toggle swaps LAB_MODE -> re-run _markClosest for all libraries -> re-render grid

WCAG luminance and contrast unaffected (use sRGB Y directly, not Lab).

Round-trip dE (delta_e_print) unaffected by Lab mode in practice (bias cancels because same Lab function applied to both endpoints).

### Corpora overhaul (Section 2)

Drop `jpn-dic` and `zh-dic` (licensed grey area).

Rename `jpn` -> `jp-trad`.

Add new `zh-trad` (526 entries from Chinese Academy of Science 1957 color name dictionary, mirrored on color-term.com / community GitHub repos).

Backfill `html` from 141 -> 147 canonical W3C CSS Color Module Level 4 keywords. Include alias pairs (gray/grey, cyan/aqua, fuchsia/magenta, darkgray/darkgrey, lightgray/lightgrey).

Schema bump v2.1 -> v3:

```json
{
  "version": 3,
  "schema_rev": "3.0",
  "corpora": [
    {
      "id": "jp-trad",
      "label": { "en": "Japanese traditional (NipponColors 250)", "ja": "日本の伝統色", "zh": "日本传统色" },
      "fields": [
        { "id": "name_ja", "label": { "en": "kanji",   "ja": "漢字",   "zh": "汉字" } },
        { "id": "romaji",  "label": { "en": "romaji",  "ja": "ローマ字", "zh": "罗马字" } },
        { "id": "name_en", "label": { "en": "English", "ja": "英語",   "zh": "英文" } },
        { "id": "name_zh", "label": { "en": "Chinese", "ja": "中国語", "zh": "中文" } }
      ],
      "default_display": "name_ja",
      "anchor": "cmyk",
      "source": "https://nipponcolors.com/ (250 entries, public)",
      "entries": [
        {
          "name_ja": "桜色", "romaji": "sakura-iro",
          "name_en": "cherry blossom", "name_zh": "樱花色",
          "hex": "#FEDFE1", "cmyk": [0, 11, 9, 0]
        }
      ]
    }
  ]
}
```

Tri-lingual field semantics per corpus:

| Corpus | name_en | name_ja | name_zh | translit field |
|---|---|---|---|---|
| jp-trad (native=ja) | gloss; fallback romaji | native (kanji) | gloss; fallback romaji | romaji always present |
| zh-trad (native=zh) | gloss; fallback pinyin | gloss; fallback pinyin | native (hanzi) | pinyin always present |
| html (native=en) | canonical always present | translit kana; fallback canonical | translit hanzi; fallback canonical | n/a |

Loader fill rule (after JSON parse, in-memory):
```js
for (const lib of libs) {
  for (const e of lib.entries) {
    for (const f of ['name_en','name_ja','name_zh']) {
      if (!e[f] || !e[f].trim()) {
        e[f] = e.romaji || e.pinyin || e.name_ja || e.name_zh || e.name_en || '?';
      }
    }
  }
}
```

Hard guarantee: every visible string slot non-empty. UI radio never shows blank entry.

Name uniqueness: closest swatch per (library, name) wears the name. Tolerance gates whether closest swatch displays it at all. Tiebreak on lower TAC, then lower K, then first encountered in lattice order.

Drop `system_name` synthesis entirely: remove `systemName`, `baseName`, `neutralName`, `lightnessBin`, `chromaBin`, `hueBin`, `HUE_NAMES`. Remove `s.system_name` field, CSV column, tooltip text.

### Per-library + global UI (Section 3)

Global match settings (link icon always visible):
- Anchor radio: cmyk | hex (governs all libraries)
- dE tolerance slider: 0.0 to 20.0, step 0.5, default 3.0

Per-library display radio (one per library, populated dynamically from lib.fields):
- Radio over each declared field + "hide" option
- User preference persisted in localStorage

UI controls update inline help text:
- "Match by CMYK->Lab (print) or hex->Lab (screen)"
- "Show a corpus name when swatch is within this dE of a named entry. Affects display only."

dE max filter is separate slider, separate concern (filters unreliable swatches by round-trip dE). Inline help: "Hide swatches whose round-trip dE on the active profile exceeds this. Use to gate gamut-safe colors."

### Profile-aware TAC + 3D-print preset (Section 4)

`data/luts/index.json` gains per-profile fields:

```json
{
  "filename": "CoatedFOGRA39.icc",
  "label": "Coated FOGRA39 (ISO 12647-2)",
  "tier_index": 1,
  "tac_recommended": 330,
  "tac_max": 350,
  "paper": "coated",
  "lut":  "data/luts/CoatedFOGRA39.lut",
  "rlut": "data/luts/CoatedFOGRA39.rcmyk.lut"
}
```

Values per [proof.de](https://proofing.de/proof-profile/) and [Cummings TAC notes](https://www.cummingsprinting.com/technotes/total-area-coverage/):

| Profile family | tac_recommended | tac_max |
|---|---|---|
| FOGRA39 (coated) | 330 | 350 |
| FOGRA29 (uncoated) | 260 | 290 |
| Japan Color 2001 Coated | 350 | 350 |
| Japan Color 2002 Newspaper | 240 | 260 |
| SWOP Coated | 300 | 320 |
| SWOP Uncoated | 260 | 290 |
| FOGRA27 (legacy coated) | 320 | 340 |
| FOGRA28 (legacy web coated) | 300 | 320 |

On profile change:
- If user has TAC at current default (240), snap to `profile.tac_recommended`
- If user has manually overridden TAC, leave alone, show "user override" badge
- Slider max dynamically clamps to `profile.tac_max`

TAC quick-preset buttons:
```
[ Newspaper 240 ] [ Uncoated 260 ] [ SWOP 300 ] [ FOGRA39 330 ] [ JapanColor 350 ] [ 3D-print 220 ]
```

3D-print preset checkbox: snaps TAC <=240, dE max <=3, hides unreliable swatches in one click.

### Dark-only + responsive + dynamic corpora (Section 5)

Dark mode lock: drop `@media (prefers-color-scheme:light)` block. Reason: surrounding luminance bias skews color picking in light mode.

Responsive breakpoints:

| Width | Layout |
|---|---|
| >= 1024px | sidebar 260px + grid (current) |
| 768-1023px | sidebar 220px, swatch cells auto-shrink |
| < 768px | sidebar -> slide-over drawer behind hamburger, grid full-width, cells min 36px |
| < 480px | cells 32px, detail panel becomes full-width bottom-sheet |

Touch targets >= 44px (Apple HIG / Material).

Dynamic corpora - drop hardcoded library IDs from swatch records:

Current pattern:
```js
s.jpn_name, s.jpn_closest, s.deltaE_jpn
s.html_name, s.html_closest, s.deltaE_html
_visibleNamedJpn(s), _visibleNamedHtml(s)
```

New pattern:
```js
s[`${lib.id}__name`]    // whole entry object, not just string
s[`${lib.id}__closest`]
s[`${lib.id}__deltaE`]
// Single helper:
function _visibleNamedFor(s, lib) {
  return s[`${lib.id}__closest`] && (s[`${lib.id}__deltaE`] ?? Infinity) <= curTol;
}
```

Tooltip per-library display lookup:
```js
for (const lib of CORPORA.libraries) {
  const entry = s[`${lib.id}__name`];
  if (!entry) continue;
  const displayField = _libPref(lib.id).display;
  if (displayField === 'hide') continue;
  showBadge(entry[displayField] || entry.name_en || '?');
}
```

Adding a new corpus to `name_corpora.json` (e.g. `fr-trad`, `pantone-trad`) - loader picks it up automatically, naming UI builds a section, swatches auto-gain `${lib.id}__*` fields, filter UI gets checkbox, CSV export includes it. Zero code changes required.

## Storage migrations

localStorage:

Current: `cmykUIState_v1`. New: `cmykUIState_v2`.

```js
const v1 = localStorage.getItem('cmykUIState_v1');
const v2 = localStorage.getItem('cmykUIState_v2');
if (v2) { state = JSON.parse(v2); }
else if (v1) {
  state = migrate_v1_to_v2(JSON.parse(v1));
  localStorage.setItem('cmykUIState_v2', JSON.stringify(state));
}
else { state = defaults; }
```

`migrate_v1_to_v2`:
- Add `lab_mode: 'd50'`
- Add `gamut_safe_only: false`
- Rewrite `corpora_prefs` -> `{ _global: { anchor, tolerance }, [lib.id]: { display } }`
- Map old library IDs: `jpn` -> `jp-trad`
- Discard `jpn-dic`, `zh-dic` prefs (corpora dropped)

`name_corpora.json`:
- v2.1 -> v3 (schema described above)
- Loader auto-promotes v2.1 in memory if stale JSON encountered (defensive)
- Repo ships v3 natively

`ui_defaults.json` additions:
```json
{
  "cmyk_explorer": {
    "lab_mode": "d50",
    "gamut_safe_only": false,
    "corpora_prefs": {
      "_global": { "anchor": "cmyk", "tolerance": 3.0 },
      "jp-trad": { "display": "name_ja" },
      "html":    { "display": "name_en" },
      "zh-trad": { "display": "name_zh" }
    }
  }
}
```

## Files changed/added

| Path | Change |
|---|---|
| `app/mixo-swatch.html` | Bradford + dual Lab + LAB_MODE toggle + drop systemName/HUE_NAMES + drop hardcoded library IDs (dynamic `${lib.id}__field` naming) + global anchor/tolerance + per-library display radios + TAC quick-presets + 3D-print preset + dark-only CSS + responsive breakpoints + mobile drawer + v1->v2 migration |
| `data/corpora/name_corpora.json` | v3 schema, jp-trad (250 NipponColors), html (147 W3C canonical), zh-trad (526 community) |
| `data/luts/index.json` | per-profile tac_recommended + tac_max + paper |
| `data/ui_defaults.json` | new field defaults |
| `scripts/validate_corpora.py` | new: schema + tri-lingual fill + uniqueness validation |
| `scripts/build_corpora.py` | new (optional): aggregates raw NipponColors + Chinese 526 + W3C into v3 JSON |
| `docs/superpowers/specs/2026-06-03-color-math-corpora-ui-fix-design.md` | this spec |

## Verification plan

1. **Math:** 10 known sRGB hex tested against Color.js + Photoshop Lab_D50 readings. Pass if dE <= 0.1.
2. **Round-trip dE:** values near-identical before/after Bradford fix (diff < 0.5).
3. **Uniqueness:** no name appears on two swatches per library.
4. **Tri-lingual fill:** validator script asserts no empty `name_en/name_ja/name_zh` post-load.
5. **TAC presets:** click each quick-preset, slider snaps + grid filters correctly.
6. **3D-print preset:** TAC <= 240, dE max <= 3.
7. **Lab toggle:** flip print/screen < 100ms, names shift slightly, `delta_e_print` unchanged.
8. **Dynamic corpora:** add fake `test-trad` corpus to JSON, reload, confirm UI auto-builds section + checkbox + swatch fields.
9. **Mobile:** test 1024 / 768 / 480 widths in Chrome DevTools responsive mode. Sidebar drawer opens/closes. Touch targets >= 44px.
10. **Dark-only:** confirm no light-mode flash; OS light preference does not break layout.
11. **localStorage migration:** start with v1 in DevTools, reload, confirm v2 written + UI populated from migrated state.
12. **Em-dash compliance:** run `python -c "import sys; bad=[chr(0x2014),chr(0x2013)]; [print(p) for p in sys.argv[1:] if any(c in open(p,encoding='utf-8').read() for c in bad)]" app/mixo-swatch.html data/corpora/name_corpora.json` and confirm no paths printed. Hunts U+2014 and U+2013 (both banned per memory).

## Out of scope

- Touch gestures (swipe to dismiss panels) - deferred
- Light mode - intentionally dropped
- 3D-print profile LUTs - need physical printer calibration
- Per-library unlinkable global controls - future
- Additional corpora beyond jp-trad / html / zh-trad - future
- Pantone integration - licensing prohibitive

## Sources

- [W3C CSS Color Module Level 4](https://www.w3.org/TR/css-color-4/)
- [Color.js - chromatic adaptation (Bradford)](https://colorjs.io/docs/adaptation)
- [W3C css-color issue 6061 - D50/D65/ICC](https://github.com/w3c/csswg-drafts/issues/6061)
- [ISO 15076-1 Annex E.3 - ICC Bradford CAT](https://www.color.org/sRGB.pdf)
- [Delta E 101 - CIE76/94/2000](http://zschuessler.github.io/DeltaE/learn/)
- [proof.de - international proof profiles and TAC](https://proofing.de/proof-profile/)
- [Cummings Printing - Total Area Coverage notes](https://www.cummingsprinting.com/technotes/total-area-coverage/)
- [NipponColors - 250 traditional](https://nipponcolors.com/)
- [NipponColors scraped data gist](https://gist.github.com/RobertYim/3061171b1dbfa93d7f71720e94403382)
- [color-term.com - 526 traditional China](https://color-term.com/traditional-color-of-china/)
- [zerosoul/chinese-colors](https://github.com/zerosoul/chinese-colors)
- [Wikipedia - Traditional colors of Japan](https://en.wikipedia.org/wiki/Traditional_colors_of_Japan)
- [Wikipedia - Web colors](https://en.wikipedia.org/wiki/Web_colors)
