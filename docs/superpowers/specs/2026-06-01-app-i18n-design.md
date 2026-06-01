# Spec 2 · App HTMLs tri-lingual i18n

**Date:** 2026-06-01
**Author:** mixocreative (via brainstorm cycle)
**Scope:** `app/cmyk-explorer.html`, `app/3d-explorer.html`
**Status:** awaiting user review

---

## 0. Why this spec

The landing page (`index.html`) already supports EN / 日本語 / 繁中 via inline `data-en/ja/zh` triples + a topbar segmented switch + `navigator.languages` detection + `localStorage` persistence. The two explorer apps remain English-only. Layman users in JP / TW markets land on the page, switch language successfully on the landing, then click into the apps and bounce off an English wall.

Spec 2 ports the proven landing i18n pattern into both explorer HTMLs with full coverage of static UI labels, `title` tooltips, alert / error / empty-state strings, and dynamic count labels.

---

## 1. Goals + non-goals

### Goals

- Both explorer apps render all visible UI text in EN / JA / ZH on first paint.
- Browser language is auto-detected from `navigator.languages` on first visit. EN fallback when no JA / ZH match.
- User can flip language via a topbar segmented pill (same component as landing).
- Selection persists per app via dedicated `localStorage` keys.
- Dynamic strings (count labels, alerts, empty states) translate via a JS string table with placeholder interpolation.
- Tooltip translations honor the native `title` attribute (a11y intact).

### Non-goals

- Touch `index.html`.
- Touch any Python script, ICC pipeline, or data JSON file.
- Translate user data (corpus entries, palette names typed by the user, profile names from `data/luts/index.json`). Those are data, not UI.
- Translate the comments inside the source code.
- Add a fourth language. Lock at EN / JA / ZH.
- Implement language sync across pages. Per-page localStorage keys per Q4 = B.

---

## 2. Design

### 2.1 Storage strategy (hybrid per Q2 = C)

| String class | Mechanism |
|---|---|
| Static visible UI labels (section headings, button labels, radio labels, pill text) | Inline `<span data-en>…</span><span data-ja>…</span><span data-zh>…</span>`. CSS hides non-active siblings via `html[lang="..."] [data-other]{display:none}`. Zero JS for static text. |
| `title` tooltips | `data-title-en`, `data-title-ja`, `data-title-zh` attributes on the host element. JS `applyTitles()` pass writes the matching one into the live `title` attribute on every lang change. |
| Dynamic / templated strings (count labels, alerts, empty-state copy, confirm dialogs) | JS `I18N` object literal at top of script. Lookup via `t(key, vars)` helper. Missing JA / ZH key falls back to EN silently. |

### 2.2 Topbar switch component (per Q3 = A)

Lifted verbatim from landing. Injected into `.topbar` at the right edge, just before the existing mode group.

```html
<div class="lang-switch" id="langSwitch" title="Language / 言語 / 語言">
  <button data-lang="en" class="on">EN</button>
  <button data-lang="ja">日本語</button>
  <button data-lang="zh">繁中</button>
</div>
```

CSS (lifted from landing, 8 lines per HTML):

```css
.lang-switch{display:inline-flex;gap:0;border:1px solid var(--border);border-radius:999px;padding:2px;background:var(--bg2)}
.lang-switch button{font-family:var(--font-mono);font-size:10.5px;padding:3px 9px;border:none;background:transparent;color:var(--muted);border-radius:999px;cursor:pointer;letter-spacing:.04em;transition:all .15s ease}
.lang-switch button:hover{color:var(--text)}
.lang-switch button.on{background:var(--accent);color:#fff;font-weight:500}
html[lang="en"] [data-ja],html[lang="en"] [data-zh]{display:none}
html[lang="ja"] [data-en],html[lang="ja"] [data-zh]{display:none}
html[lang="zh"] [data-en],html[lang="zh"] [data-ja]{display:none}
```

### 2.3 Detection + persistence (per Q4 = B)

```js
const I18N_KEY = 'mixoLangCmyk_v1';   // CMYK explorer
// const I18N_KEY = 'mixoLang3d_v1';   // 3D explorer
const VALID_LANGS = new Set(['en','ja','zh']);

function detectLang() {
  let stored = null;
  try { stored = localStorage.getItem(I18N_KEY); } catch {}
  if (VALID_LANGS.has(stored)) return stored;
  const langs = (navigator.languages && navigator.languages.length)
    ? navigator.languages : [navigator.language || 'en'];
  for (const raw of langs) {
    const tag = String(raw).toLowerCase();
    if (tag.startsWith('ja')) return 'ja';
    if (tag.startsWith('zh')) return 'zh';   // all Chinese locales map to ZH-Hant
    if (tag.startsWith('en')) return 'en';
  }
  return 'en';
}

let ACTIVE_LANG = 'en';
function applyLang(lang) {
  if (!VALID_LANGS.has(lang)) lang = 'en';
  ACTIVE_LANG = lang;
  document.documentElement.setAttribute('lang', lang);
  // 1. switch button highlights
  document.querySelectorAll('#langSwitch button').forEach(b =>
    b.classList.toggle('on', b.dataset.lang === lang));
  // 2. tooltip pass
  document.querySelectorAll('[data-title-en]').forEach(el => {
    const v = el.getAttribute('data-title-' + lang) ?? el.getAttribute('data-title-en');
    if (v) el.setAttribute('title', v);
  });
  // 3. dynamic-string render: call back into render() so all t() calls re-emit
  if (typeof render === 'function') render();
  try { localStorage.setItem(I18N_KEY, lang); } catch {}
}
document.getElementById('langSwitch').addEventListener('click', e => {
  const b = e.target.closest('button[data-lang]');
  if (b) applyLang(b.dataset.lang);
});
applyLang(detectLang());   // boot
```

### 2.4 Dynamic-string helper

```js
const I18N = {
  en: {
    swatches_n      : '{n} swatches',
    palettes_n      : '{n} palette',                 // singular form; UI uses plural rule conditionally
    palettes_n_plur : '{n} palettes',
    visible_of_total: '{n} / {m} visible',
    named_n_of_m    : '{n} / {m} named',
    pass_n_of_m     : '{n} / {m} pass',
    no_match_hint   : 'no match · try 桜 · coral · N804 · #FCC',
    no_palette_empty: 'No palettes yet. Click "+ New" to start one.',
    no_palette_sel  : 'No palette selected. Pick one above, or create one.',
    palette_pick    : 'No palette selected. Pick one in the sidebar, then try again.',
    palette_create  : 'No palette exists yet. Create one now?',
    profile_err     : 'Failed to load ICC pipeline: {msg}\n\nDid you run "python scripts/gen_luts.py" first? Are data/luts/index.json and data/corpora/name_corpora.json present?',
    library_err     : 'Failed to load 3D library: {msg}\n\nRun: python scripts/gen_libraries.py\nthen refresh the page.',
    confirm_reset   : 'Reset all UI controls to defaults (saved palettes are kept). Continue?',
    confirm_del_pal : 'Delete palette "{name}"? This cannot be undone.',
    confirm_clr_pal : 'Clear all {n} swatches from "{name}"?',
    rename_prompt   : 'Rename palette:',
    new_name_prompt : 'Palette name:',
    file_err_invalid: 'Invalid JSON file.',
    file_err_array  : 'No palettes array found.',
    file_proto_err  : 'mixoswatch needs to run over HTTP. Open run.bat (Windows) or run.sh (mac/Linux).',
    // … extend per discovery during implementation
  },
  ja: {
    swatches_n      : 'スウォッチ {n} 点',
    palettes_n      : 'パレット {n} 件',
    palettes_n_plur : 'パレット {n} 件',
    visible_of_total: '{n} / {m} 表示',
    named_n_of_m    : '命名済み {n} / {m}',
    pass_n_of_m     : '合格 {n} / {m}',
    no_match_hint   : '一致なし · 桜 · coral · N804 · #FCC など試す',
    no_palette_empty: 'パレットが未登録。「＋ 新規」で作成。',
    no_palette_sel  : 'パレット未選択。上から選ぶか、新規作成。',
    palette_pick    : 'パレット未選択。サイドバーで選んでから再試行。',
    palette_create  : 'パレットがまだない。今すぐ作成？',
    profile_err     : 'ICCパイプラインの読み込み失敗：{msg}\n\n「python scripts/gen_luts.py」を先に実行したか？ data/luts/index.json と data/corpora/name_corpora.json は存在するか？',
    library_err     : '3Dライブラリの読み込み失敗：{msg}\n\n実行：python scripts/gen_libraries.py\n後に再読み込み。',
    confirm_reset   : 'UI全項目を初期値に戻す（保存パレットは保持）。続行？',
    confirm_del_pal : 'パレット「{name}」を削除？ 取り消し不可。',
    confirm_clr_pal : 'パレット「{name}」のスウォッチ {n} 件をすべて消去？',
    rename_prompt   : 'パレット名変更：',
    new_name_prompt : 'パレット名：',
    file_err_invalid: '無効なJSONファイル。',
    file_err_array  : 'palettes配列が見つからない。',
    file_proto_err  : 'mixoswatch はHTTP経由で起動が必要。run.bat（Windows）または run.sh（mac/Linux）を起動。',
  },
  zh: {
    swatches_n      : '{n} 個色票',
    palettes_n      : '{n} 組色票組',
    palettes_n_plur : '{n} 組色票組',
    visible_of_total: '{n} / {m} 顯示',
    named_n_of_m    : '已命名 {n} / {m}',
    pass_n_of_m     : '通過 {n} / {m}',
    no_match_hint   : '無相符 · 試試 桜 · coral · N804 · #FCC',
    no_palette_empty: '尚未建立色票組。點「＋ 新增」開始。',
    no_palette_sel  : '未選擇色票組。請從上方挑一組，或新增一組。',
    palette_pick    : '未選擇色票組。請先在側欄挑一組再試。',
    palette_create  : '尚未建立色票組。是否現在新增？',
    profile_err     : '載入 ICC 流程失敗：{msg}\n\n是否已先執行「python scripts/gen_luts.py」？ data/luts/index.json 與 data/corpora/name_corpora.json 是否存在？',
    library_err     : '載入 3D 色庫失敗：{msg}\n\n請執行：python scripts/gen_libraries.py\n然後重新整理。',
    confirm_reset   : '將所有 UI 控制重設為預設值（已存色票組保留）。是否繼續？',
    confirm_del_pal : '刪除色票組「{name}」？此動作無法復原。',
    confirm_clr_pal : '清空色票組「{name}」內全部 {n} 個色票？',
    rename_prompt   : '重新命名色票組：',
    new_name_prompt : '色票組名稱：',
    file_err_invalid: '無效的 JSON 檔。',
    file_err_array  : '未找到 palettes 陣列。',
    file_proto_err  : 'mixoswatch 需要透過 HTTP 啟動。請開啟 run.bat（Windows）或 run.sh（mac/Linux）。',
  },
};
function t(key, vars) {
  const tbl = I18N[ACTIVE_LANG] || I18N.en;
  const s = tbl[key] ?? I18N.en[key] ?? key;
  return vars ? s.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '') : s;
}
```

Plural rule note: JP and ZH have no grammatical pluralization. The `_plur` keys exist only for the English plural; JP / ZH versions reuse the singular template. Helper consumers stay one call: `t(n === 1 ? 'palettes_n' : 'palettes_n_plur', { n })`.

### 2.5 Translation coverage by file

**`app/cmyk-explorer.html`** static surface inventory (approximate counts; exact tally during implementation):

- Sidebar section labels (`.sec-label`): ~14
- Step-group headers (`.step-group-header .lbl/.sub`): 4 groups × 2 spans = 8
- Buttons (mode group, sort buttons, palette actions, reset, search, naming radios, K-tier pills, named filter pills): ~60
- Static inline help text (the `Adding profiles / names (manual)` block, the tier explainer paragraph): ~6 paragraphs
- Topbar mode button labels (`Grid`, `Hue × Light`, `Palettes`): 3
- Detail card chip prefixes (the per-corpus chip labels in detail card): per-corpus; not translated (corpus.label is data, ships as authored)
- Tooltips (`title="..."`): ~60 controls

**`app/3d-explorer.html`** similar but smaller:

- Sidebar section labels: ~10
- Step-group headers: 4 groups × 2 spans = 8
- Buttons: ~45
- Static inline help text: ~3 paragraphs
- Topbar mode labels: 3
- Tooltips: ~50 controls

### 2.6 Excluded from translation

The following are **data**, not UI, and ship in the language they were authored in:

- Profile labels from `data/luts/index.json` (e.g. "Tier 3 · Coated FOGRA39")
- Corpus labels from `data/corpora/name_corpora.json` (e.g. "Japanese traditional", "DIC Japanese Traditional (matte, seed)")
- Corpus entry fields (kanji, romaji, English, DIC code, hex, cmyk)
- Per-swatch system_name strings (e.g. "soft-fair-blue") generated by `gen_libraries.py`
- User-typed palette names

A future spec could add per-corpus localization (corpus.label_ja / label_zh), but that is out of scope here.

---

## 3. File-by-file change list

| File | Change | Magnitude |
|---|---|---|
| `app/cmyk-explorer.html` | Inject `.lang-switch` markup + CSS in topbar / head; wrap ~120 static labels in `data-en/ja/zh` triples; add `data-title-en/ja/zh` to ~60 tooltips; embed `I18N` string table; add `applyLang()` + `detectLang()` + `t()` helpers; rewire ~25 alert / confirm / prompt / status string callsites to `t()`; rewire ~6 count-label updates to `t()` | ~700 inserted lines |
| `app/3d-explorer.html` | Same pattern; smaller surface | ~520 inserted lines |
| No new files | (none) | (none) |

No CSS variable changes. No new external fetches. Both HTMLs gain ~6 to 8 KB after gzip.

---

## 4. Translation register

All JA translations use **standard polite-modern Japanese** (です・ます調 is implied where natural; current drafts use neutral / informational tone consistent with the landing page register). Mechanical / technical terms (`CMYK`, `ICC`, `LUT`, `ΔE`, `FOGRA39`) stay Latin. **`プリンター` not `印刷機`** per project rule; **`プリント` not `印刷`** in any standalone use (compounds like `プリプレス` stay).

All ZH translations target **Traditional Chinese (Taiwan locale)**. Vocabulary chosen for Taiwan printing-industry convention: `色票` (sèpiào, swatch), `色票組` (palette), `色庫` (library), `描述檔` (profile), `印刷` (kept; Chinese spec, not subject to JP `プリント` rule), `渲染` (render), `濾鏡` / `篩選` (filter).

---

## 5. Validation gates

The implementation plan must enforce these before considering Spec 2 shipped:

1. JS parses cleanly in both HTMLs (`new Function(scriptBody)` succeeds).
2. Em-dash / en-dash count in both HTMLs stays at zero (project rule).
3. Every `data-en` span has a paired `data-ja` and `data-zh` sibling. Verified by grep audit.
4. Every `data-title-en` host has paired `data-title-ja` and `data-title-zh`. Same.
5. Every `t('key')` callsite resolves: `key` exists in `I18N.en` (treated as the source of truth). Implementation plan includes a grep cross-check to flag orphan keys (used but undefined) and dead keys (defined but unused).
6. Switching language fires no console errors and updates: button highlight + `html[lang]` + visible labels + all live `title` attributes + every dynamic string emitted by `render()`.
7. localStorage carries selection across reloads; per-page key isolation verified (CMYK explorer key does not influence 3D explorer and vice versa).
8. Boot path: setting `navigator.languages` to `['ja-JP','en']` (devtools override) on a fresh profile auto-selects JA. Same for `['zh-TW','en']` → ZH. Plain `['en-US']` → EN.
9. Manual smoke: open in EN, build a palette, switch to JA mid-session, confirm palette state intact (palette data is not in i18n scope).

---

## 6. Open questions (none blocking)

- **Profile + corpus label localization.** Currently shipped as data, single-language. A future spec could let `data/luts/index.json` carry `label_ja` / `label_zh` and `data/corpora/name_corpora.json` carry `label_ja` / `label_zh` per corpus. Out of scope here. Flag as Spec 5 candidate.
- **Per-corpus tooltip strings.** Currently English. Same future-work question as above.

---

## 7. Cross-references

- Brainstorm transcript: this session.
- Pattern source: `index.html` lang switch implementation (already shipped).
- Sibling specs:
  - **Spec 1** · landing honesty + GH Pages (approved, queued for plan)
  - **Spec 3** · app UX bundle (sidebar 4-step refine, a11y, tooltips, loading states, text-select forbid) · pending brainstorm
  - **Spec 4** · app latency hardening (Worker, IntersectionObserver, prefetch) · pending brainstorm
- ARCHITECTURE.md sections relevant on next pass: §10 (UI / UX rationale), §11 (performance budget).
