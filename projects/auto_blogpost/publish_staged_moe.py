#!/usr/bin/env python3
"""
Publisher for MOE Special Notices staged from Android Mobile Bridge
- Checks moe_staged_queue.json
- Merges English & Sinhala notices and PDFs
- Renders 1600x1066 LKUni head banner
- Publishes to LKUni.com & broadcasts to Telegram
"""

import os
import sys
import re
import json
import time
import logging
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from auto_blogger import (
    OFFICIAL_BLOG_ID,
    upload_to_google_drive,
    TEMPLATE_IMG,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_IDS,
    fetch_recent_blogger_titles
)
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import requests

QUEUE_FILE = os.path.join(BASE_DIR, "moe_staged_queue.json")
CACHE_FILE = os.path.join(BASE_DIR, "moe_posted_cache.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [MOE-PUB] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

def load_queue():
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_queue(q):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(q, f, indent=2)

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_cache(c):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(c, f, indent=2)

def parse_moe_html(html_content: str, lang: str = "en", source_url: str = ""):
    """Extracts latest notice title, bullet text, and PDF links from MOE HTML."""
    soup = BeautifulSoup(html_content, "html.parser")
    
    # 1. Extract PDFs
    pdfs = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        t = a.get_text(strip=True)
        if href.lower().endswith(".pdf"):
            if not any(href == p[1] for p in pdfs):
                # Clean label
                lbl = t or "Notice PDF"
                if "sinhala" in t.lower() or "sinhala" in href.lower() or "si" in href.lower():
                    lbl = "Sinhala Notice (PDF)"
                elif "english" in t.lower() or "english" in href.lower() or "en" in href.lower():
                    lbl = "English Notice (PDF)"
                elif "tamil" in t.lower() or "tamil" in href.lower() or "ta" in href.lower():
                    lbl = "Tamil Notice (PDF)"
                pdfs.append((lbl, href))
                
    # 2. Extract notice title
    title = None
    main = soup.find("main") or soup
    for a in main.find_all("a", href=True):
        t = a.get_text(strip=True)
        h = a["href"]
        if len(t) > 25 and not any(skip in h.lower() for skip in ["#", "page", "category", "tag", "facebook", "twitter"]):
            title = t
            break

    if not title:
        for heading in soup.find_all(["h1", "h2", "h3"]):
            t = heading.get_text(strip=True)
            if t and len(t) > 20 and not any(skip in t.lower() for skip in ["special notices", "විශේෂ නිවේදන", "menu", "search"]):
                title = t
                break

    # 3. Extract relevant article paragraphs (strictly excluding nav/footer menus)
    paragraphs = []
    content_area = soup.find("div", class_=re.compile(r"content|entry|post", re.I)) or soup.find("article") or soup.find("main")
    if content_area:
        for p in content_area.find_all("p"):
            txt = p.get_text(strip=True)
            txt_lower = txt.lower()
            if len(txt) > 35:
                # Exclude menu items, footers, minister names, branch directories
                skip_keywords = ["privacy", "copyright", "terms", "telephone", "directory", "branch", "minister", "affiliated", "menu", "search", "contact us", "site map"]
                if not any(k in txt_lower for k in skip_keywords):
                    if not any(c in txt for c in ["\u0d80", "\u0dff", "\u0b80", "\u0bff"]):  # Exclude Sinhala/Tamil text from English extraction
                        paragraphs.append(txt)

    return {
        "title": title or "Special Notice",
        "pdfs": pdfs,
        "paragraphs": paragraphs[:4],
        "lang": lang,
        "source_url": source_url or ""
    }

def simplify_banner_title(raw_title: str) -> str:
    """Creates a concise, impactful title for the 1600x1066 head banner."""
    t = raw_title.strip()
    if "Sri Lanka Education Administrative Service" in t or "SLEAS" in t:
        if "Transfer" in t:
            return "SLEAS Annual Transfers Review"
        return "Sri Lanka Education Administrative Service"
    if "Graduate Teacher Recruitment" in t or "Graduate Teacher" in t:
        return "Graduate Teacher Recruitment"
    if "Festival of Foreign Languages" in t:
        return "National Festival of Foreign Languages"
    if "Bilingual Education" in t:
        return "Postgraduate Diploma in Bilingual Education"
    if "School Timetables" in t:
        return "Preparation of School Timetables"

    # Generic cleaner: if title is longer than 8 words, try splitting by separator or capping
    words = t.split()
    if len(words) > 8:
        parts = re.split(r'[:–-]', t)
        if len(parts) > 1 and len(parts[0].split()) <= 8:
            return parts[0].strip()
        return " ".join(words[:8])
    return t

def fit_text_to_lines(text: str, font_path: str, max_w=1320, max_lines=3, initial_font_size=74, min_font_size=42):
    words = text.split()
    font_size = initial_font_size
    while font_size >= min_font_size:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()
            return [text], font_size, font

        lines = []
        curr = []
        overflow = False
        for w in words:
            test = " ".join(curr + [w])
            bbox = font.getbbox(test) if hasattr(font, "getbbox") else (0, 0, font_size * len(test) * 0.5, font_size)
            if (bbox[2] - bbox[0]) <= max_w:
                curr.append(w)
            else:
                if curr:
                    lines.append(" ".join(curr))
                    curr = [w]
                else:
                    lines.append(w)
                    curr = []
            if len(lines) > max_lines:
                overflow = True
                break
        if curr and not overflow:
            lines.append(" ".join(curr))
            if len(lines) > max_lines:
                overflow = True

        if not overflow:
            return lines, font_size, font
        font_size -= 4

    # Fallback with min_font_size
    font = ImageFont.truetype(font_path, min_font_size)
    lines = []
    curr = []
    for w in words:
        test = " ".join(curr + [w])
        bbox = font.getbbox(test) if hasattr(font, "getbbox") else (0, 0, min_font_size * len(test) * 0.5, min_font_size)
        if (bbox[2] - bbox[0]) <= max_w:
            curr.append(w)
        else:
            if curr:
                lines.append(" ".join(curr))
                curr = [w]
            else:
                lines.append(w)
                curr = []
    if curr:
        lines.append(" ".join(curr))
    return lines[:max_lines], min_font_size, font

def is_moe_duplicate(candidate_title: str, existing_titles: list) -> tuple:
    """Checks if the candidate notice title already exists on LKUni or in cache."""
    if not candidate_title or not existing_titles:
        return False, None

    c_norm = re.sub(r"[^\w\s]", " ", candidate_title.lower())
    c_words = set(c_norm.split())
    c_clean_banner = simplify_banner_title(candidate_title).lower()

    for ext in existing_titles:
        if not ext:
            continue
        e_norm = re.sub(r"[^\w\s]", " ", ext.lower())
        e_words = set(e_norm.split())

        # 1. Exact string or substring containment
        if c_norm in e_norm or e_norm in c_norm or candidate_title.strip().lower() == ext.strip().lower():
            return True, ext

        # 2. Simplified banner title match
        if c_clean_banner and len(c_clean_banner) > 8:
            if c_clean_banner in ext.lower() or ext.lower() in c_clean_banner:
                return True, ext

        # 3. Meaningful core keyword intersection
        meaningful_c = {w for w in c_words if len(w) >= 4 and w not in {"ministry", "education", "special", "notice"}}
        meaningful_e = {w for w in e_words if len(w) >= 4 and w not in {"ministry", "education", "special", "notice"}}

        if meaningful_c and meaningful_e:
            intersection = meaningful_c.intersection(meaningful_e)
            ratio_c = len(intersection) / len(meaningful_c)
            ratio_e = len(intersection) / len(meaningful_e)

            if ratio_c >= 0.65 or ratio_e >= 0.65:
                return True, ext

    return False, None

def create_moe_banner(title_text: str, year_str: str = "2027 (2026)") -> str:
    output_path = os.path.join(BASE_DIR, "moe_banner_gen.png")
    im = Image.open(TEMPLATE_IMG).convert("RGB")
    draw = ImageDraw.Draw(im)

    font_sans_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_serif_bold = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
    if not os.path.exists(font_serif_bold):
        font_serif_bold = font_sans_bold

    # 1. Green Bar (Y: 160 to 304, height: 144)
    draw.rectangle([0, 160, 1600, 304], fill=(0, 94, 32))
    inst_text = "MINISTRY OF EDUCATION, SRI LANKA"
    inst_font = ImageFont.truetype(font_sans_bold, 54)
    bbox = draw.textbbox((0, 0), inst_text, font=inst_font)
    iw = bbox[2] - bbox[0]
    ih = bbox[3] - bbox[1]
    draw.text(((1600 - iw) // 2, 160 + (144 - ih) // 2 - (bbox[1] // 2)), inst_text, fill=(255, 255, 255), font=inst_font)

    # 2. Simplified & Dynamically Fitted Title in Deep Royal Blue (RGB: 0, 38, 179)
    clean_title = simplify_banner_title(title_text)
    lines, font_size, course_font = fit_text_to_lines(clean_title, font_serif_bold, max_w=1320, max_lines=3, initial_font_size=74)

    line_height = int(font_size * 1.32)
    total_h = len(lines) * line_height
    start_y = 330 + (340 - total_h) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=course_font)
        lw = bbox[2] - bbox[0]
        lx = (1600 - lw) // 2
        ly = start_y + (i * line_height)
        draw.text((lx, ly), line, fill=(0, 38, 179), font=course_font)

    # 3. Year in Black Serif (RGB: 0, 0, 0)
    year_font = ImageFont.truetype(font_serif_bold, 84)
    bbox = draw.textbbox((0, 0), year_str, font=year_font)
    yw = bbox[2] - bbox[0]
    draw.text(((1600 - yw) // 2, 695), year_str, fill=(0, 0, 0), font=year_font)

    im.save(output_path, "PNG", quality=95)
    logging.info(f"Generated fixed MOE banner: {output_path}")
    return output_path

def publish_staged_moe_notice(target_blog_id: str = OFFICIAL_BLOG_ID):
    queue = load_queue()
    if not queue:
        logging.info("No staged MOE notices found in queue.")
        # Send missed alert to user if not already alerted today
        today_str = time.strftime("%Y-%m-%d")
        reminder_file = os.path.join(BASE_DIR, "moe_missed_reminder.json")
        last_reminder = {}
        if os.path.exists(reminder_file):
            try:
                with open(reminder_file, "r") as f:
                    last_reminder = json.load(f)
            except Exception:
                pass

        if last_reminder.get("date") != today_str:
            tg_text = (
                "⚠️ *MOE Notice Scan Missed Today!*\n\n"
                "The 6:30 PM publishing schedule ran, but no notice was received from your phone.\n\n"
                "🕒 *The VM server is in standby waiting for your phone until 12:00 AM (Midnight).*\n\n"
                "👉 *Whenever you are online, run this in Termux on your phone:*\n"
                "`python ~/moe_scanner.py`\n\n"
                "*(The server will immediately publish the post as soon as it receives your data!)*"
            )
            try:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={"chat_id": "1499235921", "text": tg_text, "parse_mode": "Markdown"},
                    timeout=10
                )
                with open(reminder_file, "w") as f:
                    json.dump({"date": today_str, "sent_at": time.time()}, f)
                logging.info("Sent missed scan reminder to Telegram.")
            except Exception as e:
                logging.warning(f"Could not send missed reminder: {e}")

        return {"status": "empty", "reminder_sent": True}

    en_data = queue.get("en", {})
    si_data = queue.get("si", {})

    en_title = en_data.get("title", "Special Notice")
    si_title = si_data.get("title", "විශේෂ නිවේදනය")

    post_title = f"{en_title} – Ministry of Education"

    cache = load_cache()
    # Fetch recent post titles directly from LKUni to check for duplicates
    blogger_titles = fetch_recent_blogger_titles(blog_id=target_blog_id, max_results=60)
    all_existing = list(set(cache + blogger_titles))

    is_dup, matched_title = is_moe_duplicate(post_title, all_existing)
    if not is_dup:
        is_dup, matched_title = is_moe_duplicate(en_title, all_existing)

    if is_dup:
        logging.info(f"[Duplicate Detected] '{post_title}' already exists on LKUni as '{matched_title}'. Skipping.")
        if post_title not in cache:
            cache.append(post_title)
            save_cache(cache)
        save_queue({})

        # Send Telegram alert that duplicate was skipped
        tg_dup_msg = (
            "ℹ️ *Notice Already on LKUni (Duplicate Skipped)*\n\n"
            f"📌 *Detected Notice:* {en_title}\n"
            f"📑 *Existing LKUni Post:* {matched_title}\n\n"
            "Skipped to prevent duplicate posts."
        )
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": "1499235921", "text": tg_dup_msg, "parse_mode": "Markdown"},
                timeout=10
            )
        except Exception:
            pass

        return {"status": "duplicate", "title": post_title, "matched": matched_title}

    # Generate banner
    banner_img = create_moe_banner(en_title)
    banner_url = upload_to_google_drive(banner_img, file_name="thumb-size.png", folder_name="MOE_Notices_2026")

    # Table rows for PDFs
    table_rows = []
    all_pdfs = en_data.get("pdfs", []) + si_data.get("pdfs", [])
    seen_links = set()

    for _, link in all_pdfs:
        link_clean = link.strip()
        if link_clean in seen_links:
            continue
        seen_links.add(link_clean)
        ll = link_clean.lower()

        if "english" in ll:
            label = "English Notice & Application (PDF)"
        elif "snhala" in ll or "sinhala" in ll or "-si" in ll:
            label = "Sinhala Notice & Application (PDF)"
        elif "tamil" in ll or "-ta" in ll:
            label = "Tamil Notice & Application (PDF)"
        elif "annexure" in ll:
            label = "Annexure 02 Transfer List (PDF)"
        else:
            label = "Official Document (PDF)"

        table_rows.append(f"""<tr>
\t<td>{label}</td>
\t<td><a href="{link_clean}" target="_blank">Click Here</a></td>
</tr>""")

    source_url = en_data.get("source_url") or si_data.get("source_url") or "https://moe.gov.lk/en/special-notices/"
    table_rows.append(f"""<tr>
\t<td>Official Source</td>
\t<td><a href="{source_url}" target="_blank">Ministry of Education (moe.gov.lk)</a></td>
</tr>""")

    rows_html = "\n".join(table_rows)

    paragraphs = en_data.get("paragraphs", [])
    if paragraphs:
        desc_html = "\n".join([f"<p>{p}</p>" for p in paragraphs[:3]])
    else:
        desc_html = f"<p>The Ministry of Education, Higher Education and Vocational Education has published the official notice regarding <b>{en_title}</b>. Official documents, guidelines, and applications are available for download in PDF format below.</p>"

    content_html = f"""<p>&nbsp;</p>
<div class="separator" style="clear: both; text-align: center;">
  <a href="{banner_url}" style="margin-left: 1em; margin-right: 1em;">
    <img border="0" data-original-height="1066" data-original-width="1600" src="{banner_url}" />
  </a>
</div>
<br/>

<p><b>Ministry of Education, Higher Education and Vocational Education</b></p>
<p><b>{en_title}</b></p>
<div>
{desc_html}
</div>
<br/>

<style>
#simple_table {{
\tfont-family: arial, sans-serif;
\tborder-collapse: collapse; 
\twidth: 100%;
\tbackground-color: #000000;
\tcolor:#33fcff;
}}
#simple_table td, #simple_table th {{
\ttext-align: left;
\tpadding: 8px;
\tborder: 1px solid #ffffff;
}}
#simple_table tr:nth-child(even) {{
\tbackground-color: #1d1b1b;
}}
#simple_table tr:hover {{
\tbackground-color: #9e0000;
}}
#simple_table tr > th {{
\tbackground: #00fbff;
\tcolor: #000000;
}}
</style>

<table id="simple_table">
<tbody>
<tr>
\t<th>Details</th>
\t<th>Links</th>
</tr>
{rows_html}
</tbody>
</table>
<br/><br/><br/>"""

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
        "title": post_title,
        "content": content_html,
        "labels": ["MOE", "SPECIAL_NOTICES", "UPDATES"]
    }

    res = service.posts().insert(blogId=target_blog_id, body=body, isDraft=False).execute()
    post_url = res.get("url")

    # Add to cache and clear queue
    cache.append(post_title)
    save_cache(cache)
    save_queue({})

    logging.info(f"Published MOE notice successfully: {post_url}")

    # Telegram broadcast
    tg_text = f"""🟩 Ministry of Education Special Notice 🟩

👉 Details & PDF - {post_url}

තවත් මෙවැනි තොරතුරු දැනගැනීමට ✅

👉 Join Our Telegram Channel :https://t.me/differentpaths

යාළුවන්ටත් දැනගන්න share කරන්න 👍👍👍"""

    for cid in TELEGRAM_CHAT_IDS:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": cid.strip(), "text": tg_text},
                timeout=10
            )
        except Exception:
            pass

    return {"status": "success", "url": post_url, "title": post_title}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Publish Staged MOE Notices")
    parser.add_argument("--test-blog", action="store_true", help="Publish to test blog")
    parser.add_argument("--force", action="store_true", help="Force publish even if in cache")
    args = parser.parse_args()

    from auto_blogger import TEST_BLOG_ID
    blog_id = TEST_BLOG_ID if args.test_blog else OFFICIAL_BLOG_ID
    if args.force:
        save_cache([])

    res = publish_staged_moe_notice(target_blog_id=blog_id)
    print("Publish Result:", res)
