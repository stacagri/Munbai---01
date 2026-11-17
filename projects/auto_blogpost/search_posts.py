import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open('/home/ubuntu/auto_blogpost/token.json') as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build('blogger', 'v3', credentials=c)

# Search posts
res = s.posts().search(blogId='3109655798381913489', q='Examination Schedule').execute()
print("Search results:")
for it in res.get('items', []):
    print("MATCH:", it['id'], it['title'], it['url'])

res2 = s.posts().search(blogId='3109655798381913489', q='National Diploma in Technology').execute()
for it in res2.get('items', []):
    print("NDT MATCH:", it['id'], it['title'], it['url'])
