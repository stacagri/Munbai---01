import os
import sys
import json
import urllib.request
import urllib.parse

SECRET_FILE = "/home/ubuntu/auto_blogpost/client_secret.json"
TOKEN_FILE = "/home/ubuntu/auto_blogpost/token.json"

with open(SECRET_FILE, "r") as f:
    cfg = json.load(f)

cred_info = cfg.get("installed", cfg.get("web", {}))
CLIENT_ID = cred_info["client_id"]
CLIENT_SECRET = cred_info["client_secret"]
REDIRECT_URI = "http://localhost"
SCOPES = ["https://www.googleapis.com/auth/blogger", "https://www.googleapis.com/auth/drive.file"]

def exchange_code_for_token(code_or_url):
    code = code_or_url.strip()
    if "code=" in code:
        parsed = urllib.parse.urlparse(code)
        qs = urllib.parse.parse_qs(parsed.query)
        if "code" in qs:
            code = qs["code"][0]
        else:
            code = code.split("code=")[-1].split("&")[0]

    data = urllib.parse.urlencode({
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    try:
        with urllib.request.urlopen(req) as resp:
            token_data = json.loads(resp.read().decode("utf-8"))
            token_obj = {
                "token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "scopes": SCOPES,
                "expiry": None
            }
            with open(TOKEN_FILE, "w") as tf:
                json.dump(token_obj, tf, indent=2)
            print("SUCCESS: Token saved to", TOKEN_FILE)
            print("Access Token:", token_data.get("access_token")[:15] + "...")
            print("Refresh Token present:", bool(token_data.get("refresh_token")))
            return True
    except Exception as e:
        print("ERROR exchanging code:", e)
        if hasattr(e, "read"):
            print("Details:", e.read().decode("utf-8"))
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        exchange_code_for_token(sys.argv[1])
    else:
        print("Usage: python3 exchange_tool.py <CODE>")
