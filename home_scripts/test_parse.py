import re
import json

with open('/home/ubuntu/gazette_2026_11_06.html', 'r', encoding='utf-8') as f:
    text = f.read()

for m in re.finditer(r'\{[^{}]*uploadedFile[^{}]*\}', text):
    raw = m.group(0)
    print("RAW:", repr(raw[:40]))
    # Replace backslash-quote with quote
    clean = raw.replace('\\"', '"')
    print("CLEAN:", repr(clean[:40]))
    try:
        obj = json.loads(clean)
        print("SUCCESS:", obj)
    except Exception as e:
        print("FAIL:", e)
