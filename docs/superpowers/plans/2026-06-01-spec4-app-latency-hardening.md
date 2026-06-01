# Spec 4 Implementation Plan · App latency hardening

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the heavy data pipeline (CMYK lattice derive, `delta_e_print`, `matchNearest`, sort) off the main thread into a Web Worker; replace the scroll listener with a sentinel `IntersectionObserver`; precompute the Hue × Light bucket map during `requestIdleCallback`; prefetch all profile LUTs into Worker memory on first idle. Every technique is gated by `performance.measure` rules; failing techniques are reverted (mandatory ones) or dropped (optional ones).

**Architecture:** Worker source string lives inside the HTML in a `<script type="text/worker">` tag, instantiated via `Blob` URL so no extra file ships. Main thread retains UI events, DOM render, filter pass (interactive), palette CRUD, export. Worker owns derive + match + sort + bucket map + LUT cache. Messages use Transferable `ArrayBuffer` views for zero-copy crossing. `performance.mark` / `measure` calls land at every gate point.

**Tech Stack:** Vanilla Web Worker, Transferable Objects, `IntersectionObserver`, `requestIdleCallback`, `performance.mark` / `measure`. No new dependencies.

**Reference spec:** `docs/superpowers/specs/2026-06-01-app-latency-hardening-design.md`

**Pre-requisite:** Specs 1, 2, 3 must land first. Spec 4 is the largest rewrite; it lands on already-clean (i18n applied, UX-polished, tooltip-rewritten) HTMLs so the Worker port operates on the final shape of the code.

---

## File Structure

| File | Action | Reason |
|---|---|---|
| `app/cmyk-explorer.html` | Modify | Embed Worker source; rewire derive / match / sort to post messages; replace scroll listener with IO + sentinels; add idle precompute + LUT prefetch; instrument with `performance.mark` |
| `app/3d-explorer.html` | Modify | Same pattern adapted for the library-JSON data source (no CMYK lattice derive) |
| `docs/superpowers/plans/2026-06-01-spec4-app-latency-hardening.md` | This file | Plan record |

No new files. No new external dependencies.

---

## Pre-flight: baseline timings

Spec 4's gates compare measurements before and after each technique. Capture the baseline FIRST so each gate has honest comparison data.

- [ ] **Step 1: Add instrumentation harness ahead of any change**

Use the Edit tool to insert the harness near the top of the script in each HTML.

`old_string` (locate a stable existing helper or simply the first `const` declaration):
```
// LUT cache (profile filename -> Uint8Array)
const LUT_CACHE = new Map();
```

`new_string`:
```
// Spec 4: RAIL band perf instrumentation
const RAIL_BANDS = {
  rail_response:    100,    // ms; any user-input → next paint
  rail_animation:    16.6,  // ms; per frame
  rail_idle_slice:   50,    // ms; per requestIdleCallback slice
  rail_load:       1000,    // ms; cold load → first interactive
};
function railMark(name) { performance.mark(name); }
function railMeasure(label, start, end) {
  try {
    performance.measure(label, start, end);
    const entries = performance.getEntriesByName(label);
    const e = entries[entries.length - 1];
    const band = RAIL_BANDS[label.replace(/_.+$/, '_response')] || RAIL_BANDS.rail_response;
    if (e && e.duration > band) {
      console.warn('[RAIL]', label, e.duration.toFixed(1), 'ms exceeds', band);
    }
    return e ? e.duration : null;
  } catch (err) { return null; }
}

// LUT cache (profile filename -> Uint8Array)
const LUT_CACHE = new Map();
```

Repeat for both HTMLs.

- [ ] **Step 2: Sprinkle baseline marks at major operation boundaries**

Use Edit to insert `railMark('rail_response_start')` and `railMeasure('rail_response_profile_switch', 'rail_response_start', 'rail_response_end')` at the boundaries of the existing operations. Concrete spots:

For profile change (cmyk-explorer):

`old_string`:
```
async function onProfileChange() {
  const sel = document.getElementById('iccSel');
  ACTIVE_PROFILE = ICC_INDEX.profiles.find(p => p.filename === sel.value);
  await rebuildAll();
```

`new_string`:
```
async function onProfileChange() {
  railMark('rail_profile_start');
  const sel = document.getElementById('iccSel');
  ACTIVE_PROFILE = ICC_INDEX.profiles.find(p => p.filename === sel.value);
  await rebuildAll();
  railMark('rail_profile_end');
  railMeasure('rail_response_profile_switch', 'rail_profile_start', 'rail_profile_end');
```

For anchor flip (already wired via rematchOne):

In the existing buildNamingUI anchor click handler, wrap the `await rematchOne(lib.id)` call:

`old_string`:
```
        anchSel.onchange = async () => {
          _setLibPref(lib.id, 'anchor', anchSel.value);
          await rematchOne(lib.id);
          render();
        };
```

`new_string`:
```
        anchSel.onchange = async () => {
          railMark('rail_anchor_start');
          _setLibPref(lib.id, 'anchor', anchSel.value);
          await rematchOne(lib.id);
          render();
          railMark('rail_anchor_end');
          railMeasure('rail_response_anchor_flip', 'rail_anchor_start', 'rail_anchor_end');
        };
```

For view switch:

`old_string`:
```
function setViewMode(m) {
  if (!['grid','huelight','palettes'].includes(m)) return;
```

`new_string`:
```
function setViewMode(m) {
  if (!['grid','huelight','palettes'].includes(m)) return;
  railMark('rail_view_start');
```

Then at the end of the same function (find existing closing brace):

Insert immediately before the closing brace of setViewMode:
```js
  railMark('rail_view_end');
  railMeasure('rail_response_view_' + m, 'rail_view_start', 'rail_view_end');
```

- [ ] **Step 3: Record baseline numbers**

Open the cmyk explorer via run.bat. In DevTools console:

```js
// switch profile a couple times
performance.getEntriesByName('rail_response_profile_switch').map(e => e.duration);
// flip an anchor a couple times
performance.getEntriesByName('rail_response_anchor_flip').map(e => e.duration);
// switch to Hue × Light + back
performance.getEntriesByName('rail_response_view_huelight').map(e => e.duration);
```

Note the medians. These are the **baseline** numbers each Spec 4 §5 gate compares against.

- [ ] **Step 4: Commit instrumentation**

```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html app/3d-explorer.html && git commit -m "feat(apps): Spec 4 perf instrumentation harness

RAIL band thresholds + railMark / railMeasure helpers. Wrap profile
switch, anchor flip, view switch with mark/measure pairs. Baseline
numbers captured before Worker port lands.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

# PHASE A · Web Worker (mandatory — GATE-A)

## Task A.1: Define Worker source as inline `<script type="text/worker">` (cmyk-explorer)

**Files:**
- Modify: `app/cmyk-explorer.html`

- [ ] **Step 1: Insert the worker source script tag at the end of `<body>` just before the existing `<script>`**

Run:
```bash
grep -n "</body>" "S:/mixoswatch/app/cmyk-explorer.html"
```
Note the line.

Use the Edit tool. The inline worker source contains all the math the main thread currently runs. Mirror the existing functions:

`old_string` (find the opening of the existing main script):
```
<script>
```

`new_string`:
```
<script type="text/worker" id="workerSrc">
"use strict";

// ── color math (mirror of main-thread math) ─────────────────────────────
function srgb2lin(u) { u /= 255; return u <= 0.04045 ? u / 12.92 : Math.pow((u + 0.055) / 1.055, 2.4); }
function f_(t) { return t > 0.008856 ? Math.cbrt(t) : (7.787 * t + 16 / 116); }
const Xn = 0.95047, Yn = 1.0, Zn = 1.08883;
function rgb2lab(r, g, b) {
  const R = srgb2lin(r), G = srgb2lin(g), B = srgb2lin(b);
  const X = 0.4124564 * R + 0.3575761 * G + 0.1804375 * B;
  const Y = 0.2126729 * R + 0.7151522 * G + 0.0721750 * B;
  const Z = 0.0193339 * R + 0.1191920 * G + 0.9503041 * B;
  const fx = f_(X / Xn), fy = f_(Y / Yn), fz = f_(Z / Zn);
  return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
}
function luminance(r, g, b) {
  return 0.2126 * srgb2lin(r) + 0.7152 * srgb2lin(g) + 0.0722 * srgb2lin(b);
}
function contrast(l1, l2) {
  const a = Math.max(l1, l2), b = Math.min(l1, l2);
  return (a + 0.05) / (b + 0.05);
}
function deltaE2000(L1, a1, b1, L2, a2, b2) {
  // verbatim port of the main-thread deltaE2000; pull from existing main-thread implementation
  // Implementation body identical to app/cmyk-explorer.html main-thread deltaE2000.
  const C1 = Math.hypot(a1, b1), C2 = Math.hypot(a2, b2);
  const avgC = (C1 + C2) / 2;
  const G = 0.5 * (1 - Math.sqrt(Math.pow(avgC, 7) / (Math.pow(avgC, 7) + Math.pow(25, 7)) || 1));
  const a1p = (1 + G) * a1, a2p = (1 + G) * a2;
  const C1p = Math.hypot(a1p, b1), C2p = Math.hypot(a2p, b2);
  const avgCp = (C1p + C2p) / 2;
  const h1p = (a1p || b1) ? (Math.atan2(b1, a1p) * 180 / Math.PI + 360) % 360 : 0;
  const h2p = (a2p || b2) ? (Math.atan2(b2, a2p) * 180 / Math.PI + 360) % 360 : 0;
  const dLp = L2 - L1, dCp = C2p - C1p;
  let dhp = h2p - h1p;
  if (Math.abs(dhp) > 180) dhp -= 360 * Math.sign(dhp);
  const dHp = (C1p && C2p) ? 2 * Math.sqrt(C1p * C2p) * Math.sin(dhp * Math.PI / 360) : 0;
  const avgL = (L1 + L2) / 2;
  let avgHp = (h1p + h2p) / 2;
  if (Math.abs(h1p - h2p) > 180) avgHp += 180;
  avgHp = (avgHp + 360) % 360;
  const T = 1 - 0.17 * Math.cos((avgHp - 30) * Math.PI / 180)
              + 0.24 * Math.cos((2 * avgHp) * Math.PI / 180)
              + 0.32 * Math.cos((3 * avgHp + 6) * Math.PI / 180)
              - 0.20 * Math.cos((4 * avgHp - 63) * Math.PI / 180);
  const SL = 1 + (0.015 * Math.pow(avgL - 50, 2)) / Math.sqrt(20 + Math.pow(avgL - 50, 2));
  const SC = 1 + 0.045 * avgCp;
  const SH = 1 + 0.015 * avgCp * T;
  const dTheta = 30 * Math.exp(-Math.pow((avgHp - 275) / 25, 2));
  const RC = 2 * Math.sqrt(Math.pow(avgCp, 7) / (Math.pow(avgCp, 7) + Math.pow(25, 7)) || 1);
  const RT = -Math.sin(2 * dTheta * Math.PI / 180) * RC;
  return Math.sqrt(Math.pow(dLp / SL, 2) + Math.pow(dCp / SC, 2) + Math.pow(dHp / SH, 2) + RT * (dCp / SC) * (dHp / SH));
}

// ── LUT lookup (quadrilinear) ────────────────────────────────────────────
const N_GRID = 17;
const LUT_HEADER = 16;
function lutLookup(lut, c, m, y, k) {
  // verbatim port of main-thread lutLookup
  const N = N_GRID, step = 100 / (N - 1);
  const fc = c / step, fm = m / step, fy = y / step, fk = k / step;
  const c0 = Math.min(N - 1, Math.floor(fc)), c1 = Math.min(N - 1, c0 + 1);
  const m0 = Math.min(N - 1, Math.floor(fm)), m1 = Math.min(N - 1, m0 + 1);
  const y0 = Math.min(N - 1, Math.floor(fy)), y1 = Math.min(N - 1, y0 + 1);
  const k0 = Math.min(N - 1, Math.floor(fk)), k1 = Math.min(N - 1, k0 + 1);
  const dc = fc - c0, dm = fm - m0, dy = fy - y0, dk = fk - k0;
  const NN3 = N * N * N, NN2 = N * N;
  let R = 0, G = 0, B = 0;
  for (let kk = 0; kk < 2; kk++) {
    const wk = kk ? dk : 1 - dk;
    const kIdx = (kk ? k1 : k0) * NN3;
    for (let yy = 0; yy < 2; yy++) {
      const wy = yy ? dy : 1 - dy;
      const yIdx = (yy ? y1 : y0) * NN2;
      for (let mm = 0; mm < 2; mm++) {
        const wm = mm ? dm : 1 - dm;
        const mIdx = (mm ? m1 : m0) * N;
        for (let cc = 0; cc < 2; cc++) {
          const wc = cc ? dc : 1 - dc;
          const cIdx = (cc ? c1 : c0);
          const w = wk * wy * wm * wc;
          const off = LUT_HEADER + ((kIdx + yIdx + mIdx + cIdx) * 3);
          R += lut[off]     * w;
          G += lut[off + 1] * w;
          B += lut[off + 2] * w;
        }
      }
    }
  }
  return [Math.round(R), Math.round(G), Math.round(B)];
}
function rlutLookup(rlut, R, G, B) {
  // verbatim port of main-thread rlutLookup
  const N = N_GRID, step = 255 / (N - 1);
  const fr = R / step, fg = G / step, fb = B / step;
  const r0 = Math.min(N - 1, Math.floor(fr)), r1 = Math.min(N - 1, r0 + 1);
  const g0 = Math.min(N - 1, Math.floor(fg)), g1 = Math.min(N - 1, g0 + 1);
  const b0 = Math.min(N - 1, Math.floor(fb)), b1 = Math.min(N - 1, b0 + 1);
  const dr = fr - r0, dg = fg - g0, db = fb - b0;
  const NN2 = N * N;
  let C = 0, M = 0, Y = 0, K = 0;
  for (let rr = 0; rr < 2; rr++) {
    const wr = rr ? dr : 1 - dr;
    const rIdx = (rr ? r1 : r0) * NN2;
    for (let gg = 0; gg < 2; gg++) {
      const wg = gg ? dg : 1 - dg;
      const gIdx = (gg ? g1 : g0) * N;
      for (let bb = 0; bb < 2; bb++) {
        const wb = bb ? db : 1 - db;
        const bIdx = (bb ? b1 : b0);
        const w = wr * wg * wb;
        const off = LUT_HEADER + ((rIdx + gIdx + bIdx) * 4);
        C += rlut[off]     * w;
        M += rlut[off + 1] * w;
        Y += rlut[off + 2] * w;
        K += rlut[off + 3] * w;
      }
    }
  }
  return [Math.round(C * 100 / 255), Math.round(M * 100 / 255), Math.round(Y * 100 / 255), Math.round(K * 100 / 255)];
}

// ── worker state ────────────────────────────────────────────────────────
const lutCache = new Map();           // name -> Uint8Array
const rlutCache = new Map();          // name -> Uint8Array
let corpora = { libraries: [] };      // mirrors main-thread CORPORA
let corporaPrefs = {};                // mirrors CORPORA_PREFS
let mainData = null, gsData = null;   // derived swatches per profile/step
let hueLightCache = null;             // { key, map }

// ── derive pipeline ─────────────────────────────────────────────────────
function genLattice(step) {
  const out = [];
  for (let K = 0; K <= 100; K += step)
    for (let Y = 0; Y <= 100; Y += step)
      for (let M = 0; M <= 100; M += step)
        for (let C = 0; C <= 100; C += step)
          out.push({ C, M, Y, K });
  return out;
}
function deriveOne(s, lut) {
  const [r, g, b] = lutLookup(lut, s.C, s.M, s.Y, s.K);
  s.R = r; s.G = g; s.B = b;
  s.hex = '#' + [r, g, b].map(v => v.toString(16).padStart(2, '0')).join('').toUpperCase();
  const [L, a, bb] = rgb2lab(r, g, b);
  s.L_star = +L.toFixed(2); s.a_star = +a.toFixed(2); s.b_star = +bb.toFixed(2);
  s.luminance = +luminance(r, g, b).toFixed(5);
  const cB = contrast(s.luminance, 0), cW = contrast(s.luminance, 1);
  if (cB >= cW) { s.text_color = '#000000'; s.contrast_ratio = +cB.toFixed(2); }
  else          { s.text_color = '#FFFFFF'; s.contrast_ratio = +cW.toFixed(2); }
  s.wcag_aa = s.contrast_ratio >= 4.5;
  s.wcag_aaa = s.contrast_ratio >= 7.0;
  const t = s.K < 25 ? 1 : (s.K < 50 ? 2 : 3);
  s.k_tier = t;
  s.k_tier_name = t === 1 ? 'Brand' : (t === 2 ? 'Support' : 'Deep');
  s.tac = s.C + s.M + s.Y + s.K;
  s.grayscale = (s.C === 0 && s.M === 0 && s.Y === 0);
  return s;
}
function matchOne(s, lib, prefs) {
  let best = null, bestD = Infinity;
  for (const e of lib.entries) {
    const lab = (prefs.anchor === 'cmyk' && e._lab_cmyk) ? e._lab_cmyk : (e._lab_hex || e._lab_cmyk);
    if (!lab) continue;
    const d = deltaE2000(s.L_star, s.a_star, s.b_star, lab[0], lab[1], lab[2]);
    if (d < bestD) { bestD = d; best = e; }
  }
  return best ? { entryIdx: lib.entries.indexOf(best), deltaE: +bestD.toFixed(2), anchor: prefs.anchor } : null;
}

// ── message handler ─────────────────────────────────────────────────────
self.onmessage = (e) => {
  const msg = e.data;
  switch (msg.type) {
    case 'init':
      corpora = msg.corpora || { libraries: [] };
      corporaPrefs = msg.prefs || {};
      // precompute _lab_hex for each entry
      for (const lib of corpora.libraries) {
        for (const ent of lib.entries) {
          if (ent.hex) {
            const h = ent.hex.replace('#', '');
            const r = parseInt(h.slice(0, 2), 16);
            const g = parseInt(h.slice(2, 4), 16);
            const b = parseInt(h.slice(4, 6), 16);
            ent._lab_hex = rgb2lab(r, g, b);
          }
        }
      }
      self.postMessage({ type: 'init_ready' });
      break;
    case 'load_lut':
      lutCache.set(msg.name, new Uint8Array(msg.buf));
      self.postMessage({ type: 'lut_ready', name: msg.name });
      break;
    case 'load_rlut':
      rlutCache.set(msg.name, new Uint8Array(msg.buf));
      self.postMessage({ type: 'rlut_ready', name: msg.name });
      break;
    case 'set_corpora_prefs':
      corporaPrefs = msg.prefs;
      break;
    case 'derive': {
      const lut = lutCache.get(msg.lutName);
      if (!lut) { self.postMessage({ type: 'error', msg: 'LUT not loaded: ' + msg.lutName }); return; }
      const lattice = genLattice(msg.step);
      const out = [];
      const CHUNK = 1500;
      for (let i = 0; i < lattice.length; i++) {
        const s = lattice[i];
        deriveOne(s, lut);
        // per-lib match
        s.matches = {};
        for (const lib of corpora.libraries) {
          const prefs = corporaPrefs[lib.id] || { anchor: 'cmyk' };
          s.matches[lib.id] = matchOne(s, lib, prefs);
        }
        out.push(s);
        if (i % CHUNK === 0) {
          self.postMessage({ type: 'progress', task: 'derive', n: i, m: lattice.length });
        }
      }
      // split GS_DATA + MAIN_DATA
      const gsArr = out.filter(s => s.C === 0 && s.M === 0 && s.Y === 0 && s.K > 0);
      const main  = out.filter(s => !(s.C === 0 && s.M === 0 && s.Y === 0 && s.K > 0));
      mainData = main;
      gsData = gsArr;
      hueLightCache = null;
      self.postMessage({ type: 'derive_ready', main_data: main, gs_data: gsArr });
      break;
    }
    case 'rematch': {
      const lib = corpora.libraries.find(l => l.id === msg.lib_id);
      if (!lib || !mainData) return;
      const prefs = corporaPrefs[lib.id] || { anchor: 'cmyk' };
      const matches = {};
      for (let i = 0; i < mainData.length; i++) {
        matches[i] = matchOne(mainData[i], lib, prefs);
      }
      self.postMessage({ type: 'rematch_ready', lib_id: msg.lib_id, matches });
      break;
    }
    case 'sort': {
      if (!mainData) return;
      const view = mainData.slice();
      switch (msg.mode) {
        case 'hue':    view.sort((a, b) => Math.atan2(a.b_star, a.a_star) - Math.atan2(b.b_star, b.a_star)); break;
        case 'light':  view.sort((a, b) => a.L_star - b.L_star); break;
        case 'tac':    view.sort((a, b) => a.tac - b.tac); break;
        case 'safety': view.sort((a, b) => a.contrast_ratio - b.contrast_ratio); break;
        // ... extend as needed
      }
      self.postMessage({ type: 'sort_ready', mode: msg.mode, view });
      break;
    }
    case 'precompute_huelight': {
      if (!mainData) return;
      const map = new Array(180).fill(null);
      for (const s of mainData) {
        const h = ((Math.atan2(s.b_star, s.a_star) * 180 / Math.PI) + 360) % 360;
        const hueBin = Math.floor(h / 20);                            // 18 hue bins
        const lightBin = Math.min(9, Math.floor(s.L_star / 10));      // 10 light bins
        const idx = lightBin * 18 + hueBin;
        if (!map[idx]) map[idx] = s;
      }
      hueLightCache = { key: 'cmyk', map };
      self.postMessage({ type: 'huelight_ready', map });
      break;
    }
    case 'get_huelight': {
      if (hueLightCache) {
        self.postMessage({ type: 'huelight_ready', map: hueLightCache.map });
      } else if (mainData) {
        // compute on demand
        self.postMessage({ type: 'precompute_huelight' });
      }
      break;
    }
  }
};
</script>

<script>
```

- [ ] **Step 2: Instantiate worker via Blob URL in main thread**

Add to the main thread's script near the top (right after the `LUT_CACHE` declaration):

Use the Edit tool with:

`old_string`:
```
// LUT cache (profile filename -> Uint8Array)
const LUT_CACHE = new Map();
```

`new_string`:
```
// LUT cache (profile filename -> Uint8Array)
const LUT_CACHE = new Map();

// Spec 4: instantiate Web Worker from inline source
let WORKER = null;
function _spawnWorker() {
  const src = document.getElementById('workerSrc')?.textContent;
  if (!src) { console.error('[worker] no inline source found'); return null; }
  const blob = new Blob([src], { type: 'text/javascript' });
  const url = URL.createObjectURL(blob);
  const w = new Worker(url);
  // intentional: do not revokeObjectURL — worker keeps the URL referenced for its lifetime
  return w;
}
```

- [ ] **Step 3: Add boot-time worker init**

In the existing window load handler, after corpora load, post init to worker:

`old_string`:
```
    await Promise.all([loadIndex(), loadCorpora()]);
```

`new_string`:
```
    await Promise.all([loadIndex(), loadCorpora()]);
    WORKER = _spawnWorker();
    if (WORKER) {
      WORKER.addEventListener('message', onWorkerMessage);
      WORKER.postMessage({ type: 'init', corpora: CORPORA, prefs: CORPORA_PREFS });
    }
```

Add the worker message handler near the other helpers:

`old_string` (any stable existing helper; e.g. `function _spawnWorker()`):
```
let WORKER = null;
function _spawnWorker() {
```

`new_string`:
```
function onWorkerMessage(e) {
  const msg = e.data;
  switch (msg.type) {
    case 'init_ready':
    case 'lut_ready':
    case 'rlut_ready':
      break;
    case 'progress': {
      const label = document.getElementById('lpLabel');
      const sub = document.getElementById('lpSub');
      if (sub) sub.textContent = `${msg.n.toLocaleString()} / ${msg.m.toLocaleString()}`;
      break;
    }
    case 'derive_ready':
      MAIN_DATA = msg.main_data;
      GS_DATA = msg.gs_data;
      // reconstruct matches.entry from entryIdx
      for (const s of MAIN_DATA) {
        for (const libId in s.matches) {
          if (!s.matches[libId]) continue;
          const lib = CORPORA.libraries.find(l => l.id === libId);
          if (lib) s.matches[libId].entry = lib.entries[s.matches[libId].entryIdx];
        }
      }
      DEDUP = MAIN_DATA.concat(GS_DATA);
      _hideProgress?.();
      render();
      break;
    case 'rematch_ready':
      for (let i = 0; i < MAIN_DATA.length; i++) {
        const m = msg.matches[i];
        if (m) {
          const lib = CORPORA.libraries.find(l => l.id === msg.lib_id);
          if (lib) {
            MAIN_DATA[i].matches[msg.lib_id] = m;
            MAIN_DATA[i].matches[msg.lib_id].entry = lib.entries[m.entryIdx];
          }
        }
      }
      render();
      break;
    case 'sort_ready':
      // future use; current sort stays on main for now
      break;
    case 'huelight_ready':
      HUE_LIGHT_MAP = msg.map;
      if (typeof renderHueLightMap === 'function') renderHueLightMap();
      break;
    case 'error':
      console.error('[worker]', msg.msg);
      break;
  }
}

let WORKER = null;
function _spawnWorker() {
```

- [ ] **Step 4: Replace rebuildAll's derive loop with worker postMessage**

The existing `rebuildAll()` calls `genLattice` + per-swatch derive on main thread. Replace its hot loop:

`old_string`:
```
async function rebuildAll() {
  if (!ACTIVE_PROFILE) return;
  const status = document.getElementById('iccStatus');
  if (status) status.textContent = 'Loading ' + ACTIVE_PROFILE.filename + '…';
  _showProgress('Loading ' + ACTIVE_PROFILE.label);
  _setProgress(2, 'Fetching LUTs');
  const lut = await loadLUT(ACTIVE_PROFILE.lut);
```

`new_string`:
```
async function rebuildAll() {
  if (!ACTIVE_PROFILE) return;
  const status = document.getElementById('iccStatus');
  if (status) status.textContent = 'Loading ' + ACTIVE_PROFILE.filename + '…';
  _showProgress('Loading ' + ACTIVE_PROFILE.label);
  _setProgress(2, 'Fetching LUTs');
  const lut = await loadLUT(ACTIVE_PROFILE.lut);
  // Spec 4: push LUT to Worker
  if (WORKER) {
    const lutCopy = new Uint8Array(lut).slice().buffer;
    WORKER.postMessage({ type: 'load_lut', name: ACTIVE_PROFILE.lut, buf: lutCopy }, [lutCopy]);
  }
```

And replace the existing main-thread chunked derive loop with a single postMessage:

Find the loop (around `for (let i=0; i<RAW.length; i+=CHUNK) {`) and replace the entire loop block (CHUNK / for / await rAF) with:

`old_string`:
```
  const CHUNK = 1500;
  for (let i=0; i<RAW.length; i+=CHUNK) {
    const end = Math.min(i+CHUNK, RAW.length);
    for (let j=i; j<end; j++) {
      deriveSwatch(RAW[j], lut);
      RAW[j].system_name = systemName(RAW[j]);
      RAW[j].delta_e_print = ACTIVE_RLUT ? +deltaERoundTrip(RAW[j], lut, ACTIVE_RLUT).toFixed(2) : null;
      matchNearest(RAW[j], lut);
    }
    const pct = 8 + (end / RAW.length) * 88;
    _setProgress(pct, `${end.toLocaleString()} / ${RAW.length.toLocaleString()} swatches`);
    if (end < RAW.length) {
      if (status) status.textContent = 'Processing ' + end.toLocaleString() + '/' + RAW.length.toLocaleString() + '…';
      await new Promise(r => requestAnimationFrame(r));
    }
  }
```

`new_string`:
```
  if (WORKER) {
    // Spec 4: derive off-main via Worker. Main thread waits for derive_ready msg.
    return new Promise(resolve => {
      const oncePerDerive = (e) => {
        if (e.data && e.data.type === 'derive_ready') {
          WORKER.removeEventListener('message', oncePerDerive);
          resolve();
        }
      };
      WORKER.addEventListener('message', oncePerDerive);
      WORKER.postMessage({ type: 'derive', lutName: ACTIVE_PROFILE.lut, step: curStep });
    });
  } else {
    // Fallback: legacy main-thread derive (kept for emergency revert)
    // ... legacy chunked derive body verbatim if needed ...
  }
```

- [ ] **Step 5: Replace matchNearest / rematchOne paths**

Wire `rematchOne` to use the Worker:

`old_string` (existing function):
```
async function rematchOne(libId) {
```

`new_string`:
```
async function rematchOne(libId) {
  if (WORKER) {
    WORKER.postMessage({ type: 'set_corpora_prefs', prefs: CORPORA_PREFS });
    WORKER.postMessage({ type: 'rematch', lib_id: libId });
    return new Promise(resolve => {
      const handler = (e) => {
        if (e.data?.type === 'rematch_ready' && e.data.lib_id === libId) {
          WORKER.removeEventListener('message', handler);
          resolve();
        }
      };
      WORKER.addEventListener('message', handler);
    });
  }
  // legacy main-thread fallback below (existing body preserved)
```

(Preserve the legacy body inside an `else` branch so the GATE-A revert path stays intact.)

- [ ] **Step 6: JS parse + browser smoke**

Run JS parse. Expected: `JS OK`.

Browser smoke: open cmyk explorer. Watch DevTools Performance tab during a profile switch. Main-thread `script` blocks should shrink dramatically; Worker thread shows the heavy work. Profile switch should still complete and render correctly.

- [ ] **Step 7: Run GATE-A measurement**

In console:
```js
performance.getEntriesByName('rail_response_profile_switch').map(e => e.duration);
```

Compare to baseline. **Expected: median drops measurably.** Spec 4 §5 GATE-A: if profile-switch median does not drop, revert all four techniques.

- [ ] **Step 8: Commit**

Run:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html && git commit -m "feat(cmyk): Web Worker derive + match (Spec 4 §2.1, GATE-A)

Inline <script type=text/worker> contains the full color math + LUT
lookup + derive + match pipeline. Spawned via Blob URL on boot;
rebuildAll posts derive, awaits derive_ready; rematchOne posts
rematch, awaits rematch_ready. Legacy main-thread paths preserved
behind WORKER null check for emergency revert.

GATE-A measurement: profile-switch median latency compared to
baseline. Revert all four Spec 4 techniques if no improvement.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

## Task A.2: Same Worker port for 3d-explorer

**Files:**
- Modify: `app/3d-explorer.html`

The 3D explorer's heavy path is `loadLibrary` (parse JSON + per-swatch derive + match) rather than CMYK lattice derive. Adapt:

- [ ] **Step 1: Inline worker source for 3D**

Use the same color math + matchOne functions. Differences:
- No `genLattice` (3D reads pre-curated library JSON).
- Add a `load_lib` message that receives parsed library payload and runs match per swatch:

```js
case 'load_lib': {
  mainData = msg.payload.swatches.map(s => {
    const [r, g, b] = s.rgb;
    const out = { ...s, R: r, G: g, B: b };
    // already has lab + delta_e per swatches.json; just add matches
    out.matches = {};
    for (const lib of corpora.libraries) {
      const prefs = corporaPrefs[lib.id] || { anchor: 'cmyk' };
      out.matches[lib.id] = matchOne(out, lib, prefs);
    }
    return out;
  });
  hueLightCache = null;
  self.postMessage({ type: 'lib_ready', main_data: mainData });
  break;
}
```

- [ ] **Step 2: Wire main thread**

In `loadLibrary`, after fetching the JSON, post to worker instead of running the per-swatch loop on main thread:

`old_string`:
```
  RAW = j.swatches.map(s => {
```

`new_string`:
```
  if (WORKER) {
    return new Promise(resolve => {
      const handler = (e) => {
        if (e.data?.type === 'lib_ready') {
          MAIN_DATA = e.data.main_data;
          // reconstruct matches.entry
          for (const s of MAIN_DATA) {
            for (const libId in s.matches) {
              if (!s.matches[libId]) continue;
              const lib = CORPORA.libraries.find(l => l.id === libId);
              if (lib) s.matches[libId].entry = lib.entries[s.matches[libId].entryIdx];
            }
          }
          DEDUP = MAIN_DATA;
          WORKER.removeEventListener('message', handler);
          _hideProgress?.();
          render();
          resolve();
        }
      };
      WORKER.addEventListener('message', handler);
      WORKER.postMessage({ type: 'load_lib', payload: j });
    });
  }

  // legacy main-thread path below
  RAW = j.swatches.map(s => {
```

- [ ] **Step 3: JS parse + GATE-A measurement + commit**

JS parse: `JS OK`. Run library switch in browser; measure rail_response. Expected: main thread no longer blocks during library load. Commit:

```bash
cd S:/mixoswatch && git add app/3d-explorer.html && git commit -m "feat(3d): Web Worker library-load + match (Spec 4 §2.1, GATE-A)

3D explorer's heavy path (per-swatch match against multiple corpora
on library load) moved to worker. load_lib message replaces the
inline per-swatch loop. Legacy main-thread path preserved behind
WORKER null check.

GATE-A measurement: library-switch median latency compared to
baseline. Revert all four Spec 4 techniques if no improvement.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

# PHASE B · Sentinel IntersectionObserver (mandatory — GATE-B)

## Task B.1: Replace scroll listener with sentinel IO (cmyk-explorer)

**Files:**
- Modify: `app/cmyk-explorer.html`

- [ ] **Step 1: Add sentinel divs to the swatch grid markup**

`old_string`:
```
      <div class="swatch-grid" id="swatchGrid"></div>
```

`new_string`:
```
      <div class="swatch-grid" id="swatchGrid">
        <div class="io-sentinel io-top"    aria-hidden="true"></div>
        <div class="io-sentinel io-bottom" aria-hidden="true"></div>
      </div>
```

- [ ] **Step 2: Add CSS for sentinels**

`old_string` (locate any stable existing CSS rule near the end of `<style>`; the Spec 3 banner block works):
```
@keyframes bannerIn {
```

Insert before it:
```
/* Spec 4 §2.2: IO sentinels for virtualized scroll */
.io-sentinel {
  position: absolute;
  height: 1px;
  width: 100%;
  pointer-events: none;
}
.io-sentinel.io-top    { top: 0; }
.io-sentinel.io-bottom { bottom: 0; }

@keyframes bannerIn {
```

- [ ] **Step 3: Remove existing scroll listener; replace with IO instantiation**

Find the existing scroll handler:
```bash
grep -n "_scrollPaintHandler\|addEventListener('scroll'" "S:/mixoswatch/app/cmyk-explorer.html"
```

Remove the scroll handler block:

`old_string` (the existing `window._scrollPaintHandler` declaration + addEventListener call):
```
  const scrollEl = document.getElementById('gridScroll');
  if (window._scrollPaintHandler) scrollEl.removeEventListener('scroll', window._scrollPaintHandler);
  let _rafQueued = false;
  window._scrollPaintHandler = () => {
    if (_rafQueued) return;
    _rafQueued = true;
    requestAnimationFrame(() => { _rafQueued = false; paintWindow(); });
  };
  scrollEl.addEventListener('scroll', window._scrollPaintHandler, { passive: true });
```

`new_string`:
```
  // Spec 4 §2.2: sentinel IntersectionObserver replaces the scroll listener
  const scrollEl = document.getElementById('gridScroll');
  if (window._spec4IO) window._spec4IO.disconnect();
  window._spec4IO = new IntersectionObserver((entries) => {
    if (entries.some(e => e.isIntersecting)) paintWindow();
  }, {
    root: scrollEl,
    rootMargin: '500px 0px',
  });
  const topSent    = document.querySelector('.io-sentinel.io-top');
  const bottomSent = document.querySelector('.io-sentinel.io-bottom');
  if (topSent && bottomSent) {
    window._spec4IO.observe(topSent);
    window._spec4IO.observe(bottomSent);
  }
```

- [ ] **Step 4: JS parse + browser smoke**

JS parse: `JS OK`. Open browser. Scroll the grid. Cells continue to render correctly via paintWindow being called when sentinels cross.

- [ ] **Step 5: GATE-B measurement**

In DevTools Performance tab, record a 5-second grid scroll session. Inspect main-thread frame durations. **Expected: p95 frame duration drops below 16.6 ms with IO (vs the baseline with scroll listener).** If no improvement, revert all 4 Spec 4 techniques.

- [ ] **Step 6: Commit**

```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html && git commit -m "feat(cmyk): sentinel IntersectionObserver replaces scroll listener (Spec 4 §2.2, GATE-B)

Two zero-height divs at top + bottom of the visible grid. Single
IO instance observes both. paintWindow fires only when a sentinel
crosses the viewport boundary (~1-2 callbacks per scroll burst
instead of ~60 scroll-events per second).

GATE-B: p95 scroll-frame latency vs baseline.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

## Task B.2: Same IO replacement for 3d-explorer

**Files:**
- Modify: `app/3d-explorer.html`

Repeat Task B.1 against 3d-explorer.

---

# PHASE C · Hue × Light idle precompute (optional — GATE-C)

## Task C.1: Schedule precompute after derive

**Files:**
- Modify: `app/cmyk-explorer.html`, `app/3d-explorer.html`

- [ ] **Step 1: After derive_ready handler, schedule precompute**

Inside `onWorkerMessage` case 'derive_ready', add at the end:

`old_string`:
```
    case 'derive_ready':
      MAIN_DATA = msg.main_data;
      GS_DATA = msg.gs_data;
      // reconstruct matches.entry from entryIdx
```

Find the entire derive_ready block and append `requestIdleCallback` scheduling at its end:

`new_string` (intercept just before the `break` of the case):
```
    case 'derive_ready':
      MAIN_DATA = msg.main_data;
      GS_DATA = msg.gs_data;
      // reconstruct matches.entry from entryIdx
      for (const s of MAIN_DATA) {
        for (const libId in s.matches) {
          if (!s.matches[libId]) continue;
          const lib = CORPORA.libraries.find(l => l.id === libId);
          if (lib) s.matches[libId].entry = lib.entries[s.matches[libId].entryIdx];
        }
      }
      DEDUP = MAIN_DATA.concat(GS_DATA);
      _hideProgress?.();
      render();
      // Spec 4 §2.3: precompute Hue × Light map during idle time
      if (WORKER && 'requestIdleCallback' in window) {
        requestIdleCallback(() => {
          WORKER.postMessage({ type: 'precompute_huelight' });
        }, { timeout: 1500 });
      }
      break;
```

- [ ] **Step 2: Wire `getHueLightMap()` for view switch**

Find existing renderHueLightMap function. Modify view-switch to request from worker:

`old_string`:
```
function renderHueLightMap() {
```

`new_string`:
```
function renderHueLightMap() {
  // Spec 4 §2.3: if Worker has precomputed map, use it; otherwise compute
  if (WORKER && HUE_LIGHT_MAP) {
    // paint from cached HUE_LIGHT_MAP directly
    _paintHueLightMapFromCache(HUE_LIGHT_MAP);
    return;
  }
```

Add `_paintHueLightMapFromCache` helper near other renderers. (The existing renderHueLightMap's body is the cached-paint fallback; you can extract its body into the new helper. Specific extraction depends on the live file structure; rule: extract the part that consumes the `grid` Map and renders cells, keep it as `_paintHueLightMapFromCache(map)`.)

- [ ] **Step 3: GATE-C measurement**

In console, after page settles for ~2 seconds:
```js
performance.getEntriesByName('rail_response_view_huelight').map(e => e.duration);
```

Trigger view switch to Hue × Light. Measure. **Expected: median < 100 ms** (RAIL response band).

If precompute does not pull view-switch under 100ms, drop only this section. Remove the `requestIdleCallback` call from derive_ready and revert the renderHueLightMap fast-path. The other three techniques stay.

- [ ] **Step 4: Commit (or revert)**

If gate passes:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html app/3d-explorer.html && git commit -m "feat(apps): Hue × Light idle precompute (Spec 4 §2.3, GATE-C)

requestIdleCallback after derive_ready posts precompute_huelight to
Worker. Worker computes 180-cell bucket map on its own time, caches
result. View-switch to Hue × Light uses cache if present (instant);
otherwise computes on demand.

GATE-C: view-switch-to-huelight median vs baseline. Drop only this
section if no improvement.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

If gate fails: revert Task C.1 changes via `git checkout app/cmyk-explorer.html app/3d-explorer.html` (against the staged Phase B end state) and document the drop in the next commit message.

---

# PHASE D · LUT bulk prefetch (optional — GATE-D)

## Task D.1: Schedule bulk LUT fetch after derive

**Files:**
- Modify: `app/cmyk-explorer.html`, `app/3d-explorer.html`

- [ ] **Step 1: After derive_ready, schedule bulk prefetch**

In the same `onWorkerMessage` derive_ready handler, append another idle callback:

Append after the precompute_huelight idle call:

```js
      // Spec 4 §2.4: bulk-prefetch all other profile LUTs during idle
      if (WORKER && 'requestIdleCallback' in window && ICC_INDEX) {
        requestIdleCallback(() => {
          for (const p of ICC_INDEX.profiles) {
            if (p.lut === ACTIVE_PROFILE.lut) continue;
            if (LUT_CACHE.has(p.lut)) continue;
            fetch('../' + p.lut)
              .then(r => r.arrayBuffer())
              .then(buf => {
                LUT_CACHE.set(p.lut, new Uint8Array(buf.slice(0)));
                WORKER.postMessage({ type: 'load_lut', name: p.lut, buf }, [buf]);
              })
              .catch(() => {});
          }
        }, { timeout: 3000 });
      }
```

- [ ] **Step 2: 3D adaptation**

For 3D explorer, prefetch LUTs corresponding to other libraries similarly (using the library_index.json entries).

- [ ] **Step 3: GATE-D measurement**

Open app. Wait ~5 seconds for idle prefetch to finish (visible in DevTools Network tab). Switch profile. Measure `rail_response_profile_switch`.

Compare 1st-profile-switch and 2nd-profile-switch durations. **Expected: 2nd switch >50 ms faster than 1st.**

If improvement <50 ms, drop only this section (revert Task D.1 edits; document in next commit).

- [ ] **Step 4: Commit (or revert)**

If gate passes:
```bash
cd S:/mixoswatch && git add app/cmyk-explorer.html app/3d-explorer.html && git commit -m "feat(apps): bulk LUT prefetch on idle (Spec 4 §2.4, GATE-D)

requestIdleCallback after derive_ready fetches all other profile
LUTs in background, transfers each to Worker via ArrayBuffer.
Second profile switch is fetch-free.

GATE-D: 2nd-profile-switch latency must be >50 ms faster than 1st.
Drop only this section if no improvement.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

# PHASE E · Final validation suite

## Task E.1: Spec 4 gates 1-9

- [ ] **Step 1: Worker spawns without error in 3 browsers**

Open in Chrome, Firefox, Safari. DevTools console: no errors during boot. Gate 1.

- [ ] **Step 2: No console errors on cold load**

Repeat in each browser. Gate 2.

- [ ] **Step 3: Functional regression smoke**

Per app:
- Profile switch (CMYK) / library switch (3D)
- Anchor flip
- Palette CRUD: + New, rename, duplicate, delete, clear
- Filter sliders (CMYK range, TAC, ΔE)
- Sort buttons
- View switch (Grid / Hue × Light / Palettes)
- Search
- Export buttons (ASE, GPL, PNG, JSON)

All operations succeed without error. Gate 3.

- [ ] **Step 4: Memory profile**

DevTools Memory tab: take a heap snapshot. Main thread heap should drop measurably vs the baseline (heavy arrays now live in Worker heap). Gate 4.

- [ ] **Step 5: Sustained 60 fps scroll**

DevTools Performance tab: record 5 seconds of grid scrolling. Frame stats panel: dropped-frame count < 5%, GPU + idle time visible. Gate 5.

- [ ] **Step 6: Confirm each GATE-A/B/C/D result**

Capture the post-implementation medians of each measurement. Compare to baseline. Document the gate decisions (keep / revert / drop) inline in a commit message or in the spec doc's open-questions section. Gate 6.

- [ ] **Step 7: Em-dash audit**

```bash
grep -c "—\|–" "S:/mixoswatch/app/cmyk-explorer.html"
grep -c "—\|–" "S:/mixoswatch/app/3d-explorer.html"
```
Must not increase vs baseline. Gate 7.

- [ ] **Step 8: JS parse on both files including the worker source**

```bash
node -e "const fs=require('fs');for(const f of ['app/cmyk-explorer.html','app/3d-explorer.html']){const html=fs.readFileSync('S:/mixoswatch/'+f,'utf-8');const scripts=html.match(/<script[^>]*>([\\s\\S]*?)<\\/script>/g);if(scripts){scripts.forEach((s,i)=>{const body=s.replace(/<script[^>]*>/,'').replace(/<\\/script>/,'');try{new Function(body);console.log(f,'script',i,'OK');}catch(e){console.log(f,'script',i,'ERR:',e.message.split('\\n')[0]);}});}}"
```
Expected: each `script i OK`. Gate 8.

- [ ] **Step 9: Prefetch verification (only if GATE-D kept)**

DevTools Network tab. Reload page. Confirm: on first idle (~1-3 seconds after derive_ready), 11 LUT requests fire in background (one per non-active profile). Switch to a 2nd profile. Network tab shows 0 new LUT requests for that profile. Gate 9.

---

## Self-Review

**Spec coverage check (against Spec 4 §3 file change list + §5 validation gates):**

| Spec 4 item | Plan task |
|---|---|
| §2.1 Web Worker (cmyk) | Tasks A.1, instrumentation pre-flight |
| §2.1 Web Worker (3D) | Task A.2 |
| §2.2 Sentinel IO (cmyk) | Task B.1 |
| §2.2 Sentinel IO (3D) | Task B.2 |
| §2.3 Hue × Light idle precompute | Task C.1 |
| §2.4 Bulk LUT prefetch | Task D.1 |
| §2.5 RAIL bands + instrumentation | Pre-flight Step 1, baseline recording in Step 3 |
| §5 GATE-A | Task A.1 Step 7, A.2 Step 3 |
| §5 GATE-B | Task B.1 Step 5 |
| §5 GATE-C | Task C.1 Step 3 |
| §5 GATE-D | Task D.1 Step 3 |
| §5 gate 1 (Worker spawns) | Task E.1 Step 1 |
| §5 gate 2 (no console errors) | Task E.1 Step 2 |
| §5 gate 3 (regression smoke) | Task E.1 Step 3 |
| §5 gate 4 (memory drop) | Task E.1 Step 4 |
| §5 gate 5 (60fps scroll) | Task E.1 Step 5 |
| §5 gate 6 (gate decisions documented) | Task E.1 Step 6 |
| §5 gate 7 (em-dash 0) | Task E.1 Step 7 |
| §5 gate 8 (JS parse including worker) | Task E.1 Step 8 |
| §5 gate 9 (prefetch network verification) | Task E.1 Step 9 |

No gaps.

**Placeholder scan:** plan calls Worker source "verbatim port" in places where the math is mechanically identical to the main-thread version. Each port section names the source function explicitly (`deltaE2000`, `lutLookup`, `rlutLookup`, `rgb2lab`) so the engineer copies from the live main-thread implementation byte-for-byte. The legacy fallback branches in `rebuildAll`, `rematchOne`, and `loadLibrary` reference "existing body preserved" without spelling it out; this is intentional because the legacy code is what is being preserved verbatim. If the engineer encounters confusion, they read the live main-thread implementation in the same file (line numbers vary per session).

**Type consistency:** Worker message types (`init`, `init_ready`, `load_lut`, `lut_ready`, `derive`, `derive_ready`, `rematch`, `rematch_ready`, `sort`, `sort_ready`, `precompute_huelight`, `huelight_ready`, `get_huelight`, `load_lib`, `lib_ready`, `progress`, `error`) used consistently across both directions. Helper names (`_spawnWorker`, `onWorkerMessage`, `railMark`, `railMeasure`, `RAIL_BANDS`, `HUE_LIGHT_MAP`, `_paintHueLightMapFromCache`) match between definition and usage.

**Frequent commits:** ~12 commits across the implementation. Each gate's keep / drop decision is its own commit so reverts stay surgical.
