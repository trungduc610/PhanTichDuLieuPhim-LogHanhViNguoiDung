"""Refresh LF-based line indices only; do not repeat runtime checks."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
inventory = json.loads((OUT/'inventory.json').read_text(encoding='utf-8'))
with (OUT/'numbered-project-files.txt').open('w',encoding='utf-8') as out:
    for item in inventory:
        text = (ROOT/item['path']).read_bytes().decode('utf-8')
        lines = text.split('\n')
        if lines and not lines[-1]:
            lines.pop()
        item['lines'] = len(lines)
        out.write('\nFILE: '+item['path']+'\n')
        for i,line in enumerate(lines,1):
            out.write(f'{i:5}: {line.rstrip(chr(13)).replace(chr(13), "<CR>")}\n')
(OUT/'inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Reindexed',len(inventory),'files using LF as the line separator; original files unchanged.')
