import os, json, re
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)
creds = Credentials.from_authorized_user_info(t)
drive_service = build("drive", "v3", credentials=creds)
blogger_service = build("blogger", "v3", credentials=creds)

POST_ID = "780447119676181670"
BLOG_ID = "3109655798381913489"

# Find Drive folder
q = "mimeType='application/vnd.google-apps.folder' and name contains 'Examination Time Table' and trashed=false"
res = drive_service.files().list(q=q).execute()
folders = res.get("files", [])
target_folder_id = folders[0]["id"] if folders else None

clean_links = {}
for lang in ["English", "Sinhala", "Tamil"]:
    p = f"/tmp/{lang}_clean.pdf"
    fn = f"GCE_OL_Time_Table_2026_{lang}.pdf"
    meta = {"name": fn}
    if target_folder_id:
        meta["parents"] = [target_folder_id]
    media = MediaFileUpload(p, mimetype="application/pdf", resumable=True)
    f_up = drive_service.files().create(body=meta, media_body=media, fields="id").execute()
    fid = f_up.get("id")
    drive_service.permissions().create(fileId=fid, body={"role": "reader", "type": "anyone"}).execute()
    clean_url = f"https://drive.google.com/file/d/{fid}/view?usp=sharing"
    clean_links[lang] = clean_url
    print(f"Uploaded clean {lang} PDF: {clean_url}")

# Update Blogger post content
post = blogger_service.posts().get(blogId=BLOG_ID, postId=POST_ID).execute()
content = post["content"]

new_pdf_row = f'<td><a href="{clean_links["English"]}" target="_blank">English</a> | <a href="{clean_links["Sinhala"]}" target="_blank">Sinhala</a> | <a href="{clean_links["Tamil"]}" target="_blank">Tamil</a></td>'

# Replace old PDF row
content = re.sub(r'<td><a href="https://drive\.google\.com/file/d/.*?</td>', new_pdf_row, content, count=1)

updated_post = blogger_service.posts().patch(
    blogId=BLOG_ID,
    postId=POST_ID,
    body={"content": content}
).execute()

print("Blogger post updated successfully with 100% clean PDFs!")
print("Post URL:", updated_post.get("url"))
