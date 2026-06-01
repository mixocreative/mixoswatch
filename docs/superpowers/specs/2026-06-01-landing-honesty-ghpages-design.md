# Spec 1 · Landing honesty pass + GitHub Pages hosting

**Date:** 2026-06-01
**Author:** mixocreative (via brainstorm cycle)
**Scope:** `index.html`, repository hosting config (no app HTMLs touched)
**Status:** awaiting user review

---

## 0. Why this spec

Two distinct but co-located needs surfaced in one brainstorm:

1. The landing page contains marketing copy that overclaims the relationship between our LUT pipeline, LittleCMS, and "the press RIP". Honest framing must replace it before public deploy.
2. The repository is structurally GH-Pages-ready but lacks the small artifacts (`.nojekyll`, footer URLs to GitHub Markdown viewer) needed for a clean first deploy.

Both ship together because the publish event is the same.

Out of scope for this spec (queued separately): tri-lingual app HTMLs, sidebar 4-step refinement on explorers, a11y / tooltip / loading audit, latency hardening.

---

## 1. Goals + non-goals

### Goals

- Replace 3 specific paragraphs of `index.html` with honest copy (EN locked, JA + ZH translated) so the page can be deployed without overclaim.
- Add `.nojekyll` to the repo root so GitHub Pages serves files verbatim and never re-evaluates Jekyll.
- Rewrite the footer's `README.md` and `ARCHITECTURE.md` links to GitHub Markdown blob viewer URLs so they render formatted instead of returning raw text.

### Non-goals

- Touch any other paragraph on the landing.
- Touch any file under `app/`, `scripts/`, `data/`, or `icc/`.
- Set up CI / GitHub Actions.
- Add a custom domain (`CNAME`).
- Add a `404.html` (default GH Pages 404 is fine for v1).

---

## 2. Honesty fixes (3 paragraph replacements)

Three paragraphs in `index.html` overclaim. EN locked, JA + ZH translations locked. All three are tri-lingual `<span data-en/ja/zh>` triples already present in the file; this spec swaps inner content only.

### 2.1 Fix A · `#why` advantages column, paragraph 2

**Location:** inside the "What this solves" `.col` block.

**Current EN:**

> Real RIP math, not Photoshop guesses. Our lookup tables are sampled from the same Pillow / LittleCMS engine a print RIP uses. The color on screen is the color the RIP will hand the press, before paper and ink physically remix it.

**New EN:**

> **Real ICC math, not Photoshop guesses.** Our lookup tables sample sRGB → CMYK at LittleCMS, the open-source color engine inside GIMP, Scribus, Krita, and many prepress tools. The data layer matches what a LittleCMS prepress flow computes. What your monitor renders is still sRGB, and what your press lays down still depends on stock, ink, and lighting.

**New JA:**

> 本物のICC演算、Photoshopの推測ではない。当ツールのLUTは、GIMP、Scribus、Krita、多くのプリプレスツールの内部で動いているオープンソースの色エンジン「LittleCMS」でsRGB → CMYKを標本化している。データ層はLittleCMSベースのプリプレスフローと同じ計算結果を返す。モニタに映る色はsRGBのレンダリング、プリンターに乗る色は依然として用紙・インク・照明に依存する。

**New ZH:**

> 真實的 ICC 演算，不是 Photoshop 的猜測。我們的查找表在 LittleCMS 取樣 sRGB → CMYK。LittleCMS 是 GIMP、Scribus、Krita 與許多印前工具內部使用的開源色彩引擎。資料層計算結果與 LittleCMS 印前流程一致。螢幕呈現的仍是 sRGB，印刷機落紙的顏色仍受紙張、油墨與光照影響。

**Verification basis:** ARCHITECTURE.md §4.1 (Pillow + LittleCMS, intent = Relative Colorimetric) and §4.4 (gen_luts.py uses `ImageCms.applyTransform`). LittleCMS is the engine; the claim "many RIPs use it" was unverifiable, so the new copy names the four specific consumers we can attest to (GIMP, Scribus, Krita, "many prepress tools") and explicitly disclaims monitor + press as out of scope.

---

### 2.2 Fix B · `#why` key-features column, "Batch export" paragraph

**Location:** inside the "What is unique" `.col` block.

**Current EN:**

> Batch export for 3D print pipelines. Every palette exports as ASE (Photoshop / Affinity / Substance), GPL (GIMP / Krita / Inkscape / Blender), PNG sheet, and JSON. Same swatches drop straight into Mimaki RasterLink, Stratasys GrabCAD Print, Cura material libraries, or your CAD's color manager.

**New EN:**

> **Batch export, two interop tiers.** *Direct:* ASE for Photoshop / Illustrator / Affinity / Substance, GPL for GIMP / Krita / Inkscape / Blender (via the GPL Palette Importer add-on), PNG sheet for any visual reference. *Indirect:* copy CMYK or hex values out of the JSON into Mimaki RasterLink spot tables, Stratasys GrabCAD pickers, Cura material profiles, or your CAD's color manager. The swatch files target design apps; the JSON is the bridge to 3D-print pipelines.

**New JA:**

> バッチ書き出し、二層の互換ルート。直接層：Photoshop / Illustrator / Affinity / SubstanceにASE、GIMP / Krita / Inkscape / Blender（GPL Palette Importerアドオン経由）にGPL、視覚参照用にPNGシート。間接層：JSONからCMYKまたはhex値をコピーし、Mimaki RasterLinkのスポットテーブル、Stratasys GrabCADのピッカー、Curaのマテリアルプロファイル、CADのカラーマネージャに入れる。スウォッチファイルはデザインアプリ向け、JSONは3Dプリントパイプラインへの橋渡し。

**New ZH:**

> 批次匯出，兩種介接層級。直接層：ASE 給 Photoshop / Illustrator / Affinity / Substance，GPL 給 GIMP / Krita / Inkscape / Blender（透過 GPL Palette Importer 外掛）、PNG 圖片做視覺參考。間接層：從 JSON 複製 CMYK 或 hex 數值，填入 Mimaki RasterLink 專色表、Stratasys GrabCAD 取色器、Cura 材料描述檔，或你 CAD 的色彩管理器。色票檔針對設計軟體，JSON 是進入 3D 列印流程的橋樑。

**Verification basis:** ASE / GPL formats import natively into the four design apps named in the Direct tier (verified against ARCHITECTURE.md §5.7, §5.8 and against each app's documented swatch-import paths). Mimaki RasterLink, Stratasys GrabCAD Print, and Cura do NOT ingest ASE/GPL; they accept CMYK/hex values via their own data entry. New copy separates the two tiers explicitly and names the JSON as the bridge.

---

### 2.3 Fix C · `#byo` opening paragraph

**Location:** first `<p>` directly after the `#byo` `<h3>`.

**Current EN:**

> The browser tools never touch the ICC binary. Two Python scripts do the heavy color math offline and emit small data files the HTML pages fetch. Same color engine your press RIP uses (Pillow's LittleCMS binding), same intent (Relative Colorimetric), no approximation drift.

**New EN:**

> The browser tools never touch the ICC binary. Two Python scripts do the heavy color math offline and emit small data files the HTML pages fetch. Same color engine many prepress tools and FOSS RIPs share (Pillow's LittleCMS binding), same intent (Relative Colorimetric). Interpolation between LUT nodes adds about ΔE 0.3 of drift, well below the threshold of human perception.

**New JA:**

> ブラウザツールはICCバイナリに直接触れない。二つのPythonスクリプトがオフラインで色彩演算を行い、HTMLが読み込む小さなデータファイルを書き出す。多くのプリプレスツールやFOSS RIPが共有する色エンジン（PillowのLittleCMSバインディング）と同じ、同じインテント（相対比色）。LUTノード間の補間で約 ΔE 0.3 の誤差が生じるが、人間の知覚閾値を十分下回る。

**New ZH:**

> 瀏覽器工具不直接接觸 ICC 二進位檔。兩支 Python 腳本在離線時做完所有色彩運算，產出 HTML 讀取的小型資料檔。與許多印前工具及 FOSS RIP 共用的色彩引擎（Pillow 的 LittleCMS 綁定）、相同的渲染目的（相對色度）。LUT 節點之間的內插帶來約 ΔE 0.3 的偏差，遠低於人眼可察覺的閾值。

**Verification basis:** ARCHITECTURE.md §4.1: "interpolation error ~ΔE 0.3, perceptually invisible." The previous "no approximation drift" statement was mathematically incorrect; the new copy names the magnitude and frames it as below the perceptual threshold.

---

## 3. GitHub Pages hosting changes

### 3.1 Add `.nojekyll`

**Action:** Create `S:\mixoswatch\.nojekyll` as a zero-byte file.

**Why:** Disables GitHub's Jekyll preprocessing step. Skips a build pass we don't need, and protects against any future filename starting with `_` being silently dropped (e.g., a future `_locale/` folder).

**Zero downside:** GH Pages serves the file tree verbatim. No behavior change for any current file.

---

### 3.2 Rewrite footer markdown links

**Location:** `<footer>` block at the bottom of `index.html`.

**Current markup:**

```html
<footer>
  <a href="README.md">README</a>
  <span class="sep">·</span>
  <a href="ARCHITECTURE.md">Architecture</a>
  <span class="sep">·</span>
  <a href="https://github.com/">Repository</a>
</footer>
```

**New markup:**

```html
<footer>
  <a href="https://github.com/mixocreative/mixoswatch/blob/main/README.md" target="_blank" rel="noopener">README</a>
  <span class="sep">·</span>
  <a href="https://github.com/mixocreative/mixoswatch/blob/main/ARCHITECTURE.md" target="_blank" rel="noopener">Architecture</a>
  <span class="sep">·</span>
  <a href="https://github.com/mixocreative/mixoswatch" target="_blank" rel="noopener">Repository</a>
</footer>
```

**Why:** GitHub Pages serves `.md` files as raw text (browser displays source). The `/blob/main/<file>.md` URL routes through GitHub's Markdown renderer + repo chrome. `target="_blank"` opens the repo viewer in a new tab so the landing tab stays alive. `rel="noopener"` is the standard security hygiene for `target=_blank` links.

---

### 3.3 Deploy strategy (documentation only)

No file change. Decision recorded for the implementation plan:

- **Source:** Settings → Pages → Source: Deploy from a branch, `main`, `/` (root).
- **Artifacts already tracked:** `data/luts/*.lut`, `data/luts/*.rcmyk.lut`, `data/luts/index.json`, `data/libraries/*.json`, `data/libraries/library_index.json`, `data/corpora/name_corpora.json`, `data/ui_defaults.json`. Verified via `git ls-files data/`.
- **Artifacts still gitignored:** `icc/*.icc`, `icc/*.icm`. Stay out. Users bring their own per the README workflow.
- **No CNAME this round.** Default URL: `https://mixocreative.github.io/mixoswatch/`.
- **No CI workflow this round.** Pages auto-rebuilds on push to `main`.

---

## 4. File-by-file change list

| File | Change | Lines touched (approx) |
|---|---|---|
| `index.html` | Replace 3 `<p>` blocks (Fix A, B, C); 3 × 3 = 9 inner-span swaps | ~30 lines |
| `index.html` | Rewrite 3 `<a>` tags in `<footer>` | 3 lines |
| `.nojekyll` (new) | Create zero-byte file | new file |

No other files touched.

---

## 5. Validation gates (post-implementation)

The implementation plan will enforce these gates before the spec is considered shipped:

1. `index.html` JS still parses cleanly (`new Function(scriptBody)` succeeds).
2. Em-dash / en-dash count in `index.html` stays at 0 (project hard rule).
3. `data-en` / `data-ja` / `data-zh` triples remain balanced (no language goes missing on any of the 3 fixed paragraphs).
4. Footer links resolve to live URLs (HTTP 200 against `https://github.com/mixocreative/mixoswatch/...`) once the repo is public.
5. `.nojekyll` file exists at repo root, zero bytes.

---

## 6. Open questions (none blocking)

- Custom domain? Deferred until later round. Default `<user>.github.io/<repo>/` is fine for v1.
- Should ARCHITECTURE.md footer reference §-numbers explicitly? Not in this spec. Could be added when Section 2 of the brainstorm cycle picks up app i18n.

---

## 7. Cross-references

- Brainstorm transcript: this session.
- Related queued specs (will brainstorm separately):
  - **Spec 2** · app HTMLs tri-lingual i18n
  - **Spec 3** · app UX refinement bundle (sidebar 4-step refine, a11y, tooltips, loading states, text-select forbid)
  - **Spec 4** · app latency hardening (Worker, IntersectionObserver, prefetch)
- Source verification: `ARCHITECTURE.md` §2.2, §2.4, §4.1, §4.4, §5.7, §5.8.
