import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)
c = Credentials.from_authorized_user_info(t)
s = build("blogger", "v3", credentials=c)

# Permanently delete the trashed post
try:
    s.posts().delete(blogId="3109655798381913489", postId="7656809780093998803").execute()
    print("Permanently deleted 7656809780093998803 from Blogger trash.")
except Exception as e:
    print("Delete error:", e)

# Remove from posted_cache.json
cache_file = "/home/ubuntu/auto_blogpost/posted_cache.json"
with open(cache_file, "r") as f:
    cache = json.load(f)

url = "https://tamilguru.lk/gce-ol-examination-time-table-2026/"
if url in cache:
    cache.remove(url)
    with open(cache_file, "w") as f:
        json.dump(cache, f, indent=2)
    print(f"Removed {url} from cache.")
