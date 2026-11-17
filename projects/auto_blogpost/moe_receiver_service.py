#!/usr/bin/env python3
"""
MOE Bridge Receiver Service
- Listens on 0.0.0.0:8080
- Receives English & Sinhala Special Notices HTML directly from Android phone
- Extracts notices, bullet points, and PDF links
- Stashes them into moe_staged_queue.json for 6:30 PM publication
- Sends immediate confirmation to User via Telegram
"""

import os
import sys
import json
import time
import socket
import logging
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

# Set default socket timeout so external scanners can never hang the server
socket.setdefaulttimeout(30)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from publish_staged_moe import parse_moe_html, load_queue, save_queue, publish_staged_moe_notice
from auto_blogger import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [MOE-RECEIVER] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

class MoeReceiverHandler(BaseHTTPRequestHandler):
    timeout = 15  # Prevent deadlocks from hanging connections

    def _send_json(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_GET(self):
        if self.path == "/health" or self.path == "/":
            self._send_json(200, {"status": "ok", "service": "LKUni MOE Bridge Receiver"})
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path.startswith("/upload_moe"):
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                payload = json.loads(body)

                en_html = payload.get("en_html", "")
                si_html = payload.get("si_html", "")
                en_source = payload.get("en_source_url", "")
                si_source = payload.get("si_source_url", "")
                publish_now = payload.get("publish_now", False)

                if en_html:
                    with open(os.path.join(BASE_DIR, "en_raw_phone.html"), "w", encoding="utf-8") as f:
                        f.write(en_html)
                if si_html:
                    with open(os.path.join(BASE_DIR, "si_raw_phone.html"), "w", encoding="utf-8") as f:
                        f.write(si_html)

                queue = load_queue()

                if en_html:
                    queue["en"] = parse_moe_html(en_html, lang="en", source_url=en_source)
                if si_html:
                    queue["si"] = parse_moe_html(si_html, lang="si", source_url=si_source)

                save_queue(queue)

                en_data = queue.get("en", {})
                si_data = queue.get("si", {})

                en_pdfs_count = len(en_data.get("pdfs", []))
                si_pdfs_count = len(si_data.get("pdfs", []))

                logging.info(f"Received MOE Special Notices: EN='{en_data.get('title')}', SI='{si_data.get('title')}'")

                # Check if this is after 6:30 PM (Catch-up Mode until 12:00 AM) or explicit publish_now
                now_hour = int(time.strftime("%H"))
                now_minute = int(time.strftime("%M"))
                is_catchup = publish_now or (now_hour == 18 and now_minute >= 30) or (now_hour > 18)

                if is_catchup:
                    logging.info(f"Catch-up publication triggered (Current time: {now_hour:02d}:{now_minute:02d})...")
                    res = publish_staged_moe_notice()
                    post_url = res.get("url")
                    
                    catchup_msg = (
                        "🎉 *MOE Notice Received & Published (Catch-Up Mode)!*\n\n"
                        f"🇬🇧 *English Title:* {en_data.get('title', 'N/A')}\n"
                        f"🇱🇰 *Sinhala Title:* {si_data.get('title', 'N/A')}\n\n"
                        f"👉 *Live Post URL:* {post_url or 'Published'}\n\n"
                        "✅ Successfully posted to LKUni and broadcast to Telegram!"
                    )
                    try:
                        requests.post(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                            json={"chat_id": "1499235921", "text": catchup_msg, "parse_mode": "Markdown"},
                            timeout=10
                        )
                    except Exception as tg_err:
                        logging.warning(f"Could not send Telegram catchup confirmation: {tg_err}")

                    self._send_json(200, {
                        "status": "success",
                        "mode": "catchup_published",
                        "published": True,
                        "url": post_url,
                        "en_title": en_data.get("title")
                    })
                    return

                # Normal daytime staging (before 6:30 PM)
                tg_msg = (
                    "📥 *MOE Special Notices Received from Phone!*\n\n"
                    f"🇬🇧 *English Title:* {en_data.get('title', 'N/A')}\n"
                    f"📄 *English PDFs Found:* {en_pdfs_count}\n\n"
                    f"🇱🇰 *Sinhala Title:* {si_data.get('title', 'N/A')}\n"
                    f"📄 *Sinhala PDFs Found:* {si_pdfs_count}\n\n"
                    "⏰ *Status:* Successfully staged. Scheduled for publication at 6:30 PM!"
                )

                try:
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                        json={"chat_id": "1499235921", "text": tg_msg, "parse_mode": "Markdown"},
                        timeout=10
                    )
                except Exception as tg_err:
                    logging.warning(f"Could not send Telegram confirmation: {tg_err}")

                self._send_json(200, {
                    "status": "success",
                    "mode": "staged_for_630pm",
                    "staged": True,
                    "en_title": en_data.get("title"),
                    "si_title": si_data.get("title"),
                    "en_pdfs": en_pdfs_count,
                    "si_pdfs": si_pdfs_count
                })

            except Exception as e:
                logging.exception(f"Error handling upload: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})
        else:
            self._send_json(404, {"error": "Endpoint not found"})

def run_server(port=8080):
    server = ThreadingHTTPServer(("0.0.0.0", port), MoeReceiverHandler)
    server.daemon_threads = True
    logging.info(f"MOE Multi-threaded Receiver Service listening on http://0.0.0.0:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

if __name__ == "__main__":
    run_server()
