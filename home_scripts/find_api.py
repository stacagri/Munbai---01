import requests, re

print("Downloading main.dart.js...")
js = requests.get('https://rivernet.lk/main.dart.js').text
print(f"Loaded {len(js)} bytes.")

# 1. Inspect the function making the river_level request
idx = js.find('river_level')
if idx != -1:
    print("\n=== Context around 'river_level' ===")
    start = max(0, idx - 400)
    end = min(len(js), idx + 800)
    print(js[start:end])

# 2. Inspect where ratnapura / ratnapura_region is defined
idx_rat = js.find('ratnapura_region')
if idx_rat != -1:
    print("\n=== Context around 'ratnapura_region' ===")
    start = max(0, idx_rat - 300)
    end = min(len(js), idx_rat + 500)
    print(js[start:end])

# 3. Look for HTTP POST/GET URLs or paths
print("\n=== Searching for URL strings ===")
urls = set(re.findall(r'https?://[a-zA-Z0-9_\-\.]+(?:/[a-zA-Z0-9_\-\./\?=&%]*)?', js))
api_urls = [u for u in urls if 'rivernet' in u or 'api' in u]
for u in api_urls:
    print("Found API URL:", u)
