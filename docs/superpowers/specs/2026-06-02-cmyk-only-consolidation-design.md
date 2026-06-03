# Spec 5: CMYK-Only Consolidation + Landing Honesty Finalization

**Date:** 2026-06-02
**Branch target:** `spec5-cmyk-only` (new, off `main`)
**Supersedes (in execution priority):** in-flight Spec 1 (`spec1-landing-honesty`) — its remaining tasks 3–7 are absorbed here.
**Defers:** Specs 2, 3, 4 specs + plans remain frozen on disk. Rewritten when each begins.

---

## 1. Purpose

Replace the dual-tool architecture (`cmyk-explorer.html` + `3d-explorer.html`) with a single CMYK-only browser tool. The 3D-print color-matching use case is **kept** (`cmyk-explorer.html` still serves both 2D and 3D print workflows), but the curated-library workflow (`gen_libraries.py` → `swatches.json` → `3d-explorer.html`) is **retired**. The one feature worth preserving from the 3D explorer — the ΔE max filter slider — is ported into `cmyk-explorer.html` using its existing per-swatch `delta_e_print` round-trip field. The repo simplifies to one tool, one entrypoint, one mental model.

Spec 1's remaining landing-honesty tasks (Fix B, Fix C, footer URL rewrite, `.nojekyll`, validation) execute on the same branch.

## 2. Out of Scope

- Specs 2 / 3 / 4 implementation. Their spec + plan files stay frozen on disk and are rewritten when each spec begins.
- `swatches.py` — already untouched per prior contract.
- ICC profile redistribution — `.gitignore` still blocks `icc/*.icc` / `icc/*.icm`.
- Any change to telemetry posture — no upload, no telemetry remains invariant.

## 3. Architecture

### 3.1 Before

```
index.html (landing, tri-lingual, 2 tool cards)
  ├─ app/cmyk-explorer.html  (live lattice via ICC LUT, full CMYK range filters)
  └─ app/3d-explorer.html    (loads swatches/swatches.json, ΔE max filter)

scripts/
  ├─ gen_luts.py             (ICC → 17⁴ LUT binary, used by cmyk-explorer)
  └─ gen_libraries.py        (ICC → curated swatches.json, used by 3d-explorer)
```

### 3.2 After

```
index.html (landing, tri-lingual, 1 tool card)
  └─ app/cmyk-explorer.html  (live lattice via ICC LUT + NEW ΔE max filter)

scripts/
  └─ gen_luts.py             (unchanged)
```

### 3.3 ΔE max slider port — implementation contract

- New sidebar slider `slDEmax` + value display `vDEmax`, placed adjacent to the existing TAC slider in the sidebar.
- Range: `0.0` … `10.0`, step `0.1`, default `null` (off).
- When off (default): no swatches hidden by this filter. Backwards-compatible with prior behavior.
- When set to value V: filter pipeline hides any swatch with `delta_e_print > V`.
- Reuses already-computed `delta_e_print` from the round-trip safety sort path. No new computation cost.
- localStorage key: `mixoDEmax_v1`. Persists across reload like other sliders.
- Tooltip copy (EN): "Hide swatches whose round-trip color drift exceeds this ΔE. Off = show all. 0.5 = mathematically equal under the profile. 1.0 = trained-eye limit."
- Off-state UI: slider thumb at far-left labeled "off" (not `0.0`, which means "perfect match only").

### 3.4 Single source of truth for use-case framing

`cmyk-explorer.html` is the only tool. Landing copy frames it as serving:
- 2D print (flat / coated / uncoated CMYK presses)
- 3D color printing (Mimaki 3DUJ class)
- Screen mockup (via hex)

The "3D Print" use case is preserved in hero + body copy. Only the dual-tool framing ("3D explorer browses the pre-filtered safe set") is dropped.

## 4. File-Level Changes

### 4.1 Deletions

| Path | Reason |
|---|---|
| `app/3d-explorer.html` | Tool retired |
| `scripts/gen_libraries.py` | Sole consumer was 3d-explorer |
| `swatches/` (folder, currently empty) | Output dir of `gen_libraries.py` |

### 4.2 Modifications

**`app/cmyk-explorer.html`:**
- Add ΔE max slider markup + value display
- Add slider event handler `onDEmax(v)` filtering pipeline
- Add localStorage read/write for `mixoDEmax_v1`
- Include slider state in `resetUIToDefaults()`

**`index.html`:**
- Tool card row: drop 3d-explorer card; cmyk-explorer card centered or full-width
- Hero subheadline: keep "Screen × Flat Print × 3D Print" framing (use case preserved); drop any "two tools" implication
- "Same library serves 2D print and 3D-print" paragraph (~line 1577): rephrase to "One tool serves 2D print and 3D-print color matching." Keep tri-lingual triple.
- "Curated for 3D Modeling × 3D Coloured Print" section (~lines 1617–1632): drop entirely (was 3d-explorer-specific framing). Tri-lingual triple count drops by 1 set.
- Footer Architecture section (~lines 2245–2249): drop "the 3D explorer browses the pre-filtered safe set you just produced" clause. Replace with single-tool framing.

**`ARCHITECTURE.md`:**
- Drop 3d-explorer column from any comparison tables
- Drop `gen_libraries.py` workflow chapter
- Drop `swatches.json` schema chapter
- Drop 3d-explorer feature descriptions

**`README.md`:**
- Drop 3d-explorer mentions
- Drop `gen_libraries.py` install/run instructions

**`run.sh` + `run.bat`:**
- Drop the `3D explorer: http://localhost:8765/app/3d-explorer.html` echo line in both

**`data/ui_defaults.json`:**
- Remove entire `3d_explorer` block
- Add `delta_e_max: null` to `cmyk_explorer` block (default off)
- Update `_doc` string: drop `cmykUIState3d_v1` mention; reference `cmykUIState_v1` only

### 4.3 Untouched

| Path | Reason |
|---|---|
| `scripts/gen_luts.py` | Still needed for cmyk-explorer's LUTs |
| `icc/` + `icc/luts/` | Same |
| `data/corpora/name_corpora.json` | Shared corpora, not 3d-specific |
| `swatches.py` (top-level, if present) | Per prior untouched contract |
| All Spec 2 / 3 / 4 spec + plan files in `docs/superpowers/` | Frozen, rewritten at kickoff |
| `index.html` landing tri-lingual `data-en/ja/zh` structural pattern | Preserved verbatim across all surviving content |

## 5. Absorbed Spec 1 Tasks 3–7

These continue under Spec 5 numbering (Tasks 5.6 onwards in the plan). Specs unchanged:

| Original | Description |
|---|---|
| Spec 1 Task 3 (Fix B) | Batch export interop tiers honesty pass on landing |
| Spec 1 Task 4 (Fix C) | LUT interpolation drift named explicitly on landing |
| Spec 1 Task 5 | Footer URL rewrite to `github.com/mixocreative/mixoswatch` blob URLs |
| Spec 1 Task 6 | Create `.nojekyll` at repo root |
| Spec 1 Task 7 | Final validation suite (em-dash count, triple balance, JS parse, GH Pages target) |

Verbatim Spec 1 content (paragraph swap targets, exact strings) carries over without rewriting — only the task numbering rehomes.

## 6. Branch Strategy

1. Stash WIP on `spec1-landing-honesty` (7 modified files): `git stash push -m "spec1-wip-pre-spec5"`
2. Create new branch off `main`: `git checkout main && git checkout -b spec5-cmyk-only`
3. Cherry-pick in order:
   - `56abfac` (em-dash pre-flight fix on `index.html`)
   - `b290e2a` (Fix A: Real ICC math paragraph swap)
4. Pop stash, audit each restored file:
   - `.gitignore`, `ARCHITECTURE.md`, `README.md`, `app/cmyk-explorer.html`, `data/corpora/name_corpora.json`, `data/ui_defaults.json` — likely relevant to Spec 5, keep + audit
   - `app/3d-explorer.html` — about to be deleted, can be dropped
5. Abandon `spec1-landing-honesty` branch (left in repo as historical; not deleted).

## 7. Verification

### 7.1 Per-task gates

- Em-dash + en-dash count = 0 in modified files: `grep -c "—\|–" index.html app/cmyk-explorer.html ARCHITECTURE.md README.md run.sh run.bat`
- Triple balance in `index.html`: `data-en` count = `data-ja` count = `data-zh` count
- JS parse: node syntax check on all inline `<script>` blocks of `index.html` + `app/cmyk-explorer.html`
- Zero remaining `3d-explorer` references: `grep -ri "3d-explorer\|3d_explorer" . --exclude-dir=.git --exclude-dir=docs/superpowers/specs --exclude-dir=docs/superpowers/plans`
- Zero remaining `gen_libraries` / `swatches.json` references (same scope)
- `gen_luts.py` still runs to completion on at least one ICC profile (smoke test)

### 7.2 ΔE max slider behavior

- Default (off): same swatch count as pre-port build
- Slider at 1.0: only swatches with `delta_e_print ≤ 1.0` visible
- Slider at 0.5: subset of the 1.0 result, all with `delta_e_print ≤ 0.5`
- Reload page → slider state persists from `mixoDEmax_v1`
- Click "Reset UI to defaults" → slider returns to off

### 7.3 Landing render

- One tool card visible. Centered or full-width depending on layout decision at plan time.
- Hero retains "Screen × Flat Print × 3D Print" triple use-case framing
- Footer Architecture clause reads as single-tool
- No 404 from landing → click → cmyk-explorer opens
- Lighthouse on landing: no broken anchors, no broken external links

### 7.4 Architectural invariants (regression checks)

- `.gitignore` still contains `icc/*.icc` and `icc/*.icm` blocks
- No upload / no telemetry: zero `fetch(` calls to non-relative URLs in `app/cmyk-explorer.html` (existing pattern check)
- Japanese register: `印刷` not appearing in standalone JA strings (was tooled into プリント / プリンター); compounds like `プリプレス` may remain. ZH strings untouched.

## 8. Risks + Mitigations

| Risk | Mitigation |
|---|---|
| Cherry-pick conflict on `index.html` ~line 2277 | Both `56afac` and `b290e2a` modify the same region in sequence on `spec1-landing-honesty`; cherry-pick in original order onto fresh `main` reproduces the same sequence — conflict-free unless `main` has drifted (it has not; checked at brainstorm time) |
| Stashed WIP contains unrelated changes | Audit each file post-pop; revert files not relevant to Spec 5 |
| `swatches/` empty but referenced elsewhere | Grep cleanup catches stragglers; folder safe to remove |
| Landing layout assumed 2 tool cards | Plan-time check before commit; switch to `max-w-md mx-auto` centering for single card |
| ΔE max slider hides too aggressively at default 0.0 | Default is **off** (null), not 0.0; slider has explicit "off" position at far-left distinct from "0.0" |
| `data/ui_defaults.json` schema break for existing users on first reload | New key `delta_e_max: null` is additive and ignored by old explorer code; removed `3d_explorer` block has no consumer post-deletion |
| Frozen Spec 2/3/4 plans reference 3d-explorer | Acceptable — they will be rewritten before execution; current state is "pre-3d-removal" and that is recorded in the Spec 5 commit message |

## 9. Open Questions

None. All scoping decisions resolved during brainstorm:
- ΔE max slider only ported; library loader + `gen_libraries.py` dropped (chose option c, Q2)
- New branch `spec5-cmyk-only` with cherry-pick (Q3 / Q5)
- Spec 1 tasks 3–7 absorbed (Q4)
- Folder structure preserved: `app/cmyk-explorer.html` stays (Q5)
- Specs 2/3/4 frozen on disk, defer rewrite (Q6)

## 10. Acceptance

Spec 5 is complete when:

1. Branch `spec5-cmyk-only` contains all changes in section 4
2. All verification gates in section 7 pass
3. Original Spec 1 tasks 3–7 land as commits on the same branch
4. Landing renders correctly in a browser; cmyk-explorer renders correctly with ΔE max slider working at off / 1.0 / 0.5 / 0.0
5. `gen_luts.py` smoke-tested against one ICC profile
6. No remaining 3d-explorer / gen_libraries / swatches.json references outside `docs/superpowers/{specs,plans}/` (frozen prior docs)
7. Implementation plan written via `superpowers:writing-plans` and committed
