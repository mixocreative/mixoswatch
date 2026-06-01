# Spec 3 · App UX bundle (sidebar collapse + a11y + tooltip + states + select-forbid)

**Date:** 2026-06-01
**Author:** mixocreative (via brainstorm cycle)
**Scope:** `app/cmyk-explorer.html`, `app/3d-explorer.html`
**Status:** awaiting user review

---

## 0. Why this spec

The two explorer apps work but a layman opening either lands on a wall of dense controls with technical labels, jargon-heavy tooltips, silent failure modes, and accidental text-highlighting when dragging sliders. Spec 3 bundles five concrete UX hardening fixes that each tighten the user feedback loop without changing what the tools do.

The five concerns are independent enough that any one could ship in isolation, but they touch the same files and gain from being implemented in one pass. Keeping them as one spec avoids merge-friction.

Dependency note: Section 3 (tooltip layman rewrite) ships in English first. Spec 2 (i18n) implementation then translates the already-clean English. If Specs 2 and 3 implement in parallel, the i18n table re-translates after the rewrite lands. To avoid wasted work, implement Spec 3 Section 3 before Spec 2's tooltip-translation pass.

---

## 1. Goals + non-goals

### Goals

- Sidebar's 4-step grouping becomes sticky + collapsible. User can fold steps independently. Default state: all open. Reset-to-defaults restores all-open.
- Top 5 a11y issues fixed (form-control grouping, focus rings, aria-live status, dialog focus trap, missing ARIA labels on custom widgets).
- All ~110 tooltips rewritten in plain language with optional brand-name suffix for power users. Vocabulary aligned with landing glossary.
- Loading, error, and empty-state messaging follows one consistent template per category. All messages route through Spec 2's `t()` helper.
- Slider drags cannot accidentally highlight adjacent label text. Detail card values stay user-selectable.

### Non-goals

- Touch `index.html`.
- Full WCAG 2.1 AA audit. Targeted hits only.
- Color contrast retuning (already passed in prior spec).
- Internationalization mechanics (Spec 2's concern).
- Performance changes (Spec 4's concern).
- Visual redesign of any control.

---

## 2. Design

### 2.1 Sticky + collapsible step groups

**Markup change.** Wrap each step group's `.sec` blocks in native `<details>` / `<summary>` with the existing `.step-group-header` as the summary content.

```html
<details class="step-group" id="step-01" open>
  <summary class="step-group-header">
    <span class="num">01</span>
    <span class="lbl"><span data-en>Pick a profile</span><span data-ja>プロファイルを選ぶ</span><span data-zh>選擇描述檔</span></span>
    <span class="sub"><span data-en>press + size</span><span data-ja>プリンター + サイズ</span><span data-zh>機台 + 尺寸</span></span>
    <span class="chev" aria-hidden="true"></span>
  </summary>
  <div class="step-group-body">
    <!-- existing .sec blocks live here verbatim -->
  </div>
</details>
```

**Why `<details>`/`<summary>`:** native HTML disclosure. Free keyboard handling (Enter and Space toggle), free `aria-expanded`, free screen-reader announcement, zero JS for the open / close mechanic itself.

**CSS additions:**

```css
.step-group { margin: 0; }
.step-group + .step-group { margin-top: 8px; }
.step-group > summary {
  cursor: pointer;
  list-style: none;
  position: sticky;
  top: 0;
  z-index: 2;
  background: var(--surface);
  padding-block: 12px;
  /* override existing .step-group-header margin from earlier turn */
  margin: 0;
}
.step-group > summary::-webkit-details-marker { display: none; }
.step-group > summary .chev {
  width: 8px; height: 8px;
  margin-left: auto;
  border-right: 1.5px solid var(--accent);
  border-bottom: 1.5px solid var(--accent);
  transform: rotate(-45deg);
  transition: transform .18s ease;
  flex: none;
}
.step-group[open] > summary .chev { transform: rotate(45deg); }
.step-group-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-block: 8px 4px;
}
```

**Multi-open default per Q2 = C.** All four steps render with `<details open>` on first paint.

**Persistence.** New `localStorage` key per app: `cmykStepFold_v1` for the CMYK explorer, `threeDStepFold_v1` for the 3D explorer. Shape:

```json
{ "01": true, "02": true, "03": false, "04": true }
```

`true` = open. JS hooks `toggle` event on each `<details>` and writes the snapshot. On load, iterate the saved snapshot and set the `open` attribute per group. Missing keys default to `true` (open).

**Reset behavior.** The existing "↺ Reset UI to defaults" handler clears the `cmykStepFold_v1` / `threeDStepFold_v1` localStorage key alongside its existing key list. Re-applies all-open.

### 2.2 Targeted a11y fixes

Five mechanical fixes. Each is a single isolated edit.

| # | Issue | Fix |
|---|---|---|
| 1 | Library-filter checkboxes are visually a group but have no a11y grouping | Add `<fieldset class="flt-fieldset"><legend class="visually-hidden">{lib filter}</legend>...</fieldset>` around the checkbox list. Existing `.flt-row` markup stays inside. |
| 2 | Naming radios for each library are individually labeled but the group lacks an accessible name | Add `aria-labelledby="nm-{lib.id}-head"` to the radio container; the existing `.nm-head` element gains a matching `id`. |
| 3 | Range sliders (ΔE max, name tolerance, cell-size, CMYK ranges, TAC) have no visible focus ring | Add `input[type=range]:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; border-radius: 4px; }` |
| 4 | Status changes (LUT load progress, count label updates, error messages) not announced to screen readers | `#iccStatus` gets `role="status" aria-live="polite"`; `#countLabel` gets `aria-live="polite"`; progress overlay's `#lpLabel` gets `role="status" aria-live="assertive"`. |
| 5 | Detail card overlay lacks a dialog role + focus trap + Esc handler | Wrap content in `<div role="dialog" aria-modal="true" aria-labelledby="dTitle">`; JS captures Tab + Shift+Tab cycle inside `.detail-card`; existing Esc handler already in place. |

**Visually-hidden helper class** added to shared CSS:

```css
.visually-hidden {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  white-space: nowrap;
  border: 0;
}
```

### 2.3 Tooltip layman rewrite

**Procedure during implementation:**

1. Grep both HTMLs for `title="..."` and `data-title-en="..."`. Build an inventory.
2. Classify each entry as `safe` (no unexplained jargon) or `jargon` (contains `ΔE`, `TAC`, `K-tier`, `GCR`, `gamut`, `ICC`, `LUT`, `anchor`, `WCAG`, `chroma` without an inline definition in the same string).
3. For each `jargon` entry, rewrite to the two-clause format:

   **`{what it does in plain language} · {brand-name link for power users}`**

   The `· {brand name}` suffix is optional. Use it only when the brand term is the well-known shorthand professionals search for.

**Example rewrites:**

| Old (jargon) | New (layman + brand-name suffix) |
|---|---|
| `How loose the name match must be (Delta-E). 0 = only the single closest swatch wears the name.` | `How loose to be when matching a swatch to a named color. 0 = strict, only one swatch per name. Higher = looser. · ΔE 2000 tolerance` |
| `Total ink coverage cap. Commercial coated ≈ 300%, newspaper ≈ 240%.` | `Maximum ink the press can hold without smudging. Coated paper around 300%, newspaper around 240%. · TAC limit` |
| `Use Tier 1 for clean brand-safe darks; Tier 3 unlocks true blacks.` | `How dark colors can go. Tier 1 = light + clean. Tier 3 = deepest blacks. · K-channel range` |
| `Maximum round-trip color error (Delta-E) you'll accept.` | `How much color shift to accept between what you pick and what the press prints. Lower = safer, fewer swatches. · ΔE round-trip cap` |
| `Hex anchor matches the corpus's hex value directly. CMYK anchor routes through the active ICC profile first.` | `Which side of a named color is "real". hex = trust the published color. cmyk = trust the published ink mix; let the profile show what that ink mix actually looks like. · ICC anchor mode` |

**Cross-reference rule:** any term also explained in the landing's glossary uses the same plain-language phrasing. If the landing glossary changes, tooltips track.

**Estimate:** ~50 of ~110 entries need rewrite. Remainder pass through unchanged.

### 2.4 Standardized loading / error / empty-state messaging

#### Loading templates

| State | Template | Surface |
|---|---|---|
| Initial bootstrap | `Loading {profile_label}...` | progress overlay label |
| Per-chunk derive | `Processing {n} / {m} swatches` | progress overlay sub |
| Rematch on anchor flip | `Rematching {library_label}...` | progress overlay label |
| LUT fetch | `Fetching color tables...` | progress overlay label |
| Library JSON fetch | `Loading {library_filename}...` | progress overlay label |

All templates ship through Spec 2's `t()` so they translate to JA / ZH.

#### Error templates (banner component)

New component: top-of-grid-area dismissible banner.

```html
<div class="banner banner-err" role="alert">
  <span class="banner-icon" aria-hidden="true">!</span>
  <span class="banner-msg" id="bannerMsg"></span>
  <button class="banner-close" aria-label="Dismiss" onclick="dismissBanner()">×</button>
</div>
```

Slide-in from top of `.grid-area`, 200ms transform animation. Persists until user dismisses or the underlying condition clears.

| Trigger | Template |
|---|---|
| `file://` protocol | `mixoswatch needs HTTP. Open run.bat (Windows) or run.sh (macOS / Linux).` |
| `data/luts/index.json` 404 or fetch fail | `Color tables missing. Run: python scripts/gen_luts.py` |
| `data/libraries/library_index.json` 404 | `Curated library missing. Run: python scripts/gen_libraries.py` |
| LUT magic mismatch | `Color table file corrupt. Re-run: python scripts/gen_luts.py --force` |
| Generic fetch fail | `Cannot reach {path}. Confirm the page is served via the local HTTP server.` |
| Library count zero after filter | (handled by empty-state, not banner) |

#### Empty-state copy (inline within affected panel)

| State | Copy |
|---|---|
| No swatches pass filter | `No swatches match the current filters. Loosen K-tier, raise TAC, or clear the search box.` |
| No palette selected | `No palette selected. Pick one in the dropdown, or click + New.` |
| Empty palette | `Empty palette. Enable Select mode in the topbar and click swatches to add.` |
| No corpora loaded | `No name corpora loaded. Check data/corpora/name_corpora.json exists.` |
| No matching named swatches | `No swatches match a name in the checked libraries. Tick more libraries, raise tolerance, or clear search.` |

All routed through `t()`.

### 2.5 Text-select forbid (slider tracks + adjacent labels)

Per Q6 = B. Conservative scope. CSS-only, no JS.

```css
input[type=range],
.slider-row,
.slider-row label,
.slider-row .value-display,
#vTol, #vDEmax, #vCell, #vTAC,
#vCmn, #vCmx, #vMmn, #vMmx, #vYmn, #vYmx, #vKmn, #vKmx {
  user-select: none;
  -webkit-user-select: none;
}
.detail-card,
.detail-card * {
  user-select: text;
  -webkit-user-select: text;
}
```

Detail card explicitly opts back into selectable text so the user can copy hex / CMYK / name values into design apps.

---

## 3. File-by-file change list

| File | Change | Magnitude |
|---|---|---|
| `app/cmyk-explorer.html` | Wrap 4 step groups in `<details>` markup; add `.step-group-body` CSS + sticky summary + chevron; fold persistence via `localStorage[cmykStepFold_v1]`; clear that key in the existing reset handler; add 5 a11y fixes (fieldsets, aria-labelledby, focus-visible, aria-live, dialog role + focus trap); add `.visually-hidden` helper class; rewrite ~50 jargon tooltips; standardize ~12 message templates via `t()` (Spec 2 dependency); add `.banner` component + `dismissBanner()` JS; add `user-select: none` on slider chrome | ~480 inserted lines, ~140 modified |
| `app/3d-explorer.html` | Same pattern; smaller tooltip + message surface | ~380 inserted lines, ~110 modified |
| No new files | (none) | (none) |

---

## 4. Cross-spec ordering

| Order | Reason |
|---|---|
| Spec 3 Section 3 (tooltip rewrite) **before** Spec 2 implementation | Translate clean English, not jargon. Otherwise i18n table goes stale immediately. |
| Spec 3 Section 4 (`t()` templates) **after** Spec 2 implementation | `t()` helper does not exist until Spec 2 ships. Loading / error / empty copy can be inlined as raw English in the meantime, then swept into `t()` callsites in a follow-up commit. Implementation plan must call this out. |
| Spec 3 Section 1 (sticky collapsible) **independent** | No dependency on either Spec 2 or other Spec 3 sections. Can ship first if convenient. |
| Spec 3 Section 2 (a11y) **independent** | Mechanical. |
| Spec 3 Section 5 (select-forbid) **independent** | CSS-only. Trivial. |

Recommended implementation order within Spec 3: Section 5 (trivial) → Section 1 (markup change, low risk) → Section 2 (mechanical) → Section 3 (tooltip rewrite, English only) → Section 4 (after Spec 2's `t()` exists).

---

## 5. Validation gates

1. Native `<details>` toggles via keyboard (Enter / Space) without any added JS handler.
2. Sticky group headers do not overlap other content; horizontal scroll never appears in the sidebar.
3. Fold state persists per app key across reloads; verified by `localStorage.getItem('cmykStepFold_v1')` after a toggle.
4. Reset-to-defaults clears the `StepFold` localStorage key alongside its existing key list; verified by checking the key is gone after click.
5. DevTools accessibility tree shows: library-filter fieldset legend, naming radio groups named, range sliders focusable with visible ring, `#iccStatus` + `#countLabel` exposed as `role=status`, detail card dialog has `aria-modal=true`.
6. Tab key cycles inside the detail card when open; Tab from the last focusable element returns to the first; Esc still closes.
7. Tooltip grep: zero remaining tooltips contain unexplained `ΔE`, `TAC`, `K-tier`, `GCR`, `gamut`, `anchor`. Implementation plan includes the grep audit step.
8. Banner component appears when `data/luts/index.json` is unreachable (simulate via DevTools block-request).
9. Empty-state copy renders for: no-swatches-after-filter, no-palette-selected, empty-palette, no-corpora, no-matching-named. Manual smoke per app.
10. Slider drag attempt does not select adjacent label text. Detail card values still selectable. Verified by attempting to drag-select inside both regions.
11. JS parses cleanly in both HTMLs.
12. Em-dash / en-dash count stays at 0.

---

## 6. Open questions (none blocking)

- Should the banner component animate downward into the grid area, or float above grid content as an overlay? Spec defaults to slide-in from top; implementation plan can revisit if it interferes with scroll. Non-blocking.
- Should `<details>` step groups also collapse on a mobile breakpoint? Spec leaves them at default state (all open) on mobile; user folds manually. Could add auto-collapse on `max-width: 640px` in a later round.

---

## 7. Cross-references

- Brainstorm transcript: this session.
- Sibling specs:
  - **Spec 1** · landing honesty + GH Pages (approved, queued for plan).
  - **Spec 2** · app HTMLs tri-lingual i18n (approved, queued for plan). Dependency for Section 4 of this spec.
  - **Spec 4** · app latency hardening (Worker, IntersectionObserver, prefetch) · pending brainstorm.
- ARCHITECTURE.md sections relevant: §8.4 (view modes), §8.5 (filters), §10 (UI / UX rationale).
- Landing glossary at `index.html` `#glossary` is the canonical plain-language source for `ICC profile`, `TAC`, `K-tier`, `WCAG`, `ΔE`, `Anchor`, `Naming libraries`.
