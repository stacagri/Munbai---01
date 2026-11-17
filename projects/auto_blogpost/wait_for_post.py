import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_authorized_user_file('/home/ubuntu/auto_blogpost/token.json')
service = build('blogger', 'v3', credentials=creds)
blog_id = '2198767951950215096'

for attempt in range(6):
    items = service.posts().list(blogId=blog_id, maxResults=5).execute().get('items', [])
    titles = [p.get('title') for p in items]
    print(f"Attempt {attempt+1}: {titles}")
    if any("o/l examination time table" in t.lower() for t in titles):
        print("Found post!")
        for p in items:
            if "o/l examination time table" in p.get('title', '').lower():
                print("Post URL:", p.get('url'))
                print("Post ID:", p.get('id'))
        break
    time.sleep(5)
