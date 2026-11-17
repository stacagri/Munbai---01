import urllib.request, ssl
from bs4 import BeautifulSoup
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request("https://www.doenets.lk/", headers={"User-Agent": "Mozilla/5.0"})
try:
    html = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        if any(k in a["href"].lower() for k in ["o/l", "ol", "timetable", "time_table", "pdf"]):
            print(a.get_text(strip=True), "->", a["href"])
except Exception as e:
    print("Error:", e)
