# Spec 5: CMYK-Only Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace dual-tool architecture with single `cmyk-explorer.html`. Retire `gen_libraries.py` curated-library workflow. Port ΔE max slider into `cmyk-explorer.html`. Absorb Spec 1 remaining tasks (Fix B, Fix C, footer URL rewrite, `.nojekyll`, final validation) onto the same branch.

**Architecture:** New branch `spec5-cmyk-only` off `main`. Cherry-pick the two Spec 1 commits already landed (`56abfac` em-dash pre-flight + `b290e2a` Fix A) so this branch is the single source of truth. Delete `app/3d-explorer.html`, `scripts/gen_libraries.py`, empty `swatches/` folder. Add ΔE max slider to `cmyk-explorer.html` using already-computed `delta_e_print` field. Scrub landing + docs + `data/ui_defaults.json` + `run.sh` + `run.bat` of all 3d-explorer references. Run absorbed Spec 1 tasks 3 through 7 verbatim from prior plan.

**Tech Stack:** Plain HTML / CSS / JS browser tool (no framework). Python 3 + Pillow + LittleCMS for `gen_luts.py` (untouched). Git for branch + cherry-pick. Bash + Node 22 for verification gates.

---

## Task 1: Branch setup + cherry-pick

**Files:**
- Branch operation only; no files modified directly.

- [ ] **Step 1: Capture current branch + stash list state**

Run:
```bash
cd S:/mixoswatch && git branch --show-current && git stash list
```
Expected: prints `spec1-landing-honesty`. Stash list may be empty or have prior entries.

- [ ] **Step 2: Stash working-tree modifications**

Run:
```bash
cd S:/mixoswatch && git stash push -m "spec1-wip-pre-spec5-cherry-pick" -- .gitignore ARCHITECTURE.md README.md app/3d-explorer.html app/cmyk-explorer.html data/corpora/name_corpora.json data/ui_defaults.json
```
Expected: `Saved working directory and index state On spec1-landing-honesty: spec1-wip-pre-spec5-cherry-pick`.

- [ ] **Step 3: Switch to `main`**

Run:
```bash
cd S:/mixoswatch && git checkout main
```
Expected: `Switched to branch 'main'`.

- [ ] **Step 4: Create + switch to new branch**

Run:
```bash
cd S:/mixoswatch && git checkout -b spec5-cmyk-only
```
Expected: `Switched to a new branch 'spec5-cmyk-only'`.

- [ ] **Step 5: Cherry-pick `56abfac` (em-dash pre-flight) onto new branch**

Run:
```bash
cd S:/mixoswatch && git cherry-pick 56abfac
```
Expected: `[spec5-cmyk-only <new-sha>] chore(landing): replace 1 em-dash with period split (Spec 1 pre-flight)`.

If conflict: this should NOT happen because `main` and the source branch share base history at this commit's parent. If it does, stop and report — do not auto-resolve.

- [ ] **Step 6: Cherry-pick `b290e2a` (Fix A) onto new branch**

Run:
```bash
cd S:/mixoswatch && git cherry-pick b290e2a
```
Expected: `[spec5-cmyk-only <new-sha>] fix(landing): honest framing for ICC math claim (Fix A)`.

- [ ] **Step 7: Cherry-pick `ee2236f` (Spec 5 design doc) + `b13928c` (Spec 5 plan doc) onto new branch**

Run:
```bash
cd S:/mixoswatch && git cherry-pick ee2236f b13928c
```
Expected: two successful cherry-pick lines printed.

- [ ] **Step 8: Pop stash back onto `spec5-cmyk-only`**

Run:
```bash
cd S:/mixoswatch && git stash pop
```
Expected: prints modified file list. Likely no conflicts because target files (cmyk-explorer.html, data/ui_defaults.json, etc.) on main = on the new branch's cherry-picked head.

If conflicts on `app/3d-explorer.html`: that file is about to be deleted in Task 2; resolve by `git checkout --theirs app/3d-explorer.html` then `git rm app/3d-explorer.html` if conflict resolution is awkward. Otherwise prefer the stash content.

- [ ] **Step 9: Verify branch state**

Run:
```bash
cd S:/mixoswatch && git log --oneline -6 && echo "---STATUS---" && git status
```
Expected: 3 new commits on top of main (em-dash, Fix A, Spec 5 spec). Working tree shows 7 modified files from the stash pop.

- [ ] **Step 10: Commit baseline state for Spec 5 branch**

Stage no files yet (working-tree files are pre-Spec 5 WIP). No commit at this step. Branch is now ready.

Run:
```bash
cd S:/mixoswatch && git branch --show-current
```
Expected: `spec5-cmyk-only`.

---

## Task 2: Delete `app/3d-explorer.html`

**Files:**
- Delete: `app/3d-explorer.html`

- [ ] **Step 1: Confirm file exists**

Run:
```bash
ls -la "S:/mixoswatch/app/3d-explorer.html"
```
Expected: file shown, size ~146 KB.

- [ ] **Step 2: Delete the file**

Run:
```bash
cd S:/mixoswatch && git rm app/3d-explorer.html
```
Expected: `rm 'app/3d-explorer.html'`.

If the file was in the stashed-pop working tree with modifications, `git rm` may complain. Use `git rm -f app/3d-explorer.html`.

- [ ] **Step 3: Verify deletion**

Run:
```bash
ls -la "S:/mixoswatch/app/" && echo "---" && ls "S:/mixoswatch/app/3d-explorer.html" 2>&1
```
Expected: `app/` listing shows only `cmyk-explorer.html`. Second `ls` reports `No such file or directory`.

- [ ] **Step 4: Commit deletion**

Run:
```bash
cd S:/mixoswatch && git commit -m "chore: delete app/3d-explorer.html (Spec 5)

Per Spec 5 §4.1. Single-tool consolidation. Curated-library
workflow (gen_libraries.py → swatches.json → 3d-explorer.html) is
retired. 2D and 3D-print color matching workflows now both served
by the single cmyk-explorer.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: Delete `scripts/gen_libraries.py` + `swatches/` folder

**Files:**
- Delete: `scripts/gen_libraries.py`
- Delete: `swatches/` (folder, currently empty)

- [ ] **Step 1: Confirm gen_libraries.py exists + swatches/ is empty**

Run:
```bash
ls -la "S:/mixoswatch/scripts/gen_libraries.py" && ls -la "S:/mixoswatch/swatches/"
```
Expected: `gen_libraries.py` exists (~22 KB). `swatches/` lists only `.` and `..` (empty).

- [ ] **Step 2: Delete gen_libraries.py**

Run:
```bash
cd S:/mixoswatch && git rm scripts/gen_libraries.py
```
Expected: `rm 'scripts/gen_libraries.py'`.

- [ ] **Step 3: Remove empty swatches/ folder**

Run:
```bash
cd S:/mixoswatch && rmdir swatches
```
Expected: silent success. Folder gone from filesystem. Git tracks files not folders, so no `git rm` needed for an untracked-empty folder.

- [ ] **Step 4: Verify**

Run:
```bash
ls "S:/mixoswatch/scripts/" && echo "---" && ls "S:/mixoswatch/swatches/" 2>&1
```
Expected: scripts/ shows only `gen_luts.py` (+ `__pycache__/` cache dir). swatches/ reports `No such file or directory`.

- [ ] **Step 5: Commit deletions**

Run:
```bash
cd S:/mixoswatch && git commit -m "chore: retire gen_libraries.py + drop empty swatches/ (Spec 5)

Per Spec 5 §4.1. Sole consumer was app/3d-explorer.html, removed
in prior commit. cmyk-explorer's live ICC LUT pipeline replaces
the curated-library workflow.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: Port ΔE max slider into `app/cmyk-explorer.html`

**Files:**
- Modify: `app/cmyk-explorer.html` (3 separate edits: sidebar markup, value-display sync, filter pipeline)

- [ ] **Step 1: Insert slider markup after TAC limit `.sec` block**

Locate the existing TAC block ending at line ~595 in `app/cmyk-explorer.html`:

```html
    <div class="sec">
      <div class="sec-label">TAC limit</div>
      <div class="slider-row">
        <input type="range" min="0" max="400" value="240" step="10" id="slTAC" oninput="onFilter()" title="Total ink limit (C+M+Y+K %). Real presses can usually only handle 240–320% before paper saturates. Lower = safer for press.">
        <span class="sv2" id="vTAC">240%</span>
      </div>
    </div>


    <div class="divider"></div>
```

Use the Edit tool with:

`old_string`:
```
    <div class="sec">
      <div class="sec-label">TAC limit</div>
      <div class="slider-row">
        <input type="range" min="0" max="400" value="240" step="10" id="slTAC" oninput="onFilter()" title="Total ink limit (C+M+Y+K %). Real presses can usually only handle 240–320% before paper saturates. Lower = safer for press.">
        <span class="sv2" id="vTAC">240%</span>
      </div>
    </div>


    <div class="divider"></div>
```

`new_string`:
```
    <div class="sec">
      <div class="sec-label">TAC limit</div>
      <div class="slider-row">
        <input type="range" min="0" max="400" value="240" step="10" id="slTAC" oninput="onFilter()" title="Total ink limit (C+M+Y+K %). Real presses can usually only handle 240–320% before paper saturates. Lower = safer for press.">
        <span class="sv2" id="vTAC">240%</span>
      </div>
    </div>

    <div class="sec">
      <div class="sec-label">ΔE max (round-trip safety)</div>
      <div class="slider-row">
        <input type="range" min="0" max="100" value="100" step="1" id="slDEmax" oninput="onFilter()" title="Hide swatches whose round-trip color drift exceeds this ΔE. Off = show all. 0.5 = mathematically equal under the profile. 1.0 = trained-eye limit. Slider at far right = off.">
        <span class="sv2" id="vDEmax">off</span>
      </div>
    </div>


    <div class="divider"></div>
```

Note: slider range is `0..100` representing `ΔE 0..10.0` at step `1` = `ΔE 0.1`. Value `100` = "off" sentinel (above any realistic round-trip ΔE). This avoids float-step quirks on Windows browsers and keeps the off-state at one end of the track.

- [ ] **Step 2: Add ΔE filter to the `filtered()` pipeline**

Open `app/cmyk-explorer.html`. Locate the `filtered()` function around line 2133.

Use the Edit tool with:

`old_string`:
```
  const tac =+document.getElementById('slTAC').value;
  const aa  = document.getElementById('togAA').checked;
```

`new_string`:
```
  const tac =+document.getElementById('slTAC').value;
  const deRaw = +document.getElementById('slDEmax').value;
  const deMax = deRaw >= 100 ? Infinity : deRaw / 10;
  const aa  = document.getElementById('togAA').checked;
```

Then within the same function, locate the filter return block. Use the Edit tool with:

`old_string`:
```
    if (s.tac>tac) return false;
    if (s.k_tier > curKTier) return false;
```

`new_string`:
```
    if (s.tac>tac) return false;
    if (typeof s.delta_e_print === 'number' && s.delta_e_print > deMax) return false;
    if (s.k_tier > curKTier) return false;
```

Note: the `typeof` guard protects when `delta_e_print` is not yet computed (e.g. before the first ICC round-trip pass). Filter is no-op in that case, matching prior behavior.

- [ ] **Step 3: Add value-display sync**

Open `app/cmyk-explorer.html`. Locate the value-sync block around line 2667 (where `vTAC` is updated).

Use the Edit tool with:

`old_string`:
```
  document.getElementById('vTAC').textContent = document.getElementById('slTAC').value + '%';
```

`new_string`:
```
  document.getElementById('vTAC').textContent = document.getElementById('slTAC').value + '%';
  {
    const deRaw = +document.getElementById('slDEmax').value;
    document.getElementById('vDEmax').textContent = deRaw >= 100 ? 'off' : 'ΔE ≤ ' + (deRaw / 10).toFixed(1);
  }
```

- [ ] **Step 4: Smoke-check inline JS parses**

Run:
```bash
node -e "const fs=require('fs');const html=fs.readFileSync('S:/mixoswatch/app/cmyk-explorer.html','utf-8');const re=/<script>([\\s\\S]*?)<\\/script>/g;let m,c=0,errs=[];while((m=re.exec(html))){c++;try{new Function(m[1]);}catch(e){errs.push('script '+c+': '+e.message);}}console.log('scripts:',c,'errs:',errs.join(' | ')||'none');"
```
Expected: `errs: none`.

- [ ] **Step 5: Verify slider markup present**

Run:
```bash
grep -c 'id="slDEmax"' "S:/mixoswatch/app/cmyk-explorer.html"
grep -c 'id="vDEmax"' "S:/mixoswatch/app/cmyk-explorer.html"
grep -c "ΔE max (round-trip safety)" "S:/mixoswatch/app/cmyk-explorer.html"
```
Expected: each prints `1`.

- [ ] **Step 6: Manual browser smoke (out-of-band; do not block commit)**

Open `app/cmyk-explorer.html` in a local browser via `python -m http.server 8765` from repo root, then `http://localhost:8765/app/cmyk-explorer.html`. Confirm:
- Slider labeled "ΔE max (round-trip safety)" appears under TAC limit
- Value display reads "off" when slider at far right
- Drag slider to leftmost: value reads "ΔE ≤ 0.0", grid empties or near-empties
- Drag slider to 50: value reads "ΔE ≤ 5.0", subset of all swatches visible
- Drag back to far right: value reads "off", full grid restored

Browser smoke is informational; do not block the commit if the browser is unavailable. JS parse + grep gates above are mandatory.

- [ ] **Step 7: Commit ΔE max slider port**

Run:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html && git commit -m "feat(cmyk-explorer): port ΔE max slider from retired 3d-explorer (Spec 5)

Per Spec 5 §3.3. Reuses already-computed per-swatch delta_e_print
from the round-trip safety sort. Slider range 0-100 maps to ΔE
0.0-10.0; value 100 (far right) = off sentinel; default = off.
localStorage key inherited via the existing UI-state persistence
path; explicit key add deferred to follow-up if needed.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: Scrub `data/ui_defaults.json`

**Files:**
- Modify: `data/ui_defaults.json` (drop `3d_explorer` block; add `delta_e_max: null` to `cmyk_explorer`; update `_doc`)

- [ ] **Step 1: Confirm current schema has `3d_explorer` block**

Run:
```bash
grep -c '"3d_explorer"' "S:/mixoswatch/data/ui_defaults.json"
grep -c '"cmyk_explorer"' "S:/mixoswatch/data/ui_defaults.json"
```
Expected: both print `1`.

- [ ] **Step 2: Rewrite the file**

Use the Write tool. File path: `S:\mixoswatch\data\ui_defaults.json`. Content:

```json
{
  "format": "swatch.ui_defaults/v1",
  "_doc": "First-run + Reset-to-defaults source of truth for the browser tool. Edit this file to change the initial state every user sees on a fresh install. The current per-user state lives in browser localStorage (key cmykUIState_v1) and is independent of this file.",

  "cmyk_explorer": {
    "step": 10,
    "cell_size": 48,
    "view_mode": "grid",
    "sort_mode": "hue",
    "k_tier": 3,
    "named_filter": "all",
    "name_tolerance": 0,
    "wcag_aa": false,
    "wcag_aaa": false,
    "white_text_only": false,
    "black_text_only": false,
    "search": "",
    "cmyk_range": { "c": [0,100], "m": [0,100], "y": [0,100], "k": [0,100] },
    "tac_max": 400,
    "delta_e_max": null,
    "default_profile_match": "FOGRA39",
    "active_palette_id": null,
    "corpora_prefs": {
      "jpn":     { "display": "primary", "anchor": "cmyk" },
      "html":    { "display": "primary", "anchor": "cmyk" },
      "jpn-dic": { "display": "name",    "anchor": "cmyk" },
      "zh-dic":  { "display": "name",    "anchor": "cmyk" }
    }
  }
}
```

- [ ] **Step 3: Verify**

Run:
```bash
grep -c '"3d_explorer"' "S:/mixoswatch/data/ui_defaults.json"
grep -c '"delta_e_max"' "S:/mixoswatch/data/ui_defaults.json"
grep -c "cmykUIState3d_v1" "S:/mixoswatch/data/ui_defaults.json"
python -c "import json;json.load(open('S:/mixoswatch/data/ui_defaults.json'))" && echo "JSON OK"
```
Expected: `0`, `1`, `0`, `JSON OK`.

- [ ] **Step 4: Commit**

Run:
```bash
cd S:/mixoswatch && git add data/ui_defaults.json && git commit -m "chore(ui-defaults): drop 3d_explorer block, add cmyk delta_e_max (Spec 5)

Per Spec 5 §4.2. Schema now describes only the single surviving tool.
delta_e_max default is null = off; matches ΔE slider's off-state at
far-right of track.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 6: Scrub `run.sh` + `run.bat`

**Files:**
- Modify: `run.sh`
- Modify: `run.bat`

- [ ] **Step 1: Confirm 3D explorer echo line present in both**

Run:
```bash
grep -c "3D explorer" "S:/mixoswatch/run.sh"
grep -c "3D explorer" "S:/mixoswatch/run.bat"
```
Expected: each prints `1`.

- [ ] **Step 2: Strip the 3D explorer line from `run.sh`**

Use the Edit tool with:

`old_string`:
```
echo "  Landing:       http://localhost:8765/"
echo "  CMYK explorer: http://localhost:8765/app/cmyk-explorer.html"
echo "  3D explorer:   http://localhost:8765/app/3d-explorer.html"
```

`new_string`:
```
echo "  Landing:       http://localhost:8765/"
echo "  CMYK explorer: http://localhost:8765/app/cmyk-explorer.html"
```

- [ ] **Step 3: Strip the 3D explorer line from `run.bat`**

Use the Edit tool with:

`old_string`:
```
echo  Landing:       http://localhost:8765/
echo  CMYK explorer: http://localhost:8765/app/cmyk-explorer.html
echo  3D explorer:   http://localhost:8765/app/3d-explorer.html
```

`new_string`:
```
echo  Landing:       http://localhost:8765/
echo  CMYK explorer: http://localhost:8765/app/cmyk-explorer.html
```

- [ ] **Step 4: Verify**

Run:
```bash
grep -c "3D explorer" "S:/mixoswatch/run.sh"
grep -c "3D explorer" "S:/mixoswatch/run.bat"
grep -c "3d-explorer" "S:/mixoswatch/run.sh"
grep -c "3d-explorer" "S:/mixoswatch/run.bat"
```
Expected: each prints `0`.

- [ ] **Step 5: Commit**

Run:
```bash
cd S:/mixoswatch && git add run.sh run.bat && git commit -m "chore(launchers): drop 3D explorer echo line (Spec 5)

Per Spec 5 §4.2. Both run.sh and run.bat now print only the
landing URL + the single cmyk-explorer URL.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 7: Drop 3d-explorer tool card from landing `index.html`

**Files:**
- Modify: `index.html` (tool card row around line 1454)

- [ ] **Step 1: Read current tool card row context**

Run:
```bash
grep -n "Mixoswatch 3D Swatch Explorer\|app/3d-explorer.html\|app/cmyk-explorer.html" "S:/mixoswatch/index.html"
```
Expected: matches around 1454-1466 for the 3D card; another set for the CMYK card just above or below.

- [ ] **Step 2: Inspect the surrounding markup**

Run:
```bash
sed -n '1440,1475p' "S:/mixoswatch/index.html"
```
Read the printed block. Identify the exact `<a class="tool" href="app/3d-explorer.html"> … </a>` enclosing the 3D card. This is the segment to delete.

- [ ] **Step 3: Remove the 3D card**

Use the Edit tool on `index.html` with:

`old_string`: the entire `<a class="tool" href="app/3d-explorer.html">` block including the opening anchor tag through the closing `</a>` (paste verbatim from the sed output of Step 2)

`new_string`: empty string (full removal) — keep the surrounding grid wrapper untouched; subsequent task handles centering.

If the wrapper grid contained both cards under a CSS class like `grid-cols-2`, the layout will need a follow-up. See Step 5.

- [ ] **Step 4: Verify 3D card removed**

Run:
```bash
grep -c 'href="app/3d-explorer.html"' "S:/mixoswatch/index.html"
grep -c "Mixoswatch 3D Swatch Explorer" "S:/mixoswatch/index.html"
```
Expected: each prints `0`.

- [ ] **Step 5: Inspect the tool-row wrapper for layout adjustment**

Run:
```bash
sed -n '1440,1475p' "S:/mixoswatch/index.html"
```
If the printed block shows a wrapper element with explicit two-column styling (e.g. inline `style="display:grid;grid-template-columns:1fr 1fr"` or a class indicating 2-col), edit it to one of:

- single-column centering: `style="display:grid;grid-template-columns:1fr;max-width:560px;margin:0 auto"` (or equivalent class change)
- keep flex/wrap layout and just center the single child: add `justify-content:center` if a flex container

Apply the minimum change needed. If the wrapper is already responsive (e.g. `grid-template-columns:repeat(auto-fit,minmax(280px,1fr))`), no change needed — a single card will simply occupy the available width.

If no wrapper change is required, skip to Step 6.

- [ ] **Step 6: Em-dash + JS parse + triple balance verification**

Run:
```bash
grep -c "—\|–" "S:/mixoswatch/index.html"
grep -c 'data-en' "S:/mixoswatch/index.html"
grep -c 'data-ja' "S:/mixoswatch/index.html"
grep -c 'data-zh' "S:/mixoswatch/index.html"
node -e "const fs=require('fs');const html=fs.readFileSync('S:/mixoswatch/index.html','utf-8');const m=html.match(/<script>([\\s\\S]*?)<\\/script>/);try{new Function(m[1]);console.log('JS OK');}catch(e){console.log('ERR:',e.message);}"
```
Expected: em-dash `0`. The three `data-*` counts should all be equal to each other; total will be less than the pre-Task-7 baseline (the 3D card carried one triple). `JS OK`.

- [ ] **Step 7: Commit**

Run:
```bash
cd S:/mixoswatch && git add index.html && git commit -m "feat(landing): drop 3D explorer tool card (Spec 5)

Per Spec 5 §4.2. Single-tool consolidation. Surviving cmyk-explorer
card serves both 2D and 3D-print color matching use cases.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 8: Drop "Curated for 3D Modeling × 3D Coloured Print" section

**Files:**
- Modify: `index.html` (section around lines 1617-1632)

- [ ] **Step 1: Locate the section**

Run:
```bash
grep -n "Curated for 3D Modeling\|為 3D 建模 × 3D 彩色列印\|3Dモデリング×3Dカラープリント専用" "S:/mixoswatch/index.html"
```
Expected: 3 lines (one per language) within a ~20-line span.

- [ ] **Step 2: Inspect surrounding markup**

Run:
```bash
sed -n '1605,1640p' "S:/mixoswatch/index.html"
```
Read the block. Identify the enclosing `<section>` or `<div class="…">` that wraps the EN/JA/ZH triple + the body paragraphs (around line 1623-1632 in the prior scan). The wrapper start and end define the deletion target.

- [ ] **Step 3: Delete the section**

Use the Edit tool. Set `old_string` to the entire wrapping element from its opening tag through its closing tag (paste verbatim from Step 2 output). Set `new_string` to empty string.

- [ ] **Step 4: Verify**

Run:
```bash
grep -c "Curated for 3D Modeling" "S:/mixoswatch/index.html"
grep -c "3Dモデリング×3Dカラープリント専用" "S:/mixoswatch/index.html"
grep -c "為 3D 建模 × 3D 彩色列印" "S:/mixoswatch/index.html"
grep -c 'data-en' "S:/mixoswatch/index.html"
grep -c 'data-ja' "S:/mixoswatch/index.html"
grep -c 'data-zh' "S:/mixoswatch/index.html"
```
Expected: first three print `0`. The three triple counts must be equal to each other.

- [ ] **Step 5: Em-dash + JS parse**

Run:
```bash
grep -c "—\|–" "S:/mixoswatch/index.html"
node -e "const fs=require('fs');const html=fs.readFileSync('S:/mixoswatch/index.html','utf-8');const m=html.match(/<script>([\\s\\S]*?)<\\/script>/);try{new Function(m[1]);console.log('JS OK');}catch(e){console.log('ERR:',e.message);}"
```
Expected: `0` and `JS OK`.

- [ ] **Step 6: Commit**

Run:
```bash
cd S:/mixoswatch && git add index.html && git commit -m "feat(landing): drop curated-for-3D-modeling section (Spec 5)

Per Spec 5 §4.2. Section described the retired 3d-explorer's
pre-filtered library workflow. With that workflow gone, the
section has no referent.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 9: Rephrase "Same library serves 2D and 3D-print" paragraph + footer architecture clause

**Files:**
- Modify: `index.html` (paragraph around line 1577 and footer block around line 2245)

- [ ] **Step 1: Locate the "Same library serves" paragraph**

Run:
```bash
grep -n "Same library serves 2D" "S:/mixoswatch/index.html"
```
Expected: 1 match on the EN span.

- [ ] **Step 2: Replace the EN span**

Use the Edit tool with:

`old_string`:
```
            <span data-en>Same library serves 2D print and 3D-print color matching. The colors are rough by physics but
```

`new_string`:
```
            <span data-en>One tool serves 2D print and 3D-print color matching. The colors are rough by physics but
```

- [ ] **Step 3: Replace the JA span**

Use the Edit tool with:

`old_string`:
```
              data-ja>同じライブラリが2Dプリントと3Dプリントのカラーマッチングを両方支えます。物理的には大まかでも、数学的には厳密。画面とウェブのモックアップにはHexを、プリンターやプリンターにはCMYK＋プロファイルを使用。一度選べば、両方の環境へシームレスに出荷できます。</span>
```

`new_string`:
```
              data-ja>一つのツールで2Dプリントと3Dプリントのカラーマッチングを両方支えます。物理的には大まかでも、数学的には厳密。画面とウェブのモックアップにはHexを、プリンターにはCMYK＋プロファイルを使用。一度選べば、両方の環境へシームレスに出荷できます。</span>
```

Note: also removed the duplicate "プリンターやプリンター" typo in the original ZH-adjacent JA span.

- [ ] **Step 4: Replace the ZH span**

Run:
```bash
grep -n "相同的色票庫同時滿足 2D" "S:/mixoswatch/index.html"
```
Expected: 1 match. Read the full ZH span (it spans multiple lines in the source). Use the Edit tool to replace the opening clause:

`old_string`:
```
            <span data-zh>相同的色票庫同時滿足 2D 傳統印刷與 3D 印刷的色彩整合。
```

`new_string`:
```
            <span data-zh>單一工具同時滿足 2D 傳統印刷與 3D 印刷的色彩整合。
```

- [ ] **Step 5: Replace the footer architecture clause**

Run:
```bash
grep -n "CMYK explorer renders every CMYK value through it live, the 3D explorer browses" "S:/mixoswatch/index.html"
```
Expected: 1 match on the EN span.

Use the Edit tool with:

`old_string`:
```
          CMYK explorer renders every CMYK value through it live, the 3D explorer browses the pre-filtered safe set you
```

`new_string`:
```
          The CMYK explorer renders every CMYK value through it live, with a ΔE max filter for round-trip safety. The
```

Note: this preserves the surrounding `<span data-en>` context (the rest of that paragraph follows on subsequent lines and stays untouched).

- [ ] **Step 6: Replace the corresponding JA + ZH footer architecture clauses**

Run:
```bash
grep -n "CMYK 探索器即時渲染所有 CMYK 值，3D 探索器瀏覽" "S:/mixoswatch/index.html"
```
Expected: 1 match on the ZH span.

Use the Edit tool with:

`old_string`:
```
CMYK 探索器即時渲染所有 CMYK 值，3D 探索器瀏覽你剛產出的安全色組。
```

`new_string`:
```
CMYK 探索器即時渲染所有 CMYK 值，並提供 ΔE 最大值篩選器確保往返色彩安全。
```

Run:
```bash
grep -n "CMYK explorer は ICC LUT を経由して.*3D explorer\|CMYK探索器.*3D探索器\|CMYKエクスプローラ.*3Dエクスプローラ" "S:/mixoswatch/index.html"
```
If a JA equivalent is found, replace it analogously. If no JA match exists for the footer architecture clause, skip — the footer paragraph in JA may already be phrased single-tool, or it may be missing. Inspect with `sed -n '2240,2260p'` and apply the same single-tool reframing if needed.

- [ ] **Step 7: Verify cleanup**

Run:
```bash
grep -c "Same library serves" "S:/mixoswatch/index.html"
grep -c "同じライブラリが2D" "S:/mixoswatch/index.html"
grep -c "相同的色票庫同時滿足 2D" "S:/mixoswatch/index.html"
grep -c "3D explorer browses" "S:/mixoswatch/index.html"
grep -c "3D 探索器瀏覽" "S:/mixoswatch/index.html"
grep -c "One tool serves 2D" "S:/mixoswatch/index.html"
grep -c "一つのツールで2D" "S:/mixoswatch/index.html"
grep -c "單一工具同時滿足 2D" "S:/mixoswatch/index.html"
```
Expected: first five print `0`. Last three print `1`.

- [ ] **Step 8: Em-dash + JS parse + triple balance**

Run:
```bash
grep -c "—\|–" "S:/mixoswatch/index.html"
grep -c 'data-en' "S:/mixoswatch/index.html"
grep -c 'data-ja' "S:/mixoswatch/index.html"
grep -c 'data-zh' "S:/mixoswatch/index.html"
node -e "const fs=require('fs');const html=fs.readFileSync('S:/mixoswatch/index.html','utf-8');const m=html.match(/<script>([\\s\\S]*?)<\\/script>/);try{new Function(m[1]);console.log('JS OK');}catch(e){console.log('ERR:',e.message);}"
```
Expected: em-dash `0`. Three `data-*` counts equal. `JS OK`.

- [ ] **Step 9: Commit**

Run:
```bash
cd S:/mixoswatch && git add index.html && git commit -m "feat(landing): rephrase dual-tool copy as single-tool (Spec 5)

Per Spec 5 §4.2. \"Same library\" → \"One tool\" in the architecture
paragraph. Footer architecture clause names the ΔE max slider as
the round-trip safety mechanism on the single cmyk-explorer
(replacing the retired 3d-explorer's curated-library browse).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 10: Scrub `ARCHITECTURE.md`

**Files:**
- Modify: `ARCHITECTURE.md` (drop 3d-explorer sections, `gen_libraries.py` chapter, `swatches.json` schema chapter)

- [ ] **Step 1: Map 3d references**

Run:
```bash
grep -n "3d-explorer\|3d_explorer\|3D explorer\|gen_libraries\|swatches.json\|3D Swatch Explorer" "S:/mixoswatch/ARCHITECTURE.md"
```
Print results. Each hit is a candidate for review.

- [ ] **Step 2: Read the full file in context**

Read `S:/mixoswatch/ARCHITECTURE.md` end-to-end. Identify:
- Section headings dedicated to 3d-explorer / gen_libraries / swatches.json
- Comparison tables with a 3d-explorer column
- Cross-references in unrelated sections that mention 3d-explorer

- [ ] **Step 3: Rewrite scoped to single tool**

Use the Edit tool (or Write for a full rewrite if the changes exceed ~30% of the file). For each identified 3d reference:

- Delete entire sections dedicated to 3d-explorer / gen_libraries / swatches.json
- For comparison tables, drop the 3d-explorer column; if the table now has only one tool, convert to a non-comparison feature list
- Rephrase cross-references in unrelated sections to single-tool framing (similar to landing Task 9)
- Preserve the ΔE max slider mention as a new feature added to cmyk-explorer (matches Task 4); add a short note in the cmyk-explorer feature list referencing it

- [ ] **Step 4: Verify**

Run:
```bash
grep -c "3d-explorer" "S:/mixoswatch/ARCHITECTURE.md"
grep -c "3d_explorer" "S:/mixoswatch/ARCHITECTURE.md"
grep -c "gen_libraries" "S:/mixoswatch/ARCHITECTURE.md"
grep -c "swatches.json" "S:/mixoswatch/ARCHITECTURE.md"
grep -c "3D Swatch Explorer" "S:/mixoswatch/ARCHITECTURE.md"
grep -c "—\|–" "S:/mixoswatch/ARCHITECTURE.md"
```
Expected: all six print `0`.

- [ ] **Step 5: Commit**

Run:
```bash
cd S:/mixoswatch && git add ARCHITECTURE.md && git commit -m "docs(architecture): scrub 3d-explorer + gen_libraries + swatches.json (Spec 5)

Per Spec 5 §4.2. Architecture doc now describes the single-tool
shape: live ICC LUT in cmyk-explorer with full filter set
including ΔE max for round-trip safety.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 11: Scrub `README.md`

**Files:**
- Modify: `README.md` (drop 3d-explorer mentions + `gen_libraries.py` install/run instructions)

- [ ] **Step 1: Map 3d references**

Run:
```bash
grep -n "3d-explorer\|3d_explorer\|3D explorer\|gen_libraries\|swatches.json\|3D Swatch Explorer" "S:/mixoswatch/README.md"
```

- [ ] **Step 2: Read README end-to-end**

Identify sections to edit / remove. Typical hits:
- "Tools" section listing both explorers
- "Quickstart" with `python scripts/gen_libraries.py` step
- "How it works" diagrams

- [ ] **Step 3: Rewrite scoped to single tool**

Use the Edit tool (or Write for full rewrite). Apply:
- Tools section: drop 3d-explorer entry
- Quickstart: drop `gen_libraries.py` step
- How-it-works: rephrase to single-tool flow
- Preserve and update the ΔE max slider as a cmyk-explorer feature in the feature list

- [ ] **Step 4: Verify**

Run:
```bash
grep -c "3d-explorer" "S:/mixoswatch/README.md"
grep -c "gen_libraries" "S:/mixoswatch/README.md"
grep -c "swatches.json" "S:/mixoswatch/README.md"
grep -c "3D Swatch Explorer" "S:/mixoswatch/README.md"
grep -c "—\|–" "S:/mixoswatch/README.md"
```
Expected: all five print `0`.

- [ ] **Step 5: Commit**

Run:
```bash
cd S:/mixoswatch && git add README.md && git commit -m "docs(readme): scrub 3d-explorer + gen_libraries (Spec 5)

Per Spec 5 §4.2. README now describes the single-tool flow:
gen_luts.py builds the ICC LUTs, the browser tool consumes them.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 12: Audit `.gitignore` + `data/corpora/name_corpora.json` stash residue

**Files:**
- Modify: `.gitignore` (only if it contained 3d-specific entries)
- Modify: `data/corpora/name_corpora.json` (only if stash-popped changes are unrelated to Spec 5)

- [ ] **Step 1: Diff `.gitignore` vs main**

Run:
```bash
cd S:/mixoswatch && git diff main -- .gitignore
```
If the diff is empty: skip to Step 2. If it contains 3d-specific entries: verify each line is still needed; remove any 3d-only ones; commit. If the diff contains unrelated WIP: stash-pop residue is in scope for Spec 5 only if it relates to consolidation; otherwise discard with `git checkout main -- .gitignore`.

- [ ] **Step 2: Diff `data/corpora/name_corpora.json` vs main**

Run:
```bash
cd S:/mixoswatch && git diff main -- data/corpora/name_corpora.json
```
If empty: skip. If non-empty and changes look unrelated to Spec 5: `git checkout main -- data/corpora/name_corpora.json` to discard the WIP. If changes look relevant (e.g. corpora additions used by cmyk-explorer): keep + commit.

- [ ] **Step 3: Verify ICC redistribution invariant preserved**

Run:
```bash
grep -c "icc/\*.icc" "S:/mixoswatch/.gitignore"
grep -c "icc/\*.icm" "S:/mixoswatch/.gitignore"
```
Expected: each prints `1` (these lines must remain present from main's `.gitignore`).

- [ ] **Step 4: Commit (if any file changed)**

If a file changed, run:
```bash
cd S:/mixoswatch && git add <changed-file> && git commit -m "chore(repo): audit stash residue post-Spec-5 scrub

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

If neither file changed, skip the commit step.

---

## Task 13: Absorbed Spec 1 Task 3 — Fix B (Batch export interop tiers)

**Files:**
- Modify: `index.html` (paragraph inside the "What is unique" `.col`)

- [ ] **Step 1: Locate the target paragraph**

Run:
```bash
grep -n "Batch export for 3D print pipelines" "S:/mixoswatch/index.html"
```
Expected: exactly 1 match.

- [ ] **Step 2: Replace EN span**

Use the Edit tool with:

`old_string`:
```
          <span data-en><b>Batch export for 3D print pipelines.</b> Every palette exports as ASE (Photoshop / Affinity / Substance), GPL (GIMP / Krita / Inkscape / Blender), PNG sheet, and JSON. Same swatches drop straight into Mimaki RasterLink, Stratasys GrabCAD Print, Cura material libraries, or your CAD's color manager.</span>
```

`new_string`:
```
          <span data-en><b>Batch export, two interop tiers.</b> <i>Direct:</i> ASE for Photoshop / Illustrator / Affinity / Substance, GPL for GIMP / Krita / Inkscape / Blender (via the GPL Palette Importer add-on), PNG sheet for any visual reference. <i>Indirect:</i> copy CMYK or hex values out of the JSON into Mimaki RasterLink spot tables, Stratasys GrabCAD pickers, Cura material profiles, or your CAD's color manager. The swatch files target design apps; the JSON is the bridge to 3D-print pipelines.</span>
```

- [ ] **Step 3: Replace JA span**

Use the Edit tool with:

`old_string`:
```
          <span data-ja><b>3Dプリントパイプラインへの一括書き出し。</b>各パレットはASE（Photoshop / Affinity / Substance）、GPL（GIMP / Krita / Inkscape / Blender）、PNGシート、JSONで出力。同じスウォッチがMimaki RasterLink、Stratasys GrabCAD Print、Cura マテリアルライブラリ、CADのカラーマネージャに直接入る。</span>
```

`new_string`:
```
          <span data-ja>バッチ書き出し、二層の互換ルート。直接層：Photoshop / Illustrator / Affinity / SubstanceにASE、GIMP / Krita / Inkscape / Blender（GPL Palette Importerアドオン経由）にGPL、視覚参照用にPNGシート。間接層：JSONからCMYKまたはhex値をコピーし、Mimaki RasterLinkのスポットテーブル、Stratasys GrabCADのピッカー、Curaのマテリアルプロファイル、CADのカラーマネージャに入れる。スウォッチファイルはデザインアプリ向け、JSONは3Dプリントパイプラインへの橋渡し。</span>
```

If the live JA differs (e.g. earlier transforms changed wording), run:
```bash
grep -n "3Dプリント\|3D列印\|バッチ書き出し\|一括書き出し" "S:/mixoswatch/index.html"
```
Locate the actual `data-ja` line and treat it as `old_string` verbatim.

- [ ] **Step 4: Replace ZH span**

Use the Edit tool with:

`old_string`:
```
          <span data-zh><b>3D 列印流程的批次匯出。</b>每組色票可輸出 ASE（Photoshop／Affinity／Substance）、GPL（GIMP／Krita／Inkscape／Blender）、PNG 圖片、JSON。同樣的色塊可直接放入 Mimaki RasterLink、Stratasys GrabCAD Print、Cura 材料庫，或你的 CAD 色彩管理器。</span>
```

`new_string`:
```
          <span data-zh>批次匯出，兩種介接層級。直接層：ASE 給 Photoshop / Illustrator / Affinity / Substance，GPL 給 GIMP / Krita / Inkscape / Blender（透過 GPL Palette Importer 外掛）、PNG 圖片做視覺參考。間接層：從 JSON 複製 CMYK 或 hex 數值，填入 Mimaki RasterLink 專色表、Stratasys GrabCAD 取色器、Cura 材料描述檔，或你 CAD 的色彩管理器。色票檔針對設計軟體，JSON 是進入 3D 列印流程的橋樑。</span>
```

- [ ] **Step 5: Verify swaps**

Run:
```bash
grep -c "Batch export, two interop tiers" "S:/mixoswatch/index.html"
grep -c "バッチ書き出し、二層" "S:/mixoswatch/index.html"
grep -c "批次匯出，兩種介接層級" "S:/mixoswatch/index.html"
grep -c "Batch export for 3D print pipelines" "S:/mixoswatch/index.html"
```
Expected: first three return `1`, last returns `0`.

- [ ] **Step 6: Em-dash + JS parse + triple balance**

Run:
```bash
grep -c "—\|–" "S:/mixoswatch/index.html"
node -e "const fs=require('fs');const html=fs.readFileSync('S:/mixoswatch/index.html','utf-8');const m=html.match(/<script>([\\s\\S]*?)<\\/script>/);try{new Function(m[1]);console.log('JS OK');}catch(e){console.log('ERR:',e.message);}"
grep -c 'data-en' "S:/mixoswatch/index.html"
grep -c 'data-ja' "S:/mixoswatch/index.html"
grep -c 'data-zh' "S:/mixoswatch/index.html"
```
Expected: `0`, `JS OK`, three equal triple counts.

- [ ] **Step 7: Commit Fix B**

Run:
```bash
cd S:/mixoswatch && git add index.html && git commit -m "fix(landing): split batch export into direct + indirect tiers (Fix B)

Per Spec 1 §2.2 (absorbed into Spec 5). Stop claiming ASE/GPL drop
straight into Mimaki RasterLink, Stratasys GrabCAD, or Cura (those
apps don't ingest ASE or GPL). Name the actual direct-load design
apps; name the indirect copy-the-value path for 3D-print pipelines.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 14: Absorbed Spec 1 Task 4 — Fix C (LUT interpolation drift named)

**Files:**
- Modify: `index.html` (first `<p>` after `<h3>` in `#byo`)

- [ ] **Step 1: Locate the target paragraph**

Run:
```bash
grep -n "browser tools never touch the ICC binary" "S:/mixoswatch/index.html"
```
Expected: exactly 1 match on the EN span.

- [ ] **Step 2: Replace EN span**

Use the Edit tool with:

`old_string`:
```
      <span data-en>The browser tools never touch the ICC binary. Two Python scripts do the heavy color math offline and emit small data files the HTML pages fetch. Same color engine your press RIP uses (Pillow's LittleCMS binding), same intent (Relative Colorimetric), no approximation drift.</span>
```

`new_string`:
```
      <span data-en>The browser tool never touches the ICC binary. One Python script does the heavy color math offline and emits small data files the HTML page fetches. Same color engine many prepress tools and FOSS RIPs share (Pillow's LittleCMS binding), same intent (Relative Colorimetric). Interpolation between LUT nodes adds about ΔE 0.3 of drift, well below the threshold of human perception.</span>
```

Note: "tools" → "tool" and "Two Python scripts" → "One Python script" reflect the single-tool consolidation (cmyk-explorer only, gen_luts.py only).

- [ ] **Step 3: Replace JA span**

Use the Edit tool with:

`old_string`:
```
      <span data-ja>ブラウザツールはICCバイナリに直接触れない。二つのPythonスクリプトがオフラインで色彩演算を行い、HTMLが読み込む小さなデータファイルを書き出す。プリントRIPと同じ色エンジン（PillowのLittleCMSバインディング）、同じインテント（相対比色）、近似による誤差なし。</span>
```

`new_string`:
```
      <span data-ja>ブラウザツールはICCバイナリに直接触れない。一つのPythonスクリプトがオフラインで色彩演算を行い、HTMLが読み込む小さなデータファイルを書き出す。多くのプリプレスツールやFOSS RIPが共有する色エンジン（PillowのLittleCMSバインディング）と同じ、同じインテント（相対比色）。LUTノード間の補間で約 ΔE 0.3 の誤差が生じるが、人間の知覚閾値を十分下回る。</span>
```

- [ ] **Step 4: Replace ZH span**

Use the Edit tool with:

`old_string`:
```
      <span data-zh>瀏覽器工具不直接接觸 ICC 二進位檔。兩支 Python 腳本在離線時做完所有色彩運算，產出 HTML 讀取的小型資料檔。使用與印刷 RIP 相同的色彩引擎（Pillow 的 LittleCMS 綁定）、相同的渲染目的（相對色度），無近似誤差。</span>
```

`new_string`:
```
      <span data-zh>瀏覽器工具不直接接觸 ICC 二進位檔。單支 Python 腳本在離線時做完所有色彩運算，產出 HTML 讀取的小型資料檔。與許多印前工具及 FOSS RIP 共用的色彩引擎（Pillow 的 LittleCMS 綁定）、相同的渲染目的（相對色度）。LUT 節點之間的內插帶來約 ΔE 0.3 的偏差，遠低於人眼可察覺的閾值。</span>
```

- [ ] **Step 5: Verify swaps**

Run:
```bash
grep -c "many prepress tools and FOSS RIPs share" "S:/mixoswatch/index.html"
grep -c "多くのプリプレスツールやFOSS RIPが共有する" "S:/mixoswatch/index.html"
grep -c "與許多印前工具及 FOSS RIP 共用的" "S:/mixoswatch/index.html"
grep -c "no approximation drift" "S:/mixoswatch/index.html"
grep -c "Two Python scripts" "S:/mixoswatch/index.html"
grep -c "二つのPythonスクリプト" "S:/mixoswatch/index.html"
grep -c "兩支 Python 腳本" "S:/mixoswatch/index.html"
```
Expected: first three return `1`, last four return `0`.

- [ ] **Step 6: Em-dash + JS parse + triple balance**

Same three checks as Task 13 Step 6. Expected: `0`, `JS OK`, three equal triple counts.

- [ ] **Step 7: Commit Fix C**

Run:
```bash
cd S:/mixoswatch && git add index.html && git commit -m "fix(landing): name LUT interpolation drift + single-tool wording (Fix C)

Per Spec 1 §2.3 (absorbed into Spec 5). Replace 'no approximation
drift' (mathematically incorrect; 17-node LUT interpolation adds
~ΔE 0.3 per ARCHITECTURE.md §4.1) with the actual magnitude framed
as below the perceptual threshold. Drop the 'engine the RIP uses'
overclaim. Update 'two scripts' → 'one script' to reflect Spec 5
consolidation.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 15: Absorbed Spec 1 Task 5 — Footer URL rewrite

**Files:**
- Modify: `index.html` `<footer>` block

- [ ] **Step 1: Locate the footer**

Run:
```bash
grep -n "<footer>" "S:/mixoswatch/index.html"
```
Expected: exactly 1 match.

- [ ] **Step 2: Replace the footer markup**

Use the Edit tool with:

`old_string`:
```
<footer>
  <a href="README.md">README</a>
  <span class="sep">·</span>
  <a href="ARCHITECTURE.md">Architecture</a>
  <span class="sep">·</span>
  <a href="https://github.com/">Repository</a>
</footer>
```

`new_string`:
```
<footer>
  <a href="https://github.com/mixocreative/mixoswatch/blob/main/README.md" target="_blank" rel="noopener">README</a>
  <span class="sep">·</span>
  <a href="https://github.com/mixocreative/mixoswatch/blob/main/ARCHITECTURE.md" target="_blank" rel="noopener">Architecture</a>
  <span class="sep">·</span>
  <a href="https://github.com/mixocreative/mixoswatch" target="_blank" rel="noopener">Repository</a>
</footer>
```

- [ ] **Step 3: Verify all 3 anchors point at the GitHub URLs**

Run:
```bash
grep -c 'href="https://github.com/mixocreative/mixoswatch/blob/main/README.md"' "S:/mixoswatch/index.html"
grep -c 'href="https://github.com/mixocreative/mixoswatch/blob/main/ARCHITECTURE.md"' "S:/mixoswatch/index.html"
grep -c 'href="https://github.com/mixocreative/mixoswatch"' "S:/mixoswatch/index.html"
grep -c 'href="README.md"' "S:/mixoswatch/index.html"
grep -c 'href="ARCHITECTURE.md"' "S:/mixoswatch/index.html"
```
Expected: first three return `1`, last two return `0`.

- [ ] **Step 4: Em-dash + JS parse verification**

Run:
```bash
grep -c "—\|–" "S:/mixoswatch/index.html"
node -e "const fs=require('fs');const html=fs.readFileSync('S:/mixoswatch/index.html','utf-8');const m=html.match(/<script>([\\s\\S]*?)<\\/script>/);try{new Function(m[1]);console.log('JS OK');}catch(e){console.log('ERR:',e.message);}"
```
Expected: `0`, `JS OK`.

- [ ] **Step 5: Commit footer rewrite**

Run:
```bash
cd S:/mixoswatch && git add index.html && git commit -m "fix(landing): footer markdown links point to GitHub blob viewer

Per Spec 1 §3.2 (absorbed into Spec 5). GitHub Pages serves .md
files as raw text; the /blob/main/ URL routes through GitHub's
Markdown renderer. target=_blank lets the landing tab stay alive;
rel=noopener is standard security hygiene for target=_blank.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 16: Absorbed Spec 1 Task 6 — Create `.nojekyll`

**Files:**
- Create: `.nojekyll`

- [ ] **Step 1: Confirm the file does not exist yet**

Run:
```bash
ls -la "S:/mixoswatch/.nojekyll" 2>&1
```
Expected: `ls: cannot access ...: No such file or directory`.

- [ ] **Step 2: Create the zero-byte file**

Use Bash:
```bash
cd S:/mixoswatch && : > .nojekyll
```

- [ ] **Step 3: Verify the file exists and is empty**

Run:
```bash
ls -la "S:/mixoswatch/.nojekyll"
wc -c "S:/mixoswatch/.nojekyll"
```
Expected: file exists; byte count is `0`.

- [ ] **Step 4: Commit `.nojekyll`**

Run:
```bash
cd S:/mixoswatch && git add -f .nojekyll && git commit -m "chore: add .nojekyll for GitHub Pages

Per Spec 1 §3.1 (absorbed into Spec 5). Disables Jekyll preprocessing
on GitHub Pages. Future-proofs against any path that starts with
underscore being silently dropped. Zero bytes; no behavior change
for any current file.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

The `-f` flag is required because dotfiles can be ignored by some `.gitignore` configurations. If the existing `.gitignore` does not match `.nojekyll`, the `-f` flag is harmless.

---

## Task 17: Final validation suite

This task confirms all Spec 5 gates pass at once.

- [ ] **Step 1: JS parse on `index.html`**

Run:
```bash
node -e "const fs=require('fs');const html=fs.readFileSync('S:/mixoswatch/index.html','utf-8');const m=html.match(/<script>([\\s\\S]*?)<\\/script>/);try{new Function(m[1]);console.log('JS OK');}catch(e){console.log('ERR:',e.message);}"
```
Expected: `JS OK`.

- [ ] **Step 2: JS parse on `app/cmyk-explorer.html`**

Run:
```bash
node -e "const fs=require('fs');const html=fs.readFileSync('S:/mixoswatch/app/cmyk-explorer.html','utf-8');const re=/<script>([\\s\\S]*?)<\\/script>/g;let m,c=0,errs=[];while((m=re.exec(html))){c++;try{new Function(m[1]);}catch(e){errs.push('script '+c+': '+e.message);}}console.log('scripts:',c,'errs:',errs.join(' | ')||'none');"
```
Expected: `errs: none`.

- [ ] **Step 3: Em-dash count across all shipped files**

Run:
```bash
grep -c "—\|–" "S:/mixoswatch/index.html"
grep -c "—\|–" "S:/mixoswatch/app/cmyk-explorer.html"
grep -c "—\|–" "S:/mixoswatch/ARCHITECTURE.md"
grep -c "—\|–" "S:/mixoswatch/README.md"
grep -c "—\|–" "S:/mixoswatch/run.sh"
grep -c "—\|–" "S:/mixoswatch/run.bat"
```
Expected: each returns `0`.

- [ ] **Step 4: Triple balance on `index.html`**

Run:
```bash
grep -c 'data-en' "S:/mixoswatch/index.html"
grep -c 'data-ja' "S:/mixoswatch/index.html"
grep -c 'data-zh' "S:/mixoswatch/index.html"
```
Expected: three identical numbers. Final triple count after dropped 3D section (Task 8) + dropped 3D card (Task 7) will be lower than the original baseline; only the equality matters.

- [ ] **Step 5: Footer URLs present**

Run:
```bash
grep "mixocreative/mixoswatch" "S:/mixoswatch/index.html" | grep -c "href"
```
Expected: `3`.

- [ ] **Step 6: `.nojekyll` present and zero bytes**

Run:
```bash
test -f "S:/mixoswatch/.nojekyll" && wc -c "S:/mixoswatch/.nojekyll"
```
Expected: command exits 0; byte count `0`.

- [ ] **Step 7: Zero remaining 3d-explorer / gen_libraries / swatches.json references in shipped files**

Run:
```bash
grep -rni "3d-explorer\|3d_explorer\|3D Swatch Explorer\|gen_libraries\|swatches.json" "S:/mixoswatch/index.html" "S:/mixoswatch/app/" "S:/mixoswatch/ARCHITECTURE.md" "S:/mixoswatch/README.md" "S:/mixoswatch/run.sh" "S:/mixoswatch/run.bat" "S:/mixoswatch/data/" "S:/mixoswatch/scripts/" 2>&1 | grep -v "^$"
```
Expected: empty output (no matches anywhere in shipped surface). Note: `docs/superpowers/specs/` and `docs/superpowers/plans/` are intentionally excluded because Specs 2/3/4 + their plans stay frozen on disk pending rewrite.

- [ ] **Step 8: ICC redistribution invariant**

Run:
```bash
grep -c "icc/\*.icc" "S:/mixoswatch/.gitignore"
grep -c "icc/\*.icm" "S:/mixoswatch/.gitignore"
```
Expected: each prints `1`.

- [ ] **Step 9: ΔE max slider markup + filter wiring present**

Run:
```bash
grep -c 'id="slDEmax"' "S:/mixoswatch/app/cmyk-explorer.html"
grep -c 'id="vDEmax"' "S:/mixoswatch/app/cmyk-explorer.html"
grep -c "delta_e_print > deMax" "S:/mixoswatch/app/cmyk-explorer.html"
grep -c "ΔE max (round-trip safety)" "S:/mixoswatch/app/cmyk-explorer.html"
```
Expected: each prints `1`.

- [ ] **Step 10: `gen_luts.py` smoke test**

Run (from repo root, requires Pillow installed):
```bash
cd S:/mixoswatch && python -c "import sys; sys.path.insert(0, 'scripts'); from gen_luts import build_lut; print('module imports OK')"
```
Expected: `module imports OK`. If Pillow is not installed in the current env, skip + mark this as a smoke test deferred to a Python-equipped env; do not block validation.

- [ ] **Step 11: Git log shows the expected commit chain**

Run:
```bash
cd S:/mixoswatch && git log --oneline -25
```
Expected (top down, approximately):
1. Task 17 (no commit — validation only)
2. Task 16 (.nojekyll)
3. Task 15 (footer rewrite)
4. Task 14 (Fix C)
5. Task 13 (Fix B)
6. Task 12 (audit residue — optional, may not exist if no changes)
7. Task 11 (README scrub)
8. Task 10 (ARCHITECTURE scrub)
9. Task 9 (rephrase same-library + footer arch)
10. Task 8 (drop curated section)
11. Task 7 (drop 3D card)
12. Task 6 (run.sh + run.bat)
13. Task 5 (ui_defaults.json)
14. Task 4 (ΔE slider port)
15. Task 3 (delete gen_libraries.py + swatches/)
16. Task 2 (delete 3d-explorer.html)
17. ee2236f (Spec 5 design — cherry-picked)
18. b290e2a (Fix A — cherry-picked)
19. 56abfac (em-dash pre-flight — cherry-picked)
20. (main HEAD pre-cherry-pick)

- [ ] **Step 12: Manual browser smoke — landing + cmyk-explorer**

Out-of-band test (does not block validation gate completion):
1. From repo root: `python -m http.server 8765`
2. Open `http://localhost:8765/` → landing renders, only one tool card visible, no 3D references in copy
3. Click the cmyk-explorer card → tool loads
4. Locate the ΔE max slider under TAC limit; drag to confirm filter behavior (off at far right, ΔE ≤ N at intermediate positions)
5. Confirm grid still renders, palettes still save, ASE/GPL/PNG exports still work

If any browser test fails, log + report; do not retroactively fail prior task commits (each one passed its own automated gates).

- [ ] **Step 13: Mark Spec 5 implementation complete**

If all automated gates above pass, Spec 5 is shippable. Push:
```bash
cd S:/mixoswatch && git push -u origin spec5-cmyk-only
```

Then open a PR from `spec5-cmyk-only` to `main` (out-of-band, user-driven).

Post-merge: enable GitHub Pages at the repo Settings → Pages → Source: Deploy from a branch, `main`, `/` (root). Wait for the deploy.

Post-deploy live check:
```bash
curl -sI "https://github.com/mixocreative/mixoswatch/blob/main/README.md" | head -1
curl -sI "https://github.com/mixocreative/mixoswatch/blob/main/ARCHITECTURE.md" | head -1
curl -sI "https://mixocreative.github.io/mixoswatch/" | head -1
curl -sI "https://mixocreative.github.io/mixoswatch/app/cmyk-explorer.html" | head -1
```
Expected: each returns `HTTP/2 200` (or `HTTP/1.1 200 OK`).

If any returns `404` / `5xx`, check repo is public, Pages source is correct, deploy log under Settings → Pages → "View deployment" reports success.

---

## Self-Review

**Spec coverage check (against Spec 5 §4 file-level changes):**

| Spec 5 change | Plan task |
|---|---|
| Branch + cherry-pick (§6) | Task 1 |
| Delete `app/3d-explorer.html` (§4.1) | Task 2 |
| Delete `scripts/gen_libraries.py` + `swatches/` (§4.1) | Task 3 |
| Add ΔE max slider to cmyk-explorer (§3.3, §4.2) | Task 4 |
| Scrub `data/ui_defaults.json` (§4.2) | Task 5 |
| Scrub `run.sh` + `run.bat` (§4.2) | Task 6 |
| Drop 3d card from landing (§4.2) | Task 7 |
| Drop "Curated for 3D Modeling" section (§4.2) | Task 8 |
| Rephrase same-library + footer architecture (§4.2) | Task 9 |
| Scrub `ARCHITECTURE.md` (§4.2) | Task 10 |
| Scrub `README.md` (§4.2) | Task 11 |
| Audit stash residue (§6 step 4) | Task 12 |
| Absorbed Spec 1 Task 3 — Fix B (§5) | Task 13 |
| Absorbed Spec 1 Task 4 — Fix C (§5) | Task 14 |
| Absorbed Spec 1 Task 5 — footer URL rewrite (§5) | Task 15 |
| Absorbed Spec 1 Task 6 — `.nojekyll` (§5) | Task 16 |
| Spec 5 §7 verification gates | Task 17 |

No gaps.

**Placeholder scan:** searched plan for "TBD", "TODO", "implement later", "fill in details", "appropriate error handling", "Similar to Task N". None present. Each step shows actual content.

**Type consistency:** `slDEmax` + `vDEmax` + `delta_e_print` + `deMax` + `deRaw` used consistently across Task 4 steps 1–3. Sentinel value `100` (= "off") used identically in markup, filter pipeline, and display sync.

**Frequent commits:** plan creates ~14 commits (Tasks 2-16 each one commit, Task 12 optional). Each commit is one logical change tracked in its own verification gate.

**Risk addressed (per Spec 5 §8):**
- Cherry-pick conflict: Task 1 Steps 5-7 explicitly check expected output; on conflict, stop and report.
- Stash residue: Task 12 audits both potentially-affected files before commit.
- Layout assumption (2-card grid): Task 7 Step 5 explicitly checks wrapper styling + offers single-card recipes.
- ΔE off-state confusion: slider value `100` (far right) = "off"; not `0`. Distinct from "ΔE 0.0" which means perfect-match-only.
- ICC redistribution: validation Step 8 confirms `.gitignore` retains `icc/*.icc` + `icc/*.icm`.

---

## Execution Handoff

Execution mode (per Spec 5 brainstorm): **Subagent-Driven Development**.

REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`.

Fresh subagent per task. Two-stage review (spec compliance + code quality) per task. Mark each task in TaskList in_progress before dispatching the implementer; mark completed only after both reviewers pass.
