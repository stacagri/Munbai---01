import re
from difflib import SequenceMatcher
import urllib.request
from bs4 import BeautifulSoup
import ssl
import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def normalize_title(title: str) -> str:
    t = re.sub(r"[^\w\s]", " ", title.lower())
    t = re.sub(r"\b(application|for|degree|intake|programmes?|courses?|offered|by)\b", " ", t)
    return " ".join(t.split())

def is_duplicate(candidate_title: str, existing_titles: list) -> tuple:
    c_norm = normalize_title(candidate_title)
    c_words = set(c_norm.split())
    c_year = re.search(r"\b(202\d)\b", candidate_title)
    c_year_val = c_year.group(1) if c_year else None

    for ext in existing_titles:
        e_norm = normalize_title(ext)
        e_words = set(e_norm.split())
        e_year = re.search(r"\b(202\d)\b", ext)
        e_year_val = e_year.group(1) if e_year else None

        # If both titles explicitly contain different intake years, they are NOT duplicates
        if c_year_val and e_year_val and c_year_val != e_year_val:
            continue

        meaningful_c = {w for w in c_words if len(w) >= 3}
        meaningful_e = {w for w in e_words if len(w) >= 3}
        if not meaningful_c:
            continue

        intersection = meaningful_c.intersection(meaningful_e)
        ratio = len(intersection) / len(meaningful_c)
        sim = SequenceMatcher(None, c_norm, e_norm).ratio()

        # If key course + institute words match
        if ratio >= 0.70 or (ratio >= 0.55 and sim >= 0.60):
            return True, ext

    return False, None

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build("blogger", "v3", credentials=c)
res = s.posts().list(blogId="3109655798381913489", maxResults=50, fetchBodies=False).execute()
lkuni_titles = [p["title"] for p in res.get("items", [])]

with open("/home/ubuntu/auto_blogpost/posted_cache.json") as f:
    posted_cache = set(json.load(f))

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request("https://tamilguru.lk/category/courses/", headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
soup = BeautifulSoup(html, "html.parser")

articles = soup.find_all("article")
print("=== REAL SCAN RESULT ===")
for a in articles:
    link = a.find("a", href=True)
    title_el = a.find(["h1", "h2", "h3"])
    if link and title_el:
        url = link["href"]
        raw_title = title_el.get_text(strip=True)
        in_cache = url in posted_cache
        dup, matched_title = is_duplicate(raw_title, lkuni_titles)
        
        status = "ALREADY POSTED" if (in_cache or dup) else "NEW UNPOSTED"
        reason = []
        if in_cache: reason.append("In Cache")
        if dup: reason.append(f"Matches '{matched_title}'")
        
        print(f"[{status}] {raw_title}")
        print(f"  URL: {url}")
        if reason:
            print(f"  Reason: {', '.join(reason)}")
        print()
