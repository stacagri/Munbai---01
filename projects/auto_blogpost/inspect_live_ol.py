import urllib.request
from bs4 import BeautifulSoup

url = 'https://www.lkuni.com/2026/11/examination-schedule-for-gce-ol.html'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')
soup = BeautifulSoup(html, 'html.parser')

post_body = soup.find('div', class_='post-body') or soup.find('article')
print("Post Title in HTML:", soup.find('h1'))
if post_body:
    print("Post Body HTML:\n", post_body.prettify()[:1000])
else:
    print("No post body found, full snippet:\n", soup.get_text()[:500])
