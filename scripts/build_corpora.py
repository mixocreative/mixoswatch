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
