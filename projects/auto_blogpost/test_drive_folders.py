import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)

c = Credentials.from_authorized_user_info(t)
drive_service = build('drive', 'v3', credentials=c)

def get_or_create_folder(folder_name, parent_id=None):
    q = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    res = drive_service.files().list(q=q, fields='files(id, name)').execute()
    files = res.get('files', [])
    if files:
        return files[0]['id']
    meta = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
    if parent_id:
        meta['parents'] = [parent_id]
    f = drive_service.files().create(body=meta, fields='id').execute()
    fid = f.get('id')
    try:
        drive_service.permissions().create(fileId=fid, body={'role': 'reader', 'type': 'anyone'}).execute()
    except Exception:
        pass
    return fid

root_folder_id = get_or_create_folder("LKUni_Blog_Uploads")
print("Main Folder ID:", root_folder_id)

post_folder_id = get_or_create_folder("Test_Post_Folder", parent_id=root_folder_id)
print("Subfolder ID:", post_folder_id)

media = MediaFileUpload('/home/ubuntu/auto_blogpost/thumb-size.png', mimetype='image/png')
meta = {'name': 'thumb.png', 'mimeType': 'image/png', 'parents': [post_folder_id]}
up = drive_service.files().create(body=meta, media_body=media, fields='id').execute()
img_id = up.get('id')
drive_service.permissions().create(fileId=img_id, body={'role': 'reader', 'type': 'anyone'}).execute()
print("Uploaded image inside subfolder! URL: https://lh3.googleusercontent.com/d/" + img_id)
