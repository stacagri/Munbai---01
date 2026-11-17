#!/usr/bin/env python3
"""
LKUni Daily Post Summary Monitor (/daily)
- Scans both TamilGuru Courses (https://tamilguru.lk/category/courses/)
  and Guruwaraya (https://www.guruwaraya.lk/) for posts published TODAY.
- If no posts were published today, sends a clean notification:
  "No updates published today on either site."
- If posts were published today, presents all details with live LKUni links
  and 1-tap Publish buttons for unposted items.
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
    OFFICIAL_BLOG_ID,
    HEADERS,
    SSL_CTX,
    fetch_recent_blogger_posts,
    find_blogger_match,
    is_date_expired
)
from tamilguru_bot import (
    detect_institution as detect_tg_inst,
    extract_summary_points,
    COURSES_CATEGORY_URL as TG_COURSES_URL
)
from guruwaraya_bot import (
    is_education_or_teacher_post,
    detect_institution as detect_gw_inst,
    check_expiry,
    get_point_summary,
    FEED_URL as GW_FEED_URL
)
from alert_monitor import (
    make_alert_id,
    load_pending_alerts,
    save_pending_alerts
)

API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
SL_TZ = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

def fetch_today_posts() -> tuple:
    """
    Fetches all posts published TODAY from both TamilGuru Courses and Guruwaraya.
    Returns: (today_tg_posts, today_gw_posts, today_str, today_human, current_time_str)
    """
    now = datetime.datetime.now(SL_TZ)
    today_str = now.strftime("%Y-%m-%d")
    today_human = now.strftime("%B %d, %Y")
    current_time_str = now.strftime("%I:%M %p")

    blogger_posts = fetch_recent_blogger_posts(blog_id=OFFICIAL_BLOG_ID, max_results=60)
    today_tg = []
    today_gw = []

    # 1. TamilGuru Courses
    try:
        req = urllib.request.Request(TG_COURSES_URL, headers=HEADERS)
        html_content = urllib.request.urlopen(req, context=SSL_CTX, timeout=15).read().decode("utf-8")
        soup = BeautifulSoup(html_content, "html.parser")

        for a in soup.find_all("article"):
            time_tag = a.find("time")
            link_tag = a.find("a", href=True)
            title_tag = a.find(["h1", "h2", "h3"])

            if not link_tag or not title_tag:
                continue

            href = link_tag["href"]
            if not href.startswith("https://tamilguru.lk/") or "/category/" in href or "/tag/" in href or "/page/" in href:
                continue

            # Check published date
            pub_date_iso = ""
            pub_date_text = ""
            if time_tag:
                pub_date_iso = (time_tag.get("datetime") or "")[:10]
                pub_date_text = time_tag.get_text(strip=True)

            if pub_date_iso != today_str and pub_date_text != today_human:
                # Not published today
                continue

            title = title_tag.get_text(strip=True)
            inst = detect_tg_inst(title)

            # Fetch details
            closing_date = None
            points = []
            try:
                art_req = urllib.request.Request(href, headers=HEADERS)
                art_html = urllib.request.urlopen(art_req, context=SSL_CTX, timeout=10).read().decode("utf-8")
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
            except Exception:
                pass

            is_dup, matched_title, matched_url = find_blogger_match(title, blogger_posts)
            is_posted = bool(is_dup and matched_url)
            is_expired = is_date_expired(closing_date) if closing_date else False

            alert_id = make_alert_id("tg", href)
            today_tg.append({
                "id": alert_id,
                "source": "tamilguru",
                "title": title,
                "url": href,
                "institution": inst,
                "published_date": pub_date_text or today_human,
                "closing_date": closing_date or "Not specified",
                "summary_points": points,
                "is_already_posted": is_posted,
                "is_expired": is_expired,
                "matched_title": matched_title,
                "matched_url": matched_url
            })
    except Exception as e:
        logging.error(f"[Daily Summary] Error fetching TamilGuru courses: {e}")

    # 2. Guruwaraya
    try:
        res = requests.get(GW_FEED_URL, headers=HEADERS, timeout=15).json()
        entries = res.get("feed", {}).get("entry", [])

        for e in entries:
            pub_date = (e.get("published", {}).get("$t") or "")[:10]
            if pub_date != today_str:
                continue

            title = e.get("title", {}).get("$t", "").strip()
            cats = [c.get("term") for c in e.get("category", [])]
            links = [l.get("href") for l in e.get("link", []) if l.get("rel") == "alternate"]
            post_url = links[0] if links else ""

            if not title or not post_url:
                continue

            if not is_education_or_teacher_post(title, cats):
                continue

            content_html = e.get("content", {}).get("$t", "") or e.get("summary", {}).get("$t", "")
            soup = BeautifulSoup(content_html, "html.parser")
            full_text = f"{title} {soup.get_text(' ', strip=True)}"
            is_expired, closing_date = check_expiry(full_text)
            points = get_point_summary(soup)
            inst = detect_gw_inst(title, cats)

            is_dup, matched_title, matched_url = find_blogger_match(title, blogger_posts)
            is_posted = bool(is_dup and matched_url)

            alert_id = make_alert_id("gw", post_url)
            today_gw.append({
                "id": alert_id,
                "source": "guruwaraya",
                "title": title,
                "url": post_url,
                "institution": inst,
                "published_date": pub_date,
                "closing_date": closing_date or "Not specified",
                "summary_points": points,
                "is_already_posted": is_posted,
                "is_expired": is_expired,
                "matched_title": matched_title,
                "matched_url": matched_url
            })
    except Exception as e:
        logging.error(f"[Daily Summary] Error fetching Guruwaraya posts: {e}")

    return today_tg, today_gw, today_str, today_human, current_time_str

def send_daily_summary(chat_id: int):
    """Generates and sends the daily summary message to Telegram."""
    today_tg, today_gw, today_str, today_human, current_time_str = fetch_today_posts()
    total_posts = len(today_tg) + len(today_gw)

    # CASE 1: No updates published today on either site
    if total_posts == 0:
        lines = [
            f"ℹ️ <b>Daily Post Summary — {today_human}</b>",
            f"🕒 <b>Checked:</b> {current_time_str} (Sri Lanka Time)\n",
            "No updates published today on either <b>TamilGuru Courses</b> or <b>Guruwaraya</b>.\n",
            "💡 <i>Tip: The real-time background monitor is active (checking every 30 mins). As soon as any new course or teacher notice is published today, an instant alert with an Approve button will arrive here automatically!</i>"
        ]
        payload = {
            "chat_id": chat_id,
            "text": "\n".join(lines),
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        try:
            requests.post(f"{API_BASE}/sendMessage", json=payload, timeout=15)
        except Exception as e:
            logging.error(f"Error sending empty daily summary: {e}")
        return

    # CASE 2: Posts WERE published today
    lines = [
        f"📅 <b>Daily Post Summary — {today_human}</b>",
        f"🕒 <b>Checked:</b> {current_time_str} (Sri Lanka Time)",
        f"Found <b>{total_posts}</b> post(s) published today:\n"
    ]

    inline_keyboard = []
    pending = load_pending_alerts()
    all_today = []

    for p in today_tg:
        all_today.append(("🎓 TamilGuru Courses", p))
    for p in today_gw:
        all_today.append(("📚 Guruwaraya", p))

    for idx, (source_tag, p) in enumerate(all_today):
        num = idx + 1
        t_esc = html.escape(p["title"])
        inst_esc = html.escape(p.get("institution", "Higher Education"))
        pub_esc = html.escape(p.get("published_date", "Today"))
        close_esc = html.escape(p.get("closing_date", "Not specified"))
        orig_url = p["url"]

        lines.append(f"<b>{num}. [{source_tag}]</b>")
        lines.append(f"📌 <b>Title:</b> {t_esc}")
        lines.append(f"🏛 <b>Institution:</b> {inst_esc}")
        lines.append(f"📅 <b>Published:</b> {pub_esc} | ⏳ <b>Closing:</b> {close_esc}")

        points = p.get("summary_points", [])
        if points:
            lines.append("📝 <b>Details:</b>")
            for pt in points[:2]:
                lines.append(f" • {html.escape(pt)}")

        lines.append(f"🔗 <a href='{orig_url}'>View Original Post</a>")

        if p.get("is_already_posted"):
            match_url = p.get("matched_url", "https://www.lkuni.com/")
            lines.append("✅ <b>Status: Already Published on LKUni.com</b>")
            lines.append(f"🌐 <b>LKUni Link:</b> <a href='{match_url}'>{match_url}</a>\n")
        elif p.get("is_expired"):
            lines.append(f"⚠️ <b>Status: Notice Expired (Closed: {close_esc})</b>\n")
        else:
            lines.append("⏳ <b>Status: Not Yet Published to LKUni</b>\n")
            alert_id = p["id"]
            # Register in pending alerts so approval callback works
            pending[alert_id] = {
                "id": alert_id,
                "source": p["source"],
                "title": p["title"],
                "url": p["url"],
                "institution": p["institution"],
                "closing_date": p["closing_date"],
                "summary_points": points,
                "created_at": datetime.datetime.now().isoformat()
            }
            btn_title = p["title"][:22] + "..." if len(p["title"]) > 22 else p["title"]
            inline_keyboard.append([
                {"text": f"🚀 Approve & Publish #{num}: {btn_title}", "callback_data": f"appr_alert_{alert_id}"}
            ])

    save_pending_alerts(pending)

    payload = {
        "chat_id": chat_id,
        "text": "\n".join(lines),
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if inline_keyboard:
        payload["reply_markup"] = {"inline_keyboard": inline_keyboard}

    try:
        requests.post(f"{API_BASE}/sendMessage", json=payload, timeout=15)
    except Exception as e:
        logging.error(f"Error sending daily summary: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing fetch_today_posts()...")
    tg, gw, t_str, t_hum, t_tim = fetch_today_posts()
    print(f"Results for {t_str}: TamilGuru={len(tg)}, Guruwaraya={len(gw)}")
