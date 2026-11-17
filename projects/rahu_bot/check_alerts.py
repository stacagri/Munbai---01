import json
import os
import requests
from datetime import datetime, timedelta

BOT_TOKEN = "8767707271:AAH28Brd09XyOyx3FtMyG92AU8AmzQlA2ks"
ADMIN_CHAT_ID = "1499235921"
TIMES_FILE = "/home/ubuntu/rahu_bot/today_times.json"
SUBS_FILE = "/home/ubuntu/rahu_bot/subscribers.json"

def load_subscribers():
    if os.path.exists(SUBS_FILE):
        try:
            with open(SUBS_FILE, "r", encoding="utf-8") as f:
                subs = json.load(f)
                if isinstance(subs, list) and subs:
                    return [str(s) for s in subs]
        except Exception:
            pass
    return [ADMIN_CHAT_ID]

def broadcast_msg(text):
    for chat_id in load_subscribers():
        try:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10
            )
        except Exception:
            pass

def check():
    if not os.path.exists(TIMES_FILE):
        return

    with open(TIMES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    now = datetime.now()
    now_hm = now.strftime("%H:%M")
    sent = data.get("sent_alerts", [])
    updated = False

    for p in data.get("periods", []):
        label = p["label"]
        start_dt = datetime.strptime(p["start_24"], "%H:%M")
        end_dt = datetime.strptime(p["end_24"], "%H:%M")

        before_5 = (start_dt - timedelta(minutes=5)).strftime("%H:%M")
        start_0  = start_dt.strftime("%H:%M")
        after_5  = (start_dt + timedelta(minutes=5)).strftime("%H:%M")
        end_0    = end_dt.strftime("%H:%M")

        key_pre = f"{label}_before_5_{before_5}"
        if now_hm == before_5 and key_pre not in sent:
            broadcast_msg(f"⏳ *Rahu Kalaya Reminder*\n\n*{label} Rahu Kalaya* will start in *5 minutes*!\n🕒 Period: `{p['start_12']} - {p['end_12']}`")
            sent.append(key_pre)
            updated = True

        key_start = f"{label}_start_{start_0}"
        if now_hm == start_0 and key_start not in sent:
            broadcast_msg(f"🔴 *Rahu Kalaya Started*\n\n*{label} Rahu Kalaya* has just started now.\n🕒 Ends at: `{p['end_12']}`")
            sent.append(key_start)
            updated = True

        key_post = f"{label}_after_5_{after_5}"
        if now_hm == after_5 and key_post not in sent:
            broadcast_msg(f"⚠️ *Rahu Kalaya Active (5 mins in)*\n\n*{label} Rahu Kalaya* started 5 minutes ago and is currently active.\n🕒 Active until: `{p['end_12']}`")
            sent.append(key_post)
            updated = True

        key_end = f"{label}_end_{end_0}"
        if now_hm == end_0 and key_end not in sent:
            broadcast_msg(f"✅ *Rahu Kalaya Ended*\n\n*{label} Rahu Kalaya* (`{p['start_12']} - {p['end_12']}`) has now ended. You can resume auspicious work!")
            sent.append(key_end)
            updated = True

    if updated:
        data["sent_alerts"] = sent
        with open(TIMES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    check()
