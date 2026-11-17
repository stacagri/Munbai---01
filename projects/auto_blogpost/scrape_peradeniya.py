import urllib.request
import re
import json
from bs4 import BeautifulSoup

url = "https://tamilguru.lk/bba-external-degree-intake-university-of-peradeniya/"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
html = urllib.request.urlopen(urllib.request.Request(url, headers=headers)).read().decode("utf-8")
soup = BeautifulSoup(html, "html.parser")

title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "No title"
print("Title:", title)

imgs = []
for img in soup.find_all("img"):
    src = img.get("src", "")
    if any(ext in src.lower() for ext in [".jpg", ".png", ".jpeg", ".webp"]) and not any(skip in src.lower() for skip in ["logo", "avatar", "icon"]):
        imgs.append(src)

print("Images found:", imgs)

# The second or third image is typically the advertisement flyer:
# ['...Bachelor-of-Business-Administration-BBA-External-Degree-2026-University-of-Peradeniya.jpg', '...BBA-External-Degree-2026-University-of-Peradeniya-ad-E.jpg', '...BBAonlinenewsyllabus.jpg']

for idx, img_url in enumerate(imgs):
    req = urllib.request.Request(img_url, headers=headers)
    img_bytes = urllib.request.urlopen(req).read()
    dest = f"/home/ubuntu/auto_blogpost/peradeniya_{idx}.jpg"
    with open(dest, "wb") as f:
        f.write(img_bytes)
    print(f"Saved {img_url} to {dest} ({len(img_bytes)} bytes)")
