import calendar
import csv
import datetime
import io
import json
import logging
import math
import os
import re
import threading
import time
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
import pytz
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==============================================================================
# CONFIGURATION
# ==============================================================================
BOT_TOKEN = "7423618627:AAEXiEry62CYCL0sYoqQmNbOaBttYOIChGg"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1N7cG4N5bhO0tlGAymtFUKH7EkmO2r453dt8EaS6HP7U/export?format=csv"
DEFAULT_ADMIN_ID = 1499235921
TIMEZONE = pytz.timezone("Asia/Colombo")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SUBSCRIBERS_FILE = os.path.join(BASE_DIR, "subscribers.json")
LOG_FILE = os.path.join(BASE_DIR, "birthday_bot.log")
BROADCAST_RECORD_FILE = os.path.join(BASE_DIR, "last_broadcast.txt")

DAILY_CHECK_HOUR = 6
DAILY_CHECK_MINUTE = 0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

SINHALA_TO_ENGLISH_MAP = {
    "දැරණියගල": "Deraniyagala",
    "සශිකා": "Sashika",
    "මේධානි": "Medhani",
    "රුවන්": "Ruwan",
    "විශාකා": "Vishaka",
    "රුවන්ති": "Ruwanthi",
    "ඉෂාන්": "Ishan",
    "චන්දිමා": "Chandima",
    "ලක්මාලි": "Lakmali",
    "සමීර": "Sameera",
    "කෝකිල": "Kokila",
    "නලීන්": "Nalin",
    "ලහිරු": "Lahiru",
    "සංජිවනි": "Sanjeewani",
    "අනුෂා": "Anusha",
    "ඉරේෂා": "Iresha",
    "ප්‍රැන්සිස්": "Francis",
    "එදිරිසිංහ": "Edirisinghe",
    "ප්‍රභාත්": "Prabath",
    "නිපුනි": "Nipuni",
    "අසෝකා": "Asoka",
    "නිලංගනී": "Nilangani",
    "අනුරුද්ධ": "Anuruddha",
    "වත්සලා": "Vathsala",
    "ලසන්ත": "Lasantha",
    "කිර්ති": "Keerthi",
    "කපිල": "Kapila",
    "අසන්තා": "Asantha",
    "චන්දන": "Chandana",
    "කුමුදිනි": "Kumudini",
    "සුභද්‍රා": "Subhadra",
    "ඉනෝකා": "Inoka",
    "ගයනි": "Gayani",
    "දංගල්ල": "Dangalla",
    "චරිතා": "Charitha",
    "රාජපක්ෂ": "Rajapaksha",
    "මහේෂා": "Mahesha",
    "සම්පත්": "Sampath",
    "තුලන්දි": "Thulandi",
    "සුරංගනී": "Surangani",
    "සුභසිංහ": "Subhasinghe",
    "නිරංජලා": "Niranjala",
    "මිහිරි": "Mihiri",
    "සෝමරත්න": "Somarathne",
    "චින්තා": "Chintha",
    "කුමාරි": "Kumari",
    "නිමේෂිකා": "Nimeshika",
    "සමන්ලතා": "Samanlatha",
    "ධම්මි": "Dhammi",
    "මිලානි": "Milani",
    "පමුදිකා": "Pamudika",
    "යසස්සි": "Yasassi",
    "මුදිතා": "Muditha",
    "වජිර": "Vajira",
    "චූලාංගනී": "Chulangani",
    "සිතුමිණි": "Sithumini",
    "අනුත්තරා": "Anuththara",
    "දිලානි": "Dilani",
    "වසුන්දරා": "Vasundara",
    "අතුල": "Athula",
    "චතුරී": "Chathuri",
    "නිමල්": "Nimal",
    "සමරසිංහ": "Samarasinghe",
    "මොරින්": "Morin",
    "දයානි": "Dayani",
    "මධුරාණි": "Madhurani",
    "ගනේපල්ල": "Ganepalla",
    "ශයාමා": "Shayama",
    "සඳරේණු": "Sandarenu",
    "අනුජා": "Anuja",
    "දිල්හානි": "Dilhani",
    "කසුනිකා": "Kasunika",
    "බාලසුරිය": "Balasuriya",
    "බන්දුමතී": "Bandumathi",
    "විදර්ශන": "Vidarshana",
    "සදමාලි": "Sadamali",
    "මාදවී": "Madhavi",
    "මාධවී": "Madhavi",
    "ආනන්ද": "Ananda",
    "ඕෂදී": "Oshadi",
    "ඉන්දික": "Indika",
    "සේරම්": "Seram",
    "ජිනාලි": "Jinali",
    "මාලිකා": "Malika",
    "ශ්‍රියානි": "Shriyani",
    "රණතුංග ආරච්චිලාගේ පුන්‍යා දමයන්ති": "Punya Damayanthi",
    "රණතුංග ආරච්චිලාගේ පුන්යා දමයන්ති": "Punya Damayanthi",
}

VOWELS_MAP = {
    '\u0D85': 'A', '\u0D86': 'Aa', '\u0D87': 'Ae', '\u0D88': 'Aae',
    '\u0D89': 'I', '\u0D8A': 'Ee', '\u0D8B': 'U', '\u0D8C': 'Oo',
    '\u0D8F': 'E', '\u0D90': 'Ee', '\u0D91': 'E', '\u0D92': 'Ee',
    '\u0D93': 'Ai', '\u0D94': 'O', '\u0D95': 'Oo', '\u0D96': 'Au'
}

CONSONANTS_MAP = {
    '\u0D9A': 'k', '\u0D9B': 'kh', '\u0D9C': 'g', '\u0D9D': 'gh', '\u0D9E': 'ng', '\u0D9F': 'ng',
    '\u0DA0': 'ch', '\u0DA1': 'chh', '\u0DA2': 'j', '\u0DA3': 'jh', '\u0DA4': 'ny', '\u0DA5': 'jny', '\u0DA6': 'ndj',
    '\u0DA7': 't', '\u0DA8': 'th', '\u0DA9': 'd', '\u0DAA': 'dh', '\u0DAB': 'n', '\u0DAC': 'nd',
    '\u0DAD': 'th', '\u0DAE': 'th', '\u0DAF': 'd', '\u0DB0': 'dh', '\u0DB1': 'n', '\u0DB3': 'nd',
    '\u0DB4': 'p', '\u0DB5': 'ph', '\u0DB6': 'b', '\u0DB7': 'bh', '\u0DB8': 'm', '\u0DB9': 'mb',
    '\u0DBA': 'y', '\u0DBB': 'r', '\u0DBD': 'l', '\u0DBF': 'v',
    '\u0DC0': 'v', '\u0DC1': 'sh', '\u0DC2': 'sh', '\u0DC3': 's', '\u0DC4': 'h', '\u0DC5': 'l', '\u0DC6': 'f'
}

SIGNS_MAP = {
    '\u0DCA': '',       # Virama (al)
    '\u0DCF': 'a',      # a-karanaya
    '\u0DD0': 'ae',     # ae
    '\u0DD1': 'ae',     # aae
    '\u0DD2': 'i',      # i
    '\u0DD3': 'ee',     # ee
    '\u0DD4': 'u',      # u
    '\u0DD6': 'oo',     # oo
    '\u0DD8': 'ru',     # ru
    '\u0DD9': 'e',      # kombuva
    '\u0DDA': 'e',      # kombuva + hal
    '\u0DDB': 'ai',     # kombu deka
    '\u0DDC': 'o',      # kombuva + a-karanaya
    '\u0DDD': 'o',      # kombuva + hal + a-karanaya
    '\u0DDE': 'au',     # kombuva + gayanukitta
    '\u0DF2': 'o',
    '\u0DF3': 'o',
    '\u0D82': 'ng',     # anusvaraya
    '\u0D83': 'h'       # visargaya
}

def transliterate_sinhala(text: str) -> str:
    res = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in VOWELS_MAP:
            res.append(VOWELS_MAP[c])
            i += 1
        elif c in CONSONANTS_MAP:
            cons = CONSONANTS_MAP[c]
            if i + 1 < n and text[i+1] in SIGNS_MAP:
                sign = text[i+1]
                vowel_part = SIGNS_MAP[sign]
                res.append(cons + vowel_part)
                i += 2
            else:
                res.append(cons + 'a')
                i += 1
        elif c in SIGNS_MAP:
            res.append(SIGNS_MAP[c])
            i += 1
        else:
            res.append(c)
            i += 1
    return ''.join(res).strip().title()

# ==============================================================================
# DATA PERSISTENCE & SUBSCRIBERS
# ==============================================================================
def load_subscribers() -> List[int]:
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            logging.error(f"Error reading subscribers: {e}")
    subs = [DEFAULT_ADMIN_ID]
    save_subscribers(subs)
    return subs

def save_subscribers(subs: List[int]):
    try:
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(set(subs)), f, indent=2)
    except Exception as e:
        logging.error(f"Error saving subscribers: {e}")

subscribers = load_subscribers()

# ==============================================================================
# SHEET DATA FETCHER & PARSER
# ==============================================================================
class BirthdayPerson:
    def __init__(self, no: str, name_si: str, name_en: str, year: int, month: int, day: int, phone: str):
        self.no = no
        self.name_si = name_si.strip()
        self.raw_name_en = name_en.strip()
        self.year = year
        self.month = month
        self.day = day
        self.phone = phone.strip()
        self.clean_english_name = self._resolve_english_name()

    def _resolve_english_name(self) -> str:
        if self.raw_name_en:
            return self.raw_name_en.title()
        name_clean = self.name_si.strip()
        if name_clean in SINHALA_TO_ENGLISH_MAP:
            return SINHALA_TO_ENGLISH_MAP[name_clean]
        for k, v in SINHALA_TO_ENGLISH_MAP.items():
            if k.strip() == name_clean:
                return v
        if re.search(r"[\u0D80-\u0DFF]", name_clean):
            trans = transliterate_sinhala(name_clean)
            if trans:
                return trans
        return name_clean.title()

    @property
    def display_name(self) -> str:
        return self.clean_english_name

    @property
    def month_name(self) -> str:
        return calendar.month_name[self.month]

    @property
    def whatsapp_url(self) -> Optional[str]:
        cleaned = re.sub(r"[^\d]", "", self.phone)
        if not cleaned:
            return None
        if cleaned.startswith("0") and len(cleaned) == 10:
            cleaned = "94" + cleaned[1:]
        elif len(cleaned) == 9:
            cleaned = "94" + cleaned
        return f"https://wa.me/{cleaned}"

def parse_date_string(date_str: str) -> Optional[Tuple[int, int, int]]:
    date_str = date_str.strip().rstrip(".")
    m1 = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$", date_str)
    if m1:
        return int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
    m2 = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$", date_str)
    if m2:
        p1, p2, year = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        if p1 > 12:
            return year, p2, p1
        return year, p1, p2
    return None

cached_people: List[BirthdayPerson] = []
cached_time: float = 0

def fetch_sheet_people(force_refresh: bool = False) -> List[BirthdayPerson]:
    global cached_people, cached_time
    if not force_refresh and cached_people and (time.time() - cached_time < 3600):
        return cached_people

    logging.info("Fetching updated birthdays from Google Sheets...")
    try:
        resp = requests.get(SHEET_URL, timeout=15)
        resp.encoding = "utf-8"
        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)

        people = []
        for i, row in enumerate(rows[1:], start=2):
            if len(row) < 3 or not row[1].strip():
                continue
            no = row[0].strip() if len(row) > 0 else str(i)
            name_si = row[1].strip() if len(row) > 1 else ""
            bday_raw = row[2].strip() if len(row) > 2 else ""
            phone = row[3].strip() if len(row) > 3 else ""
            name_en = row[4].strip() if len(row) > 4 else ""

            dt = parse_date_string(bday_raw)
            if dt:
                people.append(BirthdayPerson(no, name_si, name_en, dt[0], dt[1], dt[2], phone))
            else:
                logging.warning(f"Row {i} unparsed date: {name_si} -> '{bday_raw}'")

        cached_people = people
        cached_time = time.time()
        logging.info(f"Loaded {len(people)} contacts from Sheet.")
        return people
    except Exception as e:
        logging.error(f"Error fetching Google Sheet: {e}")
        return cached_people

# ==============================================================================
# CARD GENERATOR (HIGH-IMPACT "HAPPY BIRTHDAY" BANNER)
# ==============================================================================
def draw_star(draw: ImageDraw.ImageDraw, x: float, y: float, size: float, fill: str):
    points = []
    for i in range(10):
        r = size if i % 2 == 0 else size / 2.2
        angle = i * math.pi / 5 - math.pi / 2
        points.append((x + r * math.cos(angle), y + r * math.sin(angle)))
    draw.polygon(points, fill=fill)

def generate_birthday_card(person: BirthdayPerson) -> io.BytesIO:
    width, height = 1080, 1080
    img = Image.new("RGB", (width, height), "#0B0D1B")
    draw = ImageDraw.Draw(img)

    for y in range(height):
        ratio = y / height
        r = int(11 + 22 * ratio)
        g = int(13 + 15 * ratio)
        b = int(27 + 60 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    draw.rounded_rectangle([35, 35, width-35, height-35], radius=38, outline="#FFD700", width=4)
    draw.rounded_rectangle([50, 50, width-50, height-50], radius=28, outline="#997A15", width=1)

    colors = ["#FFD700", "#FF6B6B", "#4ECDC4", "#FFE66D", "#FF9F43", "#A29BFE"]
    for i in range(50):
        cx = (i * 33 + 51) % (width - 140) + 70
        cy = (i * 61 + 79) % (height - 140) + 70
        if 130 < cy < 270 or 360 < cy < 670:
            continue
        c = colors[i % len(colors)]
        if i % 3 == 0:
            draw_star(draw, cx, cy, 11, fill=c)
        else:
            draw.ellipse([cx-4, cy-4, cx+4, cy+4], fill=c)

    font_hb_huge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 66)
    font_sub_teacher = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
    font_name = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 68)
    font_wish = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
    font_date = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)

    hb_box_w = 880
    hb_box_h = 135
    hbx1 = (width - hb_box_w) / 2
    hby1 = 115

    draw.rounded_rectangle([hbx1, hby1, hbx1 + hb_box_w, hby1 + hb_box_h], radius=24, fill="#1B1F3D", outline="#FFD700", width=3)
    draw.rounded_rectangle([hbx1 + 8, hby1 + 8, hbx1 + hb_box_w - 8, hby1 + hb_box_h - 8], radius=16, outline="#6B5914", width=1)

    draw_star(draw, hbx1 + 55, hby1 + hb_box_h/2, 22, fill="#FFD700")
    draw_star(draw, hbx1 + hb_box_w - 55, hby1 + hb_box_h/2, 22, fill="#FFD700")

    hb_text = "HAPPY BIRTHDAY"
    draw.text((width/2 + 2, hby1 + hb_box_h/2 + 2), hb_text, fill="#7A5A00", font=font_hb_huge, anchor="mm")
    draw.text((width/2, hby1 + hb_box_h/2), hb_text, fill="#FFDF00", font=font_hb_huge, anchor="mm")

    draw.text((width/2, 285), "★  TO OUR DEAR TEACHER  ★", fill="#38BDF8", font=font_sub_teacher, anchor="mm")

    np_w = 840
    np_h = 240
    npx1 = (width - np_w) / 2
    npy1 = 360

    draw.rounded_rectangle([npx1, npy1, npx1 + np_w, npy1 + np_h], radius=26, fill="#161933", outline="#FFD700", width=2)
    draw.rounded_rectangle([npx1 + 10, npy1 + 10, npx1 + np_w - 10, npy1 + np_h - 10], radius=18, outline="#303763", width=1)

    clean_name = person.clean_english_name
    name_size = 68
    while name_size > 26:
        font_name = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", name_size)
        bbox = draw.textbbox((0, 0), clean_name, font=font_name)
        if (bbox[2] - bbox[0]) <= (np_w - 60):
            break
        name_size -= 4
    draw.text((width/2, npy1 + np_h/2), clean_name, fill="#FFFFFF", font=font_name, anchor="mm")

    wish_text = "Thank you for your guidance, wisdom, and dedication.\nWishing you immense happiness, peace, and great success\nin all your journeys ahead!"
    draw.text((width/2, 735), wish_text, fill="#CBD5E1", font=font_wish, anchor="mm", align="center")

    date_badge_w = 460
    date_badge_h = 68
    bx1 = (width - date_badge_w) / 2
    by1 = 915

    draw.rounded_rectangle([bx1, by1, bx1 + date_badge_w, by1 + date_badge_h], radius=34, fill="#23284A", outline="#FFD700", width=2)
    full_date_str = f"★  {person.day:02d} {person.month_name}  ★"
    draw.text((width/2, by1 + date_badge_h/2), full_date_str, fill="#FFD700", font=font_date, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    return buf

# ==============================================================================
# BROADCAST & NOTIFICATIONS
# ==============================================================================
def broadcast_birthday(person: BirthdayPerson, target_chats: Optional[List[int]] = None):
    targets = target_chats if target_chats is not None else subscribers
    if not targets:
        return

    caption = f"HAPPY BIRTHDAY to {person.clean_english_name} Teacher! ✨ Wishing our dear teacher immense happiness and success! 🌸"

    reply_markup = None
    if person.whatsapp_url:
        reply_markup = InlineKeyboardMarkup()
        reply_markup.add(InlineKeyboardButton("📱 Wish on WhatsApp", url=person.whatsapp_url))

    for cid in targets:
        try:
            card_img = generate_birthday_card(person)
            bot.send_photo(cid, card_img, caption=caption, reply_markup=reply_markup)
            logging.info(f"Sent birthday card for Teacher {person.clean_english_name} to chat {cid}")
        except Exception as e:
            logging.error(f"Failed to send card to {cid}: {e}")

def check_and_broadcast_today(force: bool = False):
    now = datetime.datetime.now(TIMEZONE)
    today = now.date()

    if os.path.exists(BROADCAST_RECORD_FILE):
        try:
            with open(BROADCAST_RECORD_FILE, "r", encoding="utf-8") as f:
                saved = f.read().strip()
                if saved == str(today) and not force:
                    logging.info(f"Today's birthdays already broadcasted ({today}). Skipping.")
                    return
        except Exception:
            pass

    people = fetch_sheet_people(force_refresh=True)
    today_matches = [p for p in people if p.month == now.month and p.day == now.day]

    if today_matches:
        logging.info(f"Found {len(today_matches)} teacher birthday(s) today ({today})!")
        for person in today_matches:
            broadcast_birthday(person)
    else:
        logging.info(f"No birthdays today ({today}).")

    try:
        with open(BROADCAST_RECORD_FILE, "w", encoding="utf-8") as f:
            f.write(str(today))
    except Exception as e:
        logging.error(f"Error saving broadcast record: {e}")

# ==============================================================================
# BOT COMMAND HANDLERS
# ==============================================================================
@bot.message_handler(commands=["start", "help"])
def handle_start(message):
    help_text = (
        "🎂 *Teachers Birthday Reminder Bot* 🎈\n\n"
        "Here are the available commands:\n"
        "• `/today` — Check if any teacher has a birthday today\n"
        "• `/upcoming` — View teacher birthdays in the next 14 days\n"
        "• `/card <name>` — Generate a card for any teacher\n"
        "• `/subscribe` — Receive daily birthday notifications in this chat/group at 06:00 AM\n"
        "• `/unsubscribe` — Stop notifications in this chat\n"
        "• `/chatid` — Show the current chat ID\n"
        "• `/reload` — Refresh the list from Google Sheets\n"
    )
    bot.reply_to(message, help_text)

@bot.message_handler(commands=["today"])
def handle_today(message):
    now = datetime.datetime.now(TIMEZONE)
    people = fetch_sheet_people()
    today_matches = [p for p in people if p.month == now.month and p.day == now.day]

    if not today_matches:
        bot.reply_to(message, f"🎈 No teacher birthdays today ({now.strftime('%B %d')}).")
        return

    bot.reply_to(message, f"🎉 *{len(today_matches)} Birthday(s) Today!* Sending card(s)...")
    for person in today_matches:
        broadcast_birthday(person, target_chats=[message.chat.id])

@bot.message_handler(commands=["upcoming"])
def handle_upcoming(message):
    now = datetime.datetime.now(TIMEZONE)
    today = now.date()
    people = fetch_sheet_people()

    upcoming_list = []
    for p in people:
        try:
            bday_this_year = datetime.date(today.year, p.month, p.day)
        except ValueError:
            bday_this_year = datetime.date(today.year, 2, 28)

        if bday_this_year < today:
            bday_next = datetime.date(today.year + 1, p.month, p.day)
        else:
            bday_next = bday_this_year

        days_left = (bday_next - today).days
        if 0 < days_left <= 14:
            upcoming_list.append((days_left, bday_next, p))

    upcoming_list.sort(key=lambda x: x[0])

    if not upcoming_list:
        bot.reply_to(message, "📅 No teacher birthdays coming up in the next 14 days.")
        return

    lines = ["🎁 *Upcoming Teacher Birthdays (Next 14 Days):*\n"]
    for days, bdate, p in upcoming_list:
        day_str = f"in {days} day" if days == 1 else f"in {days} days"
        lines.append(f"• *Teacher {p.clean_english_name}* — {bdate.strftime('%d %b')} ({day_str})")
        if p.whatsapp_url:
            lines.append(f"   📱 [WhatsApp]({p.whatsapp_url})")

    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=["card"])
def handle_card(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "Usage: `/card <name>` (e.g., `/card vishaka` or `/card ruwan`)")
        return

    query = args[1].strip().lower()
    people = fetch_sheet_people()
    matched = None
    for p in people:
        if query in p.clean_english_name.lower() or query in p.name_si.lower() or query in p.raw_name_en.lower():
            matched = p
            break

    if not matched:
        bot.reply_to(message, f"❌ No teacher found matching '*{args[1]}*'.")
        return

    bot.reply_to(message, f"🎨 Generating card for *Teacher {matched.clean_english_name}*...")
    broadcast_birthday(matched, target_chats=[message.chat.id])

@bot.message_handler(commands=["subscribe"])
def handle_subscribe(message):
    cid = message.chat.id
    if cid not in subscribers:
        subscribers.append(cid)
        save_subscribers(subscribers)
        bot.reply_to(message, "✅ Subscribed! Daily birthday reminders will be posted here at 06:00 AM.")
    else:
        bot.reply_to(message, "ℹ️ This chat is already subscribed.")

@bot.message_handler(commands=["unsubscribe"])
def handle_unsubscribe(message):
    cid = message.chat.id
    if cid in subscribers:
        subscribers.remove(cid)
        save_subscribers(subscribers)
        bot.reply_to(message, "👋 Unsubscribed. Daily reminders removed for this chat.")
    else:
        bot.reply_to(message, "ℹ️ This chat is not currently subscribed.")

@bot.message_handler(commands=["chatid"])
def handle_chatid(message):
    bot.reply_to(message, f"📍 Current Chat ID: `{message.chat.id}`\nTitle: *{message.chat.title or message.chat.first_name}*")

@bot.message_handler(commands=["reload"])
def handle_reload(message):
    people = fetch_sheet_people(force_refresh=True)
    bot.reply_to(message, f"🔄 Reloaded! Total {len(people)} teacher contacts loaded from Google Sheet.")

# ==============================================================================
# BACKGROUND SCHEDULER
# ==============================================================================
def scheduler_loop():
    logging.info("Background daily scheduler started.")
    while True:
        try:
            now = datetime.datetime.now(TIMEZONE)
            if now.hour == DAILY_CHECK_HOUR and now.minute == DAILY_CHECK_MINUTE:
                logging.info(f"Scheduled check triggered at {now.strftime('%Y-%m-%d %H:%M:%S')}")
                check_and_broadcast_today()
                time.sleep(65)
        except Exception as e:
            logging.error(f"Scheduler exception: {e}")
        time.sleep(25)

# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
if __name__ == "__main__":
    fetch_sheet_people(force_refresh=True)

    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()

    logging.info("Starting Telegram Bot long-polling...")
    bot.infinity_polling(timeout=20, long_polling_timeout=15)
