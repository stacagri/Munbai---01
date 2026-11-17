import urllib.request
import ssl
from bs4 import BeautifulSoup
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://tamilguru.lk/gce-ol-examination-time-table-2026/"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
soup = BeautifulSoup(html, "html.parser")

print("Title:", soup.find("h1").get_text(strip=True))
print("\nImages:")
for img in soup.find_all("img"):
    src = img.get("src")
    if src and "tamilguru" in src:
        print(" ", src)

print("\nTables:")
for tr in soup.find_all("tr"):
    tds = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
    links = [a["href"] for a in tr.find_all("a", href=True)]
    print(" ", tds, "->", links)
