"""Convert all hanzi in zh-trad raw + glosses + corpus output from
Simplified to Traditional Chinese using OpenCC s2t."""
from __future__ import annotations
import json
from pathlib import Path
from opencc import OpenCC

cc = OpenCC('s2t')

def conv(s):
    return cc.convert(s) if s else s

def cv_entry(e):
    out = dict(e)
    for k in ('name_zh','name_ja','name_en'):
        if k in out and isinstance(out[k], str):
            out[k] = conv(out[k])
    # pinyin + hex unchanged
    return out

# Convert raw
raw_path = Path('scripts/source_data/zh_trad_raw.json')
raw = json.loads(raw_path.read_text(encoding='utf-8'))
raw_t = []
for r in raw:
    r2 = dict(r)
    if 'name' in r2:
        r2['name'] = conv(r2['name'])
    raw_t.append(r2)
raw_path.write_text(json.dumps(raw_t, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'raw: {len(raw_t)} entries converted')

# Convert glosses
gloss_path = Path('scripts/source_data/zh_trad_glosses.json')
glosses = json.loads(gloss_path.read_text(encoding='utf-8'))
glosses_t = {}
for k, v in glosses.items():
    new_key = conv(k)
    new_val = {kk: conv(vv) for kk, vv in v.items()}
    glosses_t[new_key] = new_val
gloss_path.write_text(json.dumps(glosses_t, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'glosses: {len(glosses_t)} keys converted')

# Convert built corpus
v3_path = Path('scripts/source_data/zh_trad_v3.json')
v3 = json.loads(v3_path.read_text(encoding='utf-8'))
v3['entries'] = [cv_entry(e) for e in v3['entries']]
v3_path.write_text(json.dumps(v3, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'v3 entries: {len(v3["entries"])} converted')
