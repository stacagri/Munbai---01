import urllib.request
from bs4 import BeautifulSoup

url = "https://www.lkuni.com/"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req).read().decode("utf-8")

# Check for thumbnail script or snippet in homepage html
print("Homepage length:", len(html))
for line in html.splitlines():
    if "resizeImage" in line or "snippet" in line or "thumbnail" in line.lower() or "googleusercontent" in line:
        if len(line.strip()) < 200:
            print("Line:", line.strip())
