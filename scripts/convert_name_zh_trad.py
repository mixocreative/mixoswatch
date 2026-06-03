"""Convert simplified Chinese name_zh entries in name_corpora.json to traditional Chinese."""
import json
import sys
import io
from pathlib import Path
from opencc import OpenCC

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
cc = OpenCC('s2t')

data_path = Path('data/corpora/name_corpora.json')
data = json.loads(data_path.read_text(encoding='utf-8'))

count = 0
for corp in data['corpora']:
    # Convert corpus label.zh
    if 'label' in corp and 'zh' in corp['label']:
        old = corp['label']['zh']
        new = cc.convert(old)
        if old != new:
            print(f'label.zh: "{old}" -> "{new}"')
            corp['label']['zh'] = new
            count += 1

    # Convert field labels
    if 'fields' in corp:
        for field in corp['fields']:
            if 'label' in field and 'zh' in field['label']:
                old = field['label']['zh']
                new = cc.convert(old)
                if old != new:
                    print(f'field "{field["id"]}" label.zh: "{old}" -> "{new}"')
                    field['label']['zh'] = new
                    count += 1

    # Convert name_zh entries
    if 'entries' in corp:
        for entry in corp['entries']:
            if 'name_zh' in entry and entry['name_zh']:
                old = entry['name_zh']
                new = cc.convert(old)
                if old != new:
                    label = entry.get('name_en', entry.get('name_ja', '?'))
                    print(f'  {label}: "{old}" -> "{new}"')
                    entry['name_zh'] = new
                    count += 1

print(f'\nTotal conversions: {count}')

data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('File written successfully.')