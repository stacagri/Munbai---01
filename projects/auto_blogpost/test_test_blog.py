import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build("blogger", "v3", credentials=c)
res = s.posts().list(blogId="2198767951950215096", maxResults=5, fetchBodies=False).execute()
print("TEST BLOG POSTS:")
for p in res.get("items", []):
    print(f"{p['id']} - {p['title']} - {p['url']}")
