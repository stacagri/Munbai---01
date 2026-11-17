#!/usr/bin/env python3
"""
LKUni Government Gazette Auto-Poster & Scraper
- Source: https://documents.gov.lk/web/gazettes
- Target Blog: LKUni (https://www.lkuni.com/)
- Format: Matches https://www.lkuni.com/2025/11/government-gazette-2025-november-14.html
- Features:
  * Automatic date extraction from documents.gov.lk
  * Duplicate check via local cache & live Blogger API
  * Custom 1600x1066 head banner creation
  * Google Drive CDN upload for head banner
  * Clean #simple_table layout for English, Sinhala, and Tamil gazettes
  * Telegram notifications (optional)
"""

import os
import sys
import json
import time
import ssl
import re
import datetime
import urllib.request
import urllib.parse
import argparse
import logging
from PIL import Image, ImageDraw, ImageFont
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==============================================================================
# CONFIGURATION
# ==============================================================================
OFFICIAL_BLOG_ID = "3109655798381913489"  # https://www.lkuni.com/
TEST_BLOG_ID = "2198767951950215096"      # https://lkunitest.blogspot.com/
DEFAULT_BLOG_ID = OFFICIAL_BLOG_ID

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9269727444:AAHwsO8xw7__8BWWfxSGNDWuUnwF7lQ6FVw")
TELEGRAM_CHAT_IDS = [cid.strip() for cid in os.getenv("TELEGRAM_CHAT_IDS", "1499235921,@differentpaths").split(",") if cid.strip()]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, "gazette_posted_cache.json")
TEMPLATE_IMG = os.path.join(BASE_DIR, "thumb_template.png")

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# ==============================================================================
# SCRAPER FUNCTIONS FOR DOCUMENTS.GOV.LK
# ==============================================================================
def fetch_available_gazette_dates() -> list:
    """Fetches list of published gazette dates from documents.gov.lk/web/gazettes."""
    url = "https://documents.gov.lk/web/gazettes"
    import requests, urllib3
    urllib3.disable_warnings()

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, verify=False, timeout=25)
            if resp.status_code == 200:
                dates = sorted(list(set(re.findall(r"(\d{4}-\d{2}-\d{2})T00:00:00\.000Z", resp.text))), reverse=True)
                if dates:
                    return dates
        except Exception as e:
            logging.warning(f"Attempt {attempt+1} failed to fetch gazette dates: {e}")
            time.sleep(2)

    return []

def fetch_gazette_details_for_date(date_str: str) -> dict:
    """
    Fetches documents.gov.lk/web/Gazette?date=YYYY-MM-DD and extracts all PDF files.
    """
    url = f"https://documents.gov.lk/web/Gazette?date={date_str}"
    import requests, urllib3
    urllib3.disable_warnings()

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    html = ""
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, verify=False, timeout=25)
            if resp.status_code == 200:
                html = resp.text
                break
        except Exception as e:
            logging.warning(f"Attempt {attempt+1} failed to fetch gazette details for {date_str}: {e}")
            time.sleep(2)

    if not html:
        return None

    # Parse JSON entries from Next.js SSR payload
    entries = []
    for m in re.finditer(r"\{[^{}]*uploadedFile[^{}]*\}", html):
        clean = m.group(0).replace('\\"', '"')
        try:
            data = json.loads(clean)
            if data.get("uploadedFileFormat", "").upper() == "PDF":
                entries.append(data)
        except Exception:
            pass

    # Resolve links for English, Sinhala, Tamil
    # Preference: Part 1 Section (IIA) -> Part 1 Section (I) -> Any Part 1 -> Any PDF
    base_file_url = "https://documents.gov.lk/api/content-file-proxy?file=/"

    def find_best_file(language: str):
        lang_upper = language.upper()
        # 1. Section (IIA)
        for e in entries:
            if e.get("language", "").upper() == lang_upper and "IIA" in (e.get("section", "") or ""):
                return base_file_url + urllib.parse.quote(e["uploadedFile"], safe="/")
        # 2. Section (I)
        for e in entries:
            if e.get("language", "").upper() == lang_upper and ("SECTION (I)" in (e.get("section", "") or "") or "I-I" in (e.get("uploadedFile", "") or "")):
                return base_file_url + urllib.parse.quote(e["uploadedFile"], safe="/")
        # 3. Any in this language
        for e in entries:
            if e.get("language", "").upper() == lang_upper:
                return base_file_url + urllib.parse.quote(e["uploadedFile"], safe="/")
        return None

    english_link = find_best_file("ENGLISH")
    sinhala_link = find_best_file("SINHALA")
    tamil_link = find_best_file("TAMIL")

    # Date formatting: e.g. "2026-11-06" -> "2026 November 06"
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        month_name = dt.strftime("%B")
        day_str = dt.strftime("%d")
        formatted_date = f"{dt.year} {month_name} {day_str}"
    except Exception:
        formatted_date = date_str

    title = f"Government Gazette - {formatted_date}"

    return {
        "date": date_str,
        "formatted_date": formatted_date,
        "title": title,
        "files": {
            "english": english_link,
            "sinhala": sinhala_link,
            "tamil": tamil_link,
        },
        "all_entries": entries
    }

# ==============================================================================
# BANNER GENERATION (1600x1066)
# ==============================================================================
def create_gazette_head_image(date_str: str) -> str:
    """Generates the official LKUni Gazette head banner (1600x1066)."""
    output_path = os.path.join(BASE_DIR, f"gazette_banner_{date_str}.png")
    if not os.path.exists(TEMPLATE_IMG):
        raise FileNotFoundError(f"Template image {TEMPLATE_IMG} not found!")

    im = Image.open(TEMPLATE_IMG).convert("RGB")
    draw = ImageDraw.Draw(im)

    font_sans_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_serif_bold = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
    if not os.path.exists(font_serif_bold):
        font_serif_bold = font_sans_bold

    # 1. Institution Name in Green Bar (Y: 160 to 304, height: 144)
    draw.rectangle([0, 160, 1600, 304], fill=(0, 94, 32))
    inst_text = "Department of Government Printing"
    inst_font = ImageFont.truetype(font_sans_bold, 56)
    bbox = draw.textbbox((0, 0), inst_text, font=inst_font)
    inst_w = bbox[2] - bbox[0]
    inst_h = bbox[3] - bbox[1]
    inst_x = (1600 - inst_w) // 2
    inst_y = 160 + (144 - inst_h) // 2 - (bbox[1] // 2)
    draw.text((inst_x, inst_y), inst_text, fill=(255, 255, 255), font=inst_font)

    # 2. 'Gazette' in Deep Royal Blue (0, 38, 179)
    title_text = "Gazette"
    title_font = ImageFont.truetype(font_serif_bold, 110)
    bbox = draw.textbbox((0, 0), title_text, font=title_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (1600 - tw) // 2
    ty = 360 + (280 - th) // 2
    draw.text((tx, ty), title_text, fill=(0, 38, 179), font=title_font)

    # 3. Date in Black Serif (0, 0, 0)
    date_font = ImageFont.truetype(font_serif_bold, 86)
    bbox = draw.textbbox((0, 0), date_str, font=date_font)
    dw = bbox[2] - bbox[0]
    dx = (1600 - dw) // 2
    dy = 695
    draw.text((dx, dy), date_str, fill=(0, 0, 0), font=date_font)

    im.save(output_path, "PNG", quality=95)
    logging.info(f"Generated gazette head image: {output_path}")
    return output_path

# ==============================================================================
# GOOGLE DRIVE & BLOGGER INTEGRATION
# ==============================================================================
def get_or_create_drive_folder(drive_service, folder_name: str, parent_id: str = None) -> str:
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    meta = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    folder = drive_service.files().create(body=meta, fields="id").execute()
    return folder.get("id")

def upload_banner_to_drive(image_path: str, date_str: str) -> str:
    token_file = os.path.join(BASE_DIR, "token.json")
    if not os.path.exists(token_file):
        raise FileNotFoundError("token.json not found!")

    with open(token_file, "r") as f:
        creds_data = json.load(f)
    creds = Credentials.from_authorized_user_info(creds_data)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    drive_service = build("drive", "v3", credentials=creds)
    parent_folder_id = get_or_create_drive_folder(drive_service, "LKUni_Blog_Uploads")
    folder_name = f"Government_Gazette_{date_str.replace('-', '_')}"
    target_folder_id = get_or_create_drive_folder(drive_service, folder_name, parent_id=parent_folder_id)

    file_metadata = {
        "name": "thumb-size.png",
        "parents": [target_folder_id]
    }
    media = MediaFileUpload(image_path, resumable=True)
    uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    file_id = uploaded_file.get("id")

    drive_service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"}
    ).execute()

    cdn_url = f"https://lh3.googleusercontent.com/d/{file_id}"
    logging.info(f"Drive image uploaded: {cdn_url}")
    return cdn_url

def build_post_html(formatted_date: str, banner_url: str, files: dict) -> str:
    """Builds exact LKUni post HTML matching sample post."""
    table_rows = []
    if files.get("english"):
        table_rows.append(f"""<tr>
\t<td>English Gazette</td>
\t<td><a href="{files['english']}" target="_blank">Click Here</a></td>
</tr>""")

    if files.get("sinhala"):
        table_rows.append(f"""<tr>
\t<td>Sinhala Gazette</td>
\t<td><a href="{files['sinhala']}" target="_blank">Click Here</a></td>
</tr>""")

    if files.get("tamil"):
        table_rows.append(f"""<tr>
\t<td>Tamil Gazette</td>
\t<td><a href="{files['tamil']}" target="_blank">Click Here</a></td>
</tr>""")

    rows_html = "\n".join(table_rows)

    html = f"""<p>&nbsp;</p><div class="separator" style="clear: both; text-align: center;"><a href="{banner_url}" style="margin-left: 1em; margin-right: 1em;"><img border="0" data-original-height="1066" data-original-width="1600" src="{banner_url}" /></a></div><div><br /></div><div><br /></div><div><h3>Government Gazette {formatted_date}</h3></div><br /><p></p>

<style>
#simple_table {{
\tfont-family: arial, sans-serif;
\t border-collapse: collapse; 
\t width: 100%;
\tbackground-color: #000000;
\tcolor:#33fcff;
}}
#simple_table td, #simple_table th {{
\t text-align: left;
\t padding: 8px;
\t border: 1px solid #ffffff;
}}
#simple_table tr:nth-child(even) {{
\tbackground-color: #1d1b1b;
}}
#simple_table tr:hover {{
\tbackground-color: #9e0000;
}}
#simple_table tr > th 
{{
\tbackground: #00fbff;
\t color: #000000;
}}
</style>
 <table id="simple_table">
<tbody><tr>
\t<th><p class="MsoNormal">Details<o:p></o:p></p></th>
\t<th><p class="MsoNormal">Links<o:p></o:p></p></th>
</tr>

{rows_html}
</tbody></table><br /><br /><br /><br />"""

    return html

# ==============================================================================
# CACHE & DUPLICATE CHECK
# ==============================================================================
def load_posted_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    # convert old list format to dict
                    return {d: {} for d in data}
                return data
        except Exception:
            return {}
    return {}

def save_posted_cache(cache: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

def get_existing_post_for_date(date_str: str, formatted_date: str, blog_id: str = OFFICIAL_BLOG_ID):
    """Checks cache and live Blogger posts for existing publication of this gazette date."""
    cache = load_posted_cache()
    if date_str in cache and cache[date_str].get("post_id"):
        return cache[date_str]

    # Check live Blogger posts
    token_file = os.path.join(BASE_DIR, "token.json")
    if os.path.exists(token_file):
        try:
            with open(token_file, "r") as f:
                creds_data = json.load(f)
            creds = Credentials.from_authorized_user_info(creds_data)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_file, "w") as f:
                    f.write(creds.to_json())
            service = build("blogger", "v3", credentials=creds)
            res = service.posts().list(blogId=blog_id, labels="gazette", maxResults=20, fetchBodies=False).execute()
            target_str = formatted_date.lower()
            for p in res.get("items", []):
                t = p.get("title", "").lower()
                if target_str in t or date_str in t:
                    return {"post_id": p.get("id"), "url": p.get("url"), "title": p.get("title")}
        except Exception as e:
            logging.warning(f"Could not verify live Blogger titles: {e}")

    return None

# ==============================================================================
# TELEGRAM BROADCAST
# ==============================================================================
def format_telegram_message(formatted_date: str, post_url: str) -> str:
    """Formats Telegram post text according to LKUni Gazette template."""
    return f"""🟩 Government Gazette {formatted_date} 🟩

👉 Gazette - {post_url}

තවත් මෙවැනි තොරතුරු දැනගැනීමට ✅

👉 Join Our Telegram Channel :https://t.me/differentpaths

යාළුවන්ටත් දැනගන්න share කරන්න 👍👍👍"""

def send_telegram_notification(formatted_date: str, post_url: str) -> bool:
    """Broadcasts gazette post to configured Telegram channels/chats."""
    if not TELEGRAM_BOT_TOKEN:
        logging.warning("No TELEGRAM_BOT_TOKEN configured.")
        return False

    msg_text = format_telegram_message(formatted_date, post_url)
    import requests

    success = False
    for cid in TELEGRAM_CHAT_IDS:
        cid = cid.strip()
        if not cid:
            continue
        try:
            tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": cid,
                "text": msg_text,
                "disable_web_page_preview": False
            }
            res = requests.post(tg_url, json=payload, timeout=15)
            if res.status_code == 200:
                logging.info(f"Telegram notification delivered to {cid}")
                success = True
            else:
                logging.warning(f"Telegram returned {res.status_code} for {cid}: {res.text}")
        except Exception as e:
            logging.error(f"Error sending Telegram update to {cid}: {e}")

    return success

# ==============================================================================
# PUBLISH CONTROLLER
# ==============================================================================
def publish_gazette(date_str: str, target_blog_id: str = OFFICIAL_BLOG_ID, force: bool = False) -> dict:
    details = fetch_gazette_details_for_date(date_str)
    if not details:
        return {"status": "error", "message": f"Could not retrieve details for gazette date {date_str}"}

    cache = load_posted_cache()
    cached_info = cache.get(date_str, {})
    existing = get_existing_post_for_date(date_str, details["formatted_date"], blog_id=target_blog_id)

    # Check if files changed or if it's already posted
    if existing and not force:
        cached_files = cached_info.get("files", {})
        current_files = details["files"]
        has_new_files = any(current_files.get(k) and not cached_files.get(k) for k in ["english", "sinhala", "tamil"])
        if not has_new_files:
            return {
                "status": "duplicate",
                "message": f"Gazette for date {date_str} ({details['formatted_date']}) is already published.",
                "url": existing.get("url")
            }
        else:
            logging.info(f"New files detected for existing gazette {date_str}. Updating post...")
            banner_url = cached_info.get("banner_url")
            if not banner_url:
                banner_img_path = create_gazette_head_image(date_str)
                banner_url = upload_banner_to_drive(banner_img_path, date_str)
            content_html = build_post_html(details["formatted_date"], banner_url, current_files)

            token_file = os.path.join(BASE_DIR, "token.json")
            with open(token_file, "r") as f:
                creds_data = json.load(f)
            creds = Credentials.from_authorized_user_info(creds_data)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_file, "w") as f:
                    f.write(creds.to_json())
            service = build("blogger", "v3", credentials=creds)
            patch_res = service.posts().patch(
                blogId=target_blog_id,
                postId=existing["post_id"],
                body={"content": content_html}
            ).execute()
            cache[date_str] = {
                "post_id": existing["post_id"],
                "url": patch_res.get("url"),
                "banner_url": banner_url,
                "files": current_files
            }
            save_posted_cache(cache)
            logging.info(f"Updated gazette post with new files: {patch_res.get('url')}")
            return {
                "status": "updated",
                "title": details["title"],
                "url": patch_res.get("url"),
                "date": date_str
            }

    # Generate banner
    banner_img_path = create_gazette_head_image(date_str)
    banner_url = upload_banner_to_drive(banner_img_path, date_str)

    # Build HTML
    content_html = build_post_html(details["formatted_date"], banner_url, details["files"])

    # Publish to Blogger
    token_file = os.path.join(BASE_DIR, "token.json")
    with open(token_file, "r") as f:
        creds_data = json.load(f)
    creds = Credentials.from_authorized_user_info(creds_data)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    service = build("blogger", "v3", credentials=creds)
    body = {
        "kind": "blogger#post",
        "title": details["title"],
        "content": content_html,
        "labels": ["gazette"]
    }

    res = service.posts().insert(blogId=target_blog_id, body=body, isDraft=False).execute()
    post_url = res.get("url")
    post_id = res.get("id")

    # Update cache
    cache[date_str] = {
        "post_id": post_id,
        "url": post_url,
        "banner_url": banner_url,
        "files": details["files"]
    }
    save_posted_cache(cache)

    logging.info(f"Published gazette successfully: {post_url}")

    # Send Telegram notification
    try:
        send_telegram_notification(details["formatted_date"], post_url)
    except Exception as e:
        logging.warning(f"Failed to send Telegram notification: {e}")

    return {
        "status": "success",
        "title": details["title"],
        "url": post_url,
        "date": date_str
    }

# ==============================================================================
# CLI
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="LKUni Gazette Auto-Publisher")
    parser.add_argument("--date", help="Specific gazette date YYYY-MM-DD to process")
    parser.add_argument("--test-blog", action="store_true", help="Post to test blog instead of official")
    parser.add_argument("--sample", action="store_true", help="Generate sample post layout only")
    parser.add_argument("--force", action="store_true", help="Force publish even if already in cache")
    args = parser.parse_args()

    blog_id = TEST_BLOG_ID if args.test_blog else OFFICIAL_BLOG_ID

    dates = fetch_available_gazette_dates()
    if not dates:
        print("No gazette dates could be retrieved from documents.gov.lk")
        return

    target_date = args.date or dates[0]
    print(f"Target gazette date: {target_date}")

    if args.sample:
        details = fetch_gazette_details_for_date(target_date)
        print("SAMPLE POST DETAILS:")
        print("Title:", details["title"])
        print("Files:", json.dumps(details["files"], indent=2))
        dummy_url = f"https://www.lkuni.com/{target_date[:4]}/{target_date[5:7]}/government-gazette-{target_date}.html"
        print("\nSAMPLE TELEGRAM MESSAGE:")
        print(format_telegram_message(details["formatted_date"], dummy_url))
        return

    res = publish_gazette(target_date, target_blog_id=blog_id, force=args.force)
    print("Result:", res)

if __name__ == "__main__":
    main()
