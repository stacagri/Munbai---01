import json
import urllib.request
import re
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
<p>Test external image thumbnail generation.</p>
'''

res = s.posts().insert(blogId=TEST_BLOG_ID, body={"title": "Thumbnail Test External", "content": html_body}, isDraft=False).execute()
post_id = res["id"]
print("Inserted post ID:", post_id)
print("Post URL:", res.get("url"))

# Now fetch the homepage of lkunitest.blogspot.com
import time
time.sleep(3)
html = urllib.request.urlopen("https://lkunitest.blogspot.com/").read().decode("utf-8")
matches = re.findall(rf"post-thumb-{post_id}[^{{]*\{{[^}}]*\}}", html)
print("Matches found on homepage:", matches)
for line in html.splitlines():
    if f"post-thumb-{post_id}" in line:
        print("Line:", line.strip())

# Clean up test post
s.posts().delete(blogId=TEST_BLOG_ID, postId=post_id).execute()
print("Cleaned up test post.")
