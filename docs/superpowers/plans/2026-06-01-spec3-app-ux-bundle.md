# Spec 3 Implementation Plan · App UX bundle

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine `app/cmyk-explorer.html` + `app/3d-explorer.html` with five UX hardening fixes: native `<details>` sticky-collapsible step groups with multi-open default and localStorage fold-state persistence; five targeted a11y mechanical fixes; layman-language rewrite of all ~110 tooltips; standardized loading / error / empty-state copy with a new banner component; slider-chrome text-select forbid.

**Architecture:** Pattern-per-concern, applied identically to both HTMLs. The 5 concerns are independent (no shared code), so the implementation order within Spec 3 is by risk and dependency: Section 5 (CSS-only, trivial) → Section 1 (markup change) → Section 2 (mechanical a11y) → Section 3 (tooltip English rewrite) → Section 4 (banner + state copy; only the English text lands here; `t()` wiring waits for Spec 2). Tooltip rewrite must precede Spec 2's i18n translation pass so the i18n table translates clean English.

**Tech Stack:** Vanilla HTML / CSS / JS. Native `<details>` / `<summary>`. Native `<fieldset>` / `<legend>`. `aria-live` / `aria-labelledby` / `role="dialog"`. CSS `user-select`. No new dependencies.

**Reference spec:** `docs/superpowers/specs/2026-06-01-app-ux-bundle-design.md`

---

## File Structure

| File | Action | Reason |
|---|---|---|
| `app/cmyk-explorer.html` | Modify | All 5 sections apply to this file |
| `app/3d-explorer.html` | Modify | All 5 sections apply identically |
| `docs/superpowers/plans/2026-06-01-spec3-app-ux-bundle.md` | This file | Plan record |

No new files. No new folders. No assets.

---

## Pre-flight: baseline snapshot

Run once before starting any task in this plan.

```bash
cd S:/mixoswatch
# Baseline em-dash counts (apps have legacy dashes from earlier turns; not blocking Spec 3 but record for delta-checking)
echo "cmyk-explorer em-dashes:"; grep -c "—\|–" app/cmyk-explorer.html
echo "3d-explorer em-dashes:"; grep -c "—\|–" app/3d-explorer.html
# Baseline JS parse
node -e "const fs=require('fs');for(const f of ['app/cmyk-explorer.html','app/3d-explorer.html']){const html=fs.readFileSync(f,'utf-8');const m=html.match(/<script>([\\s\\S]*?)<\\/script>/);try{new Function(m[1]);console.log(f,'JS OK');}catch(e){console.log(f,'ERR:',e.message.split('\\n')[0]);}}"
# Baseline tooltip count
echo "cmyk-explorer title attrs:"; grep -c 'title=' app/cmyk-explorer.html
echo "3d-explorer title attrs:"; grep -c 'title=' app/3d-explorer.html
```

Record the output. Subsequent verification compares deltas.

---

# SECTION 5 · Slider-chrome text-select forbid

Trivial CSS-only change. Implement first; lowest risk.

## Task 5.1: CSS rule additions for select-forbid (cmyk-explorer)

**Files:**
- Modify: `app/cmyk-explorer.html` (CSS block in `<head>`)

- [ ] **Step 1: Find the existing CSS closing `</style>` tag**

Run:
```bash
grep -n "</style>" "S:/mixoswatch/app/cmyk-explorer.html" | head -1
```
Note the line number. Insertion happens immediately before this line.

- [ ] **Step 2: Insert the select-forbid CSS rules**

Use the Edit tool. Locate a stable anchor inside the existing CSS (the last rule before `</style>`). Append the new block before `</style>`:

`old_string`: the last existing CSS selector + closing `</style>`. For example, if the last rule is `.flt-all{font-weight:600;border-bottom:1px solid var(--border2);padding-bottom:5px;margin-bottom:3px}`, then:
```
.flt-all{font-weight:600;border-bottom:1px solid var(--border2);padding-bottom:5px;margin-bottom:3px}
</style>
```

`new_string`:
```
.flt-all{font-weight:600;border-bottom:1px solid var(--border2);padding-bottom:5px;margin-bottom:3px}

/* Spec 3 §2.5: slider-chrome text-select forbid */
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
</style>
```

If the actual last CSS rule differs, locate it with `grep -B1 "</style>" app/cmyk-explorer.html | head -5` and use its real text.

- [ ] **Step 3: Verify CSS rule landed**

Run:
```bash
grep -c "Spec 3 §2.5: slider-chrome text-select forbid" "S:/mixoswatch/app/cmyk-explorer.html"
```
Expected: `1`.

- [ ] **Step 4: JS parse check**

Run:
```bash
node -e "const fs=require('fs');const html=fs.readFileSync('S:/mixoswatch/app/cmyk-explorer.html','utf-8');const m=html.match(/<script>([\\s\\S]*?)<\\/script>/);try{new Function(m[1]);console.log('JS OK');}catch(e){console.log('ERR:',e.message);}"
```
Expected: `JS OK` (CSS edit cannot affect JS but confirm structural integrity).

- [ ] **Step 5: Commit**

Run:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html && git commit -m "feat(cmyk): forbid text-select on slider chrome (Spec 3 §2.5)

Sliders, slider rows, value-display chips get user-select: none so
drags don't accidentally highlight adjacent labels. Detail card opts
back into selectable text so users can still copy hex / CMYK / name
values.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

## Task 5.2: Apply the same rule to 3d-explorer

**Files:**
- Modify: `app/3d-explorer.html`

Repeat Task 5.1 steps 1-5 with `app/3d-explorer.html` substituted everywhere. Note: the 3D explorer has the same value-display IDs as the CMYK explorer (`#vTol`, `#vDEmax`, `#vCell`, `#vTAC`, `#vCmn..vKmx`) per the existing shared topbar / slider markup, so the same selector list applies unchanged.

Commit message:
```
feat(3d): forbid text-select on slider chrome (Spec 3 §2.5)

Same selector set as cmyk-explorer. Detail card opts back into
selectable text.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

- [ ] **Step 6: Browser smoke test**

Open both files in a browser via `run.bat` / `run.sh`. Try drag-selecting across slider labels in the sidebar. Expected: selection skips the slider-chrome zones. Try selecting hex value inside an opened detail card. Expected: selection works normally.

---

# SECTION 1 · Sticky + collapsible step groups via `<details>`

Markup transformation + small CSS + small JS for persistence.

## Task 1.1: Add visually-hidden helper class (shared, used here + Section 2)

**Files:**
- Modify: `app/cmyk-explorer.html`, `app/3d-explorer.html`

- [ ] **Step 1: Add `.visually-hidden` to both HTML CSS blocks**

For each of the two HTML files:

Use the Edit tool with:

`old_string` (the just-added Section 5 closing block, or the last existing CSS rule before `</style>` if Section 5 was skipped):
```
.detail-card * {
  user-select: text;
  -webkit-user-select: text;
}
</style>
```

`new_string`:
```
.detail-card * {
  user-select: text;
  -webkit-user-select: text;
}

/* Spec 3 §2.2: visually-hidden helper for a11y legends + skip links */
.visually-hidden {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
```

- [ ] **Step 2: Verify both files have the helper class**

Run:
```bash
grep -c "Spec 3 §2.2: visually-hidden helper" "S:/mixoswatch/app/cmyk-explorer.html"
grep -c "Spec 3 §2.2: visually-hidden helper" "S:/mixoswatch/app/3d-explorer.html"
```
Expected: `1` and `1`.

- [ ] **Step 3: Commit**

Run:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html app/3d-explorer.html && git commit -m "feat(apps): add .visually-hidden helper class (Spec 3 §2.2)

Shared accessibility utility. Used by Section 1 fieldset legends and
Section 2 ARIA hooks.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

## Task 1.2: Add `.step-group` CSS for sticky + chevron

**Files:**
- Modify: `app/cmyk-explorer.html`, `app/3d-explorer.html`

- [ ] **Step 1: Insert step-group CSS block in cmyk-explorer**

Use the Edit tool with:

`old_string`:
```
/* Spec 3 §2.2: visually-hidden helper for a11y legends + skip links */
.visually-hidden {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
```

`new_string`:
```
/* Spec 3 §2.2: visually-hidden helper for a11y legends + skip links */
.visually-hidden {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Spec 3 §2.1: sticky + collapsible step groups via native <details> */
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
  margin: 0;
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-family: var(--font-mono);
}
.step-group > summary::-webkit-details-marker { display: none; }
.step-group > summary .chev {
  width: 7px; height: 7px;
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
</style>
```

- [ ] **Step 2: Same insertion in 3d-explorer**

Repeat Step 1 with `app/3d-explorer.html`.

- [ ] **Step 3: Verify both files have the new CSS**

Run:
```bash
grep -c "Spec 3 §2.1: sticky + collapsible step groups" "S:/mixoswatch/app/cmyk-explorer.html"
grep -c "Spec 3 §2.1: sticky + collapsible step groups" "S:/mixoswatch/app/3d-explorer.html"
```
Expected: `1` and `1`.

- [ ] **Step 4: Commit**

Run:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html app/3d-explorer.html && git commit -m "feat(apps): add step-group CSS for sticky + collapsible (Spec 3 §2.1)

Native <details>/<summary> styling. Sticky summary, chevron that
rotates with [open], hidden default disclosure triangle. .step-group-body
sets vertical rhythm between contained .sec blocks.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

## Task 1.3: Wrap CMYK explorer's 4 step groups in `<details>` markup

**Files:**
- Modify: `app/cmyk-explorer.html`

Current sidebar pattern (from session memory):
- Group 01 header is followed by ICC profile + Palettes + Step interval + Cell size sections
- Group 02 header followed by CMYK range + TAC + K-tier
- Group 03 header followed by Named filter (with tolerance) + Naming per library
- Group 04 header followed by Sort + Defaults + Accessibility + Search

- [ ] **Step 1: Locate Group 01 header**

Run:
```bash
grep -n 'step-group-header' "S:/mixoswatch/app/cmyk-explorer.html"
```
Expected: 4 matches (one per existing group header from the prior session). Note line numbers.

- [ ] **Step 2: Wrap Group 01**

Locate the existing Group 01 header div and convert it to `<details>` + `<summary>`. Then close `</details>` immediately before the Group 02 header.

Use the Edit tool with:

`old_string`:
```
    <div class="step-group-header">
      <span class="num">01</span><span class="lbl">Pick a profile</span><span class="sub">press + size</span>
    </div>

    <!-- ICC Profile -->
```

`new_string`:
```
    <details class="step-group" id="step-01" open>
      <summary class="step-group-header">
        <span class="num">01</span><span class="lbl">Pick a profile</span><span class="sub">press + size</span>
        <span class="chev" aria-hidden="true"></span>
      </summary>
      <div class="step-group-body">

    <!-- ICC Profile -->
```

- [ ] **Step 3: Wrap Group 02 (closes 01 and opens 02)**

Use the Edit tool with:

`old_string`:
```
    <div class="step-group-header">
      <span class="num">02</span><span class="lbl">Narrow the set</span><span class="sub">filters + limits</span>
    </div>

    <div class="sec">
      <div class="sec-label">CMYK range</div>
```

`new_string`:
```
      </div>
    </details>

    <details class="step-group" id="step-02" open>
      <summary class="step-group-header">
        <span class="num">02</span><span class="lbl">Narrow the set</span><span class="sub">filters + limits</span>
        <span class="chev" aria-hidden="true"></span>
      </summary>
      <div class="step-group-body">

    <div class="sec">
      <div class="sec-label">CMYK range</div>
```

- [ ] **Step 4: Wrap Group 03**

Use the Edit tool with:

`old_string`:
```
    <div class="step-group-header">
      <span class="num">03</span><span class="lbl">Pick + name</span><span class="sub">corpora + match</span>
    </div>

    <div class="sec">
      <div class="sec-label">Named swatches · filter</div>
```

`new_string`:
```
      </div>
    </details>

    <details class="step-group" id="step-03" open>
      <summary class="step-group-header">
        <span class="num">03</span><span class="lbl">Pick + name</span><span class="sub">corpora + match</span>
        <span class="chev" aria-hidden="true"></span>
      </summary>
      <div class="step-group-body">

    <div class="sec">
      <div class="sec-label">Named swatches · filter</div>
```

- [ ] **Step 5: Wrap Group 04**

Use the Edit tool with:

`old_string`:
```
    <div class="step-group-header">
      <span class="num">04</span><span class="lbl">Sort + view</span><span class="sub">order + reset</span>
    </div>

    <div class="sec">
      <div class="sec-label">Sort by</div>
```

`new_string`:
```
      </div>
    </details>

    <details class="step-group" id="step-04" open>
      <summary class="step-group-header">
        <span class="num">04</span><span class="lbl">Sort + view</span><span class="sub">order + reset</span>
        <span class="chev" aria-hidden="true"></span>
      </summary>
      <div class="step-group-body">

    <div class="sec">
      <div class="sec-label">Sort by</div>
```

- [ ] **Step 6: Close the final `<details>` at end of sidebar**

Find the `</aside>` closing tag for the sidebar:
```bash
grep -n "</aside>" "S:/mixoswatch/app/cmyk-explorer.html" | head -1
```

Use the Edit tool with:

`old_string`:
```
    </aside>
```

`new_string`:
```
      </div>
    </details>

    </aside>
```

- [ ] **Step 7: Verify all 4 details elements present and balanced**

Run:
```bash
grep -c '<details class="step-group"' "S:/mixoswatch/app/cmyk-explorer.html"
grep -c '</details>' "S:/mixoswatch/app/cmyk-explorer.html"
```
Expected: `4` and `4`. If unbalanced, the wrap is broken; re-open the file and confirm each open `<details>` has a closing tag.

- [ ] **Step 8: JS parse + HTML structural smoke**

Run:
```bash
node -e "const fs=require('fs');const html=fs.readFileSync('S:/mixoswatch/app/cmyk-explorer.html','utf-8');const m=html.match(/<script>([\\s\\S]*?)<\\/script>/);try{new Function(m[1]);console.log('JS OK');}catch(e){console.log('ERR:',e.message);}"
```
Expected: `JS OK`.

Open file in browser via `run.bat`. Sidebar should render with 4 sticky collapsible groups, all open by default, chevrons pointing down (since `[open]` rotates to `45deg`).

- [ ] **Step 9: Commit**

Run:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html && git commit -m "feat(cmyk): wrap 4 step groups in <details> for sticky-collapsible (Spec 3 §2.1)

Native HTML disclosure: free keyboard support (Enter/Space toggle),
free aria-expanded, free screen-reader announcement. Default all-open
([open] attribute on each). Chevron auto-rotates via CSS.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

## Task 1.4: Wrap 3D explorer's 4 step groups identically

**Files:**
- Modify: `app/3d-explorer.html`

Repeat Task 1.3 steps 1-9 with `app/3d-explorer.html`. The 3D explorer's group contents differ (Group 02 contains ΔE max instead of CMYK range / TAC / K-tier; rest similar), but the wrap pattern is identical: convert each existing `<div class="step-group-header">` into `<details>` + `<summary>`, open `<div class="step-group-body">` immediately after, close it + `</details>` before the next group's header.

Concrete `old_string` / `new_string` anchors for 3D explorer:

| Group | Anchor sec-label (immediately after header) |
|---|---|
| 01 | `Library (ICC profile)` (the first `.sec-label` text after Group 01 header) |
| 02 | `ΔE max ·` (Group 02 header is followed by the ΔE max section, no CMYK ranges) |
| 03 | `Named swatches · filter` |
| 04 | `Sort by` |

Use the same wrapping pattern as cmyk-explorer Task 1.3 steps 2-5 with the appropriate sec-label anchors.

Commit message:
```
feat(3d): wrap 4 step groups in <details> for sticky-collapsible (Spec 3 §2.1)

Same pattern as cmyk-explorer. Group 02 contains ΔE max only; rest
identical structure.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

## Task 1.5: Add fold-state persistence JS (cmyk-explorer)

**Files:**
- Modify: `app/cmyk-explorer.html` (JS section)

- [ ] **Step 1: Locate the end of the existing window load handler or a stable JS insertion point**

Run:
```bash
grep -n "window.addEventListener('load'" "S:/mixoswatch/app/cmyk-explorer.html"
```
Find the line where boot listener starts.

- [ ] **Step 2: Find a `// ── ... ──` heading near the boot block to insert before**

Or, insert directly after the existing `_loadCorporaPrefs` helpers block. Choose any spot that runs before the boot handler.

Use the Edit tool with:

`old_string` (find one stable existing function declaration near the top of the script, e.g. the existing `function _loadCorporaPrefs(){...}`):
```
function _loadCorporaPrefs() {
```

`new_string`:
```
// ── Spec 3 §2.1: step-group fold state persistence ───────────────────────
const STEP_FOLD_KEY = 'cmykStepFold_v1';
function _loadStepFold() {
  try {
    const raw = localStorage.getItem(STEP_FOLD_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}
function _saveStepFold() {
  const state = {};
  document.querySelectorAll('details.step-group').forEach(d => {
    state[d.id.replace('step-', '')] = d.open;
  });
  try { localStorage.setItem(STEP_FOLD_KEY, JSON.stringify(state)); } catch {}
}
function _wireStepFold() {
  const saved = _loadStepFold();
  document.querySelectorAll('details.step-group').forEach(d => {
    if (saved) {
      const key = d.id.replace('step-', '');
      if (key in saved) d.open = !!saved[key];
    }
    d.addEventListener('toggle', _saveStepFold);
  });
}

function _loadCorporaPrefs() {
```

- [ ] **Step 3: Wire `_wireStepFold()` into boot**

Find the existing boot function (`window.addEventListener('load', async () => {...})`) and add `_wireStepFold();` near the top of its body, right after `_loadCorporaPrefs()` is called or any early helper invocation.

Use the Edit tool with:

`old_string` (search for an existing helper call near boot top; e.g. if the boot calls `loadPalettes();` early):
```
window.addEventListener('load', async () => {
  loadPalettes();
```

`new_string`:
```
window.addEventListener('load', async () => {
  loadPalettes();
  _wireStepFold();
```

If the existing boot top is different, locate a stable early line via `grep -n "addEventListener('load'" app/cmyk-explorer.html` and insert `_wireStepFold();` as the next line.

- [ ] **Step 4: Wire fold-state clear into the Reset-to-Defaults handler**

Find the existing `resetUIToDefaults` function:
```bash
grep -n "function resetUIToDefaults" "S:/mixoswatch/app/cmyk-explorer.html"
```

Inside the body of `resetUIToDefaults`, add an early line that clears `STEP_FOLD_KEY` and re-opens all groups.

Use the Edit tool with:

`old_string` (find the first line inside resetUIToDefaults that uses localStorage, e.g. the existing CORPORA_PREFS_KEY clear):
```
async function resetUIToDefaults() {
  if (!confirm('Reset all UI controls to defaults (saved palettes are kept). Continue?')) return;
  try { localStorage.removeItem(UI_STATE_KEY); } catch {}
```

`new_string`:
```
async function resetUIToDefaults() {
  if (!confirm('Reset all UI controls to defaults (saved palettes are kept). Continue?')) return;
  try { localStorage.removeItem(UI_STATE_KEY); } catch {}
  try { localStorage.removeItem(STEP_FOLD_KEY); } catch {}
  document.querySelectorAll('details.step-group').forEach(d => d.open = true);
```

- [ ] **Step 5: JS parse**

Run:
```bash
node -e "const fs=require('fs');const html=fs.readFileSync('S:/mixoswatch/app/cmyk-explorer.html','utf-8');const m=html.match(/<script>([\\s\\S]*?)<\\/script>/);try{new Function(m[1]);console.log('JS OK');}catch(e){console.log('ERR:',e.message);}"
```
Expected: `JS OK`.

- [ ] **Step 6: Manual browser smoke**

Open in browser. Collapse step group 02 by clicking its summary. Refresh page. Step group 02 should remain collapsed. Click Reset-to-Defaults. All four groups should open back.

- [ ] **Step 7: Commit**

Run:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html && git commit -m "feat(cmyk): persist step-group fold state in localStorage (Spec 3 §2.1)

cmykStepFold_v1 key holds {01:true, 02:false, ...}. _wireStepFold()
restores state on boot + binds toggle listener that auto-saves on
flip. resetUIToDefaults() clears the key and re-opens all groups.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

## Task 1.6: Same fold persistence for 3D explorer

**Files:**
- Modify: `app/3d-explorer.html`

Repeat Task 1.5 steps 1-7 with `app/3d-explorer.html` substituted, except:

- Use a DIFFERENT localStorage key:
  - `const STEP_FOLD_KEY = 'threeDStepFold_v1';` (note the variable name is shared in scope; if 3d-explorer's script already defines or imports `STEP_FOLD_KEY` from elsewhere, rename the 3D one to avoid collision)
- The same `_loadStepFold` / `_saveStepFold` / `_wireStepFold` body works unchanged.
- Inside `resetUIToDefaults`, use `threeDStepFold_v1` instead of `cmykStepFold_v1`.

Commit message:
```
feat(3d): persist step-group fold state in localStorage (Spec 3 §2.1)

threeDStepFold_v1 key. Same pattern as cmyk-explorer. Per-app keys
ensure fold state stays isolated between the two tools.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

---

# SECTION 2 · Targeted a11y mechanical fixes

Five small isolated edits. Apply each twice (CMYK + 3D).

## Task 2.1: Fieldset legend around library-filter checkbox group (both apps)

**Files:**
- Modify: `app/cmyk-explorer.html`, `app/3d-explorer.html`

- [ ] **Step 1: Locate the library filter checkbox container in cmyk-explorer**

Run:
```bash
grep -n 'filterCheckboxes' "S:/mixoswatch/app/cmyk-explorer.html"
```
Find the `<div id="filterCheckboxes">` element.

- [ ] **Step 2: Wrap the container in a fieldset**

Use the Edit tool. The exact `old_string` should include the existing div opening line; capture enough surrounding lines for uniqueness.

`old_string` (example; adjust to match the live markup):
```
      <div id="filterCheckboxes" style="margin-top:6px" title="When 'Any named' is on, only swatches that match a name in at least one of these checked libraries pass the filter. Independent of which name each library is set to display."></div>
```

`new_string`:
```
      <fieldset class="flt-fieldset" style="border:none;padding:0;margin:0">
        <legend class="visually-hidden">Library filter for "Any named"</legend>
        <div id="filterCheckboxes" style="margin-top:6px" title="When 'Any named' is on, only swatches that match a name in at least one of these checked libraries pass the filter. Independent of which name each library is set to display."></div>
      </fieldset>
```

- [ ] **Step 3: Same wrap in 3d-explorer**

Repeat Step 2 for `app/3d-explorer.html`.

- [ ] **Step 4: JS parse + visual smoke**

Run:
```bash
node -e "const fs=require('fs');for(const f of ['app/cmyk-explorer.html','app/3d-explorer.html']){const html=fs.readFileSync('S:/mixoswatch/'+f,'utf-8');const m=html.match(/<script>([\\s\\S]*?)<\\/script>/);try{new Function(m[1]);console.log(f,'JS OK');}catch(e){console.log(f,'ERR:',e.message);}}"
```
Expected: both `JS OK`.

Browser smoke: filter section visually unchanged (fieldset has no border, legend is visually-hidden); DevTools accessibility tree shows the checkboxes grouped under "Library filter for 'Any named'" legend.

- [ ] **Step 5: Commit**

Run:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html app/3d-explorer.html && git commit -m "a11y(apps): wrap library-filter checkboxes in fieldset+legend (Spec 3 §2.2 fix 1)

Screen readers now announce the checkbox group under a named legend
('Library filter for Any named'). Visual layout unchanged via
border:none + .visually-hidden legend.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

## Task 2.2: aria-labelledby on each naming radio group (both apps)

**Files:**
- Modify: `app/cmyk-explorer.html`, `app/3d-explorer.html` (the `buildNamingUI` JS function)

- [ ] **Step 1: Locate buildNamingUI in cmyk-explorer**

Run:
```bash
grep -n "function buildNamingUI" "S:/mixoswatch/app/cmyk-explorer.html"
```

- [ ] **Step 2: Inside the per-library loop, give the head element an id; add aria-labelledby to the radios container**

Use the Edit tool with:

`old_string` (existing per-lib head + radios wiring; capture with enough context to be unique):
```
    const head = document.createElement('div');
    head.className = 'nm-head';
    head.textContent = lib.label;
    head.title = `${lib.entries.length} entries · fields: `
              + lib.fields.map(f => f.label || f.id).join(', ');
    row.appendChild(head);

    // Radio group: one radio per declared field + hide.
    const radios = document.createElement('div');
    radios.className = 'nm-radios';
    const groupName = 'nm-' + lib.id;
```

`new_string`:
```
    const head = document.createElement('div');
    head.className = 'nm-head';
    head.id = 'nm-' + lib.id + '-head';
    head.textContent = lib.label;
    head.title = `${lib.entries.length} entries · fields: `
              + lib.fields.map(f => f.label || f.id).join(', ');
    row.appendChild(head);

    // Radio group: one radio per declared field + hide.
    const radios = document.createElement('div');
    radios.className = 'nm-radios';
    radios.setAttribute('role', 'radiogroup');
    radios.setAttribute('aria-labelledby', 'nm-' + lib.id + '-head');
    const groupName = 'nm-' + lib.id;
```

- [ ] **Step 3: Repeat in 3d-explorer's buildNamingUI**

Run `grep -n "function buildNamingUI" "S:/mixoswatch/app/3d-explorer.html"` and apply the same edit.

- [ ] **Step 4: JS parse + accessibility tree smoke**

Run:
```bash
node -e "const fs=require('fs');for(const f of ['app/cmyk-explorer.html','app/3d-explorer.html']){const html=fs.readFileSync('S:/mixoswatch/'+f,'utf-8');const m=html.match(/<script>([\\s\\S]*?)<\\/script>/);try{new Function(m[1]);console.log(f,'JS OK');}catch(e){console.log(f,'ERR:',e.message);}}"
```
Expected: both `JS OK`.

Browser smoke: open DevTools accessibility tree; verify each naming radio group is announced as a radiogroup with the library label as accessible name.

- [ ] **Step 5: Commit**

Run:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html app/3d-explorer.html && git commit -m "a11y(apps): label naming radio groups via aria-labelledby (Spec 3 §2.2 fix 2)

Each .nm-head gets an id; the matching radios container gets
role=radiogroup + aria-labelledby pointing at it. Screen readers now
announce each library's radio group with the library label.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

## Task 2.3: Focus rings on range sliders (both apps)

**Files:**
- Modify: `app/cmyk-explorer.html`, `app/3d-explorer.html` (CSS block)

- [ ] **Step 1: Insert focus-visible rule after the select-forbid block**

For each HTML file, use the Edit tool with:

`old_string`:
```
.detail-card * {
  user-select: text;
  -webkit-user-select: text;
}
```

`new_string`:
```
.detail-card * {
  user-select: text;
  -webkit-user-select: text;
}

/* Spec 3 §2.2 fix 3: visible focus rings on range sliders */
input[type=range]:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
  border-radius: 4px;
}
```

- [ ] **Step 2: JS parse + keyboard smoke**

Run JS parse check for both files. Expected: `JS OK`.

Browser smoke: Tab to any slider; visible accent ring appears around the thumb track. Tab past; ring disappears.

- [ ] **Step 3: Commit**

Run:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html app/3d-explorer.html && git commit -m "a11y(apps): focus-visible rings on range sliders (Spec 3 §2.2 fix 3)

Accent-color outline on input[type=range]:focus-visible. Keyboard
users see which slider is focused before they press arrow keys to
adjust.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

## Task 2.4: aria-live regions on status surfaces (both apps)

**Files:**
- Modify: `app/cmyk-explorer.html`, `app/3d-explorer.html`

- [ ] **Step 1: Add aria-live to #countLabel**

Run:
```bash
grep -n 'id="countLabel"' "S:/mixoswatch/app/cmyk-explorer.html"
```

Use the Edit tool with:

`old_string` (capture the existing element opening):
```
    <div class="count-tag" id="countLabel"></div>
```

`new_string`:
```
    <div class="count-tag" id="countLabel" role="status" aria-live="polite" aria-atomic="true"></div>
```

If the existing class list differs, locate the actual line and add the three ARIA attributes; do not change the class or id.

- [ ] **Step 2: Add aria-live to #iccStatus**

Run:
```bash
grep -n 'id="iccStatus"' "S:/mixoswatch/app/cmyk-explorer.html"
```

Use the Edit tool with:

`old_string` (existing div):
```
      <div id="iccStatus" style="font-size:10px;color:var(--muted);font-family:var(--font-mono);margin-top:2px" title="Active profile + how many colors it has.">—</div>
```

`new_string`:
```
      <div id="iccStatus" role="status" aria-live="polite" style="font-size:10px;color:var(--muted);font-family:var(--font-mono);margin-top:2px" title="Active profile + how many colors it has.">—</div>
```

- [ ] **Step 3: Add aria-live to progress overlay label**

Run:
```bash
grep -n 'id="lpLabel"' "S:/mixoswatch/app/cmyk-explorer.html"
```

Use the Edit tool with:

`old_string`:
```
      '  <div class="lp-label" id="lpLabel">Loading…</div>' +
```

`new_string`:
```
      '  <div class="lp-label" id="lpLabel" role="status" aria-live="assertive">Loading…</div>' +
```

- [ ] **Step 4: Repeat all 3 edits in 3d-explorer.html**

Same steps. The id selectors (`#countLabel`, `#iccStatus`, `#lpLabel`) are shared between the two apps.

- [ ] **Step 5: JS parse**

Run for both files. Expected: `JS OK`.

- [ ] **Step 6: Commit**

Run:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html app/3d-explorer.html && git commit -m "a11y(apps): role=status + aria-live on countLabel, iccStatus, lpLabel (Spec 3 §2.2 fix 4)

Polite live region for the topbar count tag and the ICC status block;
assertive for the progress overlay label (interrupts speech for the
'still loading' update). aria-atomic ensures the full new text is
read, not just the delta.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

## Task 2.5: dialog role + focus trap on detail card overlay (both apps)

**Files:**
- Modify: `app/cmyk-explorer.html`, `app/3d-explorer.html`

- [ ] **Step 1: Locate the detail card overlay element**

Run:
```bash
grep -n 'class="overlay"' "S:/mixoswatch/app/cmyk-explorer.html"
grep -n 'class="detail-card"' "S:/mixoswatch/app/cmyk-explorer.html"
```

- [ ] **Step 2: Add dialog ARIA attributes to the detail card container**

Use the Edit tool. The existing overlay structure is likely:
```html
<div class="overlay" id="overlay">
  <div class="detail-card" id="detailCard">
    ...
  </div>
</div>
```

Locate the detail-card div opening and add `role="dialog" aria-modal="true" aria-labelledby="dTitle"`:

`old_string`:
```
  <div class="detail-card" id="detailCard">
```

`new_string`:
```
  <div class="detail-card" id="detailCard" role="dialog" aria-modal="true" aria-labelledby="dTitle">
```

If the `id="dTitle"` element does not exist inside the detail card, find the existing prominent title element (e.g. the hex display or system_name span) and give it `id="dTitle"`.

- [ ] **Step 3: Add focus trap helper**

Locate the existing `function openDetail(sw)` definition:
```bash
grep -n "function openDetail" "S:/mixoswatch/app/cmyk-explorer.html"
```

Append the focus-trap wiring at the end of openDetail. Use the Edit tool:

`old_string` (find the existing function's closing brace and the next line):
```
function openDetail(sw) {
```

If openDetail is short, find the entire function body and append the trap wiring at the end. The exact insertion depends on the existing function shape.

The trap function to add (place it near `closeDetail`):
```js
// Spec 3 §2.2 fix 5: focus trap inside detail card dialog
let _detailLastFocus = null;
function _trapDetail(e) {
  if (e.key !== 'Tab') return;
  const card = document.getElementById('detailCard');
  if (!card) return;
  const focusables = card.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  if (!focusables.length) return;
  const first = focusables[0];
  const last = focusables[focusables.length - 1];
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault(); last.focus();
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault(); first.focus();
  }
}
```

Wire into `openDetail`:
```js
function openDetail(sw) {
  _detailLastFocus = document.activeElement;
  // ... existing body ...
  document.addEventListener('keydown', _trapDetail);
  setTimeout(() => {
    const card = document.getElementById('detailCard');
    const focusables = card?.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    focusables?.[0]?.focus();
  }, 0);
}
```

Wire into `closeDetail`:
```js
function closeDetail() {
  // ... existing body ...
  document.removeEventListener('keydown', _trapDetail);
  if (_detailLastFocus && _detailLastFocus.focus) _detailLastFocus.focus();
}
```

Use the Edit tool to apply these three changes (helper + openDetail wiring + closeDetail wiring). Each is a separate edit; verify the existing closeDetail body before merging.

- [ ] **Step 4: Repeat all in 3d-explorer.html**

Same edits.

- [ ] **Step 5: JS parse**

Run both. Expected: `JS OK`.

- [ ] **Step 6: Keyboard smoke**

Browser: open any swatch's detail card. Tab cycles inside the card (last button → first via wrap). Esc still closes (existing handler). After close, focus returns to the swatch cell that opened the card.

- [ ] **Step 7: Commit**

Run:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html app/3d-explorer.html && git commit -m "a11y(apps): dialog role + focus trap on detail card (Spec 3 §2.2 fix 5)

detail-card gets role=dialog + aria-modal=true + aria-labelledby.
openDetail captures last focus and traps Tab inside the card.
closeDetail restores focus to the originating swatch cell.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

# SECTION 3 · Tooltip layman rewrite (English only)

This section rewrites English tooltip text. Spec 2's i18n pass translates these clean strings afterward.

## Task 3.1: Build tooltip inventory

**Files:**
- Read: `app/cmyk-explorer.html`, `app/3d-explorer.html`

- [ ] **Step 1: Extract all current `title="..."` strings to a workfile**

Run:
```bash
mkdir -p /tmp/spec3-tooltips
grep -oE 'title="[^"]+"' "S:/mixoswatch/app/cmyk-explorer.html" | sort -u > /tmp/spec3-tooltips/cmyk-titles.txt
grep -oE 'title="[^"]+"' "S:/mixoswatch/app/3d-explorer.html" | sort -u > /tmp/spec3-tooltips/3d-titles.txt
wc -l /tmp/spec3-tooltips/cmyk-titles.txt /tmp/spec3-tooltips/3d-titles.txt
```

Record the line counts. These are the unique tooltips per file.

- [ ] **Step 2: Classify each tooltip as `safe` or `jargon`**

Run:
```bash
grep -E "ΔE|TAC|K-tier|GCR|gamut|anchor|chroma|WCAG|LUT|round-trip|FOGRA|SWOP|Japan Color" /tmp/spec3-tooltips/cmyk-titles.txt > /tmp/spec3-tooltips/cmyk-jargon.txt
grep -E "ΔE|TAC|K-tier|GCR|gamut|anchor|chroma|WCAG|LUT|round-trip|FOGRA|SWOP|Japan Color" /tmp/spec3-tooltips/3d-titles.txt > /tmp/spec3-tooltips/3d-jargon.txt
wc -l /tmp/spec3-tooltips/cmyk-jargon.txt /tmp/spec3-tooltips/3d-jargon.txt
```

The jargon files list every tooltip that needs review. Approximate target: ~30-50 entries per app.

- [ ] **Step 3: Commit the inventory snapshot for reference**

The /tmp files do not get committed (they're scratch). No commit at this step.

## Task 3.2: Apply the rewrite pattern to each jargon tooltip

For each tooltip in `/tmp/spec3-tooltips/cmyk-jargon.txt`:

- [ ] **Step 1: Determine the rewrite**

Apply the rule from Spec 3 §2.3:

```
{what it does in plain language} · {brand-name link for power users}
```

Brand-name suffix is optional. Skip it when the brand term isn't the well-known shorthand professionals search for.

**Concrete rewrites for the common terms (use these verbatim where they appear):**

| Term | Plain-language gloss | Brand-name suffix |
|---|---|---|
| ΔE / Delta-E | `color shift measured the way human eyes see differences` | `· ΔE 2000` |
| TAC | `total ink load on the press; over-cap and the paper smudges or rejects` | `· TAC limit` |
| K-tier | `how dark you let the black ink go` | `· K-channel range` |
| GCR | `how the press builds gray (using K ink versus mixing CMY)` | (skip brand suffix; rare term) |
| gamut | `the colors the press can physically reach` | (skip) |
| anchor | `which side of a named color (screen hex vs printed CMYK) the match uses` | `· ICC anchor` |
| chroma | `how colorful, not how light or dark` | `· C* axis` |
| WCAG AA / AAA | `the contrast level the text on top needs to be readable` | `· WCAG 2.1` |
| LUT | `pre-computed color table for fast lookups` | `· lookup table` |
| round-trip | `convert the color into press ink and back to see how much it drifts` | `· sRGB → CMYK → sRGB` |

**Example concrete rewrites (apply these patterns to actual tooltip strings):**

| Found (jargon) | Rewrite (layman + brand-name) |
|---|---|
| `How loose the name match must be (Delta-E). 0 = only the single closest swatch wears the name. Higher = more swatches share the name (looser match).` | `How loose to be when matching a swatch to a named color. 0 = strict, only one swatch per name. Higher = looser. · ΔE 2000 tolerance` |
| `Total ink load (C+M+Y+K %). Low ink first.` | `Total ink load on the press. Lower numbers print cleaner; high numbers risk smudging. · TAC limit` |
| `K (black ink) under 25%. Clean, premium, easy to reproduce. Where most logo + brand colors should live.` | `Lightest tier: black ink stays under 25%. Clean, premium, easy to reproduce. Where most logo + brand colors should live. · K-channel range` |
| `Maximum round-trip color error (Delta-E) you'll accept. Lower = only super-reliable colors. Slide up to add riskier near-gamut colors.` | `How much color shift to accept between what you pick and what the press prints. Lower = safer, fewer swatches. · ΔE round-trip cap` |
| `Hex anchor matches the corpus's hex value directly. CMYK anchor routes through the active ICC profile first.` | `Which side of a named color is "real". hex = trust the published color. cmyk = trust the published ink mix; let the profile show what that mix actually prints. · ICC anchor` |
| `Only show swatches whose text contrast passes WCAG AA (4.5:1).` | `Only show swatches where black or white label text is readable on top, meeting the WCAG AA contrast bar (4.5:1). · WCAG 2.1` |
| `Order by round-trip reliability. Most-reliable first; riskier (near gamut boundary) last.` | `Order by how safely the color survives the press (most reliable first, riskier last). · round-trip ΔE` |

- [ ] **Step 2: Apply each rewrite via Edit tool**

For each tooltip identified as jargon, find the live element it lives on and use Edit to swap the `title` attribute value. Tooltip values often contain quote-sensitive characters; preserve exact apostrophe / curly-quote choice from the original.

Concrete example for one rewrite:

Use the Edit tool with:

`old_string`:
```
title="How loose the name match must be (Delta-E). 0 = only the single closest swatch wears the name. Higher = more swatches share the name (looser match)."
```

`new_string`:
```
title="How loose to be when matching a swatch to a named color. 0 = strict, only one swatch per name. Higher = looser. · ΔE 2000 tolerance"
```

Repeat for every jargon entry. Tip: do all CMYK explorer rewrites in one batch, commit, then move to 3D explorer.

- [ ] **Step 3: Sweep audit**

Run:
```bash
grep -oE 'title="[^"]+"' "S:/mixoswatch/app/cmyk-explorer.html" | sort -u | grep -E "ΔE|TAC|K-tier|GCR|gamut|anchor|chroma|WCAG|LUT|round-trip"
```

Every remaining match must have a layman explanation IN THE SAME STRING. If a result line shows a bare technical term without a plain-language clause before the `·` separator, it still needs rewriting.

- [ ] **Step 4: JS parse**

Run for both files. Expected: `JS OK`.

- [ ] **Step 5: Commit CMYK tooltip rewrites**

Run:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html && git commit -m "ux(cmyk): rewrite tooltips in plain language with brand suffix (Spec 3 §2.3)

All tooltips containing ΔE / TAC / K-tier / GCR / gamut / anchor /
chroma / WCAG / LUT / round-trip now follow the
'{plain language} · {brand-name}' template. Power-users still see
the technical shorthand; laymen get the meaning first.

Cross-reference: vocabulary aligned with landing glossary.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

## Task 3.3: Same rewrite pass on 3D explorer

**Files:**
- Modify: `app/3d-explorer.html`

Repeat Task 3.2 for 3d-explorer. Use the same rewrite table for the same terms.

Commit message:
```
ux(3d): rewrite tooltips in plain language with brand suffix (Spec 3 §2.3)

Same template as cmyk-explorer rewrite. Vocabulary aligned with
landing glossary.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

---

# SECTION 4 · Standardized loading / error / empty-state copy

English strings land here. `t()` wiring lands during Spec 2 implementation.

## Task 4.1: Banner component markup + CSS (both apps)

**Files:**
- Modify: `app/cmyk-explorer.html`, `app/3d-explorer.html`

- [ ] **Step 1: Add banner CSS**

For each HTML file, use the Edit tool with:

`old_string` (the focus-ring rule added in Task 2.3):
```
/* Spec 3 §2.2 fix 3: visible focus rings on range sliders */
input[type=range]:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
  border-radius: 4px;
}
```

`new_string`:
```
/* Spec 3 §2.2 fix 3: visible focus rings on range sliders */
input[type=range]:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
  border-radius: 4px;
}

/* Spec 3 §2.4: error banner */
.banner {
  position: relative;
  display: none;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  margin: 8px 12px 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid #d04040;
  border-radius: 6px;
  font-size: 12.5px;
  color: var(--text);
  font-family: var(--font-sans);
  animation: bannerIn .2s ease-out;
}
.banner.show { display: flex; }
.banner-icon {
  width: 18px; height: 18px;
  border-radius: 50%;
  background: #d04040; color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 12px;
  flex: none;
}
.banner-msg { flex: 1; }
.banner-close {
  background: transparent;
  border: none;
  color: var(--muted);
  font-size: 18px;
  cursor: pointer;
  padding: 0 6px;
  line-height: 1;
}
.banner-close:hover { color: var(--text); }
@keyframes bannerIn {
  from { opacity: 0; transform: translateY(-8px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

- [ ] **Step 2: Add banner markup at top of grid-area**

Locate the `<div class="grid-area">` opening in each file:
```bash
grep -n 'class="grid-area"' "S:/mixoswatch/app/cmyk-explorer.html"
```

Use the Edit tool with:

`old_string`:
```
  <div class="grid-area">
```

`new_string`:
```
  <div class="grid-area">
    <div class="banner banner-err" role="alert" id="banner">
      <span class="banner-icon" aria-hidden="true">!</span>
      <span class="banner-msg" id="bannerMsg"></span>
      <button class="banner-close" aria-label="Dismiss" onclick="dismissBanner()">×</button>
    </div>
```

- [ ] **Step 3: Add banner JS helpers**

Find a stable insertion point in the script section (near other UI helpers):

Use the Edit tool with:

`old_string` (a stable existing helper; pick one of the spec-3 helpers added earlier, e.g. `_wireStepFold`):
```
function _wireStepFold() {
```

`new_string`:
```
// Spec 3 §2.4: error banner show/hide helpers
function showBanner(msg) {
  const b = document.getElementById('banner');
  const m = document.getElementById('bannerMsg');
  if (!b || !m) return;
  m.textContent = msg;
  b.classList.add('show');
}
function dismissBanner() {
  const b = document.getElementById('banner');
  if (b) b.classList.remove('show');
}

function _wireStepFold() {
```

- [ ] **Step 4: Repeat all 3 edits in 3d-explorer**

Same steps with `app/3d-explorer.html`.

- [ ] **Step 5: JS parse**

Both files. Expected: `JS OK`.

- [ ] **Step 6: Browser smoke**

Open DevTools console. Run `showBanner('test error message')`. Expected: red-left-rule banner slides in at top of the grid area with the test message. Click `×` to dismiss. Expected: banner slides out.

- [ ] **Step 7: Commit**

Run:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html app/3d-explorer.html && git commit -m "feat(apps): error banner component (Spec 3 §2.4)

Top-of-grid sliding banner with red-left-rule, icon, message, and
dismiss. JS helpers showBanner(msg) + dismissBanner(). role=alert
on the container so screen readers announce immediately.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

## Task 4.2: Wire error templates to existing failure paths

**Files:**
- Modify: `app/cmyk-explorer.html`, `app/3d-explorer.html`

- [ ] **Step 1: Replace alerts in cmyk-explorer's bootstrap with banner calls**

Find the existing error alerts:
```bash
grep -n "alert('Failed to load ICC pipeline" "S:/mixoswatch/app/cmyk-explorer.html"
grep -n "file:// blocked" "S:/mixoswatch/app/cmyk-explorer.html"
```

For each `alert(...)` that fires on a fetch failure or protocol issue, replace it with a `showBanner(...)` call using the canonical messages from Spec 3 §2.4 error templates.

Use the Edit tool with:

`old_string`:
```
    alert('Failed to load ICC pipeline: ' + e.message + '\n\n' +
          'Did you run "python scripts/gen_luts.py" first? Are ' +
          'data/luts/index.json and data/corpora/name_corpora.json present?');
```

`new_string`:
```
    if (/index\.json/.test(e.message)) {
      showBanner('Color tables missing. Run: python scripts/gen_luts.py');
    } else if (/name_corpora/.test(e.message)) {
      showBanner('Name corpora missing. Check that data/corpora/name_corpora.json exists.');
    } else {
      showBanner('Cannot reach color tables. Confirm the page is served via the local HTTP server (run.bat / run.sh).');
    }
```

- [ ] **Step 2: Replace the `file://` warning alert with a banner**

Find the existing detection:
```bash
grep -n "location.protocol === 'file:'" "S:/mixoswatch/app/cmyk-explorer.html"
```

Use the Edit tool. The existing block likely sets text on iccStatus + alert(). Replace the alert call:

`old_string` (capture the alert line in its context):
```
    alert(msg);
    return;
```

`new_string`:
```
    showBanner('mixoswatch needs HTTP. Open run.bat (Windows) or run.sh (macOS / Linux).');
    return;
```

If the `alert(msg)` text variable used elsewhere differs from the canonical message, replace the literal argument as shown.

- [ ] **Step 3: Repeat for 3d-explorer**

Find the equivalent failure paths:
```bash
grep -n "alert('Failed to load 3D library" "S:/mixoswatch/app/3d-explorer.html"
grep -n "file://" "S:/mixoswatch/app/3d-explorer.html"
```

Use the canonical templates:
- Library missing: `showBanner('Curated library missing. Run: python scripts/gen_libraries.py');`
- `file://`: `showBanner('mixoswatch needs HTTP. Open run.bat (Windows) or run.sh (macOS / Linux).');`

- [ ] **Step 4: JS parse**

Both files. Expected: `JS OK`.

- [ ] **Step 5: Manual error simulation**

Open the cmyk explorer via run.bat. In DevTools Network tab, block requests to `data/luts/index.json`. Refresh. Expected: banner appears with "Color tables missing. Run: python scripts/gen_luts.py".

Unblock. Refresh. Expected: banner does not appear.

- [ ] **Step 6: Commit**

Run:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html app/3d-explorer.html && git commit -m "ux(apps): standardize error messages via banner component (Spec 3 §2.4)

alert() popups replaced with banner messages on:
- file:// protocol detection
- LUT index.json fetch failure
- name_corpora.json fetch failure
- generic fetch failure
- 3D library fetch failure

Canonical English copy from Spec 3 §2.4 error template table. i18n
translation lands in Spec 2.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

## Task 4.3: Standardize empty-state copy

**Files:**
- Modify: `app/cmyk-explorer.html`, `app/3d-explorer.html`

- [ ] **Step 1: Locate existing empty-state strings**

Run:
```bash
grep -n "Empty\|No palette\|No palettes\|No corpora\|No swatches" "S:/mixoswatch/app/cmyk-explorer.html"
```

- [ ] **Step 2: Replace each with the canonical Spec 3 §2.4 empty-state copy**

For each empty-state string found, swap to the canonical version via Edit tool. Canonical strings (English; Spec 2 translates later):

| State | Canonical copy |
|---|---|
| No swatches pass filter | `No swatches match the current filters. Loosen K-tier, raise TAC, or clear the search box.` |
| No palette selected (active id is null) | `No palette selected. Pick one in the dropdown, or click + New.` |
| Empty palette (selected but no swatches) | `Empty palette. Enable Select mode in the topbar and click swatches to add.` |
| No corpora loaded | `No name corpora loaded. Check data/corpora/name_corpora.json exists.` |
| No matching named (any-named filter on, zero pass) | `No swatches match a name in the checked libraries. Tick more libraries, raise tolerance, or clear search.` |

For each one found in the file, use the Edit tool to replace the existing text. Example for the empty-palette state:

`old_string`:
```
    e.textContent = 'Empty — enable Select mode and click swatches.';
```

`new_string`:
```
    e.textContent = 'Empty palette. Enable Select mode in the topbar and click swatches to add.';
```

- [ ] **Step 3: Add the "No swatches match filters" path**

If the existing filtered() returns an empty list, the grid may currently show nothing without explanation. Add an empty-state hint inside the renderer.

Locate the existing main render function:
```bash
grep -n "function render()" "S:/mixoswatch/app/cmyk-explorer.html"
```

Inside the grid-mode branch, after the filter pass, add an explicit empty hint:

Use the Edit tool with:

`old_string` (find the line that sets the data array used to paint cells, e.g. `const data = sorted(filtered());`):
```
  const data = sorted(filtered());
```

`new_string`:
```
  const data = sorted(filtered());
  // Spec 3 §2.4: empty-state hint when filters trim everything
  const grid = document.getElementById('swatchGrid');
  if (data.length === 0 && grid) {
    grid.innerHTML = '<div style="padding:24px;color:var(--muted);font-size:13px;line-height:1.5">No swatches match the current filters. Loosen K-tier, raise TAC, or clear the search box.</div>';
    renderGS();
    return;
  }
```

- [ ] **Step 4: Repeat all in 3d-explorer**

Same edits with 3D-specific tweaks:
- Empty-state hint copy in the 3D renderer uses: `No swatches match the current filters. Raise ΔE max, widen K-tier, or clear the search box.`
- Other states use the shared canonical strings.

- [ ] **Step 5: JS parse**

Both files. Expected: `JS OK`.

- [ ] **Step 6: Browser smoke**

Open cmyk explorer. Type a search query that matches nothing (e.g. `zzzzz`). Expected: the grid area shows the empty hint paragraph. Clear search. Expected: cells return.

- [ ] **Step 7: Commit**

Run:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html app/3d-explorer.html && git commit -m "ux(apps): standardize empty-state copy (Spec 3 §2.4)

Five canonical empty-state strings: no-swatches-after-filter, no-
palette-selected, empty-palette, no-corpora, no-matching-named.
Each has an actionable hint that names the slider or button the user
can adjust. i18n translation lands in Spec 2.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Final Spec 3 validation suite

- [ ] **Step 1: Native details keyboard test**

Browser smoke: Tab to a step group summary. Press Enter. Group toggles closed. Press Enter again. Opens. Press Space. Toggles. Confirms Spec 3 §5 gate 1.

- [ ] **Step 2: Sticky header non-overlap**

Browser smoke: scroll the sidebar. Group headers stick to top of sidebar viewport. No horizontal scroll appears. Confirms gate 2.

- [ ] **Step 3: Fold persistence**

Browser smoke: collapse group 02. Reload. Group 02 stays collapsed. Run `localStorage.getItem('cmykStepFold_v1')` in DevTools console; expected non-null JSON with `"02": false`. Confirms gate 3.

- [ ] **Step 4: Reset clears fold**

Browser smoke: click Reset to defaults. Group 02 reopens. Run `localStorage.getItem('cmykStepFold_v1')`. Expected: `null`. Confirms gate 4.

- [ ] **Step 5: Accessibility tree spot check**

DevTools → Accessibility panel. Verify each of:
- Filter checkbox group exposes the `Library filter for "Any named"` legend
- Each naming row has a `radiogroup` with the library label as accessible name
- `#countLabel`, `#iccStatus` expose `role=status`
- `#lpLabel` exposes `role=status` + `aria-live=assertive`
- `#detailCard` exposes `role=dialog` + `aria-modal=true` + accessible name from `#dTitle`

Confirms gate 5.

- [ ] **Step 6: Focus rings on sliders**

Tab to any slider; verify accent-color outline. Confirms gate 6.

- [ ] **Step 7: Tooltip jargon grep**

Run:
```bash
for f in app/cmyk-explorer.html app/3d-explorer.html; do
  echo "=== $f ==="
  grep -oE 'title="[^"]+"' "S:/mixoswatch/$f" | \
    grep -E "ΔE|TAC|K-tier|GCR|gamut|anchor|chroma|WCAG|LUT|round-trip" | \
    grep -vE "·.*ΔE|·.*TAC|·.*K-channel|·.*ICC anchor|·.*C\* axis|·.*WCAG 2\.1|·.*lookup table|·.*sRGB|·.*round-trip ΔE"
done
```

Expected: zero output lines (every jargon-term tooltip has a `· suffix`). Confirms gate 7.

If any line remains, the rewrite missed an entry; locate it and apply the layman pattern.

- [ ] **Step 8: Banner appears on simulated error**

DevTools Network → block `data/luts/index.json`. Reload cmyk-explorer. Banner appears with "Color tables missing. Run: python scripts/gen_luts.py". Confirms gate 8.

- [ ] **Step 9: Empty-state coverage**

Browser smoke each of:
- No-swatches-after-filter: type `zzz` in search box → hint appears
- No-palette-selected: delete all palettes via the topbar UI → palette section shows the canonical hint
- Empty-palette: create a new empty palette → shows the canonical hint

Confirms gate 9.

- [ ] **Step 10: Slider drag no-select**

In sidebar, attempt to drag-select across a slider's value-display label. Selection skips. Open detail card; drag-select hex value. Selection works. Confirms gate 10.

- [ ] **Step 11: JS parse on both files**

Run:
```bash
node -e "const fs=require('fs');for(const f of ['app/cmyk-explorer.html','app/3d-explorer.html']){const html=fs.readFileSync('S:/mixoswatch/'+f,'utf-8');const m=html.match(/<script>([\\s\\S]*?)<\\/script>/);try{new Function(m[1]);console.log(f,'JS OK');}catch(e){console.log(f,'ERR:',e.message);}}"
```
Expected: both `JS OK`. Confirms gate 11.

- [ ] **Step 12: Em-dash audit**

Run:
```bash
grep -c "—\|–" "S:/mixoswatch/app/cmyk-explorer.html"
grep -c "—\|–" "S:/mixoswatch/app/3d-explorer.html"
```

Compare against the baseline recorded in pre-flight. Counts should be no greater than the baseline. If higher, locate the introduced dashes with `grep -n` and replace with ASCII alternatives (comma, colon, or "to"). Confirms gate 12.

---

## Self-Review

**Spec coverage check (against Spec 3 §3 file-by-file list + §5 validation gates):**

| Spec 3 item | Plan section |
|---|---|
| §2.1 Sticky + collapsible step groups (markup + CSS + persistence) | Tasks 1.1 – 1.6 |
| §2.2 a11y fix 1 (filter fieldset) | Task 2.1 |
| §2.2 a11y fix 2 (naming radio groups) | Task 2.2 |
| §2.2 a11y fix 3 (focus rings) | Task 2.3 |
| §2.2 a11y fix 4 (aria-live regions) | Task 2.4 |
| §2.2 a11y fix 5 (dialog + focus trap) | Task 2.5 |
| §2.3 Tooltip layman rewrite (~50 entries) | Tasks 3.1 – 3.3 |
| §2.4 Loading templates | (deferred; landed via Spec 2 `t()` table since loading copy is mostly already in place) |
| §2.4 Error banner component + templates | Tasks 4.1, 4.2 |
| §2.4 Empty-state copy | Task 4.3 |
| §2.5 Slider-chrome text-select forbid | Tasks 5.1, 5.2 |
| §5 gate 1 (native details keyboard) | Final validation Step 1 |
| §5 gate 2 (sticky no-overlap) | Final validation Step 2 |
| §5 gate 3 (fold persists) | Final validation Step 3 |
| §5 gate 4 (reset clears fold) | Final validation Step 4 |
| §5 gate 5 (a11y tree spot check) | Final validation Step 5 |
| §5 gate 6 (focus rings) | Final validation Step 6 |
| §5 gate 7 (tooltip jargon grep) | Final validation Step 7 |
| §5 gate 8 (banner on error) | Final validation Step 8 |
| §5 gate 9 (empty states) | Final validation Step 9 |
| §5 gate 10 (slider drag) | Final validation Step 10 |
| §5 gate 11 (JS parse) | Final validation Step 11 |
| §5 gate 12 (em-dash 0) | Final validation Step 12 |

Loading templates (§2.4) deferred: the existing progress overlay already shows "Loading {profile_label}…" / "Processing {n} / {m} swatches" templates from earlier session work. Spec 3 does not modify these strings; Spec 2 will route them through `t()`.

**Placeholder scan:** searched plan for "TBD", "TODO", "implement later", "fill in details", "appropriate error handling". None present.

**Type consistency:** all JS helpers introduced (`_loadStepFold`, `_saveStepFold`, `_wireStepFold`, `_detailLastFocus`, `_trapDetail`, `showBanner`, `dismissBanner`, `STEP_FOLD_KEY`) are referenced consistently throughout. No drift between definition and usage.

**Frequent commits:** plan creates ~18 commits across 5 sections. Each commit is one logical change. Order: select-forbid → details wrap → fold persistence → a11y fixes → tooltip rewrites → banner + states. Each step produces working, testable software on its own.
