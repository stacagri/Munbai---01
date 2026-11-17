from playwright.sync_api import sync_playwright
import requests
import re
import json
import os
from datetime import datetime

BOT_TOKEN = "8767707271:AAH28Brd09XyOyx3FtMyG92AU8AmzQlA2ks"
ADMIN_CHAT_ID = "1499235921"
URL = "https://porondam.lk/rahu-kalaya/"
SCREENSHOT_PATH = "/home/ubuntu/rahu_bot/rahu_today.png"
TIMES_FILE = "/home/ubuntu/rahu_bot/today_times.json"
SUBS_FILE = "/home/ubuntu/rahu_bot/subscribers.json"

LATITUDE = 6.7132
LONGITUDE = 79.9026

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

def parse_time_range(line):
    matches = re.findall(r'(\d{1,2}:\d{2})\s*\(([AP]M)\)', line, re.IGNORECASE)
    if len(matches) >= 2:
        start_str = f"{matches[0][0]} {matches[0][1].upper()}"
        end_str = f"{matches[1][0]} {matches[1][1].upper()}"
        t_start = datetime.strptime(start_str, "%I:%M %p").strftime("%H:%M")
        t_end = datetime.strptime(end_str, "%I:%M %p").strftime("%H:%M")
        return {
            "start_24": t_start,
            "end_24": t_end,
            "start_12": start_str,
            "end_12": end_str
        }
    return None

def send_rahu_update():
    today_str = datetime.now().strftime("%Y-%m-%d (%A)")
    today_date = datetime.now().strftime("%Y-%m-%d")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 1350},
                geolocation={"latitude": LATITUDE, "longitude": LONGITUDE},
                permissions=["geolocation"]
            )
            page = context.new_page()
            
            page.goto(URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1500)
            
            try:
                page.click("text=Get nearest location", timeout=5000)
                page.wait_for_timeout(2500)
            except Exception:
                pass
            
            page.evaluate("""() => {
                const els = document.querySelectorAll('header, nav, .share-buttons, footer');
                els.forEach(e => e.style.display = 'none');
            }""")
            
            page.screenshot(path=SCREENSHOT_PATH, clip={"x": 40, "y": 140, "width": 1200, "height": 1050})
            body_text = page.inner_text("body")
            browser.close()

        lines = [line.strip() for line in body_text.splitlines() if line.strip()]
        relevant = []
        capture_next = False

        schedule_data = {"date": today_date, "periods": [], "sent_alerts": [], "caption": "", "file_id": None}
        current_period_type = None

        for line in lines:
            if "දිවා රාහු කාලය" in line or "day time rahu" in line.lower():
                current_period_type = "Daytime (දිවා)"
            elif "රාත්‍රී රාහු කාලය" in line or "night time rahu" in line.lower():
                current_period_type = "Nighttime (රාත්‍රී)"
            
            if current_period_type:
                parsed = parse_time_range(line)
                if parsed:
                    parsed["label"] = current_period_type
                    schedule_data["periods"].append(parsed)
                    current_period_type = None

            if len(line) > 95 or "සියලුම ජ්‍යොතිෂ්‍ය" in line or "standard clock" in line.lower() or line == "00:00:00":
                continue
            if capture_next:
                relevant.append(line)
                break
            if "සුබ වර්ණය" in line or "best colour" in line.lower():
                relevant.append(line)
                capture_next = True
                continue
            if re.search(r'\d{1,2}\s*[:.]\s*\d{2}', line) or any(k in line.lower() for k in [
                "සූර්ය", "දිවා රාහු", "රාත්‍රී රාහු", "සුබ දිශාව", "මරු සිටින",
                "good direction", "bad direction", "ඊශාන", "ගිනිකොන", "නිරිත", "වයඹ",
                "උතුර", "දකුණ", "නැගෙනහිර", "බස්නාහිර"
            ]):
                if line not in relevant:
                    relevant.append(line)

        text_summary = "\n".join(relevant)
        caption = f"🌅 *Rahu Kalaya Update — {today_str}*\n\n{text_summary}\n\n🔗 {URL}"
        schedule_data["caption"] = caption[:1024]

        subscribers = load_subscribers()
        api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        file_id = None
        inline_kb = json.dumps({
            "inline_keyboard": [
                [{"text": "🔍 Check Rahu Kalaya Now", "callback_data": "check_status"}]
            ]
        })

        for chat_id in subscribers:
            try:
                if file_id:
                    res = requests.post(
                        api_url,
                        data={"chat_id": chat_id, "photo": file_id, "caption": schedule_data["caption"], "parse_mode": "Markdown", "reply_markup": inline_kb},
                        timeout=15
                    )
                else:
                    with open(SCREENSHOT_PATH, "rb") as photo:
                        res = requests.post(
                            api_url,
                            data={"chat_id": chat_id, "caption": schedule_data["caption"], "parse_mode": "Markdown", "reply_markup": inline_kb},
                            files={"photo": photo},
                            timeout=20
                        )
                    if res.status_code == 200:
                        resp_json = res.json()
                        photos = resp_json.get("result", {}).get("photo", [])
                        if photos:
                            file_id = photos[-1].get("file_id")
                            schedule_data["file_id"] = file_id
                print(f"Sent photo to {chat_id}: HTTP {res.status_code}")
            except Exception as send_err:
                print(f"Failed sending to {chat_id}: {send_err}")

        with open(TIMES_FILE, "w", encoding="utf-8") as f:
            json.dump(schedule_data, f, ensure_ascii=False, indent=2)
        print("Saved today's schedule for", len(subscribers), "subscribers.")

    except Exception as e:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": ADMIN_CHAT_ID, "text": f"⚠️ Error fetching Rahu Kalaya: {e}\n{URL}"}
        )

if __name__ == "__main__":
    send_rahu_update()
