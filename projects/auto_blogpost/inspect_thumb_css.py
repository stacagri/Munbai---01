import urllib.request
import re

url = "https://www.lkuni.com/"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req).read().decode("utf-8")

matches = re.findall(r"post-thumb-\d+[^{]*\{[^}]*\}", html)
for m in matches[:5]:
    print("CSS match:", m)
