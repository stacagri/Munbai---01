import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open(/home/ubuntu/auto_blogpost/token.json) as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build(blogger, v3, credentials=c)

posts = s.posts().list(blogId=3109655798381913489, maxResults=1).execute()
item = posts[items][0]
print(TITLE:, item[title])
print(URL:, item[url])
print(--- CONTENT ---)
print(item[content])
