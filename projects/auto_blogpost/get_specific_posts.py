import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open('/home/ubuntu/auto_blogpost/token.json') as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build('blogger', 'v3', credentials=c)

for pid in ["7522282918742011766", "7656809780093998803"]:
    try:
        p = s.posts().get(blogId='3109655798381913489', postId=pid).execute()
        print(f"FOUND {pid}:")
        print("  Title:", p.get("title"))
        print("  Published:", p.get("published"))
        print("  Updated:", p.get("updated"))
        print("  URL:", p.get("url"))
    except Exception as e:
        print(f"NOT FOUND {pid}: {e}")
