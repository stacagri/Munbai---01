import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build("blogger", "v3", credentials=c)

OFFICIAL_BLOG_ID = "3109655798381913489"

# Fetch recent posts from official blog
posts = s.posts().list(blogId=OFFICIAL_BLOG_ID, maxResults=3).execute()
for p in posts.get("items", []):
    print("--- POST ---")
    print("Title:", p.get("title"))
    print("URL:", p.get("url"))
    print("Images:", p.get("images"))
    print("Content snippet (500 chars):\n", p.get("content")[:500])
