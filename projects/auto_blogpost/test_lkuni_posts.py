import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build("blogger", "v3", credentials=c)
res = s.posts().list(blogId="3109655798381913489", status=["LIVE", "DRAFT"], maxResults=20, fetchBodies=False).execute()
for p in res.get("items", []):
    print(f"{p.get('status')} | {p['id']} - {p['title']}")
