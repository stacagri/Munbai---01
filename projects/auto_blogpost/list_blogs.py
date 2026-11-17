import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    token_data = json.load(f)

creds = Credentials.from_authorized_user_info(token_data)
service = build('blogger', 'v3', credentials=creds)

blogs = service.blogs().listByUser(userId='self').execute()
print("Found blogs:")
for b in blogs.get('items', []):
    print(f"ID: {b['id']} | Name: {b['name']} | URL: {b['url']}")
