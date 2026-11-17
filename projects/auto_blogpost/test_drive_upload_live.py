import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)

c = Credentials.from_authorized_user_info(t)
drive_service = build('drive', 'v3', credentials=c)

# Test uploading thumb-size.png
file_metadata = {
    'name': 'thumb-size.png',
    'mimeType': 'image/png'
}
media = MediaFileUpload('/home/ubuntu/auto_blogpost/thumb-size.png', mimetype='image/png')

uploaded_file = drive_service.files().create(
    body=file_metadata,
    media_body=media,
    fields='id, name, webViewLink'
).execute()

file_id = uploaded_file.get('id')
print("Uploaded File ID:", file_id)

# Set permission: anyone with link can view
perm = drive_service.permissions().create(
    fileId=file_id,
    body={'role': 'reader', 'type': 'anyone'}
).execute()
print("Permission granted:", perm)

# Google Drive direct image URL formats:
direct_url = f"https://lh3.googleusercontent.com/d/{file_id}"
print("Direct Google CDN Image URL:", direct_url)
