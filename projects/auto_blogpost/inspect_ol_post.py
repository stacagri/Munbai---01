import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open('/home/ubuntu/auto_blogpost/token.json') as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build('blogger', 'v3', credentials=c)
p = s.posts().get(blogId='3109655798381913489', postId='7656809780093998803').execute()
print('TITLE:', p.get('title'))
print('URL:', p.get('url'))
print('--- CONTENT ---')
print(p.get('content'))
