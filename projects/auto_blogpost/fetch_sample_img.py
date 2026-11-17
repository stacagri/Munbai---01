import urllib.request
from bs4 import BeautifulSoup
import re

req = urllib.request.Request('https://www.lkuni.com/2025/11/external-degree-programmes-2025.html', headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')
soup = BeautifulSoup(html, 'html.parser')
for img in soup.find_all('img'):
    print("IMG:", img.get('src'))
