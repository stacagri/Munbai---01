import urllib.request
import ssl
from bs4 import BeautifulSoup
import re

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

headers = {"User-Agent": "Mozilla/5.0"}
req = urllib.request.Request("https://tamilguru.lk/category/courses/", headers=headers)
html = urllib.request.urlopen(req, context=ssl_ctx).read().decode("utf-8")
soup = BeautifulSoup(html, "html.parser")

posts = []
for a in soup.find_all("a", href=True):
    href = a["href"]
    if href.startswith("https://tamilguru.lk/") and "/category/" not in href and "/tag/" not in href and "/page/" not in href and href != "https://tamilguru.lk/":
        if href not in posts:
            posts.append(href)

print("Found posts:", posts[:5])
for p_url in posts[:5]:
    req_p = urllib.request.Request(p_url, headers=headers)
    html_p = urllib.request.urlopen(req_p, context=ssl_ctx).read().decode("utf-8")
    soup_p = BeautifulSoup(html_p, "html.parser")
    # find images inside content
    content_div = soup_p.find("div", class_=re.compile(r"entry-content|post-content"))
    if content_div:
        imgs = [img.get("src") for img in content_div.find_all("img") if img.get("src")]
        print(f"\nPost: {p_url}")
        print("Images:", imgs)
