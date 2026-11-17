import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build("blogger", "v3", credentials=c)
try:
    s.posts().delete(blogId="2198767951950215096", postId="956552848904326811").execute()
    print("Deleted 956552848904326811")
except Exception as e:
    print(e)
