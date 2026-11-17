import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)

# Note: currently token.json only has https://www.googleapis.com/auth/blogger scope.
print("Current scopes in token.json:", t.get("scopes"))

try:
    c = Credentials.from_authorized_user_info(t)
    drive_service = build('drive', 'v3', credentials=c)
    about = drive_service.about().get(fields="user").execute()
    print("Drive access successful! User:", about.get("user"))
except Exception as e:
    print("Drive error:", e)
