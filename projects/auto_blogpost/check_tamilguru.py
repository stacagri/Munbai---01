import urllib.request
import re
from bs4 import BeautifulSoup
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request("https://tamilguru.lk/category/courses/", headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
soup = BeautifulSoup(html, "html.parser")

articles = soup.find_all("article")
print(f"Total articles found: {len(articles)}")
for a in articles:
    link = a.find("a", href=True)
    title = a.find(["h1", "h2", "h3"])
    if link and title:
        print(f"- {title.get_text(strip=True)}: {link['href']}")
