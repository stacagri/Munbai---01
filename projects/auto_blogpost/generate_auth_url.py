import json
from google_auth_oauthlib.flow import InstalledAppFlow

client_config = {
  "installed": {
    "client_id": "REDACTED_GOOGLE_CLIENT_ID",
    "project_id": "lkuni-official",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "REDACTED_GOOGLE_OAUTH_SECRET",
    "redirect_uris": ["http://localhost"]
  }
}

flow = InstalledAppFlow.from_client_config(
    client_config,
    scopes=["https://www.googleapis.com/auth/blogger"],
    redirect_uri="http://localhost"
)

auth_url, _ = flow.authorization_url(
    access_type="offline",
    prompt="consent"
)

print("AUTH_URL:")
print(auth_url)
