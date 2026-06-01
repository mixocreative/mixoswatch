# Spec 1 Implementation Plan · Landing honesty + GH Pages hosting

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 3 overclaim paragraphs in `index.html` with honest copy, rewrite the footer markdown links to GitHub's `/blob/main/` viewer URLs, and add a zero-byte `.nojekyll` file so GitHub Pages can serve the repo verbatim.

**Architecture:** Pure text-replacement work plus one new zero-byte file. No JS logic changes. No CSS changes. No file moves. Each fix is a single Edit-tool replace_all, verified by grep, then committed.

**Tech Stack:** Vanilla HTML, no build step. Verification via `grep` (em-dash audit, `data-en/ja/zh` triple balance) and `node -e "new Function(scriptBody)"` (JS parse check). Git for version control.

**Reference spec:** `docs/superpowers/specs/2026-06-01-landing-honesty-ghpages-design.md`

---

## File Structure

| File | Action | Reason |
|---|---|---|
| `index.html` | Modify | Three paragraph swaps + footer URL rewrite |
| `.nojekyll` | Create | Zero-byte file; disables GH Pages Jekyll preprocessing |
| `docs/superpowers/plans/2026-06-01-spec1-landing-honesty-ghpages.md` | Already this file | Plan record |

No other files touched. No new directories.

---

## Task 1: Pre-flight baseline

**Files:**
- Read: `index.html`

- [ ] **Step 1: Confirm working tree is on `main` and clean of conflicting changes**

Run:
```bash
cd S:/mixoswatch && git status --short
```
Expected: zero modifications to `index.html` (other files may be modified from earlier sessions, ignore them; do not commit them as part of this plan).

If `index.html` is modified, stop and reconcile before continuing. The plan assumes a clean baseline for `index.html`.

- [ ] **Step 2: Record baseline em-dash count**

Run:
```bash
grep -c "—\|–" "S:/mixoswatch/index.html"
```
Expected output: `0`

If non-zero, stop and fix the existing em-dashes before applying this plan.

- [ ] **Step 3: Record baseline JS parse status**

Run:
```bash
node -e "const fs=require('fs');const html=fs.readFileSync('S:/mixoswatch/index.html','utf-8');const m=html.match(/<script>([\\s\\S]*?)<\\/script>/);try{new Function(m[1]);console.log('JS OK');}catch(e){console.log('ERR:',e.message);}"
```
Expected output: `JS OK`

If `ERR:`, stop and fix the JS before applying this plan.

- [ ] **Step 4: Record baseline `data-en` / `data-ja` / `data-zh` counts**

Run:
```bash
grep -c 'data-en' "S:/mixoswatch/index.html" && grep -c 'data-ja' "S:/mixoswatch/index.html" && grep -c 'data-zh' "S:/mixoswatch/index.html"
```
Note the three numbers. They should be equal (every translated span has the full triple). Record them; later validation will compare these to the post-fix counts.

---

## Task 2: Fix A · swap `#why` advantages paragraph 2

**Files:**
- Modify: `index.html` (the paragraph wraps three sibling spans inside a `<p>` in the "What this solves" `.col`)

- [ ] **Step 1: Locate the target paragraph**

Run:
```bash
grep -n "Real RIP math" "S:/mixoswatch/index.html"
```
Expected: exactly 1 match on the EN span (line number will vary). If 0 or >1, stop and confirm the spec target paragraph hasn't already been edited or duplicated.

- [ ] **Step 2: Replace EN span**

Use the Edit tool with:

`old_string`:
```
            <span data-en><b>Real RIP math, not Photoshop guesses.</b> Our lookup tables are sampled from the same Pillow / LittleCMS engine a print RIP uses. The color on screen is the color the RIP will hand the press, before paper and ink physically remix it.</span>
```

`new_string`:
```
            <span data-en><b>Real ICC math, not Photoshop guesses.</b> Our lookup tables sample sRGB → CMYK at LittleCMS, the open-source color engine inside GIMP, Scribus, Krita, and many prepress tools. The data layer matches what a LittleCMS prepress flow computes. What your monitor renders is still sRGB, and what your press lays down still depends on stock, ink, and lighting.</span>
```

If the Edit tool reports `String to replace not found`, run the grep from Step 1 and inspect the actual current EN text; the exact source string may include slightly different surrounding markup. Update `old_string` to match the live HTML byte-for-byte and re-run Edit.

- [ ] **Step 3: Replace JA span**

Use the Edit tool with:

`old_string`:
```
            <span data-ja><b>本物のRIP演算、Photoshopの推測ではない。</b>当ツールのLUTは、プリントRIPと同じPillow / LittleCMSエンジンで標本化。画面上の色はRIPがプリンターに渡す色（紙とインクが物理的に再混合する直前の色）。</span>
```

`new_string`:
```
            <span data-ja>本物のICC演算、Photoshopの推測ではない。当ツールのLUTは、GIMP、Scribus、Krita、多くのプリプレスツールの内部で動いているオープンソースの色エンジン「LittleCMS」でsRGB → CMYKを標本化している。データ層はLittleCMSベースのプリプレスフローと同じ計算結果を返す。モニタに映る色はsRGBのレンダリング、プリンターに乗る色は依然として用紙・インク・照明に依存する。</span>
```

If `String to replace not found`, the JA source in the live file differs from the version above (likely because the project's `印刷` → `プリント` rule already transformed the original; if so the JA source may instead read `プリントRIP` / `プリンター`). Run:
```bash
grep -n "本物のRIP演算\|本物のICC演算\|プリントRIPと同じPillow" "S:/mixoswatch/index.html"
```
Use the actual line as the `old_string`.

- [ ] **Step 4: Replace ZH span**

Use the Edit tool with:

`old_string`:
```
            <span data-zh><b>真實 RIP 演算，不是 Photoshop 的猜測。</b>查找表來自與印刷 RIP 相同的 Pillow / LittleCMS 引擎。螢幕上的色就是 RIP 即將遞給印刷機的色（在紙與油墨物理上再混合之前）。</span>
```

`new_string`:
```
            <span data-zh>真實的 ICC 演算，不是 Photoshop 的猜測。我們的查找表在 LittleCMS 取樣 sRGB → CMYK。LittleCMS 是 GIMP、Scribus、Krita 與許多印前工具內部使用的開源色彩引擎。資料層計算結果與 LittleCMS 印前流程一致。螢幕呈現的仍是 sRGB，印刷機落紙的顏色仍受紙張、油墨與光照影響。</span>
```

- [ ] **Step 5: Verify all three swaps landed**

Run:
```bash
grep -c "Real ICC math, not Photoshop guesses" "S:/mixoswatch/index.html"
grep -c "本物のICC演算" "S:/mixoswatch/index.html"
grep -c "真實的 ICC 演算" "S:/mixoswatch/index.html"
grep -c "Real RIP math, not Photoshop guesses" "S:/mixoswatch/index.html"
```
Expected: first three return `1`, last returns `0`. The fourth check confirms the old EN copy is gone.

- [ ] **Step 6: Verify em-dash count still zero**

Run:
```bash
grep -c "—\|–" "S:/mixoswatch/index.html"
```
Expected output: `0`

If non-zero, run `grep -n "—\|–" "S:/mixoswatch/index.html"` to locate the offending dash and replace with the appropriate ASCII alternative (comma, colon, or "to").

- [ ] **Step 7: Verify JS still parses**

Run:
```bash
node -e "const fs=require('fs');const html=fs.readFileSync('S:/mixoswatch/index.html','utf-8');const m=html.match(/<script>([\\s\\S]*?)<\\/script>/);try{new Function(m[1]);console.log('JS OK');}catch(e){console.log('ERR:',e.message);}"
```
Expected: `JS OK`

- [ ] **Step 8: Verify `data-en/ja/zh` triple balance unchanged**

Run:
```bash
grep -c 'data-en' "S:/mixoswatch/index.html" && grep -c 'data-ja' "S:/mixoswatch/index.html" && grep -c 'data-zh' "S:/mixoswatch/index.html"
```
Expected: three equal numbers identical to the baseline recorded in Task 1 Step 4.

- [ ] **Step 9: Commit Fix A**

Run:
```bash
cd S:/mixoswatch && git add index.html && git commit -m "fix(landing): honest framing for ICC math claim (Fix A)

Per Spec 1 §2.1. Drop 'same engine the RIP uses' overclaim; name actual
LittleCMS consumers (GIMP, Scribus, Krita, many prepress tools);
explicitly disclaim monitor and press as out of our control.

Tri-lingual: EN + JA + ZH all swapped together to preserve data-en/ja/zh
triple balance.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

Expected: commit succeeds, working tree shows `index.html` no longer modified.

---

## Task 3: Fix B · swap `#why` key-features "Batch export" paragraph

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

- [ ] **Step 6: Verify em-dash count, JS parse, triple balance**

Same three commands as Task 2 Steps 6, 7, 8. Expected: `0`, `JS OK`, equal triple counts.

- [ ] **Step 7: Commit Fix B**

Run:
```bash
cd S:/mixoswatch && git add index.html && git commit -m "fix(landing): split batch export into direct + indirect tiers (Fix B)

Per Spec 1 §2.2. Stop claiming ASE/GPL drop straight into Mimaki
RasterLink, Stratasys GrabCAD, or Cura (those apps don't ingest ASE
or GPL). Name the actual direct-load design apps; name the indirect
copy-the-value path for 3D-print pipelines.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: Fix C · swap `#byo` opening paragraph

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
      <span data-en>The browser tools never touch the ICC binary. Two Python scripts do the heavy color math offline and emit small data files the HTML pages fetch. Same color engine many prepress tools and FOSS RIPs share (Pillow's LittleCMS binding), same intent (Relative Colorimetric). Interpolation between LUT nodes adds about ΔE 0.3 of drift, well below the threshold of human perception.</span>
```

- [ ] **Step 3: Replace JA span**

Use the Edit tool with:

`old_string`:
```
      <span data-ja>ブラウザツールはICCバイナリに直接触れない。二つのPythonスクリプトがオフラインで色彩演算を行い、HTMLが読み込む小さなデータファイルを書き出す。プリントRIPと同じ色エンジン（PillowのLittleCMSバインディング）、同じインテント（相対比色）、近似による誤差なし。</span>
```

`new_string`:
```
      <span data-ja>ブラウザツールはICCバイナリに直接触れない。二つのPythonスクリプトがオフラインで色彩演算を行い、HTMLが読み込む小さなデータファイルを書き出す。多くのプリプレスツールやFOSS RIPが共有する色エンジン（PillowのLittleCMSバインディング）と同じ、同じインテント（相対比色）。LUTノード間の補間で約 ΔE 0.3 の誤差が生じるが、人間の知覚閾値を十分下回る。</span>
```

- [ ] **Step 4: Replace ZH span**

Use the Edit tool with:

`old_string`:
```
      <span data-zh>瀏覽器工具不直接接觸 ICC 二進位檔。兩支 Python 腳本在離線時做完所有色彩運算，產出 HTML 讀取的小型資料檔。使用與印刷 RIP 相同的色彩引擎（Pillow 的 LittleCMS 綁定）、相同的渲染目的（相對色度），無近似誤差。</span>
```

`new_string`:
```
      <span data-zh>瀏覽器工具不直接接觸 ICC 二進位檔。兩支 Python 腳本在離線時做完所有色彩運算，產出 HTML 讀取的小型資料檔。與許多印前工具及 FOSS RIP 共用的色彩引擎（Pillow 的 LittleCMS 綁定）、相同的渲染目的（相對色度）。LUT 節點之間的內插帶來約 ΔE 0.3 的偏差，遠低於人眼可察覺的閾值。</span>
```

- [ ] **Step 5: Verify swaps**

Run:
```bash
grep -c "many prepress tools and FOSS RIPs share" "S:/mixoswatch/index.html"
grep -c "多くのプリプレスツールやFOSS RIPが共有する" "S:/mixoswatch/index.html"
grep -c "與許多印前工具及 FOSS RIP 共用的" "S:/mixoswatch/index.html"
grep -c "no approximation drift" "S:/mixoswatch/index.html"
```
Expected: first three return `1`, last returns `0`.

- [ ] **Step 6: Em-dash + JS parse + triple balance verification**

Same three commands. Expected: `0`, `JS OK`, equal triple counts.

- [ ] **Step 7: Commit Fix C**

Run:
```bash
cd S:/mixoswatch && git add index.html && git commit -m "fix(landing): name LUT interpolation drift explicitly (Fix C)

Per Spec 1 §2.3. Replace 'no approximation drift' (mathematically
incorrect; 17-node LUT interpolation adds ~ΔE 0.3 per ARCHITECTURE.md
§4.1) with the actual magnitude framed as below the perceptual
threshold. Also drop the 'engine the RIP uses' overclaim in the same
paragraph.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: Footer URL rewrite

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

Per Spec 1 §3.2. GitHub Pages serves .md files as raw text; the
/blob/main/ URL routes through GitHub's Markdown renderer.
target=_blank lets the landing tab stay alive; rel=noopener is
standard security hygiene for target=_blank.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 6: Create `.nojekyll`

**Files:**
- Create: `.nojekyll`

- [ ] **Step 1: Confirm the file does not exist yet**

Run:
```bash
ls -la "S:/mixoswatch/.nojekyll" 2>&1
```
Expected: `ls: cannot access ...: No such file or directory` (or PowerShell equivalent).

- [ ] **Step 2: Create the zero-byte file**

Use the Write tool with:

`file_path`: `S:\mixoswatch\.nojekyll`
`content`: (empty string, zero bytes)

If the Write tool refuses to create a zero-byte file, use Bash:
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

Per Spec 1 §3.1. Disables Jekyll preprocessing on GitHub Pages.
Future-proofs against any path that starts with underscore being
silently dropped. Zero bytes; no behavior change for any current file.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

The `-f` flag is required because dotfiles can be ignored by some `.gitignore` configurations. If the existing `.gitignore` does not match `.nojekyll`, the `-f` flag is harmless.

---

## Task 7: Final validation suite

This task confirms all Spec 1 §5 validation gates pass at once.

- [ ] **Step 1: JS parse**

Run:
```bash
node -e "const fs=require('fs');const html=fs.readFileSync('S:/mixoswatch/index.html','utf-8');const m=html.match(/<script>([\\s\\S]*?)<\\/script>/);try{new Function(m[1]);console.log('JS OK');}catch(e){console.log('ERR:',e.message);}"
```
Expected: `JS OK`. Spec 1 gate #1.

- [ ] **Step 2: Em-dash count**

Run:
```bash
grep -c "—\|–" "S:/mixoswatch/index.html"
```
Expected: `0`. Spec 1 gate #2.

- [ ] **Step 3: `data-en` / `data-ja` / `data-zh` triple balance**

Run:
```bash
grep -c 'data-en' "S:/mixoswatch/index.html"
grep -c 'data-ja' "S:/mixoswatch/index.html"
grep -c 'data-zh' "S:/mixoswatch/index.html"
```
Expected: three identical numbers, identical to the Task 1 Step 4 baseline. Spec 1 gate #3.

- [ ] **Step 4: Footer URLs present**

Run:
```bash
grep "mixocreative/mixoswatch" "S:/mixoswatch/index.html" | grep -c "href"
```
Expected: `3`. Spec 1 gate #4 (offline check; live HTTP 200 is post-deploy).

- [ ] **Step 5: `.nojekyll` present and zero bytes**

Run:
```bash
test -f "S:/mixoswatch/.nojekyll" && wc -c "S:/mixoswatch/.nojekyll"
```
Expected: command exits 0; byte count `0`. Spec 1 gate #5.

- [ ] **Step 6: Git log shows 5 new commits since baseline**

Run:
```bash
cd S:/mixoswatch && git log --oneline -10
```
Expected: top 5 entries are the commits from Tasks 2, 3, 4, 5, 6 in order. The 6th and below are pre-existing.

- [ ] **Step 7: Mark Spec 1 implementation complete**

If all gates above pass, Spec 1 is shippable. Trigger GitHub Pages deploy by pushing:
```bash
cd S:/mixoswatch && git push origin main
```

Then enable GitHub Pages at the repo Settings → Pages → Source: Deploy from a branch, `main`, `/` (root). Wait for the deploy to complete (1-3 minutes).

Post-deploy live check (gate #4 live half):
```bash
curl -sI "https://github.com/mixocreative/mixoswatch/blob/main/README.md" | head -1
curl -sI "https://github.com/mixocreative/mixoswatch/blob/main/ARCHITECTURE.md" | head -1
curl -sI "https://mixocreative.github.io/mixoswatch/" | head -1
```
Expected: each returns `HTTP/2 200` (or `HTTP/1.1 200 OK`).

If any returns `404` or `5xx`, check that the repo is public, the Pages source is set correctly, and the deploy log under Settings → Pages → "View deployment" reports success.

---

## Self-Review

**Spec coverage check (against Spec 1 §4 file-by-file list):**

| Spec 1 change | Plan task |
|---|---|
| `index.html` 3-paragraph swap (Fix A) | Task 2 |
| `index.html` 3-paragraph swap (Fix B) | Task 3 |
| `index.html` 3-paragraph swap (Fix C) | Task 4 |
| `index.html` footer 3 anchors | Task 5 |
| `.nojekyll` zero-byte file | Task 6 |
| Spec 1 §5 validation gate 1 (JS parse) | Task 7 Step 1 |
| Spec 1 §5 validation gate 2 (em-dash 0) | Task 7 Step 2 |
| Spec 1 §5 validation gate 3 (triple balance) | Task 7 Step 3 |
| Spec 1 §5 validation gate 4 (URLs resolve) | Task 7 Step 4 offline + Step 7 live |
| Spec 1 §5 validation gate 5 (.nojekyll exists, 0 bytes) | Task 7 Step 5 |

No gaps. All Spec 1 requirements have a task.

**Placeholder scan:** searched plan for "TBD", "TODO", "implement later", "fill in details", "appropriate error handling", "Similar to Task N". None present. Each step shows actual content.

**Type consistency:** plan touches no JS types, no functions, no method signatures. Pure text replacements and one new file. N/A.

**Frequent commits:** plan creates 5 commits (one per task 2-6) + plan doc itself. Each commit is one logical change.
