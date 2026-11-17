import re
import json

with open('/home/ubuntu/gazette_2026_10_30.html', 'r', encoding='utf-8') as f:
    text = f.read()

# In the HTML, find all JSON fragments with uploadedFile
matches = []
for m in re.finditer(r'\{[^{}]*uploadedFile[^{}]*\}', text):
    raw = m.group(0).replace(r'\"', '"').replace(r'\\', '/')
    try:
        data = json.loads(raw)
        matches.append(data)
    except Exception:
        pass

print(f"Total entries: {len(matches)}")
for it in matches:
    p = it.get('partNo')
    s = it.get('section')
    l = it.get('language')
    fmt = it.get('uploadedFileFormat')
    f = it.get('uploadedFile')
    print(f"Part {p} | {s} | {l} | {fmt} | {f}")
