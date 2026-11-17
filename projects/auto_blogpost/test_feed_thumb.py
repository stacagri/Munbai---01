import json
import urllib.request
import re
import time
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build("blogger", "v3", credentials=c)

TEST_BLOG_ID = "2198767951950215096"

html_body = '''
<div class="separator" style="clear: both; text-align: center;">
<a href="https://iili.io/nQT7CEQ.png" style="margin-left: 1em; margin-right: 1em;">
<img border="0" data-original-height="1066" data-original-width="1600" src="https://iili.io/nQT7CEQ.png" />
</a>
</div>
<p>Test external image thumbnail generation with longer wait.</p>
'''

res = s.posts().insert(blogId=TEST_BLOG_ID, body={"title": "Thumbnail Wait Test", "content": html_body}, isDraft=False).execute()
post_id = res["id"]
print("Inserted post ID:", post_id)
print("Post URL:", res.get("url"))

time.sleep(10)

feed_url = f"https://lkunitest.blogspot.com/feeds/posts/default?alt=json"
req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
feed_data = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))

for entry in feed_data.get("feed", {}).get("entry", []):
    if post_id in entry.get("id", {}).get("$t", ""):
        print("Found entry in JSON feed!")
        print("media$thumbnail:", entry.get("media$thumbnail"))
        break

# Clean up
s.posts().delete(blogId=TEST_BLOG_ID, postId=post_id).execute()
print("Deleted post.")
