import urllib.request
import re
from bs4 import BeautifulSoup
import ssl
import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build("blogger", "v3", credentials=c)

# Fetch latest 50 posts from www.lkuni.com
res = s.posts().list(blogId="3109655798381913489", maxResults=50, fetchBodies=False).execute()
lkuni_titles = [p["title"] for p in res.get("items", [])]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request("https://tamilguru.lk/category/courses/", headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
soup = BeautifulSoup(html, "html.parser")

articles = soup.find_all("article")
print("=== COMPARING TAMILGURU WITH LKUNI ===")
for a in articles:
    link = a.find("a", href=True)
    title = a.find(["h1", "h2", "h3"])
    if link and title:
        t_text = title.get_text(strip=True)
        # Check if already on lkuni
        matched = []
        for lk_t in lkuni_titles:
            # simple token matching
            tokens = [w.lower() for w in re.findall(r"\b[A-Za-z]{4,}\b", t_text)]
            match_count = sum(1 for tok in tokens if tok in lk_t.lower())
            if len(tokens) > 0 and (match_count / len(tokens)) >= 0.5:
                matched.append(lk_t)
        
        status = f"ALREADY ON LKUNI: {matched[0]}" if matched else "NEW (NOT ON LKUNI)"
        print(f"[{status}]\n  Tamilguru: {t_text}\n  URL: {link['href']}\n")
