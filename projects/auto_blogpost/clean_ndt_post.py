import os
import json
import urllib.request
import ssl
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)
creds = Credentials.from_authorized_user_info(t)
drive_service = build("drive", "v3", credentials=creds)
blogger_service = build("blogger", "v3", credentials=creds)

POST_ID = "7522282918742011766"
BLOG_ID = "3109655798381913489"

# Find or get the drive folder
q = "mimeType='application/vnd.google-apps.folder' and name contains 'National Diploma in Technology' and trashed=false"
res = drive_service.files().list(q=q).execute()
folders = res.get("files", [])
target_folder_id = folders[0]["id"] if folders else None

headers = {"User-Agent": "Mozilla/5.0"}

pdf_map = {
    "English": "https://tamilguru.lk/wp-content/uploads/2026/09/Gazette-Notification-Admission-for-the-NDT-2026-2027-intake-English.pdf",
    "Sinhala": "https://tamilguru.lk/wp-content/uploads/2026/09/Gazette-Notification-Admission-for-the-NDT-2026-2027-intake-Sinhala.pdf",
    "Tamil": "https://tamilguru.lk/wp-content/uploads/2026/09/Gazette-Notification-Admission-for-the-NDT-2026-2027-intake-Tamil.pdf"
}

uploaded_links = {}
for lang, url in pdf_map.items():
    fn = f"NDT_Gazette_{lang}.pdf"
    local_path = f"/tmp/{fn}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx) as r:
        with open(local_path, "wb") as f:
            f.write(r.read())
    
    meta = {"name": fn}
    if target_folder_id:
        meta["parents"] = [target_folder_id]
    media = MediaFileUpload(local_path, mimetype="application/pdf", resumable=True)
    f_up = drive_service.files().create(body=meta, media_body=media, fields="id").execute()
    fid = f_up.get("id")
    drive_service.permissions().create(fileId=fid, body={"role": "reader", "type": "anyone"}).execute()
    drive_link = f"https://drive.google.com/file/d/{fid}/view?usp=sharing"
    uploaded_links[lang] = drive_link
    print(f"Uploaded {lang} PDF: {drive_link}")

# Now update the Blogger post content
post = blogger_service.posts().get(blogId=BLOG_ID, postId=POST_ID).execute()
content = post["content"]

instructions_link = "https://itum.mrt.ac.lk/sites/default/files/inline-files/INSTRUCTIONS%20FOR%20APPLICANTS%20-%20NDT%202026-2027%20Intake.pdf"
clean_pdf_row = f'<td><a href="{uploaded_links["English"]}" target="_blank">English</a> | <a href="{uploaded_links["Sinhala"]}" target="_blank">Sinhala</a> | <a href="{uploaded_links["Tamil"]}" target="_blank">Tamil</a> | <a href="{instructions_link}" target="_blank">Instructions</a></td>'

import re
content = re.sub(r'<td><a href="https://tamilguru\.lk/.*?</td>', clean_pdf_row, content)

# Also fix the source link to official ITUM
content = content.replace("https://itum.mrt.ac.lk/ndt-26_27-intake", "https://itum.mrt.ac.lk/")

updated_post = blogger_service.posts().patch(
    blogId=BLOG_ID,
    postId=POST_ID,
    body={"content": content}
).execute()

print("Successfully updated post on Blogger! URL:", updated_post.get("url"))
