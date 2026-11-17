import urllib.parse

CLIENT_ID = "REDACTED_GOOGLE_CLIENT_ID"
REDIRECT_URI = "http://localhost"
SCOPES = "https://www.googleapis.com/auth/blogger https://www.googleapis.com/auth/drive.file"

params = {
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": SCOPES,
    "access_type": "offline",
    "prompt": "consent"
}

print("AUTH_URL:")
print("https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(params))
