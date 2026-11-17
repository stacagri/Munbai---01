#!/usr/bin/env python3
"""
OAuth2 Initial Authentication Setup for Google Blogger API
Generates token.json from client_secret.json
"""

import os
import sys
from urllib.parse import urlparse, parse_qs
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/blogger"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")

def main():
    if not os.path.exists(CLIENT_SECRET_FILE):
        print(f"Error: {CLIENT_SECRET_FILE} not found!")
        sys.exit(1)

    print("\n" + "="*70)
    print("GOOGLE BLOGGER AUTHORIZATION SETUP")
    print("="*70)

    # Use redirect_uri = 'http://localhost'
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost"
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )

    print("\nSTEP 1: Open the link below in your browser:\n")
    print(auth_url)
    print("\n" + "="*70)
    print("STEP 2: Log in with the Google Account that owns 'lkunitest.blogspot.com'.")
    print("STEP 3: Click 'Continue' / 'Allow'.")
    print("STEP 4: Google will redirect to an address starting with:")
    print("        http://localhost/?code=4/0A... (browser might say 'Site can't be reached')")
    print("STEP 5: Copy that entire address from your browser's address bar and paste it below.")
    print("="*70 + "\n")

    try:
        user_input = input("Paste redirected URL or code here: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(1)

    if not user_input:
        print("Error: Empty input.")
        sys.exit(1)

    if "code=" in user_input:
        code = parse_qs(urlparse(user_input).query).get("code", [user_input])[0]
    else:
        code = user_input

    flow.fetch_token(code=code)
    creds = flow.credentials

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    print("\n" + "="*70)
    print(f"SUCCESS! token.json has been created at:\n{TOKEN_FILE}")
    print("You can now run auto_blogger.py to publish posts automatically!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
