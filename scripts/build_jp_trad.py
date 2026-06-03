"""Transform NipponColors raw scrape into schema v3 jp-trad corpus.

Input:  scripts/source_data/nippon_colors_raw.json
Output: scripts/source_data/jp_trad_v3.json (consumed by build_corpora.py in Task 10)

Each raw entry has: { name (kanji), pronounce (romaji), hex, cmyk: [C,M,Y,K] }.
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
        hex_v = r.get("hex", "").upper()
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
        "label": {"en": "Japanese traditional (NipponColors 250)", "ja": "日本の伝統色", "zh": "日本传统色"},
        "fields": [
            {"id": "name_ja", "label": {"en": "kanji",   "ja": "漢字",   "zh": "汉字"}},
            {"id": "romaji",  "label": {"en": "romaji",  "ja": "ローマ字", "zh": "罗马字"}},
            {"id": "name_en", "label": {"en": "English", "ja": "英語",   "zh": "英文"}},
            {"id": "name_zh", "label": {"en": "Chinese", "ja": "中国語", "zh": "中文"}},
        ],
        "default_display": "name_ja",
        "anchor": "cmyk",
        "source": "https://nipponcolors.com/ (250 entries, public)",
        "entries": entries,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} with {len(entries)} entries")

if __name__ == "__main__":
    main()
