from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_authorized_user_file('/home/ubuntu/auto_blogpost/token.json')
service = build('blogger', 'v3', credentials=creds)
blog_id = '2198767951950215096'

posts = service.posts().list(blogId=blog_id, maxResults=10).execute().get('items', [])
for p in posts:
    if "o/l examination time table" in p.get("title", "").lower():
        print(f"Deleting older post: {p.get('id')} - {p.get('title')}")
        service.posts().delete(blogId=blog_id, postId=p.get("id")).execute()
        print("Deleted.")
