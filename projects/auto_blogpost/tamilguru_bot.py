#!/usr/bin/env python3
"""
TamilGuru.lk Courses Monitor & Telegram Selection Bot
- Scrapes https://tamilguru.lk/category/courses/
- Extracts course title, institution, closing date, and summary points
- Verifies duplicate status against LKUni.com (extracting live LKUni post links)
- Skips expired posts / flags closing date expiry
- Sends interactive selection list to Telegram with 1-tap publish buttons
- Integrates with auto_blogger_tamil.py to publish approved courses to LKUni.com
"""

import os
import sys
import re
import json
import html
import logging
import datetime
import urllib.request
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from auto_blogger_tamil import (
    TELEGRAM_BOT_TOKEN,
    AUTHORIZED_USERS,
    OFFICIAL_BLOG_ID,
    HEADERS,
    SSL_CTX,
    load_posted_cache,
    save_posted_cache,
    fetch_recent_blogger_posts,
    find_blogger_match,
    is_date_expired,
    process_and_publish_url
)

CANDIDATES_FILE = os.path.join(BASE_DIR, "tamilguru_candidates.json")
COURSES_CATEGORY_URL = "https://tamilguru.lk/category/courses/"

def load_candidates() -> list:
    if os.path.exists(CANDIDATES_FILE):
        try:
            with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading candidates: {e}")
    return []

def save_candidates(candidates: list):
    try:
        with open(CANDIDATES_FILE, "w", encoding="utf-8") as f:
            json.dump(candidates, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Error saving candidates: {e}")

def detect_institution(title: str, text: str = "") -> str:
    combined = f"{title} {text}".lower()
    if "ocean university" in combined or "ocu" in combined:
        return "Ocean University of Sri Lanka (OCU)"
    if "open university" in combined or "ousl" in combined:
        return "The Open University of Sri Lanka (OUSL)"
    if "university of colombo" in combined or "uciars" in combined:
        return "University of Colombo"
    if "university of peradeniya" in combined or "cdce" in combined:
        return "University of Peradeniya"
    if "university of kelaniya" in combined or "pgiar" in combined:
        return "University of Kelaniya"
    if "sabaragamuwa" in combined:
        return "Sabaragamuwa University of Sri Lanka"
    if "buddhist & pali" in combined or "buddhist and pali" in combined or "bpu" in combined:
        return "Buddhist and Pali University of Sri Lanka (BPU)"
    if "national institute of education" in combined or "nie" in combined:
        return "National Institute of Education (NIE)"
    if "ministry of health" in combined:
        return "Ministry of Health, Sri Lanka"
    if "ministry of education" in combined:
        return "Ministry of Education, Sri Lanka"
    if "moratuwa" in combined or "itum" in combined:
        return "Institute of Technology, University of Moratuwa"
    return "Department of Higher Education, Sri Lanka"

def extract_summary_points(soup: BeautifulSoup) -> list:
    points = []
    entry = soup.find("div", class_="entry-content")
    if not entry:
        return points

    # 1. Look for list items
    for li in entry.find_all("li"):
        t = li.get_text(strip=True)
        if any(skip in t.lower() for skip in ["whatsapp", "telegram", "tamilguru", "facebook", "join"]):
            continue
        if 15 <= len(t) <= 140 and t not in points:
            points.append(t)
            if len(points) == 2:
                return points

    # 2. Look for table details
    table = entry.find("table")
    if table:
        for tr in table.find_all("tr"):
            cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
            if len(cells) >= 2:
                label, val = cells[0], cells[1]
                if any(k in label.lower() for k in ["programme", "degree", "course", "intake", "qualification"]):
                    if val and val not in points and len(val) <= 120:
                        points.append(f"{label}: {val}")
                        if len(points) == 2:
                            return points
    return points

def fetch_tamilguru_candidates(limit: int = 5) -> list:
    """Scrapes https://tamilguru.lk/category/courses/ and checks LKUni duplicates & expiry."""
    try:
        req = urllib.request.Request(COURSES_CATEGORY_URL, headers=HEADERS)
        html_content = urllib.request.urlopen(req, context=SSL_CTX, timeout=15).read().decode("utf-8")
        soup = BeautifulSoup(html_content, "html.parser")
    except Exception as e:
        logging.error(f"Error fetching TamilGuru courses page: {e}")
        return []

    articles = soup.find_all("article")
    course_items = []
    for a in articles:
        link_tag = a.find("a", href=True)
        title_tag = a.find(["h1", "h2", "h3"])
        time_tag = a.find("time")
        pub_date = time_tag.get_text(strip=True) if time_tag else ""
        if link_tag and title_tag:
            href = link_tag["href"]
            if href.startswith("https://tamilguru.lk/") and "/category/" not in href and "/tag/" not in href and "/page/" not in href and href != "https://tamilguru.lk/":
                t_text = title_tag.get_text(strip=True)
                if href not in [item[0] for item in course_items]:
                    course_items.append((href, t_text, pub_date))

    blogger_posts = fetch_recent_blogger_posts(blog_id=OFFICIAL_BLOG_ID, max_results=60)

    candidates = []
    for href, title, pub_date in course_items[:limit]:
        try:
            art_req = urllib.request.Request(href, headers=HEADERS)
            art_html = urllib.request.urlopen(art_req, context=SSL_CTX, timeout=12).read().decode("utf-8")
            art_soup = BeautifulSoup(art_html, "html.parser")
        except Exception as e:
            logging.warning(f"Failed to fetch article details for {href}: {e}")
            art_soup = None

        closing_date = None
        points = []
        inst = detect_institution(title)

        if art_soup:
            points = extract_summary_points(art_soup)
            table = art_soup.find("table")
            if table:
                for tr in table.find_all("tr"):
                    row_txt = tr.get_text(" ", strip=True)
                    if "closing date" in row_txt.lower():
                        m = re.search(r"(\d{4}[./-]\d{1,2}[./-]\d{1,2})", row_txt)
                        if m:
                            closing_date = m.group(1).replace("-", ".").replace("/", ".")
            if not closing_date:
                full_text = art_soup.get_text(" ", strip=True)
                m = re.search(r"closing date\s*[:\-]?\s*(\d{4}[./-]\d{1,2}[./-]\d{1,2})", full_text, re.I)
                if m:
                    closing_date = m.group(1).replace("-", ".").replace("/", ".")

        # Check duplicate strictly against live LKUni posts
        is_dup, matched_title, matched_url = find_blogger_match(title, blogger_posts)
        is_posted = bool(is_dup and matched_url)

        is_expired = is_date_expired(closing_date) if closing_date else False

        candidates.append({
            "title": title,
            "url": href,
            "institution": inst,
            "closing_date": closing_date or "Not specified",
            "published_date": pub_date or "Recent",
            "summary_points": points,
            "is_already_posted": is_posted,
            "is_expired": is_expired,
            "matched_title": matched_title,
            "matched_url": matched_url
        })

    return candidates

def send_tamilguru_selection_list(chat_id: int = 1499235921):
    """Sends latest course candidates (recent 5) from TamilGuru to Telegram with 1-tap publish buttons."""
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    candidates = fetch_tamilguru_candidates(limit=5)

    if not candidates:
        payload = {
            "chat_id": chat_id,
            "text": f"ℹ️ <b>TamilGuru Courses Update ({today_str}):</b>\nNo courses found on https://tamilguru.lk/category/courses/.",
            "parse_mode": "HTML"
        }
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json=payload, timeout=10)
        except Exception:
            pass
        return {"ok": False, "error": "No courses found"}

    save_candidates(candidates)

    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    all_published = all(c.get("is_already_posted") for c in candidates)

    sl_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    updated_str = datetime.datetime.now(sl_tz).strftime("%Y-%m-%d | %I:%M %p")

    blocks = []
    inline_buttons = []

    for i, c in enumerate(candidates):
        num_str = number_emojis[i] if i < len(number_emojis) else f"{i+1}."
        safe_title = html.escape(c['title'])
        safe_inst = html.escape(c.get('institution', 'Higher Education'))
        safe_pub = html.escape(str(c.get('published_date', 'Recent')))
        safe_date = html.escape(str(c.get('closing_date', 'Not specified')))

        item_lines = [
            f"{num_str} <b>{safe_title}</b>",
            f"🏛 <b>Institution:</b> {safe_inst}",
            f"📅 <b>Published:</b> {safe_pub}  |  ⏳ <b>Closing:</b> {safe_date}",
            f"🔗 <a href=\"{c['url']}\">View Original Course</a>"
        ]

        if c.get("is_already_posted"):
            m_url = c.get("matched_url")
            if m_url:
                item_lines.append(f"✅ <b>Status:</b> Already Published on LKUni.com • <a href=\"{m_url}\">LKUni Link</a>")
            else:
                item_lines.append("✅ <b>Status:</b> Already Published on LKUni.com")
            btn_label = f"✅ Already Posted #{i+1}"
            inline_buttons.append([{"text": btn_label, "callback_data": f"tamil_already_posted_{i+1}"}])
        elif c.get("is_expired"):
            item_lines.append("⚠️ <b>Status:</b> Expired (Closing Date Passed)")
            btn_label = f"⚠️ Expired #{i+1}"
            inline_buttons.append([{"text": btn_label, "callback_data": f"tamil_expired_{i+1}"}])
        else:
            item_lines.append("🆕 <b>Status:</b> Ready to Publish")
            short_title = c['title'][:25] + ("..." if len(c['title']) > 25 else "")
            btn_label = f"Post {i+1}: {short_title}"
            inline_buttons.append([{"text": btn_label, "callback_data": f"tamil_pub_{i+1}"}])

        blocks.append("\n".join(item_lines))

    footer = []
    if all_published:
        footer.append("ℹ️ <b>Notice:</b> All current courses listed above are already published on www.lkuni.com.\n")

    footer.append("💡 <b>How to publish:</b>")
    footer.append("• Tap any <b>Post #X</b> button below or type <code>/tamil_1</code>, <code>/tamil_2</code> to convert and publish directly to LKUni.com.")
    footer.append("• Run <code>/tamil</code> anytime to refresh this list on demand.")
    footer_text = "\n".join(footer)

    header = (
        "🎓 <b>TamilGuru Courses – Recent Selection</b>\n"
        f"🕒 <b>Updated:</b> {updated_str} (Sri Lanka Time)\n\n"
        f"Found <b>{len(candidates)}</b> recent course announcements from <code>tamilguru.lk</code>:\n"
    )

    full_text = header + "\n" + "\n\n".join(blocks) + "\n\n" + footer_text

    payload = {
        "chat_id": chat_id,
        "text": full_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": {"inline_keyboard": inline_buttons}
    }
    try:
        res = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json=payload, timeout=15)
        if res.status_code != 200 or not res.json().get("ok"):
            logging.error(f"Telegram API rejected TamilGuru list: {res.status_code} {res.text}")
            # Fallback sending plain text without HTML to ensure user ALWAYS receives the list
            payload.pop("parse_mode", None)
            clean_text = re.sub(r"<[^>]+>", "", full_text)
            payload["text"] = clean_text
            res2 = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json=payload, timeout=15)
            logging.info(f"Fallback plain text sent: {res2.status_code}")
            return res2.json()
        logging.info("Sent TamilGuru selection list to Telegram successfully.")
        return res.json()
    except Exception as e:
        logging.error(f"Error sending TamilGuru selection list: {e}")
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": f"⚠️ Error loading TamilGuru courses: {e}"}, timeout=10)
        except Exception:
            pass
        return {"ok": False, "error": str(e)}

def publish_tamilguru_candidate(candidate_num: int, target_blog_id: str = OFFICIAL_BLOG_ID) -> dict:
    """Publishes a chosen candidate post from tamilguru daily selection to LKUni."""
    candidates = load_candidates()
    idx = candidate_num - 1
    if idx < 0 or idx >= len(candidates):
        return {"status": "error", "message": f"Candidate #{candidate_num} not found. Please refresh using /tamil."}

    c = candidates[idx]
    if c.get("is_already_posted"):
        return {"status": "duplicate", "message": f"'{c['title']}' is already published on LKUni.com."}

    if c.get("is_expired"):
        return {"status": "expired", "message": f"'{c['title']}' has expired (Closing date: {c.get('closing_date')})."}

    res = process_and_publish_url(c["url"], target_blog_id=target_blog_id)
    if res.get("status") == "success":
        c["is_already_posted"] = True
        c["matched_url"] = res.get("url")
        c["matched_title"] = res.get("title")
        candidates[idx] = c
        save_candidates(candidates)

    return res

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing send_tamilguru_selection_list...")
    result = send_tamilguru_selection_list(chat_id=1499235921)
    print("Result:", result)
