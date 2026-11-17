import os
import sys
import re
import urllib.request
import ssl
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

sys.path.append('/home/ubuntu/auto_blogpost')
from auto_blogger import upload_to_google_drive, publish_via_blogger, TEST_BLOG_ID

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://www.guruwaraya.lk/2026/11/december-2026-examination-calendar-22.html"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req, context=ctx).read().decode('utf-8', errors='ignore')
soup = BeautifulSoup(html, 'html.parser')

post_body = soup.find('div', class_='post-body') or soup.find('div', class_='entry-content')

# Extract official PDFs
pdfs = []
for a in post_body.find_all('a', href=True):
    href = a['href']
    text = a.get_text(strip=True)
    if 'doenets.lk' in href and href.endswith('.pdf'):
        name = "Download PDF"
        if "sinhala" in text.lower() or "sinhala" in href.lower():
            name = "Sinhala PDF"
        elif "tamil" in text.lower() or "tamil" in href.lower():
            name = "Tamil PDF"
        elif "english" in text.lower() or "english" in href.lower():
            name = "English PDF"
        if (name, href) not in pdfs:
            pdfs.append((name, href))

print("Extracted PDFs:", pdfs)

# Extract key exams list for bullets
exams = []
for h3 in post_body.find_all(['h3', 'h4']):
    t = h3.get_text(strip=True)
    if t and not any(x in t.lower() for x in ['related', 'comment', 'share', 'whatsapp']):
        exams.append(t)

print("Extracted Exam list count:", len(exams))
print("Top 5 exams:", exams[:5])
