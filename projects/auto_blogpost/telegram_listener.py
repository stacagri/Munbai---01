#!/usr/bin/env python3
"""
LKUni Interactive Telegram Bot Listener
- Handles /check command & '🔍 /check' button to scan for new courses on demand
- Handles custom external URLs from any blog or website to convert and publish to LKUni
- Broadcasts updates to @differentpaths and notifies the user
"""

import os
import sys
import time
import json
import re
import html
import datetime
import threading
import logging
import requests
from urllib.parse import urlparse
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Import functions from auto_blogger
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from auto_blogger import (
    TELEGRAM_BOT_TOKEN,
    AUTHORIZED_USERS,
    OFFICIAL_BLOG_ID,
    load_posted_cache,
    check_and_publish_latest,
    process_and_publish_url,
    trash_lkuni_post
)

API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [TG-BOT] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

REPLY_KEYBOARD = {
    "keyboard": [
        [{"text": "🎓 /tamil"}, {"text": "📚 /guru"}],
        [{"text": "📅 /daily"}, {"text": "📋 /recent"}]
    ],
    "resize_keyboard": True,
    "is_persistent": True
}

processing_lock = threading.Lock()

from guruwaraya_bot import send_daily_selection_list, load_candidates, publish_guruwaraya_post
from tamilguru_bot import send_tamilguru_selection_list, load_candidates as load_tamil_candidates, publish_tamilguru_candidate
from daily_summary import send_daily_summary
from alert_monitor import (
    check_new_posts,
    run_monitor_loop,
    load_pending_alerts,
    save_pending_alerts,
    load_seen_alerts,
    save_seen_alerts,
    send_telegram_alert,
    MONITOR_STATS,
    SL_TZ
)

def send_message(chat_id: int, text: str, reply_markup=None, parse_mode: str = "Markdown") -> dict:
    url = f"{API_BASE}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": False
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        res = requests.post(url, json=payload, timeout=20)
        return res.json()
    except Exception as e:
        logging.error(f"Error sending message to {chat_id}: {e}")
        return {}

def edit_message_text(chat_id: int, message_id: int, text: str, reply_markup=None, parse_mode: str = "HTML") -> dict:
    url = f"{API_BASE}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "disable_web_page_preview": True
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    else:
        payload["reply_markup"] = {"inline_keyboard": []}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        res = requests.post(url, json=payload, timeout=15)
        return res.json()
    except Exception as e:
        logging.error(f"Error editing message {message_id} in {chat_id}: {e}")
        return {}

def extract_url(text: str) -> str:
    m = re.search(r'(https?://[^\s]+)', text)
    return m.group(1) if m else None

def handle_custom_url(chat_id: int, url: str):
    """Processes any arbitrary URL from any educational blog or website."""
    if processing_lock.locked():
        send_message(chat_id, "⏳ Another task is currently processing. Please wait a moment...", reply_markup=REPLY_KEYBOARD)
        return

    def run_worker():
        with processing_lock:
            domain = urlparse(url).netloc
            if "guruwaraya.lk" in domain:
                send_message(
                    chat_id,
                    f"⏳ *Processing Guruwaraya Link:* `{url}`\n\n"
                    f"• Scraping post & official attachments\n"
                    f"• Generating 1600x1066 head banner\n"
                    f"• Extracting official PDFs and source links\n"
                    f"• Publishing clean post to LKUni.com...",
                    reply_markup=REPLY_KEYBOARD
                )
                try:
                    res = publish_guruwaraya_post(post_url=url)
                    status = res.get("status")
                    if status == "success":
                        msg = (
                            f"🎉 *Post Published Successfully to LKUni.com!*\n\n"
                            f"📌 *Title:* {res.get('title')}\n"
                            f"🌐 *Blog:* www.lkuni.com\n"
                            f"🔗 *Live URL:* {res.get('url')}\n\n"
                            f"📢 *Broadcast:* Sent to @differentpaths"
                        )
                        send_message(chat_id, msg, reply_markup=REPLY_KEYBOARD)
                    elif status == "duplicate":
                        msg = (
                            f"⚠️ *Notice: Duplicate Detected!*\n\n"
                            f"This post already exists on www.lkuni.com:\n"
                            f"👉 *{res.get('matched_title')}*\n\n"
                            f"To prevent duplicate posts, it was not republished."
                        )
                        send_message(chat_id, msg, reply_markup=REPLY_KEYBOARD)
                    else:
                        msg = f"❌ *Failed to publish Guruwaraya post:*\n{res.get('message', 'Unknown error')}"
                        send_message(chat_id, msg, reply_markup=REPLY_KEYBOARD)
                except Exception as e:
                    logging.exception(f"Exception processing Guruwaraya URL {url}: {e}")
                    send_message(chat_id, f"❌ *Exception during processing:*\n`{str(e)}`", reply_markup=REPLY_KEYBOARD)
                return

            send_message(
                chat_id,
                f"⏳ *Processing Link:* `{url}`\n\n"
                f"• Scraping `{domain}`\n"
                f"• Generating 1600x1066 head banner\n"
                f"• Scanning flyer with Gemini Vision OCR\n"
                f"• Preparing clean LKUni post & Drive upload...",
                reply_markup=REPLY_KEYBOARD
            )
            try:
                res = process_and_publish_url(url)
                status = res.get("status")
                if status == "success":
                    msg = (
                        f"🎉 *Post Published Successfully!*\n\n"
                        f"📌 *Title:* {res.get('title')}\n"
                        f"🌐 *Blog:* www.lkuni.com\n"
                        f"🔗 *URL:* {res.get('url')}\n\n"
                        f"📢 *Broadcast:* Sent to @differentpaths"
                    )
                    send_message(chat_id, msg, reply_markup=REPLY_KEYBOARD)
                elif status == "duplicate":
                    msg = (
                        f"⚠️ *Notice: Duplicate Detected!*\n\n"
                        f"This course already exists on www.lkuni.com:\n"
                        f"👉 *{res.get('matched_title')}*\n\n"
                        f"To prevent duplicate posts, it was not republished."
                    )
                    send_message(chat_id, msg, reply_markup=REPLY_KEYBOARD)
                else:
                    msg = f"❌ *Failed to process URL:*\n{res.get('message', 'Unknown error')}"
                    send_message(chat_id, msg, reply_markup=REPLY_KEYBOARD)
            except Exception as e:
                logging.exception(f"Exception processing URL {url}: {e}")
                send_message(chat_id, f"❌ *Exception during processing:*\n`{str(e)}`", reply_markup=REPLY_KEYBOARD)

    t = threading.Thread(target=run_worker)
    t.daemon = True
    t.start()

def handle_guru_publish(chat_id: int, candidate_num: int):
    """Publishes a chosen candidate post from guruwaraya daily selection."""
    if processing_lock.locked():
        send_message(chat_id, "⏳ A publishing task is currently in progress. Please wait a moment...", reply_markup=REPLY_KEYBOARD)
        return

    candidates = load_candidates()
    idx = candidate_num - 1
    if idx < 0 or idx >= len(candidates):
        send_message(chat_id, f"⚠️ Post #{candidate_num} not found. Please click 📚 /guru to refresh the candidate list.", reply_markup=REPLY_KEYBOARD)
        return

    c = candidates[idx]
    if c.get("is_already_posted") and c.get("matched_url"):
        send_message(chat_id, f"ℹ️ *Already Published:*\n'{c['title']}' is already published on LKUni.com to prevent duplicate posts.", reply_markup=REPLY_KEYBOARD)
        return

    def run_worker():
        with processing_lock:
            send_message(
                chat_id,
                f"⏳ *Publishing Post #{candidate_num} to LKUni.com...*\n\n"
                f"📌 *Title:* {c['title']}\n"
                f"🏢 *Institution:* {c['institution']}\n\n"
                f"• Generating 1600x1066 head banner\n"
                f"• Uploading to Google Drive CDN\n"
                f"• Formatting #simple_table with PDF download links...",
                reply_markup=REPLY_KEYBOARD
            )
            try:
                res = publish_guruwaraya_post(c["url"], title=c["title"], institution=c["institution"])
                if res.get("status") == "success":
                    msg = (
                        f"🎉 *Post Successfully Published to LKUni.com!*\n\n"
                        f"📌 *Title:* {res.get('title')}\n"
                        f"🔗 *Live URL:* {res.get('url')}\n\n"
                        f"📢 *Broadcast:* Successfully broadcast to @differentpaths"
                    )
                    send_message(chat_id, msg, reply_markup=REPLY_KEYBOARD)
                else:
                    send_message(chat_id, f"❌ Failed to publish: {res.get('message', 'Unknown error')}", reply_markup=REPLY_KEYBOARD)
            except Exception as e:
                logging.exception(f"Error publishing candidate #{candidate_num}: {e}")
                send_message(chat_id, f"❌ *Error publishing post:*\n`{str(e)}`", reply_markup=REPLY_KEYBOARD)

    t = threading.Thread(target=run_worker)
    t.daemon = True
    t.start()

def handle_tamil_publish(chat_id: int, candidate_num: int):
    """Publishes a chosen candidate post from tamilguru daily selection."""
    if processing_lock.locked():
        send_message(chat_id, "⏳ A publishing task is currently in progress. Please wait a moment...", reply_markup=REPLY_KEYBOARD)
        return

    candidates = load_tamil_candidates()
    idx = candidate_num - 1
    if idx < 0 or idx >= len(candidates):
        send_message(chat_id, f"⚠️ Post #{candidate_num} not found. Please click 🎓 /tamil to refresh the candidate list.", reply_markup=REPLY_KEYBOARD)
        return

    c = candidates[idx]
    if c.get("is_already_posted") and c.get("matched_url"):
        send_message(chat_id, f"ℹ️ *Already Published:*\n'{c['title']}' is already published on LKUni.com to prevent duplicate posts.", reply_markup=REPLY_KEYBOARD)
        return

    if c.get("is_expired"):
        send_message(chat_id, f"⚠️ *Expired Notice:*\n'{c['title']}' has expired (Closing date: {c.get('closing_date')}).", reply_markup=REPLY_KEYBOARD)
        return

    def run_worker():
        with processing_lock:
            send_message(
                chat_id,
                f"⏳ *Publishing Post #{candidate_num} from TamilGuru to LKUni.com...*\n\n"
                f"📌 *Title:* {c['title']}\n"
                f"🏢 *Institution:* {c.get('institution', 'Higher Education')}\n\n"
                f"• Generating 1600x1066 head banner\n"
                f"• Uploading to Google Drive CDN\n"
                f"• Formatting #simple_table with PDF download links...",
                reply_markup=REPLY_KEYBOARD
            )
            try:
                res = publish_tamilguru_candidate(candidate_num)
                if res.get("status") == "success":
                    msg = (
                        f"🎉 *Post Successfully Published to LKUni.com!*\n\n"
                        f"📌 *Title:* {res.get('title')}\n"
                        f"🔗 *Live URL:* {res.get('url')}\n\n"
                        f"📢 *Broadcast:* Successfully broadcast to @differentpaths"
                    )
                    send_message(chat_id, msg, reply_markup=REPLY_KEYBOARD)
                else:
                    send_message(chat_id, f"❌ Failed to publish: {res.get('message', 'Unknown error')}", reply_markup=REPLY_KEYBOARD)
            except Exception as e:
                logging.exception(f"Error publishing TamilGuru candidate #{candidate_num}: {e}")
                send_message(chat_id, f"❌ *Error publishing post:*\n`{str(e)}`", reply_markup=REPLY_KEYBOARD)

    t = threading.Thread(target=run_worker)
    t.daemon = True
    t.start()

def handle_alert_approval(chat_id: int, message_id: int, alert_id: str):
    """Handles 1-tap approval of a newly alerted post from TamilGuru or Guruwaraya."""
    pending = load_pending_alerts()
    if alert_id not in pending:
        send_message(chat_id, "⚠️ This alert has already been processed or expired.", reply_markup=REPLY_KEYBOARD)
        return

    alert = pending[alert_id]
    title = alert.get("title", "")
    source = alert.get("source", "")
    url = alert.get("url", "")
    institution = alert.get("institution", "")

    # Edit message immediately to show progress and remove action buttons
    edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=(
            f"🔔 <b>New Post Alert:</b> {html.escape(title)}\n\n"
            f"⏳ <b>Approved by user!</b> Publishing to LKUni.com...\n"
            f"• Generating 1600x1066 head banner\n"
            f"• Uploading to Google Drive CDN\n"
            f"• Formatting clean post with PDF links..."
        ),
        parse_mode="HTML"
    )

    def run_publish_worker():
        with processing_lock:
            try:
                if source == "guruwaraya":
                    res = publish_guruwaraya_post(post_url=url, title=title, institution=institution)
                else:
                    res = process_and_publish_url(url)

                status = res.get("status")
                if status == "success":
                    live_url = res.get("url")
                    edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=(
                            f"🎉 <b>Post Approved & Published to LKUni.com!</b>\n\n"
                            f"📌 <b>Title:</b> {html.escape(res.get('title', title))}\n"
                            f"🏛 <b>Institution:</b> {html.escape(institution)}\n"
                            f"🌐 <b>Blog:</b> <a href='https://www.lkuni.com/'>www.lkuni.com</a>\n"
                            f"🔗 <b>Live Post:</b> <a href='{live_url}'>{live_url}</a>\n\n"
                            f"📢 <b>Broadcast:</b> Successfully broadcast to @differentpaths"
                        ),
                        parse_mode="HTML"
                    )
                    cur_pending = load_pending_alerts()
                    cur_pending.pop(alert_id, None)
                    save_pending_alerts(cur_pending)
                elif status == "duplicate":
                    edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=(
                            f"⚠️ <b>Notice: Duplicate Detected</b>\n\n"
                            f"📌 <b>Title:</b> {html.escape(title)}\n\n"
                            f"This post already exists on www.lkuni.com:\n"
                            f"👉 <b>{html.escape(res.get('matched_title', 'Existing Post'))}</b>\n\n"
                            f"No duplicate post was created."
                        ),
                        parse_mode="HTML"
                    )
                    cur_pending = load_pending_alerts()
                    cur_pending.pop(alert_id, None)
                    save_pending_alerts(cur_pending)
                else:
                    send_message(chat_id, f"❌ Failed to publish approved post: {res.get('message', 'Unknown error')}", reply_markup=REPLY_KEYBOARD)
            except Exception as e:
                logging.exception(f"Error publishing approved alert {alert_id}: {e}")
                send_message(chat_id, f"❌ <b>Error publishing post:</b>\n<code>{html.escape(str(e))}</code>", reply_markup=REPLY_KEYBOARD, parse_mode="HTML")

    t = threading.Thread(target=run_publish_worker)
    t.daemon = True
    t.start()

def handle_alert_dismiss(chat_id: int, message_id: int, alert_id: str):
    """Dismisses an alert and removes its buttons."""
    pending = load_pending_alerts()
    alert = pending.pop(alert_id, None)
    save_pending_alerts(pending)

    title = alert.get("title", "Post") if alert else "Post"
    edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=(
            f"❌ <b>Post Alert Dismissed</b>\n\n"
            f"📌 <b>Title:</b> {html.escape(title)}\n\n"
            f"<i>This post was dismissed and will not be published to LKUni.com.</i>"
        ),
        parse_mode="HTML"
    )

def send_recent_lkuni_posts(chat_id: int):
    """Sends the 10 most recent posts published on LKUni.com with 1-tap Trash buttons."""
    token_file = os.path.join(BASE_DIR, "token.json")
    if not os.path.exists(token_file):
        send_message(chat_id, "❌ Error: `token.json` not found.", reply_markup=REPLY_KEYBOARD)
        return

    try:
        with open(token_file, "r") as f:
            creds_data = json.load(f)
        creds = Credentials.from_authorized_user_info(creds_data)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_file, "w") as f:
                f.write(creds.to_json())
        service = build("blogger", "v3", credentials=creds)
        res = service.posts().list(blogId=OFFICIAL_BLOG_ID, maxResults=10, fetchBodies=False).execute()
        items = res.get("items", [])
    except Exception as e:
        send_message(chat_id, f"❌ Error fetching recent posts from LKUni: {e}", reply_markup=REPLY_KEYBOARD)
        return

    if not items:
        send_message(chat_id, "ℹ️ No posts found on LKUni.com.", reply_markup=REPLY_KEYBOARD)
        return

    sl_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    updated_str = datetime.datetime.now(sl_tz).strftime("%Y-%m-%d | %I:%M %p")
    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    lines = [
        "📋 <b>LKUni.com – 10 Recent Posts</b>",
        f"🕒 <b>Updated:</b> {updated_str} (Sri Lanka Time)\n",
        "Here are the latest posts published on <a href='https://www.lkuni.com/'>www.lkuni.com</a>:\n"
    ]

    inline_keyboard = []
    for idx, p in enumerate(items):
        num_str = number_emojis[idx] if idx < len(number_emojis) else f"{idx+1}."
        title = html.escape(p.get("title", "Untitled"))
        url = p.get("url", "https://www.lkuni.com/")
        post_id = p.get("id")

        pub_iso = p.get("published", "")
        dt_str = pub_iso[:10]
        try:
            dt = datetime.datetime.fromisoformat(pub_iso.replace("Z", "+00:00")).astimezone(sl_tz)
            dt_str = dt.strftime("%Y-%m-%d | %I:%M %p")
        except Exception:
            pass

        lines.append(f"{num_str} <b>{title}</b>")
        lines.append(f"📅 <b>Published:</b> {dt_str}")
        lines.append(f"🔗 <a href='{url}'>Open on LKUni.com</a>\n")

        short_title = p.get("title", "")[:20] + ("..." if len(p.get("title", "")) > 20 else "")
        btn_label = f"🗑 Trash #{idx+1}: {short_title}"
        inline_keyboard.append([{"text": btn_label, "callback_data": f"trash_ask_{post_id}"}])

    lines.append("💡 <b>Trash Management:</b>")
    lines.append("• Tap any <b>🗑 Trash #X</b> button below to remove an accidental post from LKUni.com.")

    payload = {
        "chat_id": chat_id,
        "text": "\n".join(lines),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": {"inline_keyboard": inline_keyboard}
    }

    try:
        requests.post(f"{API_BASE}/sendMessage", json=payload, timeout=15)
    except Exception as e:
        logging.error(f"Error sending recent posts: {e}")

def main():
    logging.info("Starting LKUni Telegram Bot Listener...")
    offset = None

    while True:
        try:
            url = f"{API_BASE}/getUpdates"
            params = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset

            res = requests.get(url, params=params, timeout=40)
            if res.status_code != 200:
                time.sleep(5)
                continue

            data = res.json()
            if not data.get("ok"):
                time.sleep(5)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1

                # 1. Handle Inline Keyboard Callback Queries (1-tap buttons)
                cb = update.get("callback_query")
                if cb:
                    cb_id = cb.get("id")
                    cb_from = cb.get("from", {}).get("id")
                    cb_data = cb.get("data", "")
                    cb_chat_id = cb.get("message", {}).get("chat", {}).get("id")

                    try:
                        requests.post(f"{API_BASE}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=5)
                    except Exception:
                        pass

                    if cb_from in AUTHORIZED_USERS or cb_chat_id in AUTHORIZED_USERS or not AUTHORIZED_USERS:
                        if cb_data.startswith("guru_pub_"):
                            try:
                                p_num = int(cb_data.split("_")[-1])
                                handle_guru_publish(cb_chat_id, p_num)
                            except Exception as e:
                                logging.error(f"Error handling callback query {cb_data}: {e}")
                        elif cb_data.startswith("tamil_pub_"):
                            try:
                                p_num = int(cb_data.split("_")[-1])
                                handle_tamil_publish(cb_chat_id, p_num)
                            except Exception as e:
                                logging.error(f"Error handling callback query {cb_data}: {e}")
                        elif cb_data.startswith("tamil_already_posted"):
                            try:
                                requests.post(f"{API_BASE}/answerCallbackQuery", json={
                                    "callback_query_id": cb_id,
                                    "text": "✅ This course is already published on LKUni.com! No duplicate will be created.",
                                    "show_alert": True
                                }, timeout=5)
                            except Exception:
                                pass
                        elif cb_data.startswith("tamil_expired"):
                            try:
                                requests.post(f"{API_BASE}/answerCallbackQuery", json={
                                    "callback_query_id": cb_id,
                                    "text": "⚠️ This course has expired because its closing date has passed.",
                                    "show_alert": True
                                }, timeout=5)
                            except Exception:
                                pass
                        elif cb_data.startswith("trash_ask_"):
                            post_id = cb_data.replace("trash_ask_", "")
                            confirm_markup = {
                                "inline_keyboard": [
                                    [
                                        {"text": "🔴 Yes, Move to Trash", "callback_data": f"trash_do_{post_id}"},
                                        {"text": "❌ Cancel", "callback_data": "trash_cancel"}
                                    ]
                                ]
                            }
                            send_message(
                                cb_chat_id,
                                f"⚠️ <b>Confirm Trash Action:</b>\n\nAre you sure you want to move post <code>{post_id}</code> to Blogger Trash?\n\n<i>This will immediately remove it from www.lkuni.com.</i>",
                                reply_markup=confirm_markup,
                                parse_mode="HTML"
                            )
                        elif cb_data.startswith("trash_do_"):
                            post_id = cb_data.replace("trash_do_", "")
                            res = trash_lkuni_post(post_id)
                            if res.get("status") == "success":
                                try:
                                    requests.post(f"{API_BASE}/answerCallbackQuery", json={
                                        "callback_query_id": cb_id,
                                        "text": "🗑 Post moved to Blogger Trash!",
                                        "show_alert": True
                                    }, timeout=5)
                                except Exception:
                                    pass
                                send_message(
                                    cb_chat_id,
                                    f"🗑 <b>Post Successfully Moved to Trash!</b>\n\n"
                                    f"📌 <b>Title:</b> {html.escape(res.get('title', ''))}\n"
                                    f"🆔 <b>Post ID:</b> <code>{post_id}</code>\n\n"
                                    f"🌐 Removed from live www.lkuni.com.",
                                    reply_markup=REPLY_KEYBOARD,
                                    parse_mode="HTML"
                                )
                            else:
                                send_message(
                                    cb_chat_id,
                                    f"❌ Failed to trash post: {res.get('message', 'Unknown error')}",
                                    reply_markup=REPLY_KEYBOARD
                                )
                        elif cb_data == "trash_cancel":
                            try:
                                requests.post(f"{API_BASE}/answerCallbackQuery", json={
                                    "callback_query_id": cb_id,
                                    "text": "Action cancelled.",
                                    "show_alert": False
                                }, timeout=5)
                            except Exception:
                                pass
                            send_message(cb_chat_id, "❌ Trash action cancelled.", reply_markup=REPLY_KEYBOARD)
                        elif cb_data == "guru_already_posted":
                            try:
                                requests.post(f"{API_BASE}/answerCallbackQuery", json={
                                    "callback_query_id": cb_id,
                                    "text": "✅ This notice is already published on LKUni.com! No duplicate will be created.",
                                    "show_alert": True
                                }, timeout=5)
                            except Exception:
                                pass
                        elif cb_data.startswith("appr_alert_"):
                            a_id = cb_data.replace("appr_alert_", "")
                            msg_id = cb.get("message", {}).get("message_id")
                            handle_alert_approval(cb_chat_id, msg_id, a_id)
                        elif cb_data.startswith("dism_alert_"):
                            a_id = cb_data.replace("dism_alert_", "")
                            msg_id = cb.get("message", {}).get("message_id")
                            handle_alert_dismiss(cb_chat_id, msg_id, a_id)
                    continue

                # 2. Handle Text Messages
                msg = update.get("message")
                if not msg:
                    continue

                chat_id = msg.get("chat", {}).get("id")
                from_user = msg.get("from", {}).get("id")
                text = (msg.get("text") or "").strip()

                if not text:
                    continue

                # Authorization check
                if from_user not in AUTHORIZED_USERS and chat_id not in AUTHORIZED_USERS:
                    logging.warning(f"Unauthorized access attempt from user_id: {from_user}, chat_id: {chat_id}")
                    send_message(chat_id, "⛔ Sorry, you are not authorized to control LKUni Publisher.")
                    continue

                logging.info(f"Received command from {from_user}: {text}")

                # Check for URLs first
                found_url = extract_url(text)
                if found_url and not text.startswith("/"):
                    handle_custom_url(chat_id, found_url)
                elif text in ["/tamil", "🎓 /tamil", "/tamil@LkUni_bot"]:
                    send_message(chat_id, "🔍 *Scanning TamilGuru.lk for latest courses...*", reply_markup=REPLY_KEYBOARD)
                    threading.Thread(target=send_tamilguru_selection_list, args=(chat_id,), daemon=True).start()
                elif re.match(r"^/tamil_([1-9]\d*)", text, re.I):
                    m = re.match(r"^/tamil_([1-9]\d*)", text, re.I)
                    p_num = int(m.group(1))
                    handle_tamil_publish(chat_id, p_num)
                elif text in ["/recent", "📋 /recent", "/recent@LkUni_bot"]:
                    send_message(chat_id, "🔍 *Fetching 10 recent posts from LKUni.com...*", reply_markup=REPLY_KEYBOARD)
                    send_recent_lkuni_posts(chat_id)
                elif re.match(r"^/trash_([0-9]+)", text):
                    m = re.match(r"^/trash_([0-9]+)", text)
                    post_id = m.group(1)
                    res = trash_lkuni_post(post_id)
                    if res.get("status") == "success":
                        send_message(
                            chat_id,
                            f"🗑 <b>Post Moved to Trash!</b>\n\n📌 <b>Title:</b> {html.escape(res.get('title', ''))}\n🆔 <code>{post_id}</code>\n\n🌐 Removed from live www.lkuni.com.",
                            reply_markup=REPLY_KEYBOARD,
                            parse_mode="HTML"
                        )
                    else:
                        send_message(chat_id, f"❌ Failed to trash post: {res.get('message')}", reply_markup=REPLY_KEYBOARD)
                elif text in ["/daily", "📅 /daily", "/daily@LkUni_bot"]:
                    send_message(chat_id, "🔍 *Scanning TamilGuru & Guruwaraya for posts published today...*", reply_markup=REPLY_KEYBOARD)
                    send_daily_summary(chat_id)
                elif text in ["/guru", "📚 /guru", "/guru@LkUni_bot"]:
                    send_message(chat_id, "🔍 *Scanning Guruwaraya.lk for latest education & teacher posts...*", reply_markup=REPLY_KEYBOARD)
                    threading.Thread(target=send_daily_selection_list, args=(chat_id,), daemon=True).start()
                elif re.match(r"^/(publish|post|guru)_([1-9]\d*)", text, re.I):
                    m = re.match(r"^/(publish|post|guru)_([1-9]\d*)", text, re.I)
                    p_num = int(m.group(2))
                    handle_guru_publish(chat_id, p_num)
                elif text in ["/alert_status", "/alerts", "🔔 /alerts"]:
                    seen = load_seen_alerts()
                    pending = load_pending_alerts()
                    now = datetime.datetime.now(SL_TZ)
                    start_dt = MONITOR_STATS.get("start_time", now)
                    diff = now - start_dt
                    days = diff.days
                    hours, remainder = divmod(diff.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    parts = []
                    if days > 0:
                        parts.append(f"{days}d")
                    if hours > 0:
                        parts.append(f"{hours}h")
                    if minutes > 0 or hours > 0 or days > 0:
                        parts.append(f"{minutes}m")
                    parts.append(f"{seconds}s")
                    duration_str = " ".join(parts) if parts else "0s"
                    started_str = start_dt.strftime("%Y-%m-%d | %I:%M %p")

                    last_scan = MONITOR_STATS.get("last_scan_time")
                    if last_scan:
                        ago_secs = max(0, int((now - last_scan).total_seconds()))
                        if ago_secs < 60:
                            ago_txt = f"{ago_secs}s ago"
                        else:
                            ago_txt = f"{ago_secs // 60}m ago"
                        last_scan_str = f"{last_scan.strftime('%I:%M %p')} ({ago_txt})"
                    else:
                        last_scan_str = "Scanning now..."

                    total_scans = MONITOR_STATS.get("total_scans", 0)

                    pending_details = ""
                    if pending:
                        p_items = []
                        for pid, pdata in list(pending.items())[:5]:
                            src = "🎓 TamilGuru" if pdata.get("source") == "tamilguru" else "📚 Guruwaraya"
                            p_title = html.escape(pdata.get("title", "Untitled"))
                            p_items.append(f"   • [{src}] <i>{p_title}</i>")
                        pending_details = "\n" + "\n".join(p_items)

                    send_message(
                        chat_id,
                        f"🔔 <b>Real-time Monitor Status:</b>\n\n"
                        f"⏱ <b>Running Duration (Uptime):</b> <code>{duration_str}</code>\n"
                        f"🚀 <b>Started Since:</b> {started_str} (SL Time)\n"
                        f"🔄 <b>Scanner Status:</b> 🟢 Active (Every 30 mins)\n"
                        f"🕒 <b>Last Scanned:</b> {last_scan_str}\n"
                        f"📊 <b>Total Scans Completed:</b> {total_scans}\n\n"
                        f"🌐 <b>Monitored Sites:</b>\n"
                        f"   1. 🎓 TamilGuru Courses (tamilguru.lk/category/courses)\n"
                        f"   2. 📚 Guruwaraya Education (guruwaraya.lk)\n\n"
                        f"📁 <b>Cached Seen Posts:</b> {len(seen)}\n"
                        f"⏳ <b>Pending Approvals:</b> {len(pending)}{pending_details}\n\n"
                        f"<i>Whenever a new post appears on either site, an instant alert will appear here for your 1-tap approval before publishing.</i>",
                        reply_markup=REPLY_KEYBOARD,
                        parse_mode="HTML"
                    )
                elif text in ["/testalert", "/alert_test"]:
                    send_message(chat_id, "🚨 Sending sample alert for approval testing...", reply_markup=REPLY_KEYBOARD)
                    sample_info = {
                        "id": "tg_sample_test",
                        "source": "tamilguru",
                        "title": "Master of Teacher Education (MTE) Programme 2026 – Open University (OUSL)",
                        "url": "https://tamilguru.lk/master-of-teacher-education-mte-225-open-university-ousl/",
                        "institution": "The Open University of Sri Lanka (OUSL)",
                        "closing_date": "2026.11.20",
                        "published_date": "November 2, 2026",
                        "summary_points": [
                            "Medium: Sinhala, Tamil, English",
                            "Course Fee: Rs.140,000/="
                        ]
                    }
                    send_telegram_alert(sample_info, chat_id=chat_id)
                else:
                    send_message(
                        chat_id,
                        "🤖 *LKUni Publisher Bot*\n\n"
                        "• *🎓 /tamil* — Today's TamilGuru course selection\n"
                        "• *📚 /guru* — Today's Guruwaraya education & teacher posts\n"
                        "• *📅 /daily* — All posts published today from both sites\n"
                        "• *📋 /recent* — View 10 recent LKUni posts & trash mistakes\n"
                        "• *🔔 /alerts* — Check real-time course & teacher post monitor\n"
                        "• Or paste any educational link to convert and publish directly.",
                        reply_markup=REPLY_KEYBOARD
                    )

        except requests.exceptions.RequestException as re_err:
            logging.warning(f"Network error in listener: {re_err}")
            time.sleep(5)
        except Exception as e:
            logging.exception(f"Unexpected error in listener loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # Start real-time alert monitor thread in background (checking every 30 mins)
    monitor_thread = threading.Thread(target=run_monitor_loop, kwargs={"interval_seconds": 1800}, daemon=True)
    monitor_thread.start()
    logging.info("Real-time alert monitor thread started (1800s / 30m interval).")
    main()
