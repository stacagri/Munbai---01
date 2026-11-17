import json
import re
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)
creds = Credentials.from_authorized_user_info(t)
drive_service = build("drive", "v3", credentials=creds)
blogger_service = build("blogger", "v3", credentials=creds)

POST_ID = "7522282918742011766"
BLOG_ID = "3109655798381913489"

# Find NDT subfolder on Drive
q = "mimeType='application/vnd.google-apps.folder' and name contains 'National Diploma in Technology' and trashed=false"
res = drive_service.files().list(q=q).execute()
folders = res.get("files", [])
target_folder_id = folders[0]["id"] if folders else None

# Upload the newly generated thumb-size.png
img_path = "/home/ubuntu/auto_blogpost/thumb-size.png"
meta = {"name": "thumb-size.png"}
if target_folder_id:
    meta["parents"] = [target_folder_id]

media = MediaFileUpload(img_path, mimetype="image/png", resumable=True)
uploaded = drive_service.files().create(body=meta, media_body=media, fields="id").execute()
fid = uploaded.get("id")
drive_service.permissions().create(fileId=fid, body={"role": "reader", "type": "anyone"}).execute()
new_head_url = f"https://lh3.googleusercontent.com/d/{fid}"
print("New head banner uploaded to Drive CDN:", new_head_url)

# Update the post content
post = blogger_service.posts().get(blogId=BLOG_ID, postId=POST_ID).execute()
content = post["content"]

# Replace the previous image URL with the new authentic head banner
content = re.sub(r'https://lh3\.googleusercontent\.com/d/[a-zA-Z0-9_-]+', new_head_url, content, count=2)

updated_post = blogger_service.posts().patch(
    blogId=BLOG_ID,
    postId=POST_ID,
    body={"content": content}
).execute()

print("Successfully updated NDT post with authentic LKUni banner!")
print("Post URL:", updated_post.get("url"))
