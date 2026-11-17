import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open('/home/ubuntu/auto_blogpost/token.json') as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build('blogger', 'v3', credentials=c)
try:
    p = s.posts().get(blogId='2198767951950215096', postId='7656809780093998803').execute()
    print('Found on TEST BLOG!')
    print('TITLE:', p.get('title'))
    print('URL:', p.get('url'))
    print('CONTENT:', p.get('content')[:300])
except Exception as e:
    print('Test blog error:', e)

# Also let's check recent posts on official blog:
print("\nRecent on Official:")
res = s.posts().list(blogId='3109655798381913489', maxResults=3).execute()
for it in res.get('items', []):
    print(it['id'], it['title'], it['url'])
