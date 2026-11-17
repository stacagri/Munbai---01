import re

with open('/home/ubuntu/auto_blogpost/raw_capture.txt', 'rb') as f:
    data = f.read().decode('utf-8', errors='ignore')

url_lines = []
capturing = False
for line in data.splitlines():
    clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line).strip()
    if 'https://accounts.google.com' in clean:
        capturing = True
    if capturing:
        url_lines.append(clean)
        if 'state=' in clean:
            break

full_url = ''.join(url_lines)
print("RECONSTRUCTED URL:")
print(full_url)
print("Length:", len(full_url))
print("Contains userinfo.profile?", "userinfo.profile" in full_url)
print("Contains state?", "state=" in full_url)
