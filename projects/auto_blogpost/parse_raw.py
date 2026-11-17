import re

with open('/home/ubuntu/auto_blogpost/raw_capture.txt', 'rb') as f:
    data = f.read().decode('utf-8', errors='ignore')

# Print lines that contain accounts.google.com or https
lines = data.split('\r\n')
print(f"Total lines: {len(lines)}")
for idx, line in enumerate(lines):
    if 'accounts.google.com' in line or 'redirect_uri' in line or 'state=' in line:
        print(f"L{idx}: {repr(line)}")

# Let's see how the full URL is assembled
# Replace ansi escape codes
ansi_clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', data)
# Remove \r
no_r = ansi_clean.replace('\r', '')

match = re.search(r'https://accounts\.google\.com[^\s\x1b]+', no_r.replace('\n', ''))
if match:
    print("MATCHED URL:")
    print(match.group(0))
else:
    print("NO MATCH")
