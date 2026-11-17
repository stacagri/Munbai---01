import urllib.request
from bs4 import BeautifulSoup

url = "https://www.lkuni.com/2024/10/application-for-nvq-56-higher-national.html"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req).read().decode("utf-8")
soup = BeautifulSoup(html, "html.parser")

print("Post Title:", soup.title.string if soup.title else "")
imgs = soup.find_all("img")
print(f"Total img tags: {len(imgs)}")
for i, img in enumerate(imgs[:10]):
    print(f"Img {i}: {img.get('src')}")
