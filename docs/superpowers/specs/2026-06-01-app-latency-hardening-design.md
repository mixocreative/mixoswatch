# Spec 4 · App latency hardening (Worker + IO + idle precompute + LUT prefetch)

**Date:** 2026-06-01
**Author:** mixocreative (via brainstorm cycle)
**Scope:** `app/cmyk-explorer.html`, `app/3d-explorer.html`
**Status:** awaiting user review

---

## 0. Why this spec

The two explorer apps already coalesce render and persist via `requestAnimationFrame`, batch derive into 1500-row chunks with rAF yields, narrow rematch to one library per anchor flip, and show a progress overlay during heavy operations. None of that frees the main thread for animation; all of it still runs on the UI thread. With multiple corpora loaded and step 5 selected, the main-thread cost of derive + match + sort overflows the 16.6 ms animation budget by orders of magnitude.

Spec 4 moves the heavy data pipeline off the main thread into a Web Worker, replaces the scroll listener with an `IntersectionObserver`, precomputes the Hue × Light bucket map on idle time, and prefetches all profile LUTs into Worker memory on first idle so subsequent profile switches skip fetch + decode.

All four techniques are gated by `performance.measure` rules: anything that does not meet its RAIL band threshold in measurement is removed before merge.

---

## 1. Goals + non-goals

### Goals

- Both apps meet RAIL bands on:
  - Response: any user input renders next paint in under 100 ms.
  - Animation: every frame under 16.6 ms (60 fps sustained).
  - Idle: background tasks chunked under 50 ms per slice.
  - Load: cold page → first interactive under 1000 ms on fast 3G.
- Heavy data work (derive, match, sort) runs in a Web Worker. Main thread keeps DOM + filter + user input.
- Scroll-listener pattern replaced by sentinel `IntersectionObserver`.
- Hue × Light bucket map precomputed during idle time.
- All 12 profile LUTs prefetched during idle time so second profile switch in a session is fetch-free.
- Every named technique has a measurement gate. Techniques that do not earn their place by measurement are removed.

### Non-goals

- Touch `index.html`.
- Web Worker fallback for browsers that lack Worker support. Worker is supported in every evergreen browser; Safari 14+, Chrome 90+, Firefox 88+ all qualify.
- IndexedDB persistent cache. Single session in scope.
- OffscreenCanvas for PNG export. Out of scope; defer.
- Server-Sent Events, WebSocket, or any networking other than `fetch`.
- Service Worker for offline caching. Out of scope; defer.
- React, Vue, or any framework. App stays vanilla DOM.

---

## 2. Design

### 2.1 Web Worker (per Q4 = C; derive + match + sort move to Worker)

**Architecture.**

- One Worker per app, source string embedded in the HTML in a `<script type="text/worker">` tag.
- Worker instantiated at boot via a `Blob` URL produced from the inline source. No extra file shipped, HTML stays self-contained for GH Pages serving.
- Main thread owns: UI event handlers, DOM render, filter pass, palette CRUD, export.
- Worker owns: CMYK lattice derivation, `deriveSwatch` math, `delta_e_print` round-trip, `matchNearest` per corpus, `_ensureCorpusCmykLabs`, sort comparators, Hue × Light bucket map computation.

Filter stays on main thread. User-interactive slider drags need sub-16ms response; a postMessage round-trip costs ~1-5 ms each way and would defeat the purpose. Filtering the derived data on main thread is already O(n) at ~5-10 ms on 14k rows.

**Message protocol.**

```js
// main → worker
{ type: 'init',     corpora_libraries, ui_defaults }
{ type: 'load_lut', name, buf /* ArrayBuffer, transferred */ }
{ type: 'derive',   profile_name, step }              // CMYK explorer
{ type: 'load_lib', name, payload /* parsed JSON */ } // 3D explorer
{ type: 'rematch',  lib_id, anchor }
{ type: 'sort',     mode }
{ type: 'precompute_huelight' }
{ type: 'get_huelight' }                              // returns cached map
{ type: 'set_corpora_prefs', prefs }                  // pref sync from main
{ type: 'terminate' }

// worker → main
{ type: 'progress',       task, n, m }
{ type: 'derive_ready',   main_data, gs_data }        // see "Transferable" below
{ type: 'rematch_ready',  lib_id, matches }
{ type: 'sort_ready',     mode, view }
{ type: 'huelight_ready', map }
{ type: 'error',          msg }
```

**Transferable objects.** `derive_ready` emits the per-swatch data as a struct-of-arrays of `Float32Array` and `Uint16Array` views over a single underlying `ArrayBuffer`. The second argument of `postMessage` lists the buffer in the transfer list so ownership crosses the worker boundary with zero copy.

Shape per swatch on main thread after transfer:

```js
{
  C, M, Y, K,              // uint8 0-100
  R, G, B,                 // uint8 0-255
  L_star, a_star, b_star,  // float32
  luminance, contrast_ratio,
  delta_e_print,
  hex,                     // string, computed once on main from R/G/B (cheap)
  text_color,              // '#000' | '#fff'
  wcag_aa, wcag_aaa,       // bool
  k_tier, k_tier_name,
  tac,
  grayscale,
  system_name,
  matches: { [lib_id]: { entryIdx, deltaE, anchor } }
}
```

`matches.entry` is reconstructed on main thread by indexing into the corpora it already holds (corpus entries are not serialized across the boundary; only entry indices are).

### 2.2 Sentinel IntersectionObserver (per Q5 = B)

**Markup additions.** Inside `.swatch-grid`, two zero-size markers:

```html
<div class="swatch-grid" id="swatchGrid" style="position:relative">
  <div class="io-sentinel io-top"    aria-hidden="true"></div>
  <!-- absolutely-positioned cells render here, between the sentinels -->
  <div class="io-sentinel io-bottom" aria-hidden="true"></div>
</div>
```

**JS:** the existing scroll listener + rAF throttle + `_lastWindow` cache are removed. Replaced by one `IntersectionObserver` instance whose root is the `.grid-scroll` viewport and whose targets are the two sentinels. When either sentinel crosses the viewport boundary, the IO callback fires and the visible-window indices are recomputed from `entry.intersectionRect`.

```js
const io = new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (!e.isIntersecting) continue;
    // recompute firstRow / lastRow from current scrollTop + viewport height
    paintWindow();
  }
}, {
  root: document.getElementById('gridScroll'),
  rootMargin: '500px 0px',   // pre-paint a buffer beyond the immediate viewport
});
io.observe(topSentinel);
io.observe(bottomSentinel);
```

Net effect: ~1-2 callback fires per scroll burst instead of the existing rAF-throttled scroll handler firing every animation frame. Existing `paintWindow()` function reused as-is.

### 2.3 Idle precompute: Hue × Light bucket map (per Q6 = C, with verification gate)

After `derive_ready` lands on main thread:

```js
requestIdleCallback(() => {
  worker.postMessage({ type: 'precompute_huelight' });
}, { timeout: 1500 });
```

Worker computes the 180-cell map on its own time and stores it keyed by `(profile_name, step)`. On user click into Hue × Light view:

```js
worker.postMessage({ type: 'get_huelight' });
worker.addEventListener('message', e => {
  if (e.data.type !== 'huelight_ready') return;
  // paint immediately
});
```

If precompute already done, the response is a single tick. If not (user clicked before idle ran), worker computes on demand and replies. View switch never blocks the main thread on the math.

**Verification gate.** Measurement compares median `view_switch_grid_to_huelight` with and without the precompute. If precompute does not pull the value under the RAIL response 100ms band, the section is dropped from the spec at merge time (the other 3 techniques stay).

### 2.4 Idle-time bulk LUT prefetch (per Q7 = B)

After first `derive_ready`:

```js
requestIdleCallback(() => {
  for (const profile of ICC_INDEX.profiles) {
    if (profile.lut === ACTIVE_PROFILE.lut) continue;
    fetch(profile.lut)
      .then(r => r.arrayBuffer())
      .then(buf => worker.postMessage(
        { type: 'load_lut', name: profile.lut, buf },
        [buf]                                  // transfer ownership, zero copy
      ));
  }
}, { timeout: 3000 });
```

12 profiles × ~270KB ≈ 3.3MB total. Once per session. ArrayBuffers transferred (not copied) to Worker. Worker keeps a `Map<name, parsed_lut>` cache.

Subsequent profile switches: main thread posts `{ type: 'derive', profile_name }`; Worker hits its LUT cache, skips fetch + decode, runs only the derive. Cuts profile-switch latency by ~200-400 ms on a typical residential link.

**Verification gate.** Measure 2nd profile-switch median with and without prefetch. Keep if >50 ms improvement, drop otherwise.

### 2.5 Performance instrumentation + verification

Instrumentation pattern throughout both HTMLs:

```js
function railMark(name) { performance.mark(name); }
function railMeasure(label, startMark, endMark) {
  performance.measure(label, startMark, endMark);
  const entry = performance.getEntriesByName(label).pop();
  if (entry && entry.duration > RAIL_BANDS[label]) {
    console.warn('[RAIL]', label, entry.duration.toFixed(1), 'ms exceeds', RAIL_BANDS[label]);
  }
}
const RAIL_BANDS = {
  rail_response:    100,
  rail_animation:    16.6,
  rail_idle_slice:   50,
  rail_load:       1000,
};
```

**Measurement targets (RAIL bands per Q2 = C):**

| Operation | Target | Band |
|---|---|---|
| Profile change → first cell paint | < 100 ms | Response |
| Step 10 → step 5 (full derive) | < 1000 ms, progress overlay shown | Load |
| Anchor flip (per-lib rematch) | < 100 ms | Response |
| Slider drag → next paint | < 16.6 ms | Animation |
| Scroll frame | < 16.6 ms | Animation |
| Idle precompute slice | < 50 ms per slice | Idle |
| Cold page load → first interactive | < 1000 ms (fast 3G) | Load |

**Per-technique gates:**

```
GATE-A · Web Worker derive ON vs OFF
   Median profile-switch latency must drop. Keep if so. Revert otherwise.

GATE-B · Sentinel IO vs scroll listener
   p95 scroll-frame latency must drop below 16.6 ms. Keep if so. Revert
   otherwise.

GATE-C · Hue × Light idle precompute
   Median view-switch-to-huelight must fall under 100 ms response band.
   Drop only this technique if it does not move the needle; keep the
   other three.

GATE-D · LUT prefetch
   Median 2nd-profile-switch must be >50 ms faster than 1st. Drop only
   this technique if not satisfied.
```

Worker offload (GATE-A) and Sentinel IO (GATE-B) are treated as mandatory; revert means rollback the entire Spec 4 implementation. Precompute (GATE-C) and Prefetch (GATE-D) are individually optional; drop preserves the other three.

---

## 3. File-by-file change list

| File | Change | Magnitude |
|---|---|---|
| `app/cmyk-explorer.html` | Embed Worker source as `<script type="text/worker" id="workerSrc">`; instantiate via `URL.createObjectURL(new Blob(...))`; rewire `rebuildAll` to post messages to worker, accept transferable result; route `matchNearest` / `rematchOne` / sort through worker; replace existing scroll listener block with `IntersectionObserver` + sentinels markup; add `requestIdleCallback` calls for Hue × Light precompute + LUT bulk prefetch; add `performance.mark` / `measure` instrumentation at every named gate point | ~700 inserted lines, ~250 modified |
| `app/3d-explorer.html` | Same pattern adapted: Worker holds the parsed library JSON + per-library matches; no CMYK lattice derive; `load_lib` replaces `derive` as the heavy-data message; rest identical | ~520 inserted lines, ~190 modified |
| No new files | (none) | (none) |

---

## 4. Cross-spec ordering

| Order | Reason |
|---|---|
| Spec 4 implementation **after** Specs 1 + 2 + 3 | Worker port is the largest rewrite. Doing it on already-clean (i18n applied, UX polished, tooltips rewritten) HTMLs avoids re-touching the same callsites. |
| Spec 4 measurement gates run **alongside** implementation | Each technique lands behind a build-time feature flag. Flag flips on per technique only after its gate measurement passes. |
| Spec 4 instrumentation calls (`performance.mark`) can land **earlier** as low-risk PR | Optional. Lets us baseline the current state before any optimization, so gate measurements are honest. |

---

## 5. Validation gates (in addition to the 4 measurement gates)

1. Worker instantiates without error in Chrome 90+, Firefox 88+, Safari 14+.
2. No console errors on cold load in any of the three browsers.
3. All existing functionality preserved end to end: profile switch, anchor flip, palette CRUD, filter sliders, sort, view switch, search, exports.
4. Memory profile (DevTools Memory tab) shows main-thread heap usage drops measurably with Worker offload; the missing memory now lives in the Worker heap.
5. Sustained 60 fps measured via `performance.now()` deltas across 1000 frames while scrolling the grid at step 10.
6. All 4 measurement gates (A, B, C, D) pass per their keep-or-drop rule. Gates that fail trigger the prescribed action (revert all four or drop the individual technique).
7. Em-dash / en-dash count in both HTMLs stays at zero.
8. JS in both HTMLs parses cleanly: `new Function(mainScriptBody)` and `new Function(workerScriptBody)` each succeed.
9. After idle prefetch completes, switching between any two profiles takes a fetch-free code path (verified by DevTools Network tab showing no LUT requests).

---

## 6. Open questions (none blocking)

- **Service Worker.** Would add offline + cross-session caching. Deferred to a future spec.
- **OffscreenCanvas for PNG export.** Would move the 4096x4096 export off main thread. Deferred to a future spec.
- **IndexedDB persistent LUT cache.** Would skip even the first prefetch on repeat visits. Deferred.
- **WebGPU compute for LUT interpolation.** Theoretical. Deferred indefinitely; LUT lookup is not the bottleneck after Worker offload.

---

## 7. Cross-references

- Brainstorm transcript: this session.
- Sibling specs:
  - **Spec 1** · landing honesty + GH Pages (approved, queued for plan)
  - **Spec 2** · app HTMLs tri-lingual i18n (queued for plan)
  - **Spec 3** · app UX bundle (queued for plan)
- ARCHITECTURE.md sections relevant: §8 (HTML data pipeline), §11 (performance budget). The performance budget in §11 will need updating after Spec 4 ships to reflect the new RAIL-band targets.
- RAIL model reference: Google web.dev guidance on Response / Animation / Idle / Load thresholds.
