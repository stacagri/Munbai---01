import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_authorized_user_file('/home/ubuntu/auto_blogpost/token.json')
service = build('blogger', 'v3', credentials=creds)
blog_id = '2198767951950215096'

for i in range(12):
    items = service.posts().list(blogId=blog_id, maxResults=5).execute().get('items', [])
    print(f"Check {i+1} ({time.strftime('%H:%M:%S')}): {[p.get('title') for p in items]}")
    time.sleep(10)
