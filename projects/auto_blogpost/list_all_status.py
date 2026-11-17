import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open('/home/ubuntu/auto_blogpost/token.json') as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build('blogger', 'v3', credentials=c)

res = s.posts().list(blogId='3109655798381913489', status=['LIVE', 'DRAFT', 'SCHEDULED'], maxResults=20).execute()
print(f"Total returned: {len(res.get('items', []))}")
for p in res.get('items', []):
    print(p.get('status'), "|", p['id'], "|", p.get('published'), "|", p['title'])
