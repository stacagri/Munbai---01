import json
import os
import time
from datetime import datetime
import requests

BOT_TOKEN = "8767707271:AAH28Brd09XyOyx3FtMyG92AU8AmzQlA2ks"
SUBS_FILE = "/home/ubuntu/rahu_bot/subscribers.json"
TIMES_FILE = "/home/ubuntu/rahu_bot/today_times.json"
SCREENSHOT_PATH = "/home/ubuntu/rahu_bot/rahu_today.png"
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

MAIN_KEYBOARD = {
    "keyboard": [
        [{"text": "🔍 Check Rahu Kalaya Now"}, {"text": "📅 Today's Schedule"}],
        [{"text": "ℹ️ Help / Info"}]
    ],
    "resize_keyboard": True,
    "is_persistent": True
}

CHECK_INLINE_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "🔄 Refresh / Check Again", "callback_data": "check_status"},
            {"text": "📅 View Full Chart", "callback_data": "view_today"}
        ]
    ]
}

def setup_bot_commands():
    try:
        commands = [
            {"command": "check", "description": "Check if Rahu Kalaya is active right now"},
            {"command": "today", "description": "View today's full Rahu Kalaya chart & directions"},
            {"command": "start", "description": "Subscribe to automatic Rahu Kalaya alerts"},
            {"command": "stop", "description": "Unsubscribe from automatic alerts"}
        ]
        requests.post(f"{API_BASE}/setMyCommands", json={"commands": commands}, timeout=10)
    except Exception as e:
        print("Failed to set bot commands:", e)

def load_subscribers():
    if os.path.exists(SUBS_FILE):
        try:
            with open(SUBS_FILE, "r", encoding="utf-8") as f:
                return [str(x) for x in json.load(f)]
        except Exception:
            pass
    return []

def save_subscribers(subs):
    with open(SUBS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(dict.fromkeys(subs)), f, indent=2)

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(f"{API_BASE}/sendMessage", data=payload, timeout=10)
    except Exception as e:
        print(f"Error sending message to {chat_id}:", e)

def answer_callback(callback_query_id, text=None):
    try:
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        requests.post(f"{API_BASE}/answerCallbackQuery", data=payload, timeout=10)
    except Exception as e:
        print("Error answering callback:", e)

def get_rahu_status_text():
    if not os.path.exists(TIMES_FILE):
        return "⏳ Today's Rahu Kalaya schedule is being prepared. Please try again in a few moments!"

    try:
        with open(TIMES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return "⚠️ Error reading today's schedule file. Please try again shortly."

    periods = data.get("periods", [])
    if not periods:
        return "⏳ Today's Rahu Kalaya periods are not available yet. Please check back shortly!"

    now = datetime.now()
    now_str = now.strftime("%H:%M")
    now_12 = now.strftime("%I:%M %p")
    today_date = now.strftime("%Y-%m-%d")

    active_period = None
    next_period = None

    for p in periods:
        s = p.get("start_24", "")
        e = p.get("end_24", "")
        if s <= now_str < e:
            active_period = p
            break
        elif now_str < s:
            if next_period is None or s < next_period.get("start_24", ""):
                next_period = p

    lines = []
    lines.append(f"⏱ *Current Time:* `{now_12}` ({data.get('date', today_date)})\n")

    if active_period:
        try:
            end_dt = datetime.strptime(f"{today_date} {active_period['end_24']}", "%Y-%m-%d %H:%M")
            mins_left = max(0, int((end_dt - now).total_seconds() // 60))
        except Exception:
            mins_left = "?"

        lines.append("🔴 *දැන් රාහු කාලය පවතී!*")
        lines.append("*(Rahu Kalaya is ACTIVE right now)*\n")
        lines.append(f"📌 *කාලසීමාව (Period):* {active_period.get('label', 'Daytime')}")
        lines.append(f"⏰ *වේලාව (Time):* `{active_period['start_12']} - {active_period['end_12']}`")
        lines.append(f"⏳ *අවසන් වීමට තව (Ends in):* `{mins_left} mins`\n")
        lines.append("⚠️ *අවවාදයයි:* සුබ කටයුතු ආරම්භ කිරීමෙන් වළකින්න.")
    elif next_period:
        try:
            start_dt = datetime.strptime(f"{today_date} {next_period['start_24']}", "%Y-%m-%d %H:%M")
            mins_left = max(0, int((start_dt - now).total_seconds() // 60))
            hrs = mins_left // 60
            rem_mins = mins_left % 60
            time_left_str = f"{hrs}h {rem_mins}m" if hrs > 0 else f"{rem_mins} mins"
        except Exception:
            time_left_str = "soon"

        lines.append("🟢 *දැනට රාහු කාලය නොමැත*")
        lines.append("*(Currently Safe — Not Rahu Kalaya)*\n")
        lines.append("🔜 *ඊළඟ රාහු කාලය (Next Rahu Period):*")
        lines.append(f"📌 *කාලසීමාව:* {next_period.get('label', 'Upcoming')}")
        lines.append(f"⏰ *වේලාව:* `{next_period['start_12']} - {next_period['end_12']}`")
        lines.append(f"⏳ *ආරම්භ වීමට තව:* `{time_left_str}`\n")
        lines.append("✨ සුබ කටයුතු සඳහා මෙම කාලය භාවිත කළ හැක.")
    else:
        lines.append("🟢 *අද දින රාහු කාලයන් සියල්ල අවසන් වී ඇත!*")
        lines.append("*(All Rahu Kalaya periods for today have ended)*\n")
        lines.append("🌅 හෙට දින රාහු කාල සටහන උදෑසන 06:00 ට ලැබෙනු ඇත.")

    lines.append("\n📋 *අද දිනයේ සම්පූර්ණ කාලසටහන:*")
    for p in periods:
        lines.append(f"• {p.get('label', '')}: `{p['start_12']} - {p['end_12']}`")

    return "\n".join(lines)

def send_check_status(chat_id):
    status_text = get_rahu_status_text()
    send_message(chat_id, status_text, reply_markup=CHECK_INLINE_KEYBOARD)

def send_today_card(chat_id):
    if not os.path.exists(TIMES_FILE):
        send_message(chat_id, "⏳ Today's Rahu Kalaya schedule is being prepared. Please try again shortly!", reply_markup=MAIN_KEYBOARD)
        return

    with open(TIMES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    caption = data.get("caption")
    if not caption:
        lines = [f"🌅 *Rahu Kalaya Schedule ({data.get('date', 'Today')})*\n"]
        for p in data.get("periods", []):
            lines.append(f"• *{p['label']}:* `{p['start_12']} - {p['end_12']}`")
        caption = "\n".join(lines)

    file_id = data.get("file_id")
    inline_kb = {
        "inline_keyboard": [
            [{"text": "🔍 Check Current Status", "callback_data": "check_status"}]
        ]
    }

    if file_id:
        res = requests.post(
            f"{API_BASE}/sendPhoto",
            data={
                "chat_id": chat_id,
                "photo": file_id,
                "caption": caption,
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(inline_kb)
            },
            timeout=15
        )
        if res.status_code == 200:
            return

    if os.path.exists(SCREENSHOT_PATH):
        with open(SCREENSHOT_PATH, "rb") as photo:
            requests.post(
                f"{API_BASE}/sendPhoto",
                data={
                    "chat_id": chat_id,
                    "caption": caption,
                    "parse_mode": "Markdown",
                    "reply_markup": json.dumps(inline_kb)
                },
                files={"photo": photo},
                timeout=20
            )
    else:
        send_message(chat_id, caption, reply_markup=inline_kb)

def main():
    setup_bot_commands()
    offset = None
    print("Rahu Kalaya multi-user listener started with /check support...")
    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset
            res = requests.get(f"{API_BASE}/getUpdates", params=params, timeout=35)
            if res.status_code != 200:
                time.sleep(3)
                continue

            updates = res.json().get("result", [])
            for upd in updates:
                offset = upd["update_id"] + 1

                # Handle inline callback queries
                if "callback_query" in upd:
                    cb = upd["callback_query"]
                    cb_id = cb["id"]
                    cb_data = cb.get("data", "")
                    cb_chat_id = str(cb["message"]["chat"]["id"])

                    if cb_data == "check_status":
                        answer_callback(cb_id, "Checking Rahu Kalaya status...")
                        send_check_status(cb_chat_id)
                    elif cb_data == "view_today":
                        answer_callback(cb_id, "Loading today's schedule...")
                        send_today_card(cb_chat_id)
                    else:
                        answer_callback(cb_id)
                    continue

                msg = upd.get("message") or upd.get("edited_message")
                if not msg:
                    continue

                chat_id = str(msg["chat"]["id"])
                first_name = msg["chat"].get("first_name", "Friend")
                text = (msg.get("text") or "").strip().lower()

                if text.startswith("/start"):
                    subs = load_subscribers()
                    if chat_id not in subs:
                        subs.append(chat_id)
                        save_subscribers(subs)
                    welcome = (
                        f"ආයුබෝවන් *{first_name}*! 🙏\n\n"
                        f"✅ You are subscribed to *Daily Rahu Kalaya Alerts*.\n"
                        f"• 🌅 *6:00 AM:* Daily Rahu Kalaya chart & auspicious directions\n"
                        f"• ⏳ *Alerts:* 5 mins before, at start, 5 mins after, and when Rahu Kalaya ends.\n\n"
                        f"⚡ *Quick Options:*\n"
                        f"• `/check` — Check if Rahu Kalaya is active right now\n"
                        f"• `/today` — Get today's full Rahu Kalaya chart\n"
                        f"• `/stop` — Unsubscribe from automatic alerts\n\n"
                        f"👇 *Use the buttons below to check anytime!*"
                    )
                    send_message(chat_id, welcome, reply_markup=MAIN_KEYBOARD)
                    send_check_status(chat_id)

                elif text.startswith("/check") or "check rahu" in text or "check" == text:
                    send_check_status(chat_id)

                elif text.startswith("/today") or text.startswith("/rahu") or "today's schedule" in text or "schedule" in text:
                    send_today_card(chat_id)

                elif text.startswith("/help") or "help" in text or "info" in text:
                    help_text = (
                        "ℹ️ *Rahu Kalaya Bot Help*\n\n"
                        "You can check Rahu Kalaya anytime using:\n"
                        "• Tap *🔍 Check Rahu Kalaya Now* button\n"
                        "• Type `/check` to see if it's Rahu Kalaya right now\n"
                        "• Type `/today` to view the full chart and auspicious directions\n"
                        "• Type `/stop` to stop automatic alerts\n"
                        "• Type `/start` to resubscribe"
                    )
                    send_message(chat_id, help_text, reply_markup=MAIN_KEYBOARD)

                elif text.startswith("/stop"):
                    subs = load_subscribers()
                    if chat_id in subs:
                        subs.remove(chat_id)
                        save_subscribers(subs)
                    send_message(chat_id, "🔕 You have been unsubscribed from automatic Rahu Kalaya alerts. Send `/start` anytime to subscribe again.", reply_markup=MAIN_KEYBOARD)

        except Exception as e:
            print("Listener error:", e)
            time.sleep(5)

if __name__ == "__main__":
    main()
