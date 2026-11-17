import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open('/home/ubuntu/auto_blogpost/token.json') as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build('blogger', 'v3', credentials=c)

blogs = s.blogs().listByUser(userId='self').execute()
for b in blogs.get('items', []):
    print(f"Blog: {b['name']} ({b['id']})")
    posts = s.posts().list(blogId=b['id'], maxResults=5).execute()
    for p in posts.get('items', []):
        print(f"  [{p['id']}] {p['title']} - {p['url']}")
