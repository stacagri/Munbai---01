import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build("blogger", "v3", credentials=c)

media = MediaFileUpload("/home/ubuntu/auto_blogpost/thumb-size.png", mimetype="image/png")
post_body = {"title": "Media Test", "content": "<p>Testing media upload</p>"}

try:
    res = s.posts().insert(blogId="2198767951950215096", body=post_body, media_body=media).execute()
    print("SUCCESS with media_body!")
    print(res)
except Exception as e:
    print("FAILED with media_body:", e)
