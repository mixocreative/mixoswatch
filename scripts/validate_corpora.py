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
            for tf in ("romaji", "pinyin"):
                if e.get(tf) and e.get("name_en") and e["name_en"].strip().lower() == e[tf].strip().lower():
                    warn(f"[{lid}][{i}] name_en={e['name_en']!r} equals {tf} (gloss missing?)")
        total_entries += len(entries)
        print(f"OK: [{lid}] {len(entries)} entries pass")
    print(f"PASS: {len(libs)} corpora, {total_entries} entries total")

if __name__ == "__main__":
    main()
