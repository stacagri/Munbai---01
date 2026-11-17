import os
import re
import glob
import html
import json
import asyncio
import logging
import datetime
import subprocess
import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import yt_dlp

BOT_TOKEN = "8601740125:AAGf2xFxGg9W4zRXZh0VT5yH_bCJm0x2P2s"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "temp_downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

COOKIE_RAW = os.path.join(BASE_DIR, "cookies.txt")
COOKIE_NETSCAPE = os.path.join(BASE_DIR, "cookies_netscape.txt")


def prepare_cookies_file(raw_cookie_file=COOKIE_RAW, netscape_file=COOKIE_NETSCAPE):
    """Automatically converts JSON cookies to Netscape format if needed."""
    if not os.path.exists(raw_cookie_file):
        if os.path.exists(netscape_file) and os.path.getsize(netscape_file) > 0:
            return netscape_file
        return None

    try:
        with open(raw_cookie_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().strip()
        if not content:
            if os.path.exists(netscape_file) and os.path.getsize(netscape_file) > 0:
                return netscape_file
            return None

        if content.startswith("# Netscape") or content.startswith("# HTTP") or "\t" in content:
            # Already Netscape / tab-separated format
            with open(netscape_file, "w", encoding="utf-8") as out:
                out.write(content)
            return netscape_file

        if content.startswith("[") or content.startswith("{"):
            data = json.loads(content)
            if isinstance(data, dict):
                data = data.get("cookies", [])
            lines = ["# Netscape HTTP Cookie File\n"]
            for c in data:
                domain = c.get("domain", "")
                include_sub = "TRUE" if domain.startswith(".") else "FALSE"
                path = c.get("path", "/")
                secure = "TRUE" if c.get("secure", False) else "FALSE"
                exp = str(int(c.get("expirationDate", 2147483647)))
                name = c.get("name", "")
                val = c.get("value", "")
                if domain and name:
                    lines.append(f"{domain}\t{include_sub}\t{path}\t{secure}\t{exp}\t{name}\t{val}\n")
            with open(netscape_file, "w", encoding="utf-8") as out:
                out.writelines(lines)
            return netscape_file
    except Exception as e:
        logger.warning(f"Cookie conversion error: {e}")

    return None


def extract_youtube_id(url: str):
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"shorts\/([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


async def download_tiktok_fallback(url: str, output_path: str) -> bool:
    api_url = "https://www.tikwm.com/api/"
    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
        resp = await client.post(api_url, data={"url": url, "hd": 1})
        data = resp.json()
        if data.get("code") == 0 and data.get("data"):
            video_url = data["data"].get("play") or data["data"].get("wmplay")
            if video_url:
                async with client.stream("GET", video_url) as v_resp:
                    if v_resp.status_code == 200:
                        with open(output_path, "wb") as f:
                            async for chunk in v_resp.aiter_bytes():
                                f.write(chunk)
                        return True
    return False


def is_telegram_url(url: str) -> bool:
    return bool(re.match(r"^https?://(?:t\.me|telegram\.me)/", url.strip(), re.IGNORECASE))


async def download_telegram_video(url: str, file_prefix: str, audio_only: bool = False):
    """Download video from a public Telegram post link (t.me/channel/123)."""
    if re.search(r"/(?:c|s/\w+)/", url, re.IGNORECASE) and "/c/" in url.lower():
        raise RuntimeError(
            "Private Telegram channel links (t.me/c/...) cannot be accessed by a bot. "
            "Only public channel/group post links (e.g., https://t.me/channel/123) are supported."
        )

    match = re.search(r"https?://(?:t\.me|telegram\.me)/(?:s/)?([A-Za-z0-9_]+)/(\d+)", url, re.IGNORECASE)
    if not match:
        raise RuntimeError("Invalid Telegram post link. Expected format: https://t.me/channel/123")

    username, post_id = match.group(1), match.group(2)
    embed_url = f"https://t.me/{username}/{post_id}?embed=1&single=1"
    headers = {"User-Agent": "Mozilla/5.0"}

    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True, headers=headers) as client:
        resp = await client.get(embed_url)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch Telegram post (HTTP {resp.status_code}).")

        video_urls = re.findall(r'<video[^>]+src=["\']([^"\']+)["\']', resp.text)
        if not video_urls:
            video_urls = re.findall(r'<source[^>]+src=["\']([^"\']+)["\']', resp.text)

        if not video_urls:
            raise RuntimeError(
                "No downloadable video found in this Telegram post. "
                "It may be a private channel, deleted post, or non-video post."
            )

        media_url = html.unescape(video_urls[0])
        mp4_path = f"{file_prefix}.mp4"
        async with client.stream("GET", media_url) as v_resp:
            if v_resp.status_code != 200:
                raise RuntimeError(f"Failed to download Telegram media (HTTP {v_resp.status_code}).")
            with open(mp4_path, "wb") as f:
                async for chunk in v_resp.aiter_bytes():
                    f.write(chunk)

    if audio_only:
        mp3_path = f"{file_prefix}.mp3"
        await asyncio.to_thread(
            subprocess.run,
            ["ffmpeg", "-y", "-i", mp4_path, "-vn", "-ab", "192k", mp3_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if os.path.exists(mp4_path):
            os.remove(mp4_path)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Welcome to Anylink Bot!**\n\n"
        "Send me any video link (YouTube, Telegram public posts, TikTok, Facebook, Instagram, Bilibili, X), "
        "and I will download and send it back to you!\n\n"
        "🍪 **YouTube Authentication / Bot Bypass:**\n"
        "If YouTube blocks downloads, you can export your cookies with the 'Get cookies.txt LOCALLY' extension "
        "and simply **send the `cookies.txt` file directly as a document to this chat**.\n\n"
        "Commands:\n"
        "• /status - Check if cookies are active\n"
        "• /clearcookies - Delete current cookies\n\n"
        "⚠️ Telegram bot upload limit is 50 MB.",
        parse_mode="Markdown",
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active_cookie = prepare_cookies_file()
    if active_cookie and os.path.exists(active_cookie):
        mtime = os.path.getmtime(active_cookie)
        dt = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        size = os.path.getsize(active_cookie)
        await update.message.reply_text(
            f"✅ **YouTube Cookies: ACTIVE**\n"
            f"• File size: {size} bytes\n"
            f"• Last updated: {dt}\n\n"
            f"If YouTube blocks links in the future, just send a new `cookies.txt` file here.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "⚠️ **YouTube Cookies: NOT INSTALLED**\n\n"
            "YouTube frequently blocks server IPs with: *'Sign in to confirm you're not a bot'*.\n\n"
            "👉 **How to install:**\n"
            "1. Install the extension **Get cookies.txt LOCALLY** in Chrome/Firefox.\n"
            "2. Open YouTube while logged in and click export `cookies.txt`.\n"
            "3. Send the `cookies.txt` file directly as a document to this chat!",
            parse_mode="Markdown",
        )


async def clear_cookies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for f in [COOKIE_RAW, COOKIE_NETSCAPE]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except OSError:
                pass
    await update.message.reply_text("🗑️ Cookies file has been removed.")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc:
        return

    file_name = (doc.file_name or "").lower()
    if not (file_name.endswith(".txt") or file_name.endswith(".json")):
        await update.message.reply_text("Please upload a .txt or .json cookies file (e.g., `cookies.txt`).")
        return

    status_msg = await update.message.reply_text("📥 Receiving cookie file...")

    try:
        telegram_file = await context.bot.get_file(doc.file_id)
        temp_dest = os.path.join(DOWNLOAD_DIR, f"incoming_{doc.file_name}")
        await telegram_file.download_to_drive(temp_dest)

        with open(temp_dest, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Check if content has some recognizable cookie elements
        if "youtube" not in content.lower() and "google" not in content.lower() and "# netscape" not in content.lower():
            if os.path.exists(temp_dest):
                os.remove(temp_dest)
            await status_msg.edit_text(
                "⚠️ This file doesn't appear to contain YouTube cookies. Please ensure you exported cookies for `youtube.com`."
            )
            return

        with open(COOKIE_RAW, "w", encoding="utf-8") as out:
            out.write(content)

        if os.path.exists(temp_dest):
            os.remove(temp_dest)

        converted = prepare_cookies_file()
        if converted and os.path.exists(converted):
            await status_msg.edit_text(
                "✅ **Cookies successfully installed!**\n\n"
                "YouTube downloads are now authenticated. Try sending a YouTube link now!",
                parse_mode="Markdown",
            )
        else:
            await status_msg.edit_text("⚠️ Received file, but could not parse cookies format properly.")

    except Exception as e:
        logger.error(f"Error handling cookie document: {e}")
        await status_msg.edit_text(f"❌ Failed to install cookies: {e}")


QUALITY_PRESETS = {
    "1080": {
        "label": "🎬 1080p",
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/bestvideo+bestaudio/best",
        "fallback_format": "96/95/94/93/18/best[height<=1080][protocol*=m3u8]/best[height<=1080]/best",
        "audio_only": False,
    },
    "720": {
        "label": "🎬 720p",
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/bestvideo+bestaudio/best",
        "fallback_format": "95/94/93/18/best[height<=720][protocol*=m3u8]/best[height<=720]/best",
        "audio_only": False,
    },
    "480": {
        "label": "📱 480p",
        "format": "bestvideo[height<=480]+bestaudio/best[height<=480]/bestvideo+bestaudio/best",
        "fallback_format": "94/93/18/best[height<=480][protocol*=m3u8]/best[height<=480]/best",
        "audio_only": False,
    },
    "360": {
        "label": "📱 360p",
        "format": "bestvideo[height<=360]+bestaudio/best[height<=360]/bestvideo+bestaudio/best",
        "fallback_format": "18/93/best[height<=360][protocol*=m3u8]/best[height<=360]/best",
        "audio_only": False,
    },
    "audio": {
        "label": "🎵 Audio (MP3)",
        "format": "bestaudio/best",
        "fallback_format": "140/251/bestaudio/best",
        "audio_only": True,
    },
}


def _yt_dlp_download(url: str, ydl_opts: dict):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


async def process_video_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("Please provide a valid URL starting with http:// or https://")
        return

    token = str(update.message.message_id)
    pending = context.user_data.setdefault("pending_urls", {})
    pending[token] = url

    keyboard = [
        [
            InlineKeyboardButton("🎬 1080p (Full HD)", callback_data=f"dl|1080|{token}"),
            InlineKeyboardButton("🎬 720p (HD)", callback_data=f"dl|720|{token}"),
        ],
        [
            InlineKeyboardButton("📱 480p (SD)", callback_data=f"dl|480|{token}"),
            InlineKeyboardButton("📱 360p (Small)", callback_data=f"dl|360|{token}"),
        ],
        [
            InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"dl|audio|{token}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{token}"),
        ],
    ]

    await update.message.reply_text(
        "👇 Select the quality / format you want to download:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        reply_to_message_id=update.message.message_id,
    )


async def handle_quality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = (query.data or "").split("|")
    pending = context.user_data.get("pending_urls", {})

    if parts[0] == "cancel":
        if len(parts) > 1:
            pending.pop(parts[1], None)
        await query.edit_message_text("❌ Download cancelled.")
        return

    if parts[0] != "dl" or len(parts) != 3:
        return

    quality_key, token = parts[1], parts[2]
    preset = QUALITY_PRESETS.get(quality_key)
    url = pending.pop(token, None)

    if not preset or not url:
        await query.edit_message_text("⚠️ This link expired (bot restarted or already used). Please send the link again.")
        return

    chat_id = query.message.chat_id
    message_id = query.message.message_id
    status_msg = query.message

    await status_msg.edit_text(f"⏳ Downloading ({preset['label']})...")

    file_prefix = os.path.join(DOWNLOAD_DIR, f"{chat_id}_{message_id}")
    output_template = f"{file_prefix}.%(ext)s"

    ydl_opts = {
        "outtmpl": output_template,
        "format": preset["format"],
        "quiet": True,
        "no_warnings": True,
        "js_runtimes": {"node": {"path": "/usr/bin/node"}},
        "extractor_args": {
            "youtubepot-bgutilhttp": {
                "base_url": ["http://127.0.0.1:4416"],
            },
        },
    }

    if preset["audio_only"]:
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
    else:
        ydl_opts["merge_output_format"] = "mp4"

    cookie_path = prepare_cookies_file()
    if cookie_path:
        ydl_opts["cookiefile"] = cookie_path
    else:
        ydl_opts["extractor_args"]["youtube"] = {
            "player_client": ["android", "ios", "mweb", "web"],
        }

    try:
        if is_telegram_url(url):
            await download_telegram_video(url, file_prefix, audio_only=preset["audio_only"])
        else:
            try:
                await asyncio.to_thread(_yt_dlp_download, url, ydl_opts)
            except Exception as ydl_err:
                err_str = str(ydl_err)
                fallback_path = f"{file_prefix}.mp4"
                if "tiktok.com" in url.lower() and not preset["audio_only"]:
                    logger.info("Triggering TikTok fallback...")
                    if not await download_tiktok_fallback(url, fallback_path):
                        raise ydl_err
                elif ("youtube.com" in url.lower() or "youtu.be" in url.lower()) and "403" in err_str:
                    logger.info("YouTube 403 on DASH format, retrying with HLS/progressive format...")
                    for f in glob.glob(f"{file_prefix}.*"):
                        try:
                            os.remove(f)
                        except OSError:
                            pass
                    retry_opts = dict(ydl_opts)
                    retry_opts["format"] = preset["fallback_format"]
                    await asyncio.to_thread(_yt_dlp_download, url, retry_opts)
                else:
                    raise ydl_err

        matching_files = glob.glob(f"{file_prefix}.*")
        if not matching_files:
            raise FileNotFoundError("Download failed.")

        downloaded_path = matching_files[0]
        size_mb = round(os.path.getsize(downloaded_path) / (1024 * 1024), 1)

        if os.path.getsize(downloaded_path) > (50 * 1024 * 1024):
            raise RuntimeError(
                f"File is too large ({size_mb} MB). Telegram bots limit uploads to 50 MB. "
                f"Try selecting a lower resolution (e.g., 480p or 360p)!"
            )

        await status_msg.edit_text("⬆️ Uploading to Telegram...")

        with open(downloaded_path, "rb") as media_file:
            if preset["audio_only"]:
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=media_file,
                    caption=f"Here is your audio! 🎵 ({preset['label']})",
                )
            else:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=media_file,
                    caption=f"Here is your video! 🎬 ({preset['label']})",
                    supports_streaming=True,
                )

        await status_msg.delete()

    except Exception as exc:
        err_msg = str(exc)
        logger.error(f"Error handling URL {url}: {err_msg}")

        if "Sign in to confirm you’re not a bot" in err_msg or "Sign in to confirm you're not a bot" in err_msg:
            if not prepare_cookies_file():
                await status_msg.edit_text(
                    "❌ **YouTube Bot Check Triggered**\n\n"
                    "YouTube blocked this download because the bot is hosted on a cloud server.\n\n"
                    "👉 **How to fix in 1 minute:**\n"
                    "1. Install the browser extension **Get cookies.txt LOCALLY** in Chrome/Firefox.\n"
                    "2. Open YouTube while logged in and click export `cookies.txt`.\n"
                    "3. **Send the `cookies.txt` file directly as a document to this bot chat**.\n\n"
                    "The bot will automatically install it and authenticate your downloads!",
                    parse_mode="Markdown",
                )
            else:
                await status_msg.edit_text(
                    "❌ **YouTube Bot Check Triggered**\n\n"
                    "Your saved YouTube cookies appear to have expired.\n\n"
                    "Please export a fresh `cookies.txt` file from your browser and send it to this bot chat.",
                    parse_mode="Markdown",
                )
        else:
            await status_msg.edit_text(f"❌ Failed: {err_msg[:250]}")

    finally:
        for f in glob.glob(f"{file_prefix}.*"):
            try:
                os.remove(f)
            except OSError:
                pass


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("cookies", status_command))
    app.add_handler(CommandHandler("clearcookies", clear_cookies_command))
    app.add_handler(CallbackQueryHandler(handle_quality_callback))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_video_link))

    print("Bot is up and listening for links and cookies...")
    app.run_polling()


if __name__ == "__main__":
    main()
