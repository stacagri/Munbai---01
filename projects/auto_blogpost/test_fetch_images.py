import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build("blogger", "v3", credentials=c)

TEST_BLOG_ID = "2198767951950215096"

content = '''<p>Test Fetch Images</p><p><img src="https://iili.io/nQT7CEQ.png" alt="Test" /></p>'''

post = {
    "kind": "blogger#post",
    "title": "Fetch Images Test",
    "content": content
}

result = s.posts().insert(blogId=TEST_BLOG_ID, body=post, fetchImages=True, isDraft=False).execute()
print("Post ID:", result.get("id"))
print("URL:", result.get("url"))
print("Images field:", result.get("images"))
print("Content snippet:", result.get("content"))
