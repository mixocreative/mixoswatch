# Spec 6: Color math + corpora + UI overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix Lab math (D65->D50 Bradford CAT), replace thin/licensed corpora with clean-provenance sources (NipponColors 250, Chinese trad 526, W3C 147), unlock hardcoded knobs (per-profile TAC, print/screen Lab toggle, 3D-print preset, dynamic library IDs), consolidate UI (Hue x Light to Sort by, collapsable Palettes panel, per-swatch ZIP export, dark-only, responsive).

**Architecture:** New branch `spec6-color-math-corpora` off `spec5-cmyk-only`. Single-tool monolithic HTML preserved (`app/mixo-swatch.html`). Color math gets dual-Lab cache (D50 + D65 precomputed). Corpora data rewritten to schema v3 (tri-lingual fields). localStorage schema bumped v1 -> v2 with one-time migration. Standalone Python validator + browser test page for verification. All changes land together (single PR, single localStorage migration event).

**Tech Stack:** Plain HTML / CSS / JS (no framework). Python 3 + Pillow + LittleCMS for ground-truth color math + corpora validator. JSZip via existing app inclusion for ZIP export. Git for branch + commits.

---

## Task 1: Branch setup

**Files:**
- Branch operation only.

- [ ] **Step 1: Verify current branch**

Run:
```bash
cd S:/mixoswatch && git status && git branch --show-current
```
Expected: working tree clean, branch is `spec5-cmyk-only`.

If working tree dirty: stop and report. Do not proceed.

- [ ] **Step 2: Create + switch to new branch**

Run:
```bash
cd S:/mixoswatch && git checkout -b spec6-color-math-corpora
```
Expected: `Switched to a new branch 'spec6-color-math-corpora'`.

- [ ] **Step 3: Verify the spec doc is on this branch**

Run:
```bash
cd S:/mixoswatch && git log --oneline -5
```
Expected: top commit is `217c93d docs(spec6): add Section 5 UI consolidation` or newer; previous commit is `352618e docs(spec6): color math + corpora + UI overhaul design`.

---

## Task 2: Add Bradford constants + rgb2lab_d50 function

**Files:**
- Modify: `app/mixo-swatch.html` around line 906-920 (existing rgb2lab block)

- [ ] **Step 1: Read the current rgb2lab block**

Open `app/mixo-swatch.html` and confirm lines 906-920 contain:
```js
function srgb2lin(u) { u/=255; return u<=0.04045? u/12.92 : Math.pow((u+0.055)/1.055, 2.4); }
function rgb2xyz(r,g,b){
  const R=srgb2lin(r), G=srgb2lin(g), B=srgb2lin(b);
  return [0.4124564*R + 0.3575761*G + 0.1804375*B,
          0.2126729*R + 0.7151522*G + 0.0721750*B,
          0.0193339*R + 0.1191920*G + 0.9503041*B];
}
const Xn=0.95047, Yn=1.0, Zn=1.08883;
function f_(t){ return t > 0.008856 ? Math.cbrt(t) : (7.787*t + 16/116); }
function rgb2lab(r,g,b){
  const [X,Y,Z]=rgb2xyz(r,g,b);
  const fx=f_(X/Xn), fy=f_(Y/Yn), fz=f_(Z/Zn);
  return [116*fy - 16, 500*(fx-fy), 200*(fy-fz)];
}
```

- [ ] **Step 2: Replace with Bradford-aware dual functions**

Replace lines 906-920 with:
```js
// -- sRGB <-> Lab math --------------------------------------------------------
function srgb2lin(u) { u/=255; return u<=0.04045? u/12.92 : Math.pow((u+0.055)/1.055, 2.4); }
function rgb2xyz(r,g,b){
  const R=srgb2lin(r), G=srgb2lin(g), B=srgb2lin(b);
  return [0.4124564*R + 0.3575761*G + 0.1804375*B,
          0.2126729*R + 0.7151522*G + 0.0721750*B,
          0.0193339*R + 0.1191920*G + 0.9503041*B];
}
// Whitepoints
const WP_D65 = { Xn: 0.95047,  Yn: 1.0, Zn: 1.08883 };
const WP_D50 = { Xn: 0.96422,  Yn: 1.0, Zn: 0.82521 };
// ICC linear Bradford CAT D65 -> D50 (ISO 15076-1 Annex E.3)
const M_BRAD_D65_D50 = [
  [ 1.0478112,  0.0228866, -0.0501270],
  [ 0.0295424,  0.9904844, -0.0170491],
  [-0.0092345,  0.0150436,  0.7521316]
];
function f_(t){ return t > 0.008856 ? Math.cbrt(t) : (7.787*t + 16/116); }
function _xyzToLab(X,Y,Z,wp){
  const fx=f_(X/wp.Xn), fy=f_(Y/wp.Yn), fz=f_(Z/wp.Zn);
  return [116*fy - 16, 500*(fx-fy), 200*(fy-fz)];
}
function rgb2lab_d65(r,g,b){
  const [X,Y,Z]=rgb2xyz(r,g,b);
  return _xyzToLab(X,Y,Z,WP_D65);
}
function rgb2lab_d50(r,g,b){
  const [X,Y,Z]=rgb2xyz(r,g,b);
  const M=M_BRAD_D65_D50;
  const X2 = M[0][0]*X + M[0][1]*Y + M[0][2]*Z;
  const Y2 = M[1][0]*X + M[1][1]*Y + M[1][2]*Z;
  const Z2 = M[2][0]*X + M[2][1]*Y + M[2][2]*Z;
  return _xyzToLab(X2,Y2,Z2,WP_D50);
}
// Active-mode dispatcher: reads LAB_MODE global. Default = d50 (print-first).
let LAB_MODE = 'd50';
function rgb2lab(r,g,b){
  return LAB_MODE === 'd50' ? rgb2lab_d50(r,g,b) : rgb2lab_d65(r,g,b);
}
```

- [ ] **Step 3: Create Python ground-truth generator**

Create `scripts/test_color_math_truth.py`:
```python
"""Generate ground-truth Lab_D50 + Lab_D65 values for 10 known sRGB hex colors.
Uses Pillow + LittleCMS (same engine as gen_luts.py) to produce ICC-standard
Lab values. Output JSON is consumed by _verify/test_color_math.html for
browser-side regression testing of the Bradford fix.
"""
from __future__ import annotations
import json
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

def hex_to_rgb(h: str) -> tuple[int,int,int]:
    h = h.lstrip("#")
    return (int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))

def srgb_to_lab(r: int, g: int, b: int, illuminant: str) -> tuple[float,float,float]:
    """sRGB -> Lab via ImageCms. illuminant in {'D50','D65'}."""
    srgb_prof = ImageCms.createProfile("sRGB")
    lab_prof = ImageCms.createProfile("LAB", colorTemp=5000 if illuminant=="D50" else 6504)
    img = Image.new("RGB",(1,1),(r,g,b))
    xform = ImageCms.buildTransformFromOpenProfiles(srgb_prof, lab_prof, "RGB", "LAB")
    lab_img = ImageCms.applyTransform(img, xform)
    L_byte, a_byte, b_byte = lab_img.getpixel((0,0))
    # Pillow encodes Lab L in [0,255] -> [0,100]; a/b in [0,255] -> [-128,127]
    L = L_byte * 100.0 / 255.0
    a = a_byte - 128.0
    bv = b_byte - 128.0
    return (L, a, bv)

def main():
    rows = []
    for hx in TEST_HEXES:
        r,g,b = hex_to_rgb(hx)
        L50,a50,b50 = srgb_to_lab(r,g,b,"D50")
        L65,a65,b65 = srgb_to_lab(r,g,b,"D65")
        rows.append({
            "hex": hx,
            "rgb": [r,g,b],
            "lab_d50": [round(L50,3), round(a50,3), round(b50,3)],
            "lab_d65": [round(L65,3), round(a65,3), round(b65,3)],
        })
    out = Path("_verify/color_math_truth.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"source":"ImageCms (LittleCMS)","rows":rows}, indent=2))
    print(f"Wrote {out} with {len(rows)} test rows")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run ground-truth generator**

Run:
```bash
cd S:/mixoswatch && python scripts/test_color_math_truth.py
```
Expected: prints `Wrote _verify/color_math_truth.json with 10 test rows`.

- [ ] **Step 5: Inspect generated truth file**

Run:
```bash
cd S:/mixoswatch && python -m json.tool _verify/color_math_truth.json | head -20
```
Expected: well-formed JSON with rows containing `hex`, `rgb`, `lab_d50`, `lab_d65`.

- [ ] **Step 6: Create browser test page**

Create `_verify/test_color_math.html`:
```html
<!doctype html>
<html><head><meta charset="utf-8"><title>Color math test</title>
<style>body{font-family:monospace;background:#111;color:#eee;padding:16px}
.pass{color:#7fffa0}.fail{color:#ff7f7f}.warn{color:#ffd966}</style>
</head><body>
<h1>Bradford D65 / D50 regression test</h1>
<pre id="out">Loading...</pre>
<script>
// Duplicate of math functions in app/mixo-swatch.html (kept in sync manually).
function srgb2lin(u){u/=255;return u<=0.04045?u/12.92:Math.pow((u+0.055)/1.055,2.4);}
function rgb2xyz(r,g,b){
  const R=srgb2lin(r),G=srgb2lin(g),B=srgb2lin(b);
  return [0.4124564*R+0.3575761*G+0.1804375*B,
          0.2126729*R+0.7151522*G+0.0721750*B,
          0.0193339*R+0.1191920*G+0.9503041*B];
}
const WP_D65={Xn:0.95047,Yn:1.0,Zn:1.08883};
const WP_D50={Xn:0.96422,Yn:1.0,Zn:0.82521};
const M_BRAD=[[1.0478112,0.0228866,-0.0501270],
              [0.0295424,0.9904844,-0.0170491],
              [-0.0092345,0.0150436,0.7521316]];
function f_(t){return t>0.008856?Math.cbrt(t):(7.787*t+16/116);}
function _xyzToLab(X,Y,Z,wp){
  const fx=f_(X/wp.Xn),fy=f_(Y/wp.Yn),fz=f_(Z/wp.Zn);
  return [116*fy-16,500*(fx-fy),200*(fy-fz)];
}
function rgb2lab_d65(r,g,b){const[X,Y,Z]=rgb2xyz(r,g,b);return _xyzToLab(X,Y,Z,WP_D65);}
function rgb2lab_d50(r,g,b){
  const[X,Y,Z]=rgb2xyz(r,g,b);const M=M_BRAD;
  return _xyzToLab(M[0][0]*X+M[0][1]*Y+M[0][2]*Z,
                   M[1][0]*X+M[1][1]*Y+M[1][2]*Z,
                   M[2][0]*X+M[2][1]*Y+M[2][2]*Z, WP_D50);
}
function deltaE76(L1,a1,b1,L2,a2,b2){
  return Math.sqrt((L1-L2)**2+(a1-a2)**2+(b1-b2)**2);
}
async function run(){
  const out = document.getElementById('out');
  const truth = await fetch('color_math_truth.json').then(r=>r.json());
  let pass = 0, fail = 0, lines = [];
  const TOL_D50 = 1.5;  // Pillow Lab quantization adds noise vs analytic Bradford
  const TOL_D65 = 0.5;
  for (const row of truth.rows) {
    const [r,g,b] = row.rgb;
    const myD50 = rgb2lab_d50(r,g,b);
    const myD65 = rgb2lab_d65(r,g,b);
    const dE50 = deltaE76(...myD50, ...row.lab_d50);
    const dE65 = deltaE76(...myD65, ...row.lab_d65);
    const ok50 = dE50 <= TOL_D50;
    const ok65 = dE65 <= TOL_D65;
    if (ok50 && ok65) pass++; else fail++;
    lines.push(`${row.hex}  D50 dE=${dE50.toFixed(3)} ${ok50?'PASS':'FAIL'}  D65 dE=${dE65.toFixed(3)} ${ok65?'PASS':'FAIL'}`);
  }
  out.innerHTML = `<span class="${fail?'fail':'pass'}">${pass} pass / ${fail} fail</span>\n\n` + lines.join('\n');
}
run();
</script></body></html>
```

- [ ] **Step 7: Verify test page passes**

Start a local server + open the test page:
```bash
cd S:/mixoswatch && python -m http.server 8765 &
SERVER_PID=$!
sleep 1
# Open _verify/test_color_math.html in browser manually OR check via curl:
curl -s http://localhost:8765/_verify/test_color_math.html | head -3
kill $SERVER_PID
```
Expected: page loads. Open `http://localhost:8765/_verify/test_color_math.html` manually in browser. Confirm: top line reads `10 pass / 0 fail` in green.

If fails: investigate Bradford matrix values, _xyzToLab implementation, or Pillow Lab encoding before proceeding.

- [ ] **Step 8: Commit**

```bash
cd S:/mixoswatch && git add app/mixo-swatch.html scripts/test_color_math_truth.py _verify/test_color_math.html _verify/color_math_truth.json
git commit -m "$(cat <<'EOF'
feat(color-math): add Bradford D65->D50 + dual rgb2lab functions

- Add rgb2lab_d50 with linear Bradford CAT (ISO 15076-1 Annex E.3)
- Keep rgb2lab_d65 as previous behaviour
- Introduce LAB_MODE global (default 'd50'); rgb2lab dispatches by mode
- Python ground-truth generator using Pillow ImageCms for verification
- Standalone browser test page asserts 10 known hex against Pillow ground truth

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Dual Lab cache in deriveSwatch + corpus entries

**Files:**
- Modify: `app/mixo-swatch.html` around line 1112-1132 (`deriveSwatch`) and lines around 1195-1240 (corpus Lab cache)

- [ ] **Step 1: Update deriveSwatch to cache both Lab modes**

Find the existing `deriveSwatch` function (line 1112-1132). Replace the Lab-computation lines with:
```js
function deriveSwatch(s, lut) {
  const [R,G,B] = lutLookup(lut, s.C, s.M, s.Y, s.K);
  s.R=R; s.G=G; s.B=B;
  s.hex = '#' + [R,G,B].map(v=>v.toString(16).padStart(2,'0').toUpperCase()).join('');
  // Precompute both Lab modes; activeLab() dispatches at read time.
  s.lab_d50 = rgb2lab_d50(R,G,B);
  s.lab_d65 = rgb2lab_d65(R,G,B);
  const [L,a,b] = LAB_MODE === 'd50' ? s.lab_d50 : s.lab_d65;
  s.L_star=+L.toFixed(2); s.a_star=+a.toFixed(2); s.b_star=+b.toFixed(2);
  const Lw = luminance(R,G,B);
  s.luminance = +Lw.toFixed(5);
  const cBlack = contrast(Lw, 0);
  const cWhite = contrast(Lw, 1);
  if (cBlack >= cWhite) { s.text_color='#000000'; s.contrast_ratio=+cBlack.toFixed(2); }
  else                  { s.text_color='#FFFFFF'; s.contrast_ratio=+cWhite.toFixed(2); }
  s.wcag_aa  = s.contrast_ratio >= 4.5;
  s.wcag_aaa = s.contrast_ratio >= 7.0;
  s.tac = s.C+s.M+s.Y+s.K;
  const [t,tn] = kTier(s.K);
  s.k_tier = t; s.k_tier_name = tn;
  s.grayscale = (s.C===0 && s.M===0 && s.Y===0);
}
```

Note: `s.dic_name = ''; s.pantone_name = '';` lines removed (corpora dropped in Task 12).
Note: `system_name` synthesis removed in Task 13.

- [ ] **Step 2: Add activeLab helper after deriveSwatch**

Add immediately after `deriveSwatch`:
```js
// Dispatcher used by every code path that reads Lab from a swatch or corpus entry.
function activeLab(obj, suffix){
  // obj has both .lab_d50 and .lab_d65 (or ._lab_d50_<suffix> / ._lab_d65_<suffix>)
  const key50 = suffix ? `_lab_d50_${suffix}` : 'lab_d50';
  const key65 = suffix ? `_lab_d65_${suffix}` : 'lab_d65';
  return LAB_MODE === 'd50' ? obj[key50] : obj[key65];
}
```

- [ ] **Step 3: Update corpus entry Lab cache to dual mode**

Find the block around lines 1195-1240 that sets `e._lab_hex` and `e._lab_cmyk`. Replace with:
```js
function _cacheEntryLabs(e) {
  // Compute and cache Lab in both whitepoints for both anchor sources.
  if (e.hex) {
    const r=parseInt(e.hex.slice(1,3),16),
          g=parseInt(e.hex.slice(3,5),16),
          b=parseInt(e.hex.slice(5,7),16);
    e._lab_d50_hex = rgb2lab_d50(r,g,b);
    e._lab_d65_hex = rgb2lab_d65(r,g,b);
  }
  if (Array.isArray(e.cmyk) && e.cmyk.length === 4 && ACTIVE_LUT) {
    const [R,G,B] = lutLookup(ACTIVE_LUT, e.cmyk[0], e.cmyk[1], e.cmyk[2], e.cmyk[3]);
    e._lab_d50_cmyk = rgb2lab_d50(R,G,B);
    e._lab_d65_cmyk = rgb2lab_d65(R,G,B);
  }
}
```

Then call `_cacheEntryLabs(e)` in the corpus-loop where the old `_lab_hex` / `_lab_cmyk` lines lived. Search for `e._lab_hex` and `e._lab_cmyk` and replace each callsite with `_cacheEntryLabs(e)` exactly once per entry.

- [ ] **Step 4: Replace `_entryAnchorLab` to dispatch by LAB_MODE**

Locate the existing `_entryAnchorLab` helper (search file for that name). Replace with:
```js
function _entryAnchorLab(e, anchorPref) {
  // anchorPref in {'cmyk','hex'}. Falls back to the other if requested one missing.
  const wantCmyk = anchorPref === 'cmyk';
  const key = wantCmyk ? `_lab_d${LAB_MODE === 'd50' ? '50' : '65'}_cmyk`
                       : `_lab_d${LAB_MODE === 'd50' ? '50' : '65'}_hex`;
  if (e[key]) return e[key];
  // Fallback to other anchor
  const altKey = wantCmyk ? `_lab_d${LAB_MODE === 'd50' ? '50' : '65'}_hex`
                          : `_lab_d${LAB_MODE === 'd50' ? '50' : '65'}_cmyk`;
  return e[altKey] || null;
}
```

- [ ] **Step 5: Smoke-test the app in browser**

Start dev server:
```bash
cd S:/mixoswatch && python -m http.server 8765 &
```
Open `http://localhost:8765/app/mixo-swatch.html` in browser. Open DevTools console. Confirm:
- No errors on load
- Sample a few swatches via `MAIN_DATA[0].lab_d50`, `MAIN_DATA[0].lab_d65` in console -> both arrays of length 3
- Grid renders normally

Kill server when done.

- [ ] **Step 6: Commit**

```bash
cd S:/mixoswatch && git add app/mixo-swatch.html
git commit -m "$(cat <<'EOF'
feat(color-math): dual Lab cache per swatch + corpus entry

- deriveSwatch caches both s.lab_d50 + s.lab_d65 at preload
- _cacheEntryLabs caches both ._lab_d50_hex/cmyk + ._lab_d65_hex/cmyk
- activeLab(obj, suffix) dispatcher reads either mode
- _entryAnchorLab routes by LAB_MODE + anchor pref with fallback

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: LAB_MODE toggle UI + rerouted match path

**Files:**
- Modify: `app/mixo-swatch.html` (settings panel area + global toggle handlers)

- [ ] **Step 1: Locate the sidebar settings area**

Search for `<div class="step-group-header">` to find existing section headers. The Lab toggle belongs under section "01" (Pick a profile / preset). Confirm structure with:
```bash
cd S:/mixoswatch && grep -n "step-group-header" app/mixo-swatch.html | head -5
```

- [ ] **Step 2: Add Lab mode radio + status badge**

Find the existing profile selector block (search for `<select.*onchange="onProfileChange"` or similar). Immediately above it, insert:
```html
<div class="sec">
  <div class="sec-label" title="Color mode picks the Lab whitepoint used for corpus matching. Print mode (D50) aligns with ICC-standard swatch books. Screen mode (D65) is pure sRGB-native.">Color mode</div>
  <div class="lab-mode-row">
    <label class="lab-radio">
      <input type="radio" name="labMode" value="d50" checked onchange="setLabMode('d50')"> Print (D50)
    </label>
    <label class="lab-radio">
      <input type="radio" name="labMode" value="d65" onchange="setLabMode('d65')"> Screen (D65)
    </label>
  </div>
</div>
```

- [ ] **Step 3: Add persistent status badge to topbar**

Find the topbar (line 31-37 area, `<div class="topbar">`). Insert a span before the `<div class="topbar-sep">`:
```html
<span class="lab-mode-badge" id="labModeBadge" title="Active Lab whitepoint. Switch in sidebar under 'Color mode'.">Mode: Print (D50)</span>
```

- [ ] **Step 4: Add CSS for the badge + radio row**

In the `<style>` block near other `.topbar` rules, add:
```css
.lab-mode-badge{
  font-size:11px;color:var(--accent);background:rgba(91,163,255,.10);
  border:1px solid rgba(91,163,255,.30);border-radius:var(--r);
  padding:3px 8px;font-family:var(--font-mono);white-space:nowrap;
}
.lab-mode-row{display:flex;gap:10px;font-size:12px}
.lab-radio{display:flex;align-items:center;gap:5px;cursor:pointer;flex:1}
.lab-radio input{cursor:pointer}
```

- [ ] **Step 5: Add setLabMode handler**

Search for `function setSort` or similar handler block. Add nearby:
```js
function setLabMode(mode){
  if (mode !== 'd50' && mode !== 'd65') return;
  if (LAB_MODE === mode) return;
  LAB_MODE = mode;
  // Update aliases on every swatch (cheap; just a write loop)
  for (const s of MAIN_DATA) {
    const [L,a,b] = mode === 'd50' ? s.lab_d50 : s.lab_d65;
    s.L_star=+L.toFixed(2); s.a_star=+a.toFixed(2); s.b_star=+b.toFixed(2);
  }
  // Re-run name matching against new active Lab
  for (const lib of CORPORA.libraries) _markClosest(lib);
  // Persist + refresh badge + re-render grid
  saveUIState();
  document.getElementById('labModeBadge').textContent =
    mode === 'd50' ? 'Mode: Print (D50)' : 'Mode: Screen (D65)';
  document.querySelectorAll('input[name="labMode"]').forEach(r => {
    r.checked = (r.value === mode);
  });
  refreshGrid();
}
```

- [ ] **Step 7: Persist + restore lab_mode in UI state**

Find `saveUIState` / `applyUIState` functions (around line 832-880). Add `lab_mode: LAB_MODE` to the saved object, and in `applyUIState` add:
```js
if (typeof s.lab_mode === 'string' && (s.lab_mode === 'd50' || s.lab_mode === 'd65')) {
  LAB_MODE = s.lab_mode;
}
```

Apply badge + radio reflection at boot:
```js
document.getElementById('labModeBadge').textContent =
  LAB_MODE === 'd50' ? 'Mode: Print (D50)' : 'Mode: Screen (D65)';
document.querySelectorAll('input[name="labMode"]').forEach(r => {
  r.checked = (r.value === LAB_MODE);
});
```

- [ ] **Step 8: Smoke-test toggle in browser**

Start dev server, open the app, open DevTools. Flip the radio between D50 and D65. Confirm:
- Badge text updates
- Grid re-renders within ~100ms
- `MAIN_DATA[0].L_star` value changes after toggle
- `localStorage.cmykUIState_v1` contains `"lab_mode":"d65"` after toggling to screen

Note: keys are still `cmykUIState_v1` at this stage; v2 migration is Task 27.

- [ ] **Step 9: Commit**

```bash
cd S:/mixoswatch && git add app/mixo-swatch.html
git commit -m "$(cat <<'EOF'
feat(color-math): Lab mode toggle (Print D50 / Screen D65) with badge

- Sidebar radio + topbar status badge
- setLabMode swaps active Lab, re-runs _markClosest for all libs,
  re-renders grid; persisted to localStorage
- Default mode = D50 (print-first, aligns ICC swatch books)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Drop system_name + HUE_NAMES + bins entirely

**Files:**
- Modify: `app/mixo-swatch.html` (delete lines around 1007-1031, 2747-2748 CSV, tooltip refs)

- [ ] **Step 1: Identify all system_name / HUE_NAMES references**

Run:
```bash
cd S:/mixoswatch && grep -n "system_name\|systemName\|baseName\|neutralName\|lightnessBin\|chromaBin\|hueBin\|HUE_NAMES" app/mixo-swatch.html
```
Expected: multiple matches in:
- Lines 1007-1031 (the function definitions)
- Around line 2748 (CSV export field list)
- Possibly tooltip / detail panel code

- [ ] **Step 2: Delete the function definitions**

Remove lines 1007-1031 (the entire block from `const HUE_NAMES =` through `function systemName(s){…}`). Use Edit tool with the full block as `old_string`.

- [ ] **Step 3: Remove s.system_name field write**

Find where `s.system_name` is assigned (likely inside or after `deriveSwatch`). Delete that line.

- [ ] **Step 4: Remove system_name from CSV export**

Find line around 2747-2748:
```js
'L_star','a_star','b_star','jpn_name','jpn_romaji','deltaE_jpn',
'html_name','deltaE_html','dic_name','pantone_name'];
```
Remove any reference to `system_name`. Note: this block will be heavily rewritten in Task 12 (dynamic library IDs); for now just remove the system_name token if present.

- [ ] **Step 5: Remove system_name from tooltip**

Search for `system_name` references in tooltip/detail panel render code:
```bash
cd S:/mixoswatch && grep -n "system_name" app/mixo-swatch.html
```
Expected: 0 matches. If any remain, remove them.

- [ ] **Step 6: Smoke-test app loads cleanly**

Start dev server, open app, check console for errors. Grid should render. Click a swatch -> detail panel opens with no `system_name` field.

- [ ] **Step 7: Commit**

```bash
cd S:/mixoswatch && git add app/mixo-swatch.html
git commit -m "$(cat <<'EOF'
refactor: drop system_name synthesis + HUE_NAMES + bin thresholds

Algorithmic names had no cross-app meaning. Swatches without a
corpus match now show hex only (~93% of grid). Frees binning
config from being baked into code.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Corpora validator script

**Files:**
- Create: `scripts/validate_corpora.py`

- [ ] **Step 1: Write validator**

Create `scripts/validate_corpora.py`:
```python
"""Validate data/corpora/name_corpora.json against schema v3 rules.

Hard requirements (exit 1 on any failure):
  1. Schema version >= 3.
  2. Each corpus has id, label{en,ja,zh}, fields[], default_display, anchor, entries[].
  3. Every entry has hex (and cmyk if anchor=cmyk).
  4. After tri-lingual fallback fill (see fill_rules), every entry has non-empty
     name_en, name_ja, name_zh.
  5. Within a corpus, no duplicate (lowercased) values in any name_* field.
  6. No U+2014 em-dash or U+2013 en-dash anywhere in the file.

Soft warnings (print but do not fail):
  - Entry where name_en equals romaji/pinyin (gloss looks like a translit).
"""
from __future__ import annotations
import json, sys, re
from pathlib import Path

CORPORA_PATH = Path("data/corpora/name_corpora.json")
LANG_FIELDS = ["name_en","name_ja","name_zh"]
BAD_CHARS = [chr(0x2014), chr(0x2013)]  # em-dash U+2014, en-dash U+2013

def fail(msg: str):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)

def warn(msg: str):
    print(f"WARN: {msg}")

def fill_fallback(e: dict) -> dict:
    """Mirror loader rule: fill name_en/ja/zh from translit or native if blank."""
    fallback = (e.get("romaji") or e.get("pinyin") or e.get("name_ja") or
                e.get("name_zh") or e.get("name_en") or "?")
    out = dict(e)
    for f in LANG_FIELDS:
        if not out.get(f) or not str(out[f]).strip():
            out[f] = fallback
    return out

def main():
    if not CORPORA_PATH.exists():
        fail(f"{CORPORA_PATH} does not exist")
    raw = CORPORA_PATH.read_text(encoding="utf-8")
    for c in BAD_CHARS:
        if c in raw:
            fail(f"Banned character U+{ord(c):04X} found in {CORPORA_PATH}")
    data = json.loads(raw)
    if data.get("version", 0) < 3:
        fail(f"Schema version must be >= 3, got {data.get('version')}")
    libs = data.get("corpora") or data.get("libraries") or []
    if not libs:
        fail("corpora[] is empty or missing")
    total_entries = 0
    for lib in libs:
        lid = lib.get("id")
        if not lid:
            fail("library missing id")
        lab = lib.get("label")
        if not (isinstance(lab, dict) and all(k in lab for k in ["en","ja","zh"])):
            fail(f"[{lid}] label must be {{en,ja,zh}}")
        if not lib.get("fields"):
            fail(f"[{lid}] fields[] missing")
        if "default_display" not in lib:
            fail(f"[{lid}] default_display missing")
        if "anchor" not in lib:
            fail(f"[{lid}] anchor missing")
        entries = lib.get("entries", [])
        if not entries:
            fail(f"[{lid}] entries[] empty")
        seen = {f: {} for f in LANG_FIELDS}
        for i, e in enumerate(entries):
            if not e.get("hex"):
                fail(f"[{lid}][{i}] missing hex")
            if not re.match(r"^#[0-9A-Fa-f]{6}$", e["hex"]):
                fail(f"[{lid}][{i}] malformed hex: {e['hex']}")
            if lib["anchor"] == "cmyk":
                cmyk = e.get("cmyk")
                if not (isinstance(cmyk, list) and len(cmyk) == 4):
                    fail(f"[{lid}][{i}] anchor=cmyk requires 4-element cmyk array")
            filled = fill_fallback(e)
            for f in LANG_FIELDS:
                v = filled[f].strip()
                if not v:
                    fail(f"[{lid}][{i}] {f} still empty after fallback")
                key = v.lower()
                if key in seen[f]:
                    fail(f"[{lid}] duplicate {f}={v!r} at entries[{seen[f][key]}] and entries[{i}]")
                seen[f][key] = i
            # Soft warnings
            for tf in ("romaji", "pinyin"):
                if e.get(tf) and e.get("name_en") and e["name_en"].strip().lower() == e[tf].strip().lower():
                    warn(f"[{lid}][{i}] name_en={e['name_en']!r} equals {tf} (gloss missing?)")
        total_entries += len(entries)
        print(f"OK: [{lid}] {len(entries)} entries pass")
    print(f"PASS: {len(libs)} corpora, {total_entries} entries total")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run validator against current corpora**

Run:
```bash
cd S:/mixoswatch && python scripts/validate_corpora.py
```
Expected: FAIL because current corpora is v2.1, not v3. This is intended; corpora rewrite is Tasks 7-10.

- [ ] **Step 3: Commit validator**

```bash
cd S:/mixoswatch && git add scripts/validate_corpora.py
git commit -m "$(cat <<'EOF'
feat(scripts): corpora schema v3 validator

Enforces tri-lingual fill (post-fallback), hex/cmyk presence,
per-library name uniqueness, em-dash/en-dash ban. Used as gate
before committing name_corpora.json changes.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Build jp-trad corpus (250 NipponColors)

**Files:**
- Create: `scripts/source_data/nippon_colors_raw.json` (vendored)
- Create: `scripts/build_jp_trad.py`
- Output: feeds into Task 10

- [ ] **Step 1: Fetch NipponColors raw data**

Pull from the public gist `https://gist.github.com/RobertYim/3061171b1dbfa93d7f71720e94403382`. Save the raw JSON to `scripts/source_data/nippon_colors_raw.json`. If the gist is unreachable, the data is also mirrored at https://nipponcolors.com/ (250 entries with HEX + CMYK + romaji + kanji name).

Verify count:
```bash
cd S:/mixoswatch && python -c "import json; d=json.load(open('scripts/source_data/nippon_colors_raw.json',encoding='utf-8')); print(len(d), 'entries')"
```
Expected: `250 entries`.

- [ ] **Step 2: Write transformer**

Create `scripts/build_jp_trad.py`:
```python
"""Transform NipponColors raw scrape into schema v3 jp-trad corpus.

Input:  scripts/source_data/nippon_colors_raw.json
Output: scripts/source_data/jp_trad_v3.json (consumed by build_corpora.py in Task 10)

Each raw entry has: { name (kanji), pronounce (romaji), hex, cmyk: "C/M/Y/K" or [C,M,Y,K] }.
English gloss + Chinese gloss come from scripts/source_data/jp_trad_glosses.json,
maintained by hand. Missing glosses fall back to romaji.
"""
from __future__ import annotations
import json, re
from pathlib import Path

RAW = Path("scripts/source_data/nippon_colors_raw.json")
GLOSS = Path("scripts/source_data/jp_trad_glosses.json")
OUT = Path("scripts/source_data/jp_trad_v3.json")

def parse_cmyk(v):
    if isinstance(v, list) and len(v) == 4:
        return [int(x) for x in v]
    if isinstance(v, str):
        parts = re.split(r"[/,\s]+", v.strip())
        if len(parts) == 4:
            return [int(p) for p in parts]
    raise ValueError(f"bad cmyk: {v!r}")

def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    glosses = json.loads(GLOSS.read_text(encoding="utf-8")) if GLOSS.exists() else {}
    entries = []
    for r in raw:
        kanji = r.get("name") or r.get("kanji") or ""
        romaji = (r.get("pronounce") or r.get("romaji") or "").strip()
        hex_v = r.get("hex","").upper()
        if not hex_v.startswith("#"):
            hex_v = "#" + hex_v
        cmyk = parse_cmyk(r.get("cmyk"))
        g = glosses.get(kanji, {})
        entries.append({
            "name_ja": kanji,
            "romaji":  romaji,
            "name_en": g.get("en") or romaji,
            "name_zh": g.get("zh") or romaji,
            "hex":     hex_v,
            "cmyk":    cmyk,
        })
    OUT.write_text(json.dumps({
        "id": "jp-trad",
        "label": {"en":"Japanese traditional (NipponColors 250)","ja":"日本の伝統色","zh":"日本传统色"},
        "fields": [
            {"id":"name_ja","label":{"en":"kanji","ja":"漢字","zh":"汉字"}},
            {"id":"romaji", "label":{"en":"romaji","ja":"ローマ字","zh":"罗马字"}},
            {"id":"name_en","label":{"en":"English","ja":"英語","zh":"英文"}},
            {"id":"name_zh","label":{"en":"Chinese","ja":"中国語","zh":"中文"}},
        ],
        "default_display":"name_ja",
        "anchor":"cmyk",
        "source":"https://nipponcolors.com/ (250 entries, public)",
        "entries": entries,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} with {len(entries)} entries")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create initial glosses skeleton**

Create `scripts/source_data/jp_trad_glosses.json`:
```json
{
  "桜色":   {"en":"cherry blossom",   "zh":"樱花色"},
  "桃色":   {"en":"peach",            "zh":"桃色"},
  "鴇色":   {"en":"crested ibis pink","zh":"朱鹮色"},
  "珊瑚色": {"en":"coral",            "zh":"珊瑚色"},
  "薔薇色": {"en":"rose",             "zh":"蔷薇色"},
  "韓紅":   {"en":"deep crimson",     "zh":"韩红"},
  "紅梅色": {"en":"red plum",         "zh":"红梅色"},
  "甚三紅": {"en":"safflower red",    "zh":"红花红"}
}
```

(The full glosses dictionary will be built up iteratively. Initial 8 entries shown; expand as needed. Missing entries fall back to romaji via the build script.)

- [ ] **Step 4: Run transformer**

Run:
```bash
cd S:/mixoswatch && python scripts/build_jp_trad.py
```
Expected: `Wrote scripts/source_data/jp_trad_v3.json with 250 entries`.

- [ ] **Step 5: Spot-check output**

Run:
```bash
cd S:/mixoswatch && python -c "import json; d=json.load(open('scripts/source_data/jp_trad_v3.json',encoding='utf-8')); print(json.dumps(d['entries'][0], ensure_ascii=False, indent=2))"
```
Expected: well-formed entry with all 4 name fields + hex + cmyk.

- [ ] **Step 6: Commit**

```bash
cd S:/mixoswatch && git add scripts/source_data/nippon_colors_raw.json scripts/source_data/jp_trad_glosses.json scripts/build_jp_trad.py scripts/source_data/jp_trad_v3.json
git commit -m "$(cat <<'EOF'
data(jp-trad): vendor NipponColors 250 + build script

Raw scrape vendored from public gist; glosses dictionary
seeded with 8 common entries (rest fall back to romaji).
Transformer outputs schema v3 corpus block.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Build zh-trad corpus (526 Chinese traditional)

**Files:**
- Create: `scripts/source_data/zh_trad_raw.json` (vendored)
- Create: `scripts/source_data/zh_trad_glosses.json`
- Create: `scripts/build_zh_trad.py`

- [ ] **Step 1: Fetch Chinese traditional raw data**

Pull from one of: `https://github.com/zerosoul/chinese-colors` (data file `src/data/colors.json`) or color-term.com community list. Save normalized to `scripts/source_data/zh_trad_raw.json` with each entry like:
```json
{"name": "朱砂", "pinyin": "zhū shā", "hex": "#FF461F", "cmyk": [0, 73, 88, 0]}
```

If a source lacks CMYK, derive from hex via Pillow + sRGB->FOGRA39 (use scripts/test_color_math_truth.py's pattern):
```python
from PIL import Image, ImageCms
srgb = ImageCms.createProfile("sRGB")
cmyk = ImageCms.getOpenProfile("icc/CoatedFOGRA39.icc")
xform = ImageCms.buildTransformFromOpenProfiles(srgb, cmyk, "RGB", "CMYK")
img = Image.new("RGB",(1,1),(r,g,b)); out = ImageCms.applyTransform(img, xform)
C,M,Y,K = [round(v*100/255) for v in out.getpixel((0,0))]
```

Verify count:
```bash
cd S:/mixoswatch && python -c "import json; d=json.load(open('scripts/source_data/zh_trad_raw.json',encoding='utf-8')); print(len(d), 'entries')"
```
Expected: `526 entries` (or close; document final count in commit message).

- [ ] **Step 2: Create glosses skeleton**

Create `scripts/source_data/zh_trad_glosses.json`:
```json
{
  "朱砂":   {"en":"cinnabar",       "ja":"朱砂"},
  "胭脂":   {"en":"rouge",          "ja":"臙脂"},
  "海棠红": {"en":"crabapple red",  "ja":"海棠紅"},
  "石榴红": {"en":"pomegranate",    "ja":"石榴紅"},
  "桃红":   {"en":"peach blossom",  "ja":"桃紅"},
  "茜色":   {"en":"madder",         "ja":"茜色"},
  "天青":   {"en":"sky cyan",       "ja":"天青"},
  "藏蓝":   {"en":"navy",           "ja":"藏青"}
}
```

- [ ] **Step 3: Write transformer**

Create `scripts/build_zh_trad.py`:
```python
"""Build zh-trad corpus block from raw Chinese traditional list."""
from __future__ import annotations
import json
from pathlib import Path

RAW = Path("scripts/source_data/zh_trad_raw.json")
GLOSS = Path("scripts/source_data/zh_trad_glosses.json")
OUT = Path("scripts/source_data/zh_trad_v3.json")

def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    glosses = json.loads(GLOSS.read_text(encoding="utf-8")) if GLOSS.exists() else {}
    entries = []
    for r in raw:
        hanzi = r["name"]
        pinyin = r.get("pinyin","").strip()
        hex_v = r.get("hex","").upper()
        if not hex_v.startswith("#"):
            hex_v = "#" + hex_v
        cmyk = r.get("cmyk")
        if not (isinstance(cmyk, list) and len(cmyk) == 4):
            raise ValueError(f"missing cmyk for {hanzi}; pre-derive via Pillow")
        g = glosses.get(hanzi, {})
        entries.append({
            "name_zh": hanzi,
            "pinyin":  pinyin,
            "name_en": g.get("en") or pinyin,
            "name_ja": g.get("ja") or pinyin,
            "hex":     hex_v,
            "cmyk":    cmyk,
        })
    OUT.write_text(json.dumps({
        "id": "zh-trad",
        "label": {"en":"Chinese traditional (526)","ja":"中国の伝統色","zh":"中国传统色"},
        "fields": [
            {"id":"name_zh","label":{"en":"hanzi","ja":"漢字","zh":"汉字"}},
            {"id":"pinyin", "label":{"en":"pinyin","ja":"ピンイン","zh":"拼音"}},
            {"id":"name_en","label":{"en":"English","ja":"英語","zh":"英文"}},
            {"id":"name_ja","label":{"en":"Japanese","ja":"日本語","zh":"日文"}},
        ],
        "default_display":"name_zh",
        "anchor":"cmyk",
        "source":"https://color-term.com/traditional-color-of-china/ (526 entries)",
        "entries": entries,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} with {len(entries)} entries")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run transformer**

Run:
```bash
cd S:/mixoswatch && python scripts/build_zh_trad.py
```
Expected: `Wrote scripts/source_data/zh_trad_v3.json with N entries` (N near 526).

- [ ] **Step 5: Commit**

```bash
cd S:/mixoswatch && git add scripts/source_data/zh_trad_raw.json scripts/source_data/zh_trad_glosses.json scripts/build_zh_trad.py scripts/source_data/zh_trad_v3.json
git commit -m "$(cat <<'EOF'
data(zh-trad): vendor Chinese traditional 526 + build script

Raw data from community source (Chinese Academy of Science
1957 color dictionary, mirrored on color-term.com). Glosses
seeded with 8 common entries.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Backfill html corpus to 147 W3C canonical

**Files:**
- Create: `scripts/build_html_corpus.py`
- Output: `scripts/source_data/html_v3.json`

- [ ] **Step 1: Vendor canonical W3C named-color list**

Per CSS Color Module Level 4, 147 keywords + aliases. Create `scripts/source_data/css_named_colors.json` with full list. Reference: https://www.w3.org/TR/css-color-4/#named-colors.

Content (truncated for brevity in plan; full list of 147 must be vendored):
```json
[
  {"name":"aliceblue",            "hex":"#F0F8FF"},
  {"name":"antiquewhite",         "hex":"#FAEBD7"},
  {"name":"aqua",                 "hex":"#00FFFF"},
  {"name":"aquamarine",           "hex":"#7FFFD4"},
  {"name":"azure",                "hex":"#F0FFFF"},
  {"name":"beige",                "hex":"#F5F5DC"},
  {"name":"bisque",               "hex":"#FFE4C4"},
  {"name":"black",                "hex":"#000000"},
  {"name":"blanchedalmond",       "hex":"#FFEBCD"},
  {"name":"blue",                 "hex":"#0000FF"}
]
```

The implementer must enumerate all 147 from the spec. A quick way:
```python
# Pull dynamically once, then commit the resulting JSON:
import urllib.request, re
html = urllib.request.urlopen("https://www.w3.org/TR/css-color-4/").read().decode()
# Extract from the named-color table; manual review required.
```

Or use a known clean dataset (e.g., the `colornames` npm package canonical data, the MDN reference page, or Wikipedia "Web colors" table).

Verify:
```bash
cd S:/mixoswatch && python -c "import json; d=json.load(open('scripts/source_data/css_named_colors.json',encoding='utf-8')); print(len(d), 'keywords')"
```
Expected: `147 keywords`.

- [ ] **Step 2: Vendor translit table (en -> ja katakana / zh hanzi)**

Create `scripts/source_data/html_translit.json` mapping each English keyword to katakana + hanzi:
```json
{
  "aliceblue":      {"ja":"アリスブルー",        "zh":"爱丽丝蓝"},
  "antiquewhite":   {"ja":"アンティークホワイト","zh":"古董白"},
  "aqua":           {"ja":"アクア",              "zh":"水色"},
  "black":          {"ja":"ブラック",            "zh":"黑色"},
  "cornflowerblue": {"ja":"コーンフラワーブルー","zh":"矢车菊蓝"}
}
```

Full 147-entry table must be created; missing entries fall back to English name in the build script.

- [ ] **Step 3: Write transformer**

Create `scripts/build_html_corpus.py`:
```python
"""Build html corpus block (147 W3C named colors, schema v3)."""
from __future__ import annotations
import json
from pathlib import Path
from PIL import Image, ImageCms

RAW = Path("scripts/source_data/css_named_colors.json")
TRANSLIT = Path("scripts/source_data/html_translit.json")
ICC = Path("icc/CoatedFOGRA39.icc")
OUT = Path("scripts/source_data/html_v3.json")

def hex_to_cmyk_fogra39(hex_v: str) -> list[int]:
    """Derive CMYK from hex via sRGB->FOGRA39 ImageCms transform."""
    h = hex_v.lstrip("#")
    r,g,b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    srgb = ImageCms.createProfile("sRGB")
    if not ICC.exists():
        # icc dir is gitignored; user must supply. Skip cmyk for html corpus.
        return None
    cmyk_prof = ImageCms.getOpenProfile(str(ICC))
    xform = ImageCms.buildTransformFromOpenProfiles(srgb, cmyk_prof, "RGB", "CMYK")
    img = Image.new("RGB",(1,1),(r,g,b))
    out = ImageCms.applyTransform(img, xform)
    C,M,Y,K = [round(v*100/255) for v in out.getpixel((0,0))]
    return [C,M,Y,K]

def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    translit = json.loads(TRANSLIT.read_text(encoding="utf-8")) if TRANSLIT.exists() else {}
    entries = []
    for r in raw:
        name = r["name"]
        hex_v = r["hex"].upper()
        t = translit.get(name, {})
        e = {
            "name_en": name,
            "name_ja": t.get("ja") or name,
            "name_zh": t.get("zh") or name,
            "hex":     hex_v,
        }
        cmyk = hex_to_cmyk_fogra39(hex_v)
        if cmyk is not None:
            e["cmyk"] = cmyk
        entries.append(e)
    OUT.write_text(json.dumps({
        "id": "html",
        "label": {"en":"W3C named colors (147)","ja":"W3C 名前付き色","zh":"W3C 命名色"},
        "fields": [
            {"id":"name_en","label":{"en":"English","ja":"英語","zh":"英文"}},
            {"id":"name_ja","label":{"en":"Japanese","ja":"日本語","zh":"日文"}},
            {"id":"name_zh","label":{"en":"Chinese","ja":"中国語","zh":"中文"}},
        ],
        "default_display":"name_en",
        "anchor":"hex",
        "source":"https://www.w3.org/TR/css-color-4/#named-colors",
        "entries": entries,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} with {len(entries)} entries")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run transformer**

Run:
```bash
cd S:/mixoswatch && python scripts/build_html_corpus.py
```
Expected: `Wrote scripts/source_data/html_v3.json with 147 entries`.

- [ ] **Step 5: Commit**

```bash
cd S:/mixoswatch && git add scripts/source_data/css_named_colors.json scripts/source_data/html_translit.json scripts/build_html_corpus.py scripts/source_data/html_v3.json
git commit -m "$(cat <<'EOF'
data(html): backfill 147 W3C canonical named colors + translit

Anchor remains hex (W3C names are sRGB-native).
ja/zh translit table seeds via katakana/hanzi.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Assemble final name_corpora.json v3

**Files:**
- Create: `scripts/build_corpora.py`
- Modify: `data/corpora/name_corpora.json` (full rewrite)

- [ ] **Step 1: Write assembler**

Create `scripts/build_corpora.py`:
```python
"""Assemble per-corpus build outputs into the final name_corpora.json v3."""
from __future__ import annotations
import json
from pathlib import Path

PARTS = [
    Path("scripts/source_data/jp_trad_v3.json"),
    Path("scripts/source_data/html_v3.json"),
    Path("scripts/source_data/zh_trad_v3.json"),
]
OUT = Path("data/corpora/name_corpora.json")

def main():
    corpora = []
    for p in PARTS:
        if not p.exists():
            raise SystemExit(f"missing part: {p}; run build_{p.stem}.py first")
        corpora.append(json.loads(p.read_text(encoding="utf-8")))
    OUT.write_text(json.dumps({
        "version": 3,
        "schema_rev": "3.0",
        "_doc": "Schema v3: tri-lingual fields per entry (name_en, name_ja, name_zh) plus translit (romaji/pinyin). Loader fills empty language slots with translit/native fallback. Library label is a {en,ja,zh} object; fields[] declares all displayable name fields with tri-lingual labels.",
        "corpora": corpora,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(c["entries"]) for c in corpora)
    print(f"Wrote {OUT}: {len(corpora)} corpora, {total} entries total")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run assembler**

Run:
```bash
cd S:/mixoswatch && python scripts/build_corpora.py
```
Expected: `Wrote data/corpora/name_corpora.json: 3 corpora, ~923 entries total` (250+147+526).

- [ ] **Step 3: Run validator**

Run:
```bash
cd S:/mixoswatch && python scripts/validate_corpora.py
```
Expected: `PASS: 3 corpora, ~923 entries total`. If any FAIL line, fix the underlying glosses/translit data or the build script and re-run.

- [ ] **Step 4: Em-dash check**

Run:
```bash
cd S:/mixoswatch && python -c "import sys; bad=[chr(0x2014),chr(0x2013)]; [print(p) for p in sys.argv[1:] if any(c in open(p,encoding='utf-8').read() for c in bad)]" data/corpora/name_corpora.json
```
Expected: no output (no paths printed). If a path prints, scrub manually.

- [ ] **Step 5: Commit**

```bash
cd S:/mixoswatch && git add scripts/build_corpora.py data/corpora/name_corpora.json
git commit -m "$(cat <<'EOF'
data(corpora): assemble v3 corpora (jp-trad 250 + html 147 + zh-trad 526)

Drops jpn-dic + zh-dic seed corpora (DIC license grey).
Renames jpn -> jp-trad. Validator passes; em-dash count 0.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Loader supports schema v3 + tri-lingual fallback fill

**Files:**
- Modify: `app/mixo-swatch.html` (`loadCorpora` function around line 1166-1200)

- [ ] **Step 1: Replace loadCorpora**

Find `async function loadCorpora()` (around line 1166). Replace with:
```js
async function loadCorpora() {
  _loadCorporaPrefs();
  const r = await fetch('../data/corpora/name_corpora.json');
  const json = await r.json();
  let libs;
  if (Array.isArray(json.corpora))        libs = json.corpora;
  else if (Array.isArray(json.libraries)) libs = json.libraries;
  else                                    libs = [];
  // Promote v2 -> v3 in memory: label string -> {en,ja,zh}, primary/secondary -> fields[]
  for (const lib of libs) {
    if (typeof lib.label === 'string') {
      lib.label = { en: lib.label, ja: lib.label, zh: lib.label };
    }
    if (!Array.isArray(lib.fields)) {
      const f = [];
      if (lib.primary)   f.push({id: lib.primary.field,   label: {en: lib.primary.label   || lib.primary.field, ja:lib.primary.label||lib.primary.field, zh:lib.primary.label||lib.primary.field}});
      if (lib.secondary) f.push({id: lib.secondary.field, label: {en: lib.secondary.label || lib.secondary.field, ja:lib.secondary.label||lib.secondary.field, zh:lib.secondary.label||lib.secondary.field}});
      lib.fields = f.length ? f : [{id:'name', label:{en:'name',ja:'name',zh:'name'}}];
    }
    // Tri-lingual fallback fill: no empty strings in display slots
    for (const e of lib.entries) {
      const fallback = e.romaji || e.pinyin || e.name_ja || e.name_zh || e.name_en || e.name || '?';
      for (const f of ['name_en','name_ja','name_zh']) {
        if (!e[f] || !String(e[f]).trim()) e[f] = fallback;
      }
      _cacheEntryLabs(e);
    }
  }
  CORPORA.libraries = libs;
}
```

- [ ] **Step 2: Smoke-test in browser**

Start dev server, open app, open DevTools console. Run:
```js
CORPORA.libraries.forEach(l => console.log(l.id, l.entries.length, l.entries[0].name_en, l.entries[0].name_ja, l.entries[0].name_zh));
```
Expected: three lines like `jp-trad 250 cherry blossom 桜色 樱花色`, `html 147 aliceblue アリスブルー 爱丽丝蓝`, `zh-trad 526 cinnabar 朱砂 朱砂`.

Confirm no empty strings: `CORPORA.libraries.every(l => l.entries.every(e => e.name_en && e.name_ja && e.name_zh))` -> `true`.

- [ ] **Step 3: Commit**

```bash
cd S:/mixoswatch && git add app/mixo-swatch.html
git commit -m "$(cat <<'EOF'
feat(loader): schema v3 + tri-lingual fallback fill

- Promotes v2 lib.label string -> {en,ja,zh}; primary/secondary -> fields[]
- Fills empty name_en/name_ja/name_zh from translit or native
- Caches dual Lab per entry via _cacheEntryLabs (D50+D65)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Drop hardcoded library IDs (jpn/html) - dynamic `${lib.id}__field` pattern

**Files:**
- Modify: `app/mixo-swatch.html` (multiple sites: `_markClosest`, swatch record access, CSV export, filter helpers)

- [ ] **Step 1: Enumerate all hardcoded references**

Run:
```bash
cd S:/mixoswatch && grep -n "jpn_name\|jpn_closest\|jpn_romaji\|deltaE_jpn\|html_name\|html_closest\|deltaE_html\|_visibleNamedJpn\|_visibleNamedHtml" app/mixo-swatch.html
```
Expected: 15-25 lines. Each must be rewritten.

- [ ] **Step 2: Refactor `_markClosest` to write to dynamic field names**

Find `_markClosest` (around line 1340-1370). Replace with:
```js
function _markClosest(lib) {
  const anchor = _libPref(lib.id).anchor || lib.anchor || 'cmyk';
  // Find single closest swatch per entry; tiebreak on lower TAC, then lower K, then index.
  const bestPerEntry = new Map(); // entry index -> {sIdx, deltaE}
  for (let i=0; i<MAIN_DATA.length; i++) {
    const s = MAIN_DATA[i];
    const sLab = activeLab(s);  // current LAB_MODE
    let bestE = -1, bestD = Infinity;
    for (let j=0; j<lib.entries.length; j++) {
      const eLab = _entryAnchorLab(lib.entries[j], anchor);
      if (!eLab) continue;
      const d = deltaE2000(sLab[0],sLab[1],sLab[2], eLab[0],eLab[1],eLab[2]);
      if (d < bestD) { bestD = d; bestE = j; }
    }
    s[`${lib.id}__deltaE`] = +bestD.toFixed(2);
    s[`${lib.id}__nearestIdx`] = bestE;
    s[`${lib.id}__name`] = bestE >= 0 ? lib.entries[bestE] : null;
    s[`${lib.id}__closest`] = false; // reset; set below
  }
  // For each entry, pick which swatch wears it (closest, tiebreak lower TAC -> lower K -> lower index)
  const claim = new Map();
  for (let i=0; i<MAIN_DATA.length; i++) {
    const s = MAIN_DATA[i];
    const eIdx = s[`${lib.id}__nearestIdx`];
    if (eIdx < 0) continue;
    const d = s[`${lib.id}__deltaE`];
    const cur = claim.get(eIdx);
    if (!cur ||
        d < cur.d ||
        (d === cur.d && s.tac < cur.tac) ||
        (d === cur.d && s.tac === cur.tac && s.K < cur.K)) {
      claim.set(eIdx, {sIdx: i, d, tac: s.tac, K: s.K});
    }
  }
  for (const {sIdx} of claim.values()) {
    MAIN_DATA[sIdx][`${lib.id}__closest`] = true;
  }
}
```

- [ ] **Step 3: Replace _visibleNamedJpn / _visibleNamedHtml with single dynamic helper**

Find both functions (around line 2709-2716). Delete them. Add single helper:
```js
function _visibleNamedFor(s, lib) {
  if (!s[`${lib.id}__closest`]) return false;
  const dE = s[`${lib.id}__deltaE`];
  return typeof dE === 'number' && dE <= curTol;
}
```

- [ ] **Step 4: Replace anyCorpusVisible**

Find `anyCorpusVisible` (likely near `_visibleNamedJpn`). Replace with:
```js
function anyCorpusVisible(s) {
  return CORPORA.libraries.some(lib => _visibleNamedFor(s, lib));
}
```

- [ ] **Step 5: Rewrite CSV export header + row generators**

Find the CSV export block (search for `exportCSV` or the header array around line 2745-2755). Replace fixed columns with dynamic ones:
```js
function _csvHeader() {
  const fixed = ['C','M','Y','K','hex','R','G','B','L_star','a_star','b_star',
                 'tac','luminance','contrast_ratio','wcag_aa','wcag_aaa','k_tier','delta_e_print'];
  const dyn = [];
  for (const lib of CORPORA.libraries) {
    for (const f of lib.fields) dyn.push(`${lib.id}_${f.id}`);
    dyn.push(`${lib.id}_deltaE`);
  }
  return [...fixed, ...dyn];
}
function _csvRow(s) {
  const fixed = [s.C,s.M,s.Y,s.K,s.hex,s.R,s.G,s.B,
                 s.L_star,s.a_star,s.b_star,s.tac,s.luminance,s.contrast_ratio,
                 s.wcag_aa?1:0, s.wcag_aaa?1:0, s.k_tier,
                 s.delta_e_print ?? ''];
  const dyn = [];
  for (const lib of CORPORA.libraries) {
    const entry = s[`${lib.id}__name`];
    for (const f of lib.fields) dyn.push(entry ? (entry[f.id] || '') : '');
    dyn.push(s[`${lib.id}__deltaE`] ?? '');
  }
  return [...fixed, ...dyn];
}
```

Then in the existing `exportCSV` function, replace the header array + row map with calls to `_csvHeader()` + `_csvRow(s)`.

- [ ] **Step 6: Rewrite tooltip / detail panel name lookups**

Search for `jpn_name` or `html_name` in tooltip / detail rendering (around line 2580-2630):
```bash
cd S:/mixoswatch && grep -n "jpn_name\|html_name\|jpn_romaji" app/mixo-swatch.html
```
Replace each with dynamic iteration:
```js
function _renderSwatchNames(s) {
  const out = [];
  for (const lib of CORPORA.libraries) {
    if (!_visibleNamedFor(s, lib)) continue;
    const entry = s[`${lib.id}__name`];
    if (!entry) continue;
    const displayField = _libPref(lib.id).display;
    if (displayField === 'hide') continue;
    const name = entry[displayField] || entry.name_en || '?';
    const dE = s[`${lib.id}__deltaE`];
    out.push({ libId: lib.id, libLabel: lib.label.en, name, dE });
  }
  return out;
}
```
Then call `_renderSwatchNames(s)` wherever the per-corpus name was rendered. The exact HTML emit code depends on the current tooltip structure; preserve existing styling, just swap the data source.

- [ ] **Step 7: Smoke-test app**

Start dev server, open app. Confirm:
- No console errors
- Grid renders
- Tooltip on swatch shows corpus names from all 3 libraries when within tolerance
- CSV export downloads with new columns

- [ ] **Step 8: Commit**

```bash
cd S:/mixoswatch && git add app/mixo-swatch.html
git commit -m "$(cat <<'EOF'
refactor: drop hardcoded library IDs - dynamic field naming

- Swatch records use s[`\${lib.id}__name|closest|deltaE`]
- Single _visibleNamedFor + _renderSwatchNames helpers
- CSV header/row generated from CORPORA.libraries
- _markClosest enforces per-(lib,entry) uniqueness with
  tiebreak: lower tac -> lower K -> lower index

Adding a new corpus to JSON now requires zero code changes.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Per-library display radio (dynamic)

**Files:**
- Modify: `app/mixo-swatch.html` (`buildNamingUI` around line 1383)

- [ ] **Step 1: Rewrite buildNamingUI**

Find `function buildNamingUI()` (around line 1383). Replace with:
```js
function buildNamingUI() {
  const root = document.getElementById('namingPanel');
  if (!root) return;
  root.innerHTML = '';
  if (!CORPORA.libraries.length) { root.textContent = 'No corpora loaded.'; return; }
  for (const lib of CORPORA.libraries) {
    const pref = _libPref(lib.id);
    const div = document.createElement('div');
    div.className = 'corp-card';
    const h = document.createElement('div');
    h.className = 'corp-label';
    h.textContent = `${lib.label.en} (${lib.entries.length})`;
    div.appendChild(h);
    const row = document.createElement('div');
    row.className = 'corp-display-row';
    for (const f of lib.fields) {
      const labelText = f.label.en;
      const lab = document.createElement('label');
      lab.className = 'corp-radio';
      const input = document.createElement('input');
      input.type = 'radio'; input.name = `display-${lib.id}`; input.value = f.id;
      input.checked = (pref.display || lib.default_display) === f.id;
      input.addEventListener('change', () => {
        _setLibPref(lib.id, 'display', f.id);
        refreshGrid();
      });
      lab.append(input, ' ', labelText);
      row.appendChild(lab);
    }
    // Hide option
    const hideLab = document.createElement('label');
    hideLab.className = 'corp-radio';
    const hideIn = document.createElement('input');
    hideIn.type='radio'; hideIn.name=`display-${lib.id}`; hideIn.value='hide';
    hideIn.checked = pref.display === 'hide';
    hideIn.addEventListener('change', () => {
      _setLibPref(lib.id, 'display', 'hide');
      refreshGrid();
    });
    hideLab.append(hideIn, ' hide');
    row.appendChild(hideLab);
    div.appendChild(row);
    root.appendChild(div);
  }
}
```

- [ ] **Step 2: Add namingPanel container to sidebar**

Find the existing "Naming" / corpora UI area in the sidebar. Replace its inner HTML with:
```html
<div class="sec">
  <div class="sec-label">Display name from</div>
  <div id="namingPanel"></div>
</div>
```

- [ ] **Step 3: Add CSS**

```css
.corp-card{border:1px solid var(--border);border-radius:var(--r);padding:8px 10px;margin-bottom:8px}
.corp-label{font-size:11px;font-weight:500;color:var(--text);margin-bottom:5px}
.corp-display-row{display:flex;flex-wrap:wrap;gap:8px;font-size:11px;color:var(--muted)}
.corp-radio{display:flex;align-items:center;gap:3px;cursor:pointer}
```

- [ ] **Step 4: Smoke-test**

Start dev server, open app. Confirm sidebar shows 3 corpus cards. Each card has 4-5 radio options. Picking a different field updates the swatches.

- [ ] **Step 5: Commit**

```bash
cd S:/mixoswatch && git add app/mixo-swatch.html
git commit -m "$(cat <<'EOF'
feat(ui): per-library display radio (dynamic from lib.fields)

Each corpus card lists its fields + a hide option. Adding a
new corpus to JSON now produces a new card automatically.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: Global anchor + tolerance controls (linked, link icon always shown)

**Files:**
- Modify: `app/mixo-swatch.html` (replace existing tolerance slider + add anchor radio)

- [ ] **Step 1: Locate existing tolerance slider**

Find the "Name tolerance" section (around line 639-642). Replace with:
```html
<div class="sec">
  <div class="sec-label">
    <span class="link-badge" title="These controls apply to all libraries.">🔗 Match settings (all libraries)</span>
  </div>
  <div class="match-row">
    <div class="match-label">Anchor</div>
    <label class="match-radio"><input type="radio" name="anchor" value="cmyk" checked onchange="setGlobalAnchor('cmyk')"> CMYK</label>
    <label class="match-radio"><input type="radio" name="anchor" value="hex"  onchange="setGlobalAnchor('hex')"> hex</label>
  </div>
  <div class="match-help">Match by CMYK→Lab (print) or hex→Lab (screen). html corpus falls back to hex when anchor=cmyk.</div>
  <div class="match-row" style="margin-top:6px">
    <div class="match-label">ΔE tol · <span id="vTol">3.0</span></div>
    <input type="range" min="0" max="20" step="0.5" value="3" id="slTol" oninput="onTol(this.value)" title="Show a corpus name when swatch is within this ΔE of a named entry. Affects display only; does not affect underlying math.">
  </div>
  <div class="match-help">Higher = more swatches show names. Set to 0 to show only literal closest matches.</div>
</div>
```

Note: em-dashes and "→" replaced with hyphens. Re-verify:
```bash
cd S:/mixoswatch && python -c "bad=[chr(0x2014),chr(0x2013)]; t=open('app/mixo-swatch.html',encoding='utf-8').read(); print('OK' if not any(c in t for c in bad) else 'FAIL')"
```

If "FAIL": replace any remaining em/en dash with hyphen.

- [ ] **Step 2: Add CSS**

```css
.link-badge{font-size:11px;color:var(--accent);font-weight:500}
.match-row{display:flex;align-items:center;gap:8px;font-size:11px}
.match-label{min-width:60px;color:var(--text)}
.match-radio{display:flex;align-items:center;gap:3px;cursor:pointer;color:var(--muted)}
.match-help{font-size:10px;color:var(--faint);margin-top:3px;line-height:1.4}
```

- [ ] **Step 3: Add setGlobalAnchor handler**

```js
function setGlobalAnchor(v) {
  if (v !== 'cmyk' && v !== 'hex') return;
  CORPORA_PREFS._global = CORPORA_PREFS._global || {};
  CORPORA_PREFS._global.anchor = v;
  // Linked: every library uses this anchor
  for (const lib of CORPORA.libraries) {
    CORPORA_PREFS[lib.id] = Object.assign({}, CORPORA_PREFS[lib.id] || {}, { anchor: v });
  }
  _saveCorporaPrefs();
  for (const lib of CORPORA.libraries) _markClosest(lib);
  refreshGrid();
}
```

- [ ] **Step 4: Update _libPref to read global anchor by default**

```js
function _libPref(libId) {
  const global = (CORPORA_PREFS._global) || { anchor:'cmyk', tolerance:3.0 };
  const lib = CORPORA_PREFS[libId] || {};
  return {
    display: lib.display || (CORPORA.libraries.find(l=>l.id===libId)||{}).default_display || 'name_en',
    anchor:  global.anchor || 'cmyk',
    tolerance: global.tolerance ?? 3.0,
  };
}
```

- [ ] **Step 5: Persist + restore global anchor + tolerance**

In `saveUIState` / `applyUIState`, ensure `CORPORA_PREFS._global.tolerance` is updated when tolerance slider moves. `onTol`:
```js
function onTol(v) {
  curTol = +v;
  document.getElementById('vTol').textContent = curTol.toFixed(1);
  CORPORA_PREFS._global = CORPORA_PREFS._global || {};
  CORPORA_PREFS._global.tolerance = curTol;
  _saveCorporaPrefs();
  refreshGrid();
}
```

In `applyUIState`, after loading state:
```js
if (CORPORA_PREFS._global) {
  if (typeof CORPORA_PREFS._global.tolerance === 'number') {
    curTol = CORPORA_PREFS._global.tolerance;
    if ($('slTol')) $('slTol').value = curTol;
    if ($('vTol'))  $('vTol').textContent = curTol.toFixed(1);
  }
  if (CORPORA_PREFS._global.anchor) {
    document.querySelectorAll('input[name="anchor"]').forEach(r => {
      r.checked = (r.value === CORPORA_PREFS._global.anchor);
    });
  }
}
```

- [ ] **Step 6: Smoke-test**

Start dev server, open app. Confirm:
- "Match settings (all libraries)" section visible with link icon
- Flip anchor cmyk <-> hex; corpus matches update
- Move ΔE tol slider; visible names expand/contract

- [ ] **Step 7: Commit**

```bash
cd S:/mixoswatch && git add app/mixo-swatch.html
git commit -m "$(cat <<'EOF'
feat(ui): global anchor + dE tolerance with link badge

Single anchor radio + single tolerance slider govern all
libraries (linked). _libPref returns global values for anchor
+ tolerance; per-library display radio kept independent.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: Per-profile TAC defaults in luts/index.json

**Files:**
- Modify: `data/luts/index.json`
- Modify: `scripts/gen_luts.py` (label/manifest generator)

- [ ] **Step 1: Inspect current luts/index.json structure**

Run:
```bash
cd S:/mixoswatch && python -m json.tool data/luts/index.json | head -30
```

- [ ] **Step 2: Add tac_recommended + tac_max + paper to each entry**

Update `scripts/gen_luts.py` to write these fields. Find the manifest entry block (line ~255-262) and replace with:
```python
# TAC defaults per profile family (per proof.de + Cummings TAC reference)
TAC_TABLE = {
    "CoatedFOGRA39":           {"rec": 330, "max": 350, "paper": "coated"},
    "CoatedFOGRA27":           {"rec": 320, "max": 340, "paper": "coated"},
    "UncoatedFOGRA29":         {"rec": 260, "max": 290, "paper": "uncoated"},
    "WebCoatedFOGRA28":        {"rec": 300, "max": 320, "paper": "coated-web"},
    "JapanColor2001Coated":    {"rec": 350, "max": 350, "paper": "coated"},
    "JapanColor2001Uncoated":  {"rec": 260, "max": 290, "paper": "uncoated"},
    "JapanColor2002Newspaper": {"rec": 240, "max": 260, "paper": "newsprint"},
    "JapanWebCoated":          {"rec": 300, "max": 320, "paper": "coated-web"},
    "USSheetfedCoated":        {"rec": 320, "max": 340, "paper": "coated"},
    "USSheetfedUncoated":      {"rec": 260, "max": 290, "paper": "uncoated"},
    "USWebCoatedSWOP":         {"rec": 300, "max": 320, "paper": "coated-web"},
    "USWebUncoated":           {"rec": 260, "max": 290, "paper": "uncoated"},
}
# in the manifest-entry block:
stem = icc.stem
tac_info = TAC_TABLE.get(stem, {"rec": 300, "max": 320, "paper": "unknown"})
entry = {
    "filename":   icc.name,
    "label":      label,
    "tier_index": tier_index,
    "tac_recommended": tac_info["rec"],
    "tac_max":         tac_info["max"],
    "paper":           tac_info["paper"],
    "lut":        f"data/luts/{lut_name}",
    "rlut":       f"data/luts/{rlut_name}" if rlut_path and rlut_path.exists() else None,
}
```

- [ ] **Step 3: Regenerate luts/index.json**

Run:
```bash
cd S:/mixoswatch && python scripts/gen_luts.py
```
Expected: manifest rebuilds with new fields. If icc/ dir is empty (gitignored), use a manual edit instead:
```bash
cd S:/mixoswatch && python -c "
import json
from pathlib import Path
TAC = {
  'CoatedFOGRA39':           (330,350,'coated'),
  'CoatedFOGRA27':           (320,340,'coated'),
  'UncoatedFOGRA29':         (260,290,'uncoated'),
  'WebCoatedFOGRA28':        (300,320,'coated-web'),
  'JapanColor2001Coated':    (350,350,'coated'),
  'JapanColor2001Uncoated':  (260,290,'uncoated'),
  'JapanColor2002Newspaper': (240,260,'newsprint'),
  'JapanWebCoated':          (300,320,'coated-web'),
  'USSheetfedCoated':        (320,340,'coated'),
  'USSheetfedUncoated':      (260,290,'uncoated'),
  'USWebCoatedSWOP':         (300,320,'coated-web'),
  'USWebUncoated':           (260,290,'uncoated'),
}
p = Path('data/luts/index.json')
data = json.loads(p.read_text(encoding='utf-8'))
for e in data.get('luts', data.get('profiles', [])):
  stem = Path(e.get('filename', e.get('lut',''))).stem.replace('.lut','')
  if stem in TAC:
    e['tac_recommended'], e['tac_max'], e['paper'] = TAC[stem]
p.write_text(json.dumps(data, indent=2), encoding='utf-8')
print('Updated index.json')
"
```

- [ ] **Step 4: Inspect updated index.json**

Run:
```bash
cd S:/mixoswatch && python -m json.tool data/luts/index.json | head -20
```
Expected: each profile entry has tac_recommended, tac_max, paper.

- [ ] **Step 5: Commit**

```bash
cd S:/mixoswatch && git add data/luts/index.json scripts/gen_luts.py
git commit -m "$(cat <<'EOF'
data(luts): per-profile tac_recommended + tac_max + paper

Sources: proof.de profile reference + Cummings TAC notes.
FOGRA39=330, JapanColor2001 Coated=350, SWOP=300, etc.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 16: Profile-aware TAC + quick-preset buttons + 3D-print preset

**Files:**
- Modify: `app/mixo-swatch.html` (TAC slider area around line 590, profile change handler)

- [ ] **Step 1: Replace TAC section markup**

Find the "TAC limit" section (around line 590-593). Replace with:
```html
<div class="sec">
  <div class="sec-label">
    TAC limit · <span id="vTAC">240</span>% / max <span id="vTACMax">400</span>%
    <span class="user-override-badge" id="tacOverride" style="display:none" title="You manually set TAC. Click 'Snap to profile recommended' to reset.">user override</span>
  </div>
  <input type="range" min="0" max="400" value="240" step="10" id="slTAC" oninput="onTACInput()" title="Total ink limit (C+M+Y+K %). Real presses usually handle 240-330 depending on paper.">
  <div class="tac-presets">
    <button class="preset-btn" onclick="setTACPreset(240,'Newspaper')" title="Newspaper / newsprint">240</button>
    <button class="preset-btn" onclick="setTACPreset(260,'Uncoated')" title="Uncoated office paper">260</button>
    <button class="preset-btn" onclick="setTACPreset(300,'SWOP')" title="SWOP coated, web offset">300</button>
    <button class="preset-btn" onclick="setTACPreset(330,'FOGRA39')" title="Coated FOGRA39 sheetfed">330</button>
    <button class="preset-btn" onclick="setTACPreset(350,'JapanColor')" title="Japan Color 2001 coated">350</button>
    <button class="preset-btn" onclick="setTACPreset(220,'3D-print')" title="3D color print (PolyJet / MJF) - low TAC, clean voxel mix">220</button>
  </div>
  <div class="match-row" style="margin-top:8px">
    <label class="match-radio">
      <input type="checkbox" id="tog3D" onchange="set3DPreset(this.checked)" title="Snap TAC<=240, ΔE max<=3, hide unreliable swatches. One-click safe palette for 3D color printers.">
      3D-print preset (TAC<=240, ΔE max<=3)
    </label>
  </div>
</div>
```

- [ ] **Step 2: Add CSS for TAC presets**

```css
.tac-presets{display:flex;gap:4px;margin-top:5px;flex-wrap:wrap}
.tac-presets .preset-btn{font-size:10px;padding:3px 8px;border:1px solid var(--border);background:transparent;color:var(--muted);border-radius:var(--r);cursor:pointer}
.tac-presets .preset-btn:hover{background:var(--bg2);color:var(--text)}
.user-override-badge{font-size:9px;color:var(--accent);background:rgba(91,163,255,.15);padding:2px 5px;border-radius:3px;margin-left:5px}
```

- [ ] **Step 3: Add handlers**

```js
let TAC_USER_OVERRIDE = false;
const TAC_DEFAULT_OLD = 240; // current behavior baseline

function onTACInput() {
  TAC_USER_OVERRIDE = true;
  document.getElementById('tacOverride').style.display = 'inline-block';
  document.getElementById('vTAC').textContent = document.getElementById('slTAC').value;
  onFilter();
}
function setTACPreset(value, label) {
  TAC_USER_OVERRIDE = true;  // explicit preset counts as user choice
  const sl = document.getElementById('slTAC');
  sl.value = value;
  document.getElementById('vTAC').textContent = value;
  document.getElementById('tacOverride').style.display = 'none';
  onFilter();
}
function snapTACToProfile() {
  const lut = ACTIVE_LUT_META;
  if (!lut || typeof lut.tac_recommended !== 'number') return;
  if (TAC_USER_OVERRIDE) return; // respect user choice
  const sl = document.getElementById('slTAC');
  sl.value = lut.tac_recommended;
  sl.max   = lut.tac_max || 400;
  document.getElementById('vTAC').textContent    = sl.value;
  document.getElementById('vTACMax').textContent = sl.max;
}
function set3DPreset(on) {
  if (!on) return;
  const slTAC = document.getElementById('slTAC');
  if (+slTAC.value > 240) { slTAC.value = 240; document.getElementById('vTAC').textContent = '240'; }
  const slDEmax = document.getElementById('slDEmax');
  // slDEmax raw 0-100 -> divided by 10 = 0-10. 3 effective = raw 30.
  if (+slDEmax.value > 30) slDEmax.value = 30;
  TAC_USER_OVERRIDE = true;
  document.getElementById('tacOverride').style.display = 'inline-block';
  onFilter();
}
```

- [ ] **Step 4: Wire profile-change to snapTACToProfile**

Find the existing profile-change handler (`onProfileChange` or similar). After it loads the new LUT, call:
```js
ACTIVE_LUT_META = LUT_INDEX.luts.find(l => l.filename === selected) || null;
snapTACToProfile();
```

- [ ] **Step 5: Smoke-test**

Start dev server, open app. Confirm:
- Click each TAC preset; slider snaps + grid filters
- Toggle profile dropdown; TAC slider snaps to that profile's recommended (assuming not in user-override state)
- Move TAC slider manually; "user override" badge appears
- Check 3D-print preset checkbox; TAC drops to 240, ΔE max drops to 3, grid filters tighter

- [ ] **Step 6: Commit**

```bash
cd S:/mixoswatch && git add app/mixo-swatch.html
git commit -m "$(cat <<'EOF'
feat(ui): profile-aware TAC + quick presets + 3D-print preset

- Each profile carries tac_recommended + tac_max (from index.json)
- TAC slider snaps to profile recommended on profile change
  unless user has manually overridden (badge shown)
- 6 preset buttons (Newspaper 240 ... JapanColor 350 ... 3D-print 220)
- 3D-print checkbox: snaps TAC<=240, dE max<=3 in one click

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 17: Move Hue x Light into Sort by row

**Files:**
- Modify: `app/mixo-swatch.html` (topbar mode-group at line 437, sort-btns block at line 697-704, `setSort` and `setViewMode` handlers)

- [ ] **Step 1: Remove Hue x Light from topbar mode-group**

Find line 437. Replace the `mode-group` block:
```html
<div class="mode-group" id="modeGroup" role="tablist" aria-label="View mode">
  <button class="btn mode-btn active" id="mode-grid"     onclick="setViewMode('grid')" title="Regular swatch grid - every filtered swatch as a cell.">Grid</button>
  <button class="btn mode-btn"        id="mode-palettes" onclick="setViewMode('palettes')" title="Palettes mode - manage all saved palettes with per-palette actions.">Palettes</button>
</div>
```

(Removed the `mode-huelight` button.)

- [ ] **Step 2: Add Hue x Light button to sort-btns**

Find the sort-btns block (around line 697-704). Add a 7th button:
```html
<div class="sort-btns">
  <button class="btn sort-btn active" id="sort-hue"  onclick="setSort('hue')" title="Order by color hue.">Hue</button>
  <button class="btn sort-btn" id="sort-L"    onclick="setSort('L')" title="Order by lightness, dark - light.">Light</button>
  <button class="btn sort-btn" id="sort-tac"  onclick="setSort('tac')" title="Order by total ink load.">TAC</button>
  <button class="btn sort-btn" id="sort-C"      onclick="setSort('C')" title="Order by Cyan ink % only.">Cyan</button>
  <button class="btn sort-btn" id="sort-chroma" onclick="setSort('chroma')" title="Order by saturation.">Chroma</button>
  <button class="btn sort-btn" id="sort-safety" onclick="setSort('safety')" title="Order by round-trip reliability.">Safety</button>
  <button class="btn sort-btn" id="sort-huelight" onclick="setSort('huelight')" title="2D map: one representative cell per (hue, lightness) bucket.">Hue x Light</button>
</div>
```

- [ ] **Step 3: Update setSort to dispatch huelight as a view mode**

Find `setSort` (around line 2735). Replace the whole function with:
```js
function setSort(m) {
  // Hue x Light is a view-mode masquerading as a sort.
  if (m === 'huelight') {
    setViewMode('huelight');
    document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('sort-huelight')?.classList.add('active');
    return;
  }
  // Any other sort returns view to grid
  if (viewMode === 'huelight') setViewMode('grid');
  sortMode = m;
  document.querySelectorAll('.sort-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('sort-'+m).classList.add('active');
  _scheduleRender();
}
```

- [ ] **Step 4: Update setViewMode to clear sort-huelight active class when leaving**

```js
function setViewMode(m) {
  if (!['grid','huelight','palettes'].includes(m)) return;
  viewMode = m;
  saveUIState();
  ['grid','palettes'].forEach(k => {
    document.getElementById('mode-'+k)?.classList.toggle('active', viewMode === k);
  });
  if (m !== 'huelight') {
    document.getElementById('sort-huelight')?.classList.remove('active');
  }
  paletteMode = (viewMode === 'palettes');
  refreshGrid();
}
```

- [ ] **Step 5: Smoke-test**

Start dev server, open app. Confirm:
- Topbar shows only [Grid] [Palettes]
- Sort by row has 7 buttons including "Hue x Light"
- Click "Hue x Light"; grid switches to hue-light map; other sort buttons deactivate
- Click any other sort button; grid returns to regular grid view

- [ ] **Step 6: Commit**

```bash
cd S:/mixoswatch && git add app/mixo-swatch.html
git commit -m "$(cat <<'EOF'
ui: move Hue x Light from topbar mode-group into Sort by row

Hue x Light is conceptually a sort+collapse, not a distinct view
mode. Mode-group shrinks to [Grid] [Palettes]. Switching to any
other sort returns view to regular grid.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 18: Collapsable Palettes panel above grid

**Files:**
- Modify: `app/mixo-swatch.html` (delete sidebar palette block lines 465-510, add new panel structure, move pm-wrap)

- [ ] **Step 1: Add panel CSS**

In `<style>` add:
```css
.palette-panel{
  border-bottom:1px solid var(--border);background:var(--surface);
  display:flex;flex-direction:column;
}
.palette-panel-header{
  display:flex;align-items:center;justify-content:space-between;
  padding:8px 16px;cursor:pointer;font-size:12px;color:var(--text);
  user-select:none;border-bottom:1px solid transparent;
}
.palette-panel-header:hover{background:var(--bg2)}
.palette-panel-header .chev{transition:transform .15s}
.palette-panel.open .palette-panel-header{border-bottom-color:var(--border)}
.palette-panel.open .palette-panel-header .chev{transform:rotate(90deg)}
.palette-panel-body{display:none;padding:10px 16px;gap:10px;flex-direction:column;max-height:50vh;overflow:auto}
.palette-panel.open .palette-panel-body{display:flex}
```

- [ ] **Step 2: Insert panel above grid-area**

Find the layout (line 55: `<div class="main">...`). Restructure grid-area:
```html
<div class="grid-area">
  <div class="palette-panel" id="palettePanel">
    <div class="palette-panel-header" onclick="togglePalettePanel()">
      <span><span class="chev">▶</span> Palettes</span>
      <span class="pal-count" id="palCount">0</span>
    </div>
    <div class="palette-panel-body" id="palettePanelBody">
      <!-- moved from sidebar -->
    </div>
  </div>
  <div class="grid-scroll" id="gridScroll">
    <div class="swatch-grid" id="swatchGrid"></div>
    <div class="gs-wrap" id="gsWrap">...</div>
    <!-- pm-wrap MOVED OUT of grid-scroll -->
  </div>
</div>
```

- [ ] **Step 3: Migrate sidebar palette block to panel body**

Cut the sidebar block (lines 465-510, the `<!-- Palettes -->` div including all its rows). Paste into `<div id="palettePanelBody">`. Also move `<div class="pm-wrap" id="pmWrap" style="display:none">` from inside `grid-scroll` to inside `palettePanelBody` (at the end).

- [ ] **Step 4: Update onPalChange / select-mode rendering to use panel ids**

Confirm the `palCount` id is unique (it is - the inside-body one was deleted in the move). Same for `palSel`, `palStrip`, `palPngSize`. No JS changes needed if all IDs preserved.

- [ ] **Step 5: Add togglePalettePanel handler**

```js
function togglePalettePanel() {
  const panel = document.getElementById('palettePanel');
  const open = panel.classList.toggle('open');
  try { localStorage.setItem('palette_panel_open', open ? '1' : '0'); } catch {}
}
// Restore state at boot:
function restorePalettePanelState() {
  const v = localStorage.getItem('palette_panel_open');
  if (v === '1') document.getElementById('palettePanel').classList.add('open');
}
```

Call `restorePalettePanelState()` from app init (after `applyUIState`).

- [ ] **Step 6: Update renderPaletteMode to auto-open panel**

The `renderPaletteMode` function (around line 1865) keeps targeting `#pmWrap` since pmWrap moved into the panel body. Add a single line at the top to auto-open the panel when entering palettes view:
```js
function renderPaletteMode() {
  document.getElementById('palettePanel').classList.add('open');  // NEW
  const wrap = document.getElementById('pmWrap');
  wrap.innerHTML = '';
  // ... rest of existing function body unchanged (palette grid render logic).
  // Do NOT modify the rest; just insert the classList.add('open') as the new first line.
}
```

- [ ] **Step 7: Smoke-test**

Start dev server, open app. Confirm:
- Sidebar no longer has Palettes section
- A new "Palettes" header bar sits above the grid
- Click header; chevron rotates, body expands showing palette selector + buttons + strip + exports
- Click "Palettes" in topbar mode-group; body auto-opens, pm-wrap renders palettes-mode grid inside body
- Reload; collapsed state persists

- [ ] **Step 8: Commit**

```bash
cd S:/mixoswatch && git add app/mixo-swatch.html
git commit -m "$(cat <<'EOF'
ui: collapsable Palettes panel above grid (sidebar block + pm-wrap merged)

Sidebar Palettes section deleted. New panel sits between topbar
and grid-scroll: collapsed by default, click header to expand.
pm-wrap (palettes-view grid) moved inside panel body. Open state
persisted to localStorage.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 19: Per-swatch ZIP exporter (top-level for filtered swatches)

**Files:**
- Modify: `app/mixo-swatch.html` (add top-level export button + handler)

- [ ] **Step 1: Locate the existing per-palette ZIP exporter**

Find `exportActivePaletteZIP` (line ~495 onClick reference). Inspect its body:
```bash
cd S:/mixoswatch && grep -n "exportActivePaletteZIP\|function.*PaletteZIP\|JSZip" app/mixo-swatch.html | head -10
```

- [ ] **Step 2: Extract ZIP-build logic into reusable worker**

Refactor: pull the body of `exportActivePaletteZIP` into a new function `_buildSwatchZip(swatches, zipName)`. Modify `exportActivePaletteZIP` to call `_buildSwatchZip(activePaletteSwatches, paletteName)`.

```js
async function _buildSwatchZip(swatches, zipName) {
  const zip = new JSZip();
  const manifestRows = [];
  for (const s of swatches) {
    // Generate 128x128 pure-color PNG
    const canvas = document.createElement('canvas');
    canvas.width = 128; canvas.height = 128;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = s.hex; ctx.fillRect(0,0,128,128);
    const blob = await new Promise(r => canvas.toBlob(r, 'image/png'));
    const filename = `${s.hex.slice(1)}_C${s.C}M${s.M}Y${s.Y}K${s.K}.png`;
    zip.file(filename, blob);
    // Manifest entry
    const row = { filename, hex: s.hex, C: s.C, M: s.M, Y: s.Y, K: s.K,
                  R: s.R, G: s.G, B: s.B,
                  L: s.L_star, a: s.a_star, b: s.b_star,
                  delta_e_print: s.delta_e_print ?? null };
    for (const lib of CORPORA.libraries) {
      const entry = s[`${lib.id}__name`];
      row[`${lib.id}_name_en`] = entry?.name_en || '';
      row[`${lib.id}_deltaE`]  = s[`${lib.id}__deltaE`] ?? '';
    }
    manifestRows.push(row);
  }
  // Manifest as CSV + JSON
  const headers = Object.keys(manifestRows[0] || {});
  const csv = [headers.join(','), ...manifestRows.map(r =>
    headers.map(h => JSON.stringify(r[h] ?? '')).join(','))].join('\n');
  zip.file('manifest.csv', csv);
  zip.file('manifest.json', JSON.stringify(manifestRows, null, 2));
  const blob = await zip.generateAsync({ type: 'blob' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${zipName}.zip`;
  a.click();
  URL.revokeObjectURL(a.href);
}
```

- [ ] **Step 3: Add top-level filtered-swatch exporter**

```js
async function exportFilteredSwatchZIP() {
  const swatches = filtered();
  if (!swatches.length) { alert('No swatches in current filter.'); return; }
  if (swatches.length > 5000) {
    const mb = (swatches.length * 0.6 / 1024).toFixed(0);
    if (!confirm(`You're about to download ${swatches.length} swatches as individual PNGs (~${mb} MB ZIP). Continue?`)) return;
  }
  await _buildSwatchZip(swatches, `mixo-swatch-filtered-${swatches.length}`);
}
```

- [ ] **Step 4: Add top-level button**

Find the topbar export buttons (line 438-439, the existing CSV + PNG buttons). Add a third:
```html
<button class="btn" onclick="exportFilteredSwatchZIP()" title="Download a .zip with one 128x128 pure-color PNG per currently-filtered swatch plus manifest.csv/json.">↓ ZIP (per-swatch)</button>
```

- [ ] **Step 5: Smoke-test**

Start dev server, open app. Filter to a small set (~30 swatches via CMYK range sliders). Click "ZIP (per-swatch)". Confirm download: `mixo-swatch-filtered-30.zip` containing 30 PNGs + manifest.csv + manifest.json. Open a PNG; verify pure color 128x128.

Then filter to full grid (~14k). Click button. Confirm confirmation dialog appears.

- [ ] **Step 6: Commit**

```bash
cd S:/mixoswatch && git add app/mixo-swatch.html
git commit -m "$(cat <<'EOF'
feat(export): top-level per-swatch ZIP for filtered swatches

Mirrors per-palette ZIP exporter but on filtered() set.
128x128 pure-color PNGs + manifest.csv/json. Confirmation
dialog when count > 5000. Shared _buildSwatchZip worker.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 20: Dark-only theme lock

**Files:**
- Modify: `app/mixo-swatch.html` (CSS at top, around line 18-25)

- [ ] **Step 1: Delete light-mode media query**

Find the block:
```css
@media (prefers-color-scheme:light){:root{
  --bg:#F5F4F0; --bg2:#EEEDEA; --surface:#FFFFFF;
  --border:rgba(0,0,0,0.12); --border2:rgba(0,0,0,0.06);
  --text:#1C1B18; --muted:#6B6A65; --faint:#9B9A95; --accent:#2867AE;
  color-scheme:light;
}}
```

Delete entirely. Update the `:root` block above to ship final dark palette:
```css
:root{
  --font-mono:'IBM Plex Mono','Fira Mono',monospace;
  --font-sans:'Noto Sans JP',system-ui,sans-serif;
  --r:6px; --rl:10px;
  color-scheme:dark;
  --bg:#0E0E0F; --bg2:#1A1A1C; --surface:#16161A;
  --border:rgba(255,255,255,.10); --border2:rgba(255,255,255,.05);
  --text:#F2F2EF; --muted:#9B9A95; --faint:#6B6A65; --accent:#5BA3FF;
}
```

- [ ] **Step 2: Smoke-test**

Start dev server, open app. Switch OS to light mode (Windows: Settings -> Personalization -> Colors). Reload app. Confirm app stays dark; no light-mode flash.

- [ ] **Step 3: Commit**

```bash
cd S:/mixoswatch && git add app/mixo-swatch.html
git commit -m "$(cat <<'EOF'
ui: lock dark mode (drop light-mode media query)

Surrounding luminance bias affects color picking accuracy.
Dark is the right mode for this tool regardless of OS pref.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 21: Responsive breakpoints + sidebar drawer

**Files:**
- Modify: `app/mixo-swatch.html` (CSS + topbar hamburger + sidebar toggle)

- [ ] **Step 1: Add hamburger button to topbar**

Find topbar (line 31-37). Add at left of topbar (before topbar-title):
```html
<button class="hamburger-btn" id="hamburger" onclick="toggleSidebar()" aria-label="Toggle sidebar" title="Show / hide sidebar (mobile)">☰</button>
```

- [ ] **Step 2: Add CSS**

```css
.hamburger-btn{
  display:none;background:transparent;border:0;color:var(--text);
  font-size:18px;cursor:pointer;padding:4px 8px;
}
@media (max-width: 1023px) { .main { grid-template-columns: 220px 1fr; } }
@media (max-width: 767px) {
  .main { grid-template-columns: 1fr; }
  .sidebar {
    position: fixed; top: 52px; left: -100%; bottom: 0; width: 280px;
    transition: left .2s; z-index: 25; box-shadow: 0 0 20px rgba(0,0,0,.5);
  }
  .sidebar.open { left: 0; }
  .hamburger-btn { display: inline-flex; }
  .swatch-cell { min-width: 36px; min-height: 36px; }
  .topbar { gap: 6px; padding: 0 10px; }
  .lab-mode-badge { display: none; }  /* badge text too long on mobile; still visible in sidebar */
}
@media (max-width: 479px) {
  .swatch-cell { min-width: 32px; min-height: 32px; }
  .detail-panel { width: 100% !important; max-width: 100% !important; }
}
/* Touch targets >= 44px on mobile */
@media (max-width: 767px) {
  .btn, .sort-btn, .pill, .preset-btn, .mode-btn {
    min-height: 44px;
  }
}
```

- [ ] **Step 3: Add toggleSidebar handler**

```js
function toggleSidebar() {
  document.querySelector('.sidebar').classList.toggle('open');
}
// Close sidebar when clicking outside it (mobile only)
document.addEventListener('click', (e) => {
  if (window.innerWidth > 767) return;
  const sb = document.querySelector('.sidebar');
  const hb = document.getElementById('hamburger');
  if (sb.classList.contains('open') && !sb.contains(e.target) && e.target !== hb) {
    sb.classList.remove('open');
  }
});
```

- [ ] **Step 4: Smoke-test**

Start dev server, open app. Use Chrome DevTools responsive mode:
- Set width to 1024: sidebar 260px. Sort buttons visible. No hamburger.
- Set width to 900: sidebar 220px. Hamburger hidden still.
- Set width to 700: hamburger visible, sidebar slides off screen by default. Click hamburger; sidebar slides in.
- Set width to 400: cells shrink to 32px min. Detail panel goes full-width.
- Touch targets >= 44px on buttons (inspect height).

- [ ] **Step 5: Commit**

```bash
cd S:/mixoswatch && git add app/mixo-swatch.html
git commit -m "$(cat <<'EOF'
ui: responsive breakpoints 1024 / 768 / 480 + sidebar drawer

Mobile (< 768): sidebar becomes slide-over drawer behind
hamburger. Touch targets >= 44px on all controls. Detail
panel goes full-width on < 480.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 22: ui_defaults.json additions

**Files:**
- Modify: `data/ui_defaults.json`

- [ ] **Step 1: Add new fields**

Update `data/ui_defaults.json` to:
```json
{
  "format": "swatch.ui_defaults/v1",
  "_doc": "First-run + Reset-to-defaults source of truth for the browser tool.",

  "cmyk_explorer": {
    "step": 10,
    "cell_size": 48,
    "view_mode": "grid",
    "sort_mode": "hue",
    "k_tier": 3,
    "named_filter": "all",
    "wcag_aa": false,
    "wcag_aaa": false,
    "white_text_only": false,
    "black_text_only": false,
    "search": "",
    "cmyk_range": { "c": [0,100], "m": [0,100], "y": [0,100], "k": [0,100] },
    "tac_max": 240,
    "delta_e_max": null,
    "default_profile_match": "FOGRA39",
    "active_palette_id": null,

    "lab_mode": "d50",
    "gamut_safe_only": false,
    "palette_panel_open": false,

    "corpora_prefs": {
      "_global": { "anchor": "cmyk", "tolerance": 3.0 },
      "jp-trad": { "display": "name_ja" },
      "html":    { "display": "name_en" },
      "zh-trad": { "display": "name_zh" }
    }
  }
}
```

- [ ] **Step 2: Commit**

```bash
cd S:/mixoswatch && git add data/ui_defaults.json
git commit -m "$(cat <<'EOF'
data(ui_defaults): add lab_mode, gamut_safe_only, palette_panel_open

corpora_prefs reshaped to {_global, [lib.id]} with global
anchor + tolerance defaults. jpn -> jp-trad rename; jpn-dic
and zh-dic removed (corpora dropped).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 23: localStorage v1 -> v2 migration

**Files:**
- Modify: `app/mixo-swatch.html` (around `applyUIState` / boot init)

- [ ] **Step 1: Add migration function**

Find `applyUIState` (around line 850). Above it, add:
```js
function _migrate_v1_to_v2(v1) {
  const out = { ...v1 };
  // Add new fields with defaults
  if (typeof out.lab_mode !== 'string')        out.lab_mode = 'd50';
  if (typeof out.gamut_safe_only !== 'boolean') out.gamut_safe_only = false;
  if (typeof out.palette_panel_open !== 'boolean') out.palette_panel_open = false;
  // Rewrite corpora_prefs
  const oldPrefs = out.corpora_prefs || {};
  const newPrefs = {
    _global: { anchor: 'cmyk', tolerance: 3.0 },
    'jp-trad': { display: oldPrefs.jpn?.display || 'name_ja' },
    'html':    { display: oldPrefs.html?.display || 'name_en' },
    'zh-trad': { display: 'name_zh' },
  };
  if (oldPrefs.jpn?.anchor)  newPrefs._global.anchor = oldPrefs.jpn.anchor;
  if (typeof out.name_tolerance === 'number') newPrefs._global.tolerance = out.name_tolerance;
  out.corpora_prefs = newPrefs;
  // Discard dropped corpora prefs
  delete out.jpn_dic_prefs;
  return out;
}
```

- [ ] **Step 2: Update boot init to check v2 first, fall back to v1 migration**

Find where the state is loaded (search for `cmykUIState_v1`):
```bash
cd S:/mixoswatch && grep -n "cmykUIState_v1\|cmykUIState" app/mixo-swatch.html
```

Replace the load with:
```js
function _loadUIState() {
  const v2 = localStorage.getItem('cmykUIState_v2');
  if (v2) {
    try { return JSON.parse(v2); } catch {}
  }
  const v1 = localStorage.getItem('cmykUIState_v1');
  if (v1) {
    try {
      const migrated = _migrate_v1_to_v2(JSON.parse(v1));
      localStorage.setItem('cmykUIState_v2', JSON.stringify(migrated));
      return migrated;
    } catch {}
  }
  return null;
}
function saveUIState() {
  const state = {
    step: curStep, cell_size: curCell, view_mode: viewMode,
    sort_mode: curSort, k_tier: curKTier, named_filter: curNamed,
    cmyk_range: { c:[+$('slCmn').value, +$('slCmx').value],
                  m:[+$('slMmn').value, +$('slMmx').value],
                  y:[+$('slYmn').value, +$('slYmx').value],
                  k:[+$('slKmn').value, +$('slKmx').value] },
    tac_max: +$('slTAC').value,
    delta_e_max: +$('slDEmax').value,
    default_profile_match: ACTIVE_LUT_FILE || null,
    lab_mode: LAB_MODE,
    palette_panel_open: document.getElementById('palettePanel')?.classList.contains('open') || false,
  };
  try { localStorage.setItem('cmykUIState_v2', JSON.stringify(state)); } catch {}
}
```

Note: `cmykUIState_v1` key is preserved (not deleted) so users can downgrade if needed. Delete in a future release.

- [ ] **Step 3: Update applyUIState entrypoint**

Find `applyUIState(s)` (around line 846). Add a guard for null + insert two new field restores. Locate the line `if (typeof s.name_tolerance === 'number') curTol    = s.name_tolerance;` (around line 854) and modify the function to:
```js
function applyUIState(s) {
  if (!s) return;  // null = first-run; defaults applied elsewhere
  const $ = id => document.getElementById(id);
  if (typeof s.step           === 'number') curStep   = s.step;
  if (typeof s.cell_size      === 'number') curCell   = s.cell_size;
  if (typeof s.view_mode      === 'string') viewMode  = s.view_mode;
  if (typeof s.sort_mode      === 'string') sortMode  = s.sort_mode;
  if (typeof s.k_tier         === 'number') curKTier  = s.k_tier;
  if (typeof s.named_filter   === 'string') curNamed  = s.named_filter;
  if (typeof s.lab_mode       === 'string' && (s.lab_mode==='d50'||s.lab_mode==='d65')) LAB_MODE = s.lab_mode;
  // ... preserve the rest of the original function body (sliders, toggles,
  // pills, corpora_prefs hookup) exactly as it currently exists from line
  // 855 onward. Do not delete the existing lines; just add the lab_mode
  // restore line above and the !s guard at the top.
}
```

Also restore palette panel open state in the same function:
```js
  if (s.palette_panel_open === true) {
    document.getElementById('palettePanel')?.classList.add('open');
  }
```

- [ ] **Step 4: Verify migration manually**

Open the app once normally to write v1 state. Then in DevTools console:
```js
const oldV1 = {
  step:10, cell_size:48, view_mode:'grid', sort_mode:'hue',
  k_tier:3, named_filter:'all', name_tolerance:5,
  corpora_prefs: { jpn:{display:'romaji',anchor:'hex'}, html:{display:'name'} },
};
localStorage.removeItem('cmykUIState_v2');
localStorage.setItem('cmykUIState_v1', JSON.stringify(oldV1));
location.reload();
```

After reload, in console:
```js
JSON.parse(localStorage.getItem('cmykUIState_v2'))
```
Expected: object with `lab_mode:'d50'`, `corpora_prefs._global.anchor:'hex'` (migrated from old jpn.anchor), `corpora_prefs._global.tolerance:5` (migrated from name_tolerance), `corpora_prefs['jp-trad'].display:'romaji'` (mapped from jpn.display).

- [ ] **Step 5: Commit**

```bash
cd S:/mixoswatch && git add app/mixo-swatch.html
git commit -m "$(cat <<'EOF'
feat(state): cmykUIState_v1 -> v2 one-time migration

Reads v2 first, falls back to v1 + transforms (jpn -> jp-trad,
name_tolerance -> _global.tolerance, anchor inherits old jpn.anchor).
v1 key kept on disk for downgrade safety.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 24: Final verification pass

**Files:**
- All test artefacts

- [ ] **Step 1: Run corpora validator**

```bash
cd S:/mixoswatch && python scripts/validate_corpora.py
```
Expected: `PASS: 3 corpora, ~923 entries total`.

- [ ] **Step 2: Run em-dash compliance check**

```bash
cd S:/mixoswatch && python -c "
import sys
bad = [chr(0x2014), chr(0x2013)]
files = ['app/mixo-swatch.html', 'data/corpora/name_corpora.json', 'data/ui_defaults.json', 'data/luts/index.json']
fails = []
for p in files:
  t = open(p,encoding='utf-8').read()
  if any(c in t for c in bad):
    fails.append(p)
if fails:
  print('FAIL:', fails); sys.exit(1)
print('PASS: 0 em-dash / en-dash')
"
```
Expected: `PASS: 0 em-dash / en-dash`.

- [ ] **Step 3: Run color math test page**

```bash
cd S:/mixoswatch && python -m http.server 8765 &
```
Open `http://localhost:8765/_verify/test_color_math.html` in browser. Confirm top line reads `10 pass / 0 fail`.

- [ ] **Step 4: Manual UI verification matrix**

Open `http://localhost:8765/app/mixo-swatch.html`. Walk through:

| Check | Steps | Expected |
|---|---|---|
| Lab toggle | Flip Print/Screen radio | Badge updates, grid re-renders <100ms |
| Corpus names | Hover swatch in grid | Names from up to 3 libs render based on display radio |
| Name uniqueness | Search for `桜色` | Only ONE swatch wears the name |
| Global anchor | Flip cmyk <-> hex | Closest matches shift |
| TAC preset | Click each preset | Slider snaps, grid filters |
| 3D-print preset | Check the box | TAC -> 240, dE max -> 3, grid tighter |
| Profile change | Pick different LUT | TAC snaps to profile recommended (no user override) |
| Hue x Light | Click sort button | View switches to map, other sort buttons deactivate |
| Palettes panel | Click header bar | Body expands; selector + strip + exports visible |
| Per-swatch ZIP | Filter to ~50, click ZIP | Download contains 50 PNGs + manifest |
| Mobile drawer | Resize to 400px | Hamburger appears; click opens drawer |
| Dark only | Switch OS to light | App stays dark |

- [ ] **Step 5: Add fake test-trad corpus to verify dynamic loading**

Create temporary file `data/corpora/name_corpora.json.test` (or add a 4th entry inline temporarily):
```json
{
  "id": "test-trad",
  "label": {"en":"Test corpus","ja":"テスト","zh":"测试"},
  "fields": [{"id":"name_en","label":{"en":"Name","ja":"名前","zh":"名称"}}],
  "default_display":"name_en",
  "anchor":"hex",
  "entries":[
    {"name_en":"fake1","name_ja":"フェイク1","name_zh":"假色1","hex":"#123456"},
    {"name_en":"fake2","name_ja":"フェイク2","name_zh":"假色2","hex":"#789ABC"}
  ]
}
```

Manually append to corpora[] in name_corpora.json. Reload app. Confirm:
- 4th card appears in "Display name from" panel
- 4th column appears in CSV export
- Swatch tooltips include test-trad matches

Then revert the change (`git checkout data/corpora/name_corpora.json`).

- [ ] **Step 6: Commit verification artefacts (if any)**

```bash
cd S:/mixoswatch && git status
```
Expected: clean tree (test file already reverted). If anything new, commit with `chore(verify): final verification artefacts`.

- [ ] **Step 7: Tag spec6 work-complete checkpoint**

```bash
cd S:/mixoswatch && git tag spec6-complete -m "Spec 6 implementation complete; ready for review"
```

---

## Task 25: Update ARCHITECTURE.md + README

**Files:**
- Modify: `ARCHITECTURE.md`
- Modify: `README.md` (if it references jpn / dic corpora)

- [ ] **Step 1: Update ARCHITECTURE.md corpora sections**

Find sections mentioning `jpn`, `jpn-dic`, `html`, system_name. Update:
- jpn -> jp-trad (250)
- Remove jpn-dic + zh-dic references
- Add zh-trad (526)
- Remove system_name section
- Add Bradford / D50/D65 / lab_mode section
- Add corpora schema v3 + tri-lingual fallback section
- Add per-profile TAC + 3D-print preset section
- Add UI consolidation notes (Hue x Light in Sort by, collapsable Palettes panel, per-swatch ZIP)
- Add responsive + dark-only notes

Em-dash check after editing:
```bash
cd S:/mixoswatch && python -c "import sys; bad=[chr(0x2014),chr(0x2013)]; t=open('ARCHITECTURE.md',encoding='utf-8').read(); print('FAIL' if any(c in t for c in bad) else 'OK')"
```
Expected: `OK`.

- [ ] **Step 2: Update README.md sections**

Find any references to `jpn-dic`, `system_name`, old corpora counts. Update to match new state.

- [ ] **Step 3: Commit docs**

```bash
cd S:/mixoswatch && git add ARCHITECTURE.md README.md
git commit -m "$(cat <<'EOF'
docs: refresh ARCHITECTURE + README for spec6 changes

- jpn -> jp-trad (250); zh-trad (526) added; DIC dropped
- Bradford D50/D65 dual-Lab pipeline + lab_mode toggle
- Corpora schema v3 + tri-lingual fallback rules
- Per-profile TAC defaults + 3D-print preset
- UI consolidation: Hue x Light in Sort by, Palettes panel,
  per-swatch ZIP, dark-only, responsive

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Pass

After all 25 tasks complete, confirm:

- [ ] Every spec section maps to >=1 task (Section 1 -> Tasks 2-4; Section 2 -> Tasks 6-11; Section 3 -> Tasks 13-14; Section 4 -> Tasks 15-16; Section 5 -> Tasks 17-19; Section 6 -> Tasks 12, 20-21; Storage migration -> Tasks 22-23; Verification -> Task 24; Docs -> Task 25)
- [ ] No `system_name` field anywhere
- [ ] No hardcoded `jpn_*` / `html_*` field references
- [ ] No em-dash anywhere in shipped files
- [ ] Per-library name uniqueness enforced
- [ ] Both Lab modes cached per swatch + per corpus entry
- [ ] Per-profile TAC fields present in luts/index.json
- [ ] Palettes panel collapsable + collapsed by default
- [ ] Per-swatch ZIP export works on filtered set
- [ ] Dark mode is the only mode
- [ ] Responsive at 1024 / 768 / 480
- [ ] localStorage v1 -> v2 migration tested
- [ ] All scripts validator-clean

If any check fails, add a remediation task and re-run.
