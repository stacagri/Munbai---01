#!/usr/bin/env python3
"""
Real-time Alert Monitor for TamilGuru Courses & Guruwaraya
- Continuously scans TamilGuru Courses and Guruwaraya feed
- Sends instant Telegram alerts with post details when new items appear
- Provides [ ✅ Approve & Publish ] and [ ❌ Dismiss ] inline buttons
- Strictly respects user approval before publishing to LKUni.com
"""

import os
import sys
import re
import json
import time
import html
import hashlib
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
    fetch_recent_blogger_posts,
    find_blogger_match,
    is_date_expired
)
from tamilguru_bot import detect_institution as detect_tg_inst, extract_summary_points
from guruwaraya_bot import (
    is_education_or_teacher_post,
    detect_institution as detect_gw_inst,
    check_expiry,
    get_point_summary,
    FEED_URL as GW_FEED_URL
)

TG_COURSES_URL = "https://tamilguru.lk/category/courses/"
SEEN_ALERTS_FILE = os.path.join(BASE_DIR, "seen_alerts.json")
PENDING_ALERTS_FILE = os.path.join(BASE_DIR, "pending_alerts.json")
API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

SL_TZ = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
MONITOR_STATS = {
    "start_time": datetime.datetime.now(SL_TZ),
    "last_scan_time": None,
    "total_scans": 0,
    "interval_seconds": 1800
}

# ==============================================================================
# PERSISTENCE HELPERS
# ==============================================================================
def load_seen_alerts() -> dict:
    if os.path.exists(SEEN_ALERTS_FILE):
        try:
            with open(SEEN_ALERTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading seen alerts: {e}")
    return {}

def save_seen_alerts(seen: dict):
    try:
        with open(SEEN_ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(seen, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Error saving seen alerts: {e}")

def load_pending_alerts() -> dict:
    if os.path.exists(PENDING_ALERTS_FILE):
        try:
            with open(PENDING_ALERTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading pending alerts: {e}")
    return {}

def save_pending_alerts(alerts: dict):
    try:
        with open(PENDING_ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(alerts, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Error saving pending alerts: {e}")

def make_alert_id(prefix: str, url: str) -> str:
    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{h}"

# ==============================================================================
# INITIALIZATION (PREVENTS SPAM OF OLD POSTS ON FIRST RUN)
# ==============================================================================
def init_seen_alerts_if_needed():
    """Initializes seen_alerts.json with current active URLs if file doesn't exist."""
    if os.path.exists(SEEN_ALERTS_FILE):
        return

    logging.info("[Alert Monitor] First run detected. Seeding seen_alerts.json with existing URLs...")
    seen = {}
    now_str = datetime.datetime.now().isoformat()

    # 1. Seed TamilGuru
    try:
        req = urllib.request.Request(TG_COURSES_URL, headers=HEADERS)
        html_content = urllib.request.urlopen(req, context=SSL_CTX, timeout=15).read().decode("utf-8")
        soup = BeautifulSoup(html_content, "html.parser")
        for a in soup.find_all("article"):
            link_tag = a.find("a", href=True)
            if link_tag:
                href = link_tag["href"]
                if href.startswith("https://tamilguru.lk/") and "/category/" not in href and "/tag/" not in href:
                    seen[href] = {"source": "tamilguru", "seeded": True, "date": now_str}
    except Exception as e:
        logging.warning(f"Error seeding TamilGuru: {e}")

    # 2. Seed Guruwaraya
    try:
        res = requests.get(GW_FEED_URL, headers=HEADERS, timeout=15).json()
        for e in res.get("feed", {}).get("entry", []):
            links = [l.get("href") for l in e.get("link", []) if l.get("rel") == "alternate"]
            if links:
                seen[links[0]] = {"source": "guruwaraya", "seeded": True, "date": now_str}
    except Exception as e:
        logging.warning(f"Error seeding Guruwaraya: {e}")

    save_seen_alerts(seen)
    logging.info(f"[Alert Monitor] Seeded {len(seen)} existing URLs into seen_alerts.json")

# ==============================================================================
# SEND ALERT MESSAGE WITH INLINE APPROVAL
# ==============================================================================
def send_telegram_alert(post_info: dict, chat_id: int = 1499235921) -> bool:
    """Sends an approval request alert to Telegram with Approve & Dismiss buttons."""
    alert_id = post_info["id"]
    source_label = "TamilGuru Courses" if post_info["source"] == "tamilguru" else "Guruwaraya"
    source_badge = "🎓" if post_info["source"] == "tamilguru" else "📚"

    sl_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    time_str = datetime.datetime.now(sl_tz).strftime("%I:%M %p")

    title_escaped = html.escape(post_info["title"])
    inst_escaped = html.escape(post_info.get("institution", "Higher Education"))
    closing_str = html.escape(post_info.get("closing_date", "Not specified"))
    pub_str = html.escape(post_info.get("published_date", "Recent"))
    url = post_info["url"]

    lines = [
        f"🚨 <b>NEW POST ALERT — {source_badge} {source_label}</b>",
        f"🕒 <b>Detected:</b> {time_str} (SL Time)\n",
        f"📌 <b>Title:</b> {title_escaped}",
        f"🏛 <b>Institution:</b> {inst_escaped}",
        f"📅 <b>Published:</b> {pub_str} | ⏳ <b>Closing:</b> {closing_str}",
    ]

    points = post_info.get("summary_points", [])
    if points:
        lines.append("📝 <b>Details:</b>")
        for pt in points[:2]:
            lines.append(f" • {html.escape(pt)}")

    lines.append(f"🔗 <a href='{url}'>View Original Source Post</a>\n")
    lines.append("⚡ <b>Action Required:</b> Tap <b>Approve & Publish</b> below to format with banner and publish to LKUni.com:")

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "🚀 Approve & Publish to LKUni", "callback_data": f"appr_alert_{alert_id}"}
            ],
            [
                {"text": "❌ Dismiss", "callback_data": f"dism_alert_{alert_id}"}
            ]
        ]
    }

    payload = {
        "chat_id": chat_id,
        "text": "\n".join(lines),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": reply_markup
    }

    try:
        r = requests.post(f"{API_BASE}/sendMessage", json=payload, timeout=15)
        res_data = r.json()
        if res_data.get("ok"):
            msg_id = res_data.get("result", {}).get("message_id")
            post_info["telegram_message_id"] = msg_id
            post_info["telegram_chat_id"] = chat_id
            # Save pending alert
            pending = load_pending_alerts()
            pending[alert_id] = post_info
            save_pending_alerts(pending)
            logging.info(f"[Alert Monitor] Sent alert for: {post_info['title']} (ID: {alert_id}, msg_id: {msg_id})")
            return True
        else:
            logging.error(f"[Alert Monitor] Telegram API error: {res_data}")
    except Exception as e:
        logging.error(f"[Alert Monitor] Exception sending Telegram alert: {e}")
    return False

# ==============================================================================
# SCAN FOR NEW POSTS
# ==============================================================================
def check_new_posts(chat_id: int = 1499235921) -> int:
    """Scans TamilGuru courses and Guruwaraya feed. Sends alerts for newly detected posts."""
    init_seen_alerts_if_needed()
    seen = load_seen_alerts()
    blogger_posts = fetch_recent_blogger_posts(blog_id=OFFICIAL_BLOG_ID, max_results=60)
    alerts_sent = 0
    now_str = datetime.datetime.now().isoformat()
    MONITOR_STATS["last_scan_time"] = datetime.datetime.now(SL_TZ)
    MONITOR_STATS["total_scans"] += 1

    # --------------------------------------------------------------------------
    # 1. Scan TamilGuru Courses (https://tamilguru.lk/category/courses/)
    # --------------------------------------------------------------------------
    try:
        req = urllib.request.Request(TG_COURSES_URL, headers=HEADERS)
        html_content = urllib.request.urlopen(req, context=SSL_CTX, timeout=15).read().decode("utf-8")
        soup = BeautifulSoup(html_content, "html.parser")
        articles = soup.find_all("article")

        for a in articles:
            link_tag = a.find("a", href=True)
            title_tag = a.find(["h1", "h2", "h3"])
            time_tag = a.find("time")
            pub_date = time_tag.get_text(strip=True) if time_tag else "Recent"

            if not link_tag or not title_tag:
                continue

            href = link_tag["href"]
            if not href.startswith("https://tamilguru.lk/") or "/category/" in href or "/tag/" in href:
                continue

            if href in seen:
                continue

            title = title_tag.get_text(strip=True)

            # Check if duplicate on LKUni live site
            is_dup, matched_title, _ = find_blogger_match(title, blogger_posts)
            if is_dup:
                logging.info(f"[Alert Monitor] Skipping already published TamilGuru post: {title}")
                seen[href] = {"source": "tamilguru", "already_published": True, "date": now_str}
                continue

            # Fetch details for closing date and points
            closing_date = None
            points = []
            inst = detect_tg_inst(title)

            try:
                art_req = urllib.request.Request(href, headers=HEADERS)
                art_html = urllib.request.urlopen(art_req, context=SSL_CTX, timeout=12).read().decode("utf-8")
                art_soup = BeautifulSoup(art_html, "html.parser")
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
                    m = re.search(r"closing date\s*[:\-]?\s*(\d{4}[./-]\d{1,2}[./-]\d{1,2})", art_soup.get_text(" ", strip=True), re.I)
                    if m:
                        closing_date = m.group(1).replace("-", ".").replace("/", ".")
            except Exception as e:
                logging.warning(f"Error reading TamilGuru article details for {href}: {e}")

            if closing_date and is_date_expired(closing_date):
                logging.info(f"[Alert Monitor] Skipping expired TamilGuru post: {title} ({closing_date})")
                seen[href] = {"source": "tamilguru", "expired": True, "date": now_str}
                continue

            alert_id = make_alert_id("tg", href)
            post_info = {
                "id": alert_id,
                "source": "tamilguru",
                "title": title,
                "url": href,
                "institution": inst,
                "closing_date": closing_date or "Not specified",
                "published_date": pub_date,
                "summary_points": points,
                "created_at": now_str
            }

            if send_telegram_alert(post_info, chat_id=chat_id):
                seen[href] = {"source": "tamilguru", "alerted": True, "alert_id": alert_id, "date": now_str}
                alerts_sent += 1

    except Exception as e:
        logging.error(f"[Alert Monitor] Error scanning TamilGuru: {e}")

    # --------------------------------------------------------------------------
    # 2. Scan Guruwaraya (https://www.guruwaraya.lk/feeds/posts/default?alt=json)
    # --------------------------------------------------------------------------
    try:
        res = requests.get(GW_FEED_URL, headers=HEADERS, timeout=15).json()
        entries = res.get("feed", {}).get("entry", [])

        for e in entries:
            title = e.get("title", {}).get("$t", "").strip()
            cats = [c.get("term") for c in e.get("category", [])]
            links = [l.get("href") for l in e.get("link", []) if l.get("rel") == "alternate"]
            post_url = links[0] if links else ""
            pub_date = e.get("published", {}).get("$t", "")[:10]

            if not title or not post_url:
                continue

            if post_url in seen:
                continue

            # Check if education/teacher post
            if not is_education_or_teacher_post(title, cats):
                logging.info(f"[Alert Monitor] [Filtered Out] Guruwaraya post excluded (non-education): '{title}'")
                seen[post_url] = {"source": "guruwaraya", "filtered_out": True, "date": now_str}
                continue

            # Check if duplicate on LKUni live site
            is_dup, matched_title, _ = find_blogger_match(title, blogger_posts)
            if is_dup:
                logging.info(f"[Alert Monitor] Skipping already published Guruwaraya post: {title}")
                seen[post_url] = {"source": "guruwaraya", "already_published": True, "date": now_str}
                continue

            # Check closing date and expiry
            content_html = e.get("content", {}).get("$t", "") or e.get("summary", {}).get("$t", "")
            soup = BeautifulSoup(content_html, "html.parser")
            full_text = f"{title} {soup.get_text(' ', strip=True)}"
            is_exp, closing_date = check_expiry(full_text)
            if is_exp:
                logging.info(f"[Alert Monitor] Skipping expired Guruwaraya post: {title} ({closing_date})")
                seen[post_url] = {"source": "guruwaraya", "expired": True, "date": now_str}
                continue

            points = get_point_summary(soup)
            inst = detect_gw_inst(title, cats)
            alert_id = make_alert_id("gw", post_url)

            post_info = {
                "id": alert_id,
                "source": "guruwaraya",
                "title": title,
                "url": post_url,
                "institution": inst,
                "closing_date": closing_date or "Not specified",
                "published_date": pub_date,
                "summary_points": points,
                "created_at": now_str
            }

            if send_telegram_alert(post_info, chat_id=chat_id):
                seen[post_url] = {"source": "guruwaraya", "alerted": True, "alert_id": alert_id, "date": now_str}
                alerts_sent += 1

    except Exception as e:
        logging.error(f"[Alert Monitor] Error scanning Guruwaraya: {e}")

    save_seen_alerts(seen)
    return alerts_sent

# ==============================================================================
# BACKGROUND MONITOR LOOP
# ==============================================================================
def run_monitor_loop(interval_seconds: int = 1800):
    """Continuous background loop scanning for new posts every `interval_seconds` (default: 1800s / 30 mins)."""
    logging.info(f"[Alert Monitor] Started background post monitor (Interval: {interval_seconds}s / {interval_seconds // 60} mins)")
    while True:
        try:
            check_new_posts()
        except Exception as e:
            logging.error(f"[Alert Monitor] Error in monitor loop iteration: {e}")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print("Testing alert monitor scan...")
    count = check_new_posts()
    print(f"Scan complete. Alerts sent: {count}")
