import urllib.request, re, ssl
from bs4 import BeautifulSoup
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request('https://itum.mrt.ac.lk/', headers={'User-Agent': 'Mozilla/5.0'})
try:
    html = urllib.request.urlopen(req, context=ctx).read().decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    for a in soup.find_all('a', href=True):
        if 'ndt' in a['href'].lower() or 'admission' in a['href'].lower():
            print(a.get_text(strip=True), '->', a['href'])
except Exception as e:
    print('Error:', e)
