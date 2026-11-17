import json
import os
import time
import threading
import subprocess
from datetime import datetime
import requests

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "8992942076:AAGOKyMoJ6unQTcYf3cQSOxyTMT3FrwyfkY"
INITIAL_ADMIN_CHAT_ID = "1499235921"
SUBSCRIBERS_FILE = "/home/ubuntu/subscribers.json"
API_URL = "https://api.rivernet.lk/api/overview/latest-status-paginated"

DEFAULT_ALERT_LEVEL = 5.20
POLL_INTERVAL = 300       # Check every 5 minutes
ALERT_INTERVAL = 1800     # Broadcast every 30 minutes during flood alert

subscribers_lock = threading.Lock()


def load_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return {INITIAL_ADMIN_CHAT_ID}
    try:
        with open(SUBSCRIBERS_FILE, "r") as f:
            data = json.load(f)
            return set(data)
    except Exception:
        return {INITIAL_ADMIN_CHAT_ID}


def save_subscribers(subs):
    try:
        with open(SUBSCRIBERS_FILE, "w") as f:
            json.dump(list(subs), f)
    except Exception as e:
        print(f"[{datetime.now()}] Failed to save subscribers: {e}")


def add_subscriber(chat_id):
    chat_id = str(chat_id)
    with subscribers_lock:
        subs = load_subscribers()
        if chat_id not in subs:
            subs.add(chat_id)
            save_subscribers(subs)
            print(f"[{datetime.now()}] Registered new subscriber: {chat_id}")
            return True
        return False


APP_ALERT_URL = "https://ntfy.sh/kalu_ganga_alert_lk_live"


def trigger_app_alert(message: str):
    try:
        requests.post(APP_ALERT_URL, data=message.encode("utf-8"), timeout=5)
        print(f"[{datetime.now()}] App alert broadcast sent: {message}")
    except Exception as e:
        print(f"[{datetime.now()}] Failed to broadcast app alert: {e}")


def get_keyboard():
    return {
        "keyboard": [
            [{"text": "/check"}, {"text": "🚨 Test App Alarm"}]
        ],
        "resize_keyboard": True,
        "persistent": True
    }


def send_telegram(chat_id: str, text: str, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": str(chat_id),
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(url, json=payload, timeout=(5, 10))
        if r.status_code == 403:
            with subscribers_lock:
                subs = load_subscribers()
                if str(chat_id) in subs:
                    subs.remove(str(chat_id))
                    save_subscribers(subs)
                    print(f"[{datetime.now()}] Unregistered inactive/blocked user: {chat_id}")
    except Exception as e:
        print(f"[{datetime.now()}] Delivery failed for {chat_id}: {e}")


def broadcast_telegram(text: str, reply_markup=None):
    with subscribers_lock:
        recipients = list(load_subscribers())
    for chat_id in recipients:
        try:
            send_telegram(chat_id, text, reply_markup)
            time.sleep(0.05)
        except Exception as e:
            print(f"[{datetime.now()}] Broadcast error for {chat_id}: {e}")


def fetch_river_data():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }
    params = {
        "deviceType": "river_level",
        "page": 1,
        "isTableView": 1
    }
    resp = requests.get(API_URL, params=params, headers=headers, timeout=(5, 15))
    resp.raise_for_status()
    json_data = resp.json()

    items = json_data.get("results", {}).get("data", [])
    for item in items:
        if item.get("unitId") == "I97" or "Kalu Ganga (Ratnapura)" in item.get("location", ""):
            latest = item.get("latest", {})
            raw_val = (
                latest.get("actualLatestRecord", {}).get("value")
                or latest.get("latestLevel")
                or latest.get("latestRecord", {}).get("value")
            )
            water_level = float(raw_val) if raw_val else None

            alert_level = DEFAULT_ALERT_LEVEL
            minor_level = 7.50
            major_level = 9.50
            critical_level = 10.50

            for a in item.get("alerts", []):
                label = a.get("alertLabel", "").lower()
                val = float(a.get("alertValue", 0))
                if label == "alert":
                    alert_level = val
                elif label == "minor":
                    minor_level = val
                elif label == "major":
                    major_level = val
                elif label == "critical":
                    critical_level = val

            alert_type = latest.get("alertType", "normal").capitalize()
            recorded_time = latest.get("datetime", "")
            change = latest.get("change")
            before_30m_raw = latest.get("before30mLevel")
            before_30m = float(before_30m_raw) if before_30m_raw else None

            return water_level, alert_level, minor_level, major_level, critical_level, alert_type, recorded_time, change, before_30m

    return None, DEFAULT_ALERT_LEVEL, 7.50, 9.50, 10.50, "Unknown", "", None, None


def get_trend_display(change, water_level, before_30m):
    """Calculates directional trend (Rising/Falling/Steady) and 30-minute delta."""
    if change == 1:
        arrow = "⬆️"
        trend_name = "RISING (Going Up)"
    elif change == -1:
        arrow = "⬇️"
        trend_name = "FALLING (Going Down)"
    elif change == 0:
        arrow = "➡️"
        trend_name = "STEADY (Stable)"
    else:
        if before_30m is not None and water_level is not None:
            diff = water_level - before_30m
            if diff > 0.01:
                arrow = "⬆️"
                trend_name = "RISING (Going Up)"
            elif diff < -0.01:
                arrow = "⬇️"
                trend_name = "FALLING (Going Down)"
            else:
                arrow = "➡️"
                trend_name = "STEADY (Stable)"
        else:
            return "➡️", "➡️ *STEADY (Stable)*"

    delta_str = ""
    if before_30m is not None and water_level is not None:
        diff = water_level - before_30m
        sign = "+" if diff > 0 else ""
        delta_str = f" ({sign}{diff:.2f} m in 30 mins)"

    return arrow, f"{arrow} *{trend_name}*{delta_str}"


def format_status_message(header="💧 *Live Water Level Report*"):
    water_level, alert_lvl, minor_lvl, major_lvl, crit_lvl, alert_type, rec_time, change, before_30m = fetch_river_data()
    if water_level is None:
        return "⚠️ Unable to fetch data from RiverNet right now. Please try again shortly."

    if water_level >= crit_lvl:
        badge = "🚨 CRITICAL FLOOD"
    elif water_level >= major_lvl:
        badge = "🚨 MAJOR FLOOD"
    elif water_level >= minor_lvl:
        badge = "⚠️ MINOR FLOOD"
    elif water_level >= alert_lvl:
        badge = "⚠️ ALERT LEVEL"
    else:
        badge = "🟢 NORMAL"

    arrow, trend_line = get_trend_display(change, water_level, before_30m)

    msg = (
        f"{header}\n"
        f"*Location:* Kalu Ganga (Ratnapura)\n\n"
        f"💧 *Current Level:* `{water_level:.2f} m` {arrow}\n"
        f"📈 *Trend:* {trend_line}\n"
        f"📊 *Status:* {badge} ({alert_type})\n"
        f"🚨 *Alert Level:* `{alert_lvl:.2f} m`\n"
        f"🌊 *Minor Flood:* `{minor_lvl:.2f} m`\n"
        f"🛑 *Major Flood:* `{major_lvl:.2f} m`\n"
        f"🕒 *Station Time:* {rec_time}\n"
        f"🌐 *Source:* [rivernet.lk/ratnapura](https://rivernet.lk/ratnapura)"
    )
    return msg


# --- AUTO-RESTARTING BACKGROUND MONITOR ---
def monitor_loop():
    print(f"[{datetime.now()}] Automated monitor thread started.")
    is_in_alert = False
    last_alert_sent_time = 0
    last_summary_date = None
    # 0: Normal (<5.20m), 1: Alert (>=5.20m), 2: Minor (>=7.50m), 3: Major (>=9.50m), 4: Critical (>=10.50m)
    # Initialize to 1 if already in alert stage on launch, so we only alert when a new higher stage is reached
    highest_stage_alerted = 1

    while True:
        try:
            now = datetime.now()
            water_level, alert_level, minor_lvl, major_lvl, crit_lvl, alert_type, recorded_time, change, before_30m = fetch_river_data()

            if water_level is not None:
                arrow, trend_line = get_trend_display(change, water_level, before_30m)
                print(f"[{now}] Monitored: {water_level:.2f} m {arrow} | Trend: {trend_line} | Threshold: {alert_level:.2f} m")

                # Determine current flood stage
                if water_level >= crit_lvl:
                    current_stage = 4
                    stage_title = f"CRITICAL FLOOD ({crit_lvl:.2f} m)"
                elif water_level >= major_lvl:
                    current_stage = 3
                    stage_title = f"MAJOR FLOOD ({major_lvl:.2f} m)"
                elif water_level >= minor_lvl:
                    current_stage = 2
                    stage_title = f"MINOR FLOOD ({minor_lvl:.2f} m)"
                elif water_level >= alert_level:
                    current_stage = 1
                    stage_title = f"ALERT LEVEL ({alert_level:.2f} m)"
                else:
                    current_stage = 0
                    stage_title = "NORMAL"

                # --- MOBILE APP ALERT LOGIC (Trigger ONLY once per newly breached stage) ---
                if current_stage > highest_stage_alerted and current_stage > 0:
                    alert_reason = f"🚨 FLOOD WARNING: Kalu Ganga reached {water_level:.2f} m! Crossed {stage_title}!"
                    print(f"[{now}] New flood stage {current_stage} ({stage_title}) reached! Alerting all mobile apps...")
                    trigger_app_alert(alert_reason)
                    highest_stage_alerted = current_stage
                elif current_stage < highest_stage_alerted:
                    # Water receded below a stage (or completely back below 5.20m)
                    highest_stage_alerted = current_stage
                    print(f"[{now}] Water receded to stage {current_stage}. Stage tracker reset to {highest_stage_alerted}.")

                # --- TELEGRAM BOT LOGIC (30-minute updates while above alert_level) ---
                if water_level >= alert_level:
                    current_timestamp = time.time()
                    time_since_last_alert = current_timestamp - last_alert_sent_time

                    if not is_in_alert or time_since_last_alert >= ALERT_INTERVAL:
                        is_in_alert = True
                        last_alert_sent_time = current_timestamp
                        print(f"[{now}] Triggering 30-min flood broadcast...")
                        msg = format_status_message("⚠️ *FLOOD ALERT ACTIVE*") + "\n\n_Next update in 30 minutes._"
                        broadcast_telegram(msg, reply_markup=get_keyboard())

                # Normal / Receding Mode
                else:
                    if is_in_alert:
                        is_in_alert = False
                        highest_stage_alerted = 0
                        recovery_msg = (
                            f"✅ *SAFE: Water Receded Below Alert Level*\n\n"
                            f"💧 *Current Level:* `{water_level:.2f} m` {arrow}\n"
                            f"📈 *Trend:* {trend_line}\n"
                            f"🚨 *Alert Threshold:* `{alert_level:.2f} m`\n"
                            f"🕒 *Station Time:* {recorded_time}\n"
                            f"🌐 *Source:* [rivernet.lk/ratnapura](https://rivernet.lk/ratnapura)\n\n"
                            f"Daily 6:00 AM summary schedule resumed."
                        )
                        broadcast_telegram(recovery_msg, reply_markup=get_keyboard())

                    # Daily 6:00 AM summary
                    today_str = now.strftime("%Y-%m-%d")
                    if now.hour == 6 and last_summary_date != today_str:
                        summary_msg = format_status_message("📊 *Ratnapura Daily River Summary (6:00 AM)*")
                        broadcast_telegram(summary_msg, reply_markup=get_keyboard())
                        last_summary_date = today_str

        except Exception as err:
            print(f"[{datetime.now()}] Monitor loop caught exception: {err}")

        time.sleep(POLL_INTERVAL)


def telegram_listener():
    offset = None
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"

    while True:
        try:
            params = {"timeout": 25}
            if offset:
                params["offset"] = offset

            resp = requests.get(url, params=params, timeout=(5, 30))
            if resp.status_code == 200:
                data = resp.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    chat_id = str(msg.get("chat", {}).get("id", ""))
                    text = msg.get("text", "").strip().lower()

                    if not chat_id:
                        continue

                    add_subscriber(chat_id)

                    if text.startswith("/start"):
                        welcome_text = (
                            "👋 *Welcome to the Ratnapura RiverNet Water Level Monitor!*\n\n"
                            "You are registered to receive:\n"
                            "• 🚨 Telegram updates every 30 mins during floods (above 5.20 m)\n"
                            "• 📊 Daily summary at 6:00 AM\n\n"
                            "Tap `/check` for an instant reading, or tap `🚨 Test App Alarm` to test your mobile app siren."
                        )
                        send_telegram(chat_id, welcome_text, reply_markup=get_keyboard())
                    elif text in ["/check", "/status", "check"]:
                        status_text = format_status_message("⚡ *Instant Water Level Check*")
                        send_telegram(chat_id, status_text, reply_markup=get_keyboard())
                    elif text in ["/test", "/test_app", "🚨 test app alarm", "test app alarm", "test"]:
                        trigger_app_alert("🚨 TEST ALARM: Emergency Siren & Screen Wakeup triggered from Telegram Bot!")
                        send_telegram(
                            chat_id,
                            "🔔 *Mobile App Siren Test Triggered!*\n\n"
                            "Emergency trigger signal transmitted to your mobile app. Your screen will wake up and ring the siren now!",
                            reply_markup=get_keyboard()
                        )
                    elif text in ["/update_app", "/update", "/publish_update"]:
                        send_telegram(
                            chat_id,
                            "🚀 *Initiating Remote App Update...*\n\n"
                            "The VM is compiling the new APK build and will broadcast the update signal to all phones shortly.\n"
                            "Your phone will prompt you to update in about ~30 seconds!",
                            reply_markup=get_keyboard()
                        )
                        def run_pub():
                            subprocess.run(["/home/ubuntu/publish_app_update.py"])
                        threading.Thread(target=run_pub, daemon=True).start()
        except Exception as e:
            time.sleep(3)


def main():
    add_subscriber(INITIAL_ADMIN_CHAT_ID)

    # Start background polling thread
    t = threading.Thread(target=monitor_loop, daemon=True)
    t.start()

    # Run Telegram listener
    telegram_listener()


if __name__ == "__main__":
    main()
