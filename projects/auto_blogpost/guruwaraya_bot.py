#!/usr/bin/env python3
"""
Guruwaraya.lk Education & Teacher Post Monitor & Publisher
- Directly scans https://www.guruwaraya.lk/ from Oracle Cloud VM (No mobile bridge needed)
- Strictly filters for Education & Teacher posts (Ignores general non-education job vacancies)
- Sends daily selection list to User via Telegram at 6:00 PM with one-tap /publish buttons
- Formats approved posts with 1600x1066 head banner, #simple_table, and official PDF download links
- Publishes to LKUni.com and broadcasts to @differentpaths
"""

import os
import sys
import re
import json
import time
import datetime
import logging
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from auto_blogger import (
    OFFICIAL_BLOG_ID,
    TEST_BLOG_ID,
    upload_to_google_drive,
    TEMPLATE_IMG,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_IDS,
    fetch_recent_blogger_posts,
    find_blogger_match,
    fetch_recent_blogger_titles,
    is_duplicate_on_blogger
)
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CACHE_FILE = os.path.join(BASE_DIR, "guruwaraya_posted_cache.json")
CANDIDATES_FILE = os.path.join(BASE_DIR, "guruwaraya_candidates.json")
FEED_URL = "https://www.guruwaraya.lk/feeds/posts/default?alt=json&max-results=35"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [GURU-BOT] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def load_cache() -> list:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_cache(cache: list):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

def load_candidates() -> list:
    if os.path.exists(CANDIDATES_FILE):
        try:
            with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_candidates(candidates: list):
    with open(CANDIDATES_FILE, "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2)

# ==============================================================================
# EDUCATION & TEACHER FILTERING LOGIC
# ==============================================================================
def is_education_or_teacher_post(title: str, categories: list) -> bool:
    """Strictly checks if a post is education/teacher-related and excludes general jobs."""
    t_low = title.lower()
    c_low = " ".join([c.lower() for c in categories])
    combined = f"{t_low} {c_low}"

    # 1. Immediate exclusions for general non-education job vacancies
    non_edu_keywords = [
        "cricket", "transport", "excise", "pucsl", "consumer consultative", 
        "security officer", "driver", "quantity surveyor", "computer operator",
        "scurp", "administration & finance", "procurement assistant",
        "additional project director", "medical officer", "director / public relations",
        "court clerk", "judicial service", "grama niladhari", "court", "police"
    ]
    if any(k in t_low for k in non_edu_keywords):
        return False

    # 2. Education / Teacher / Examination / Circular keywords
    edu_keywords = [
        "teacher", "teaching", "education", "school", "principal", "b.ed",
        "ncoe", "vidyapeeta", "sleas", "slts", "slps", "exam", "doenets",
        "results", "circular", "reforms", "stationery", "scholarship",
        "university", "degree", "diploma", "postgraduate", "master",
        "course", "intake", "student", "shishyadhara", "ncpa", "child protection",
        "guidelines", "academic", "lecturer"
    ]
    return any(k in combined for k in edu_keywords)

def detect_institution(title: str, categories: list) -> str:
    """Infers appropriate institution heading for the banner."""
    combined = f"{title} {' '.join(categories)}".lower()

    # Education Ministry & Commission bodies
    if "examination" in combined or "doenets" in combined or "exam department" in combined:
        return "Department of Examinations, Sri Lanka"
    if "principals service" in combined or "slps" in combined or "principal vacancy" in combined or "school principal" in combined:
        return "Ministry of Education – Principals Service"
    if "teacher recruitment" in combined or "teachers service" in combined or "slts" in combined or "b.ed" in combined or "teaching" in combined:
        return "Ministry of Education – Teachers Service"
    if "ugc" in combined or "university grants commission" in combined:
        return "University Grants Commission (UGC) Sri Lanka"

    # Sri Lankan Universities
    if "rajarata" in combined or re.search(r'\brusl\b', combined):
        return "Rajarata University of Sri Lanka"
    if "peradeniya" in combined or re.search(r'\buop\b', combined) or "cdce" in combined:
        return "University of Peradeniya"
    if "colombo" in combined or re.search(r'\buoc\b', combined) or "uciars" in combined or "ucsc" in combined:
        return "University of Colombo"
    if "kelaniya" in combined or re.search(r'\buok\b', combined) or "pgiar" in combined:
        return "University of Kelaniya"
    if "moratuwa" in combined or re.search(r'\buom\b', combined) or "itum" in combined:
        return "University of Moratuwa"
    if "jayewardenepura" in combined or re.search(r'\busj\b', combined):
        return "University of Sri Jayewardenepura"
    if "wayamba" in combined or re.search(r'\bwusl\b', combined):
        return "Wayamba University of Sri Lanka"
    if "ruhuna" in combined or re.search(r'\buor\b', combined):
        return "University of Ruhuna"
    if "university of jaffna" in combined or "jaffna university" in combined or re.search(r'\buoj\b', combined):
        return "University of Jaffna"
    if "eastern university" in combined or re.search(r'\beusl\b', combined):
        return "Eastern University, Sri Lanka"
    if "south eastern" in combined or re.search(r'\bseusl\b', combined):
        return "South Eastern University of Sri Lanka"
    if "sabaragamuwa university" in combined or re.search(r'\bsusl\b', combined):
        return "Sabaragamuwa University of Sri Lanka"
    if "uva wellassa" in combined or re.search(r'\buwu\b', combined):
        return "Uva Wellassa University"
    if "open university" in combined or re.search(r'\bousl\b', combined):
        return "The Open University of Sri Lanka (OUSL)"
    if "ocean university" in combined or re.search(r'\bocu\b', combined):
        return "Ocean University of Sri Lanka (OCU)"
    if "buddhist & pali" in combined or "buddhist and pali" in combined or re.search(r'\bbpu\b', combined):
        return "Buddhist and Pali University of Sri Lanka (BPU)"
    if "biksu" in combined or re.search(r'\bbuss\b', combined):
        return "Bhiksu University of Sri Lanka"
    if "kotelawala" in combined or re.search(r'\bkdu\b', combined):
        return "General Sir John Kotelawala Defence University (KDU)"
    if "sliate" in combined or re.search(r'\bati\b', combined):
        return "Sri Lanka Institute of Advanced Technological Education (SLIATE)"
    if "national institute of education" in combined or re.search(r'\bnie\b', combined):
        return "National Institute of Education (NIE)"

    # Provinces and departments
    if "sabaragamuwa" in combined and "province" in combined:
        return "Sabaragamuwa Provincial Department of Education"
    if "ncpa" in combined or "child protection" in combined:
        return "National Child Protection Authority (NCPA)"
    if "ministry of health" in combined:
        return "Ministry of Health, Sri Lanka"
    if "reforms" in combined or "shishyadhara" in combined or "stationery" in combined or "ministry of education" in combined or re.search(r'\bmoe\b', combined):
        return "Ministry of Education, Sri Lanka"

    return "Department of Education, Sri Lanka"

# ==============================================================================
# EXPIRY & SUMMARY EXTRACTION LOGIC
# ==============================================================================
MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12
}

def check_expiry(text: str) -> tuple:
    """Detects closing date and determines whether the application period has already passed."""
    today = datetime.date.today()
    # 1. 'apply before DD Month' or 'closing date: DD Month'
    m = re.search(r'(apply\s+(?:online\s+)?before|apply\s+by|closing\s+date[:\s]*)\s+(\d{1,2})\s+([a-zA-Z]+)(?:\s+(\d{4}))?', text, re.I)
    if m:
        action = m.group(1).lower()
        d = int(m.group(2))
        mth_name = m.group(3).lower()
        mth = MONTH_MAP.get(mth_name)
        if mth:
            y = int(m.group(4)) if m.group(4) else today.year
            try:
                c_date = datetime.date(y, mth, d)
                date_str = c_date.strftime("%d %B %Y")
                if "before" in action and c_date <= today:
                    return True, date_str
                if c_date < today:
                    return True, date_str
                return False, date_str
            except Exception:
                pass

    # 2. Sinhala or numeric date: 2026.11.02, 2026-11-02
    m_num = re.search(r'(?:closing|deadline|අවසන් දිනය)[^\d]*(\d{4})[./-](\d{1,2})[./-](\d{1,2})', text, re.I)
    if m_num:
        y, m, d = int(m_num.group(1)), int(m_num.group(2)), int(m_num.group(3))
        try:
            c_date = datetime.date(y, m, d)
            date_str = c_date.strftime("%d %B %Y")
            return c_date < today, date_str
        except Exception:
            pass

    return False, None

def get_point_summary(soup: BeautifulSoup) -> list:
    """Extracts 1-2 clean descriptive bullet points from post body."""
    points = []
    elements = soup.find_all(["p", "li", "td"])
    for el in elements:
        t = el.get_text(" ", strip=True)
        t = re.sub(r'-[a-zA-Z]{3,5}-\s*', '', t).strip()
        # Must be mostly English (ASCII)
        non_ascii = len(re.findall(r'[^\x00-\x7F]', t))
        if non_ascii > 5:
            continue
        low = t.lower()
        if any(skip in low for skip in [
            "whatsapp", "telegram", "guruwaraya", "closing date", "apply before", 
            "visit the official", "information based", "read the complete", 
            "all rights reserved", "advertisement", "source:"
        ]):
            continue
        t = re.sub(r'\s+', ' ', t).strip()
        if 35 <= len(t) <= 180 and t not in points:
            t = re.sub(r'^[•\-\*\s]+', '', t).strip()
            points.append(t)
            if len(points) == 2:
                break
    return points

# ==============================================================================
# SCAN GURUWARAYA FEED & GET CANDIDATES
# ==============================================================================
def fetch_candidate_posts(limit: int = 35, only_today: bool = True) -> list:
    """Scrapes guruwaraya.lk feed and returns unposted, unexpired education/teacher candidate posts."""
    try:
        res = requests.get(FEED_URL, headers=HEADERS, timeout=15).json()
        entries = res.get("feed", {}).get("entry", [])
    except Exception as e:
        logging.error(f"Error fetching Guruwaraya feed: {e}")
        return []

    cache = set(load_cache())
    blogger_posts = fetch_recent_blogger_posts(blog_id=OFFICIAL_BLOG_ID, max_results=60)
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    candidates = []
    for e in entries:
        title = e.get("title", {}).get("$t", "").strip()
        cats = [c.get("term") for c in e.get("category", [])]
        links = [l.get("href") for l in e.get("link", []) if l.get("rel") == "alternate"]
        post_url = links[0] if links else ""
        pub = e.get("published", {}).get("$t", "")
        post_date = pub[:10]

        if not title or not post_url:
            continue

        # Filter strictly for posts published today if only_today is True
        if only_today and post_date != today_str:
            continue

        if not is_education_or_teacher_post(title, cats):
            continue

        # Check if already posted on LKUni strictly via live Blogger API
        is_dup, matched_title, matched_url = find_blogger_match(title, blogger_posts)
        is_posted = bool(is_dup and matched_url)

        content_html = e.get("content", {}).get("$t", "") or e.get("summary", {}).get("$t", "")
        soup = BeautifulSoup(content_html, "html.parser")
        full_text = f"{title} {soup.get_text(' ', strip=True)}"

        # Skip expired posts whose closing date has passed
        is_expired, closing_date = check_expiry(full_text)
        if is_expired:
            logging.info(f"Skipping expired post ({closing_date}): {title}")
            continue

        points = get_point_summary(soup)
        inst = detect_institution(title, cats)
        candidates.append({
            "title": title,
            "url": post_url,
            "categories": cats,
            "institution": inst,
            "closing_date": closing_date,
            "published_date": post_date,
            "summary_points": points,
            "is_already_posted": is_posted,
            "matched_url": matched_url,
            "matched_title": matched_title
        })

    logging.info(f"Found {len(candidates)} valid education/teacher posts from Guruwaraya (only_today={only_today}).")
    return candidates

# ==============================================================================
# TELEGRAM DAILY SELECTION LIST (6:00 PM)
# ==============================================================================
def send_daily_selection_list(chat_id: int = 1499235921):
    """Sends list of recent candidates (recent 5) to Telegram with published date, original link, details, and 1-tap publish buttons."""
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    candidates = fetch_candidate_posts(limit=35, only_today=False)
    if not candidates:
        logging.info("No education/teacher posts found on Guruwaraya.")
        payload = {
            "chat_id": chat_id,
            "text": f"ℹ️ *Guruwaraya Update ({today_str}):*\nNo education or teacher-related posts found on Guruwaraya.\n\n💡 *Tip:* If you spot a notice on Guruwaraya, simply paste its link into this chat anytime to publish it immediately!",
            "parse_mode": "Markdown"
        }
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json=payload, timeout=10)
        except Exception:
            pass
        return

    # Keep top 5 recent candidates
    top_candidates = candidates[:5]
    save_candidates(top_candidates)

    sl_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    updated_str = datetime.datetime.now(sl_tz).strftime("%Y-%m-%d | %I:%M %p")

    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    lines = [
        "📚 *Guruwaraya Education Posts – Recent Selection*",
        f"🕒 *Updated:* {updated_str} (Sri Lanka Time)\n",
        f"Found *{len(top_candidates)}* recent education & teacher posts from `guruwaraya.lk`:\n"
    ]

    blocks = []
    inline_keyboard = []
    for i, c in enumerate(top_candidates):
        num_str = number_emojis[i] if i < len(number_emojis) else f"{i+1}."
        safe_title = c['title'].replace("*", "").replace("_", "")
        inst = c.get('institution', 'Department of Education')

        item_lines = [
            f"{num_str} *{safe_title}*",
            f"🏛 *Institution:* {inst}"
        ]
        
        p_date = c.get("published_date", "Recent")
        c_date = c.get("closing_date")
        if c_date:
            item_lines.append(f"📅 *Published:* {p_date}  |  ⏳ *Closing:* {c_date}")
        else:
            item_lines.append(f"📅 *Published:* {p_date}")

        item_lines.append(f"🔗 [View Original Article]({c['url']})")

        if c.get("is_already_posted") and c.get("matched_url"):
            status_line = f"✅ *Status:* Already Published on LKUni.com • [LKUni Link]({c['matched_url']})"
            item_lines.append(status_line)
            btn_label = f"✅ Already Posted #{i+1}"
            inline_keyboard.append([{"text": btn_label, "callback_data": f"guru_already_posted_{i+1}"}])
        else:
            item_lines.append("🆕 *Status:* Ready to Publish")
            short_title = safe_title[:28] + ("..." if len(safe_title) > 28 else "")
            btn_label = f"Post {i+1}: {short_title}"
            inline_keyboard.append([{"text": btn_label, "callback_data": f"guru_pub_{i+1}"}])

        blocks.append("\n".join(item_lines))

    footer = [
        "💡 *How to publish:*",
        "• Tap any button below or type `/publish_1`, `/publish_2` to publish directly to LKUni.com!",
        "• If a post appears anytime, just send the link here to publish instantly."
    ]
    footer_text = "\n".join(footer)

    header = (
        "📚 *Guruwaraya Education Posts – Recent 5 Selection*\n"
        f"🕒 *Updated:* {updated_str} (Sri Lanka Time)\n\n"
        f"Found *{len(top_candidates)}* recent education & teacher posts from `guruwaraya.lk`:\n"
    )

    full_text = header + "\n" + "\n\n".join(blocks) + "\n\n" + footer_text

    payload = {
        "chat_id": chat_id,
        "text": full_text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
        "reply_markup": {"inline_keyboard": inline_keyboard}
    }
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json=payload,
            timeout=15
        )
        if r.status_code == 200:
            logging.info("Sent daily selection list to user via Telegram successfully.")
        else:
            logging.error(f"Telegram API error {r.status_code}: {r.text}")
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")

# ==============================================================================
# BANNER GENERATOR
# ==============================================================================
def fit_text_to_lines(text: str, font_path: str, max_w=1320, max_lines=3, initial_font_size=74, min_font_size=42):
    words = text.split()
    font_size = initial_font_size
    while font_size >= min_font_size:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()
            return [text], font_size, font

        lines = []
        curr = []
        overflow = False
        for w in words:
            test = " ".join(curr + [w])
            bbox = font.getbbox(test) if hasattr(font, "getbbox") else (0, 0, font_size * len(test) * 0.5, font_size)
            if (bbox[2] - bbox[0]) <= max_w:
                curr.append(w)
            else:
                if curr:
                    lines.append(" ".join(curr))
                    curr = [w]
                else:
                    lines.append(w)
                    curr = []
            if len(lines) > max_lines:
                overflow = True
                break
        if curr and not overflow:
            lines.append(" ".join(curr))
            if len(lines) > max_lines:
                overflow = True

        if not overflow:
            return lines, font_size, font
        font_size -= 4

    font = ImageFont.truetype(font_path, min_font_size)
    lines = []
    curr = []
    for w in words:
        test = " ".join(curr + [w])
        bbox = font.getbbox(test) if hasattr(font, "getbbox") else (0, 0, min_font_size * len(test) * 0.5, min_font_size)
        if (bbox[2] - bbox[0]) <= max_w:
            curr.append(w)
        else:
            if curr:
                lines.append(" ".join(curr))
                curr = [w]
            else:
                lines.append(w)
                curr = []
    if curr:
        lines.append(" ".join(curr))
    return lines[:max_lines], min_font_size, font

def simplify_banner_title(title: str) -> str:
    """Shortens verbose title for clean banner presentation."""
    t = title.strip()
    # Remove trailing parts like "| Sinhala, Tamil...", "– Apply Before..."
    t = re.split(r'[|–-]\s*(Apply|Sinhala|Closing|25 Districts)', t, flags=re.I)[0].strip()
    words = t.split()
    if len(words) > 8:
        return " ".join(words[:8])
    return t

def create_guruwaraya_banner(inst_name: str, title: str, year_str: str = "2026") -> str:
    """Generates official 1600x1066 LKUni head banner."""
    output_path = os.path.join(BASE_DIR, "guruwaraya_banner_gen.png")
    if not os.path.exists(TEMPLATE_IMG):
        raise FileNotFoundError(f"Template image {TEMPLATE_IMG} not found!")

    im = Image.open(TEMPLATE_IMG).convert("RGB")
    draw = ImageDraw.Draw(im)

    font_sans_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_serif_bold = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
    if not os.path.exists(font_serif_bold):
        font_serif_bold = font_sans_bold

    # 1. Green Bar (Y: 160 to 304, height: 144)
    draw.rectangle([0, 160, 1600, 304], fill=(0, 94, 32))
    inst_clean = inst_name.upper().strip()
    inst_font_size = 54
    try:
        inst_font = ImageFont.truetype(font_sans_bold, inst_font_size)
    except Exception:
        inst_font = ImageFont.load_default()

    while inst_font_size > 28:
        bbox = draw.textbbox((0, 0), inst_clean, font=inst_font)
        text_w = bbox[2] - bbox[0]
        if text_w <= 1450:
            break
        inst_font_size -= 2
        try:
            inst_font = ImageFont.truetype(font_sans_bold, inst_font_size)
        except Exception:
            break

    bbox = draw.textbbox((0, 0), inst_clean, font=inst_font)
    iw = bbox[2] - bbox[0]
    ih = bbox[3] - bbox[1]
    draw.text(((1600 - iw) // 2, 160 + (144 - ih) // 2 - (bbox[1] // 2)), inst_clean, fill=(255, 255, 255), font=inst_font)

    # 2. Fitted Title in Deep Royal Blue (RGB: 0, 38, 179)
    clean_t = simplify_banner_title(title)
    lines, font_size, course_font = fit_text_to_lines(clean_t, font_serif_bold, max_w=1320, max_lines=3, initial_font_size=74)

    line_height = int(font_size * 1.32)
    total_h = len(lines) * line_height
    start_y = 330 + (340 - total_h) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=course_font)
        lw = bbox[2] - bbox[0]
        lx = (1600 - lw) // 2
        ly = start_y + (i * line_height)
        draw.text((lx, ly), line, fill=(0, 38, 179), font=course_font)

    # 3. Year in Black Serif (RGB: 0, 0, 0)
    year_font = ImageFont.truetype(font_serif_bold, 84)
    bbox = draw.textbbox((0, 0), year_str, font=year_font)
    yw = bbox[2] - bbox[0]
    draw.text(((1600 - yw) // 2, 695), year_str, fill=(0, 0, 0), font=year_font)

    im.save(output_path, "PNG", quality=95)
    logging.info(f"Generated Guruwaraya banner: {output_path}")
    return output_path

# ==============================================================================
# SCRAPE INDIVIDUAL POST & PUBLISH
# ==============================================================================
def scrape_guruwaraya_post(post_url: str) -> dict:
    """Scrapes a specific post from guruwaraya.lk and extracts all download links."""
    r = requests.get(post_url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        raise Exception(f"Failed to fetch post: HTTP {r.status_code}")

    soup = BeautifulSoup(r.text, "html.parser")
    entry = soup.find("div", class_="entry-content") or soup.find("div", class_="post-body") or soup

    # Extract clean paragraphs
    paragraphs = []
    for p in entry.find_all("p"):
        txt = p.get_text(strip=True)
        # Exclude competitor tags, links, and empty lines
        if len(txt) > 35 and not any(k in txt.lower() for k in ["guruwaraya", "whatsapp", "telegram", "facebook", "join our"]):
            # Exclude Sinhala/Tamil text from English body
            if not any(c in txt for c in ["\u0d80", "\u0dff", "\u0b80", "\u0bff"]):
                paragraphs.append(txt)

    # Extract all download links (PDFs, Drive links, DO spaces)
    downloads = []
    seen = set()
    for a in entry.find_all("a", href=True):
        href = a["href"].strip()
        t = a.get_text(strip=True)
        h_low = href.lower()

        # Skip social shares
        if any(skip in h_low for skip in ["whatsapp", "facebook", "twitter", "telegram", "pinterest", "blogger", "sharer"]):
            continue

        is_download = (
            h_low.endswith(".pdf") or 
            "drive.google.com" in h_low or 
            "digitaloceanspaces.com" in h_low or 
            "doenets.lk" in h_low or
            "moe.gov.lk" in h_low or
            ".gov.lk" in h_low or
            ".ac.lk" in h_low or
            any(cls in " ".join(a.get("class", [])).lower() for cls in ["download", "btn", "listbtn"])
        )

        if is_download and href not in seen:
            seen.add(href)
            # Clean label
            label = t or "Official Document (PDF)"
            label = re.sub(r'^[📄📥📋🎓📤📅]\s*', '', label).strip()
            downloads.append((label, href))

    # Extract year
    year_match = re.search(r'\b(202[5-9])\b', r.text)
    year_str = year_match.group(1) if year_match else "2026"

    # Extract page title
    page_title = ""
    title_tag = soup.find(["h1", "h2"], class_=lambda c: c and ("entry-title" in c or "post-title" in c)) or soup.find("h1")
    if title_tag:
        page_title = title_tag.get_text(strip=True)
    elif soup.find("title"):
        page_title = soup.find("title").get_text(strip=True)
        page_title = re.split(r'[-|–]\s*Guruwaraya', page_title, flags=re.I)[0].strip()

    return {
        "title": page_title,
        "paragraphs": paragraphs[:4],
        "downloads": downloads,
        "year": year_str,
        "source_url": post_url
    }

def publish_guruwaraya_post(post_url: str, title: str = "", institution: str = "", target_blog_id: str = OFFICIAL_BLOG_ID) -> dict:
    """Publishes the approved guruwaraya post to LKUni.com."""
    details = scrape_guruwaraya_post(post_url)
    post_title = title or details.get("title") or "Education & Teacher Update – Sri Lanka"
    inst_name = institution or detect_institution(post_title, [])

    # Check duplicate on Blogger
    blogger_titles = fetch_recent_blogger_titles(blog_id=target_blog_id, max_results=60)
    is_dup, matched = is_duplicate_on_blogger(post_title, blogger_titles)
    if is_dup:
        logging.info(f"Duplicate detected on Blogger: matches '{matched}'. Skipping.")
        return {
            "status": "duplicate",
            "matched_title": matched,
            "title": post_title
        }

    # 1. Generate Head Banner
    banner_img = create_guruwaraya_banner(inst_name, post_title, details["year"])
    banner_url = upload_to_google_drive(banner_img, file_name="thumb-size.png", folder_name="Guruwaraya_Posts_2026")

    # Find official government/institutional website if present
    official_site = None
    for label, link in details["downloads"]:
        l_low = link.lower()
        if (".gov.lk" in l_low or ".ac.lk" in l_low or "doenets.lk" in l_low) and not link.endswith(".pdf"):
            official_site = link
            break

    # 2. Build #simple_table rows:
    # Rule:
    # 1. Document / Detail links first
    # 2. Apply Online link before the source
    # 3. Official Website (source ) at the very end of the table
    regular_rows = []
    apply_rows = []

    def is_apply_item(lbl: str, url: str) -> bool:
        l_clean = lbl.lower()
        u_clean = url.lower()
        apply_keywords = [
            "apply online", "online application", "apply now", "apply here",
            "online apply", "registration", "application online", "submit application"
        ]
        if any(k in l_clean for k in apply_keywords):
            return True
        if any(k in u_clean for k in ["/apply", "/registration", "forms.gle", "google.com/forms", "online-application"]):
            if not u_clean.endswith(".pdf"):
                return True
        if "apply" in l_clean and not any(k in l_clean for k in ["closing", "how to", "instruction", "guide", ".pdf", "pdf", "fee", "calling"]):
            if not u_clean.endswith(".pdf"):
                return True
        return False

    def is_source_item(lbl: str) -> bool:
        return lbl.lower().strip() in ["official website", "official source", "source", "website", "official portal"]

    for label, link in details["downloads"]:
        clean_lbl = re.sub(r'^[📄📥📋🎓📤📅📝]\s*', '', label).strip()
        if is_source_item(clean_lbl):
            if not official_site:
                official_site = link
            continue
        if is_apply_item(clean_lbl, link):
            apply_rows.append(f"""<tr>
\t<td>{clean_lbl}</td>
\t<td><a href="{link}" target="_blank">Click Here</a></td>
</tr>""")
        else:
            regular_rows.append(f"""<tr>
\t<td>{clean_lbl}</td>
\t<td><a href="{link}" target="_blank">Click Here</a></td>
</tr>""")

    table_rows = regular_rows + apply_rows

    # Source / Official Website rows at the very end of the table
    source_target = official_site or post_url
    table_rows.append(f"""<tr>
\t<td>Official Website (source )</td>
\t<td><a href="{source_target}" target="_blank">{inst_name}</a></td>
</tr>""")

    rows_html = "\n".join(table_rows)

    # 3. Clean English description
    if details["paragraphs"]:
        desc_html = "\n".join([f"<p>{p}</p>" for p in details["paragraphs"][:3]])
    else:
        desc_html = f"<p>The {inst_name} has announced the latest updates regarding <b>{post_title}</b>. All related guidelines, circulars, and official application documents can be downloaded in PDF format below.</p>"

    content_html = f"""<p>&nbsp;</p>
<div class="separator" style="clear: both; text-align: center;">
  <a href="{banner_url}" style="margin-left: 1em; margin-right: 1em;">
    <img border="0" data-original-height="1066" data-original-width="1600" src="{banner_url}" />
  </a>
</div>
<br/>

<p><b>{inst_name}</b></p>
<p><b>{post_title}</b></p>
<div>
{desc_html}
</div>
<br/>

<style>
#simple_table {{
\tfont-family: arial, sans-serif;
\tborder-collapse: collapse; 
\twidth: 100%;
\tbackground-color: #000000;
\tcolor:#33fcff;
}}
#simple_table td, #simple_table th {{
\ttext-align: left;
\tpadding: 8px;
\tborder: 1px solid #ffffff;
}}
#simple_table tr:nth-child(even) {{
\tbackground-color: #1d1b1b;
}}
#simple_table tr:hover {{
\tbackground-color: #9e0000;
}}
#simple_table tr > th {{
\tbackground: #00fbff;
\tcolor: #000000;
}}
</style>

<table id="simple_table">
<tbody>
<tr>
\t<th>Details</th>
\t<th>Links</th>
</tr>
{rows_html}
</tbody>
</table>
<br/><br/><br/>"""

    # 4. Insert into Blogger
    token_file = os.path.join(BASE_DIR, "token.json")
    with open(token_file, "r") as f:
        creds_data = json.load(f)
    creds = Credentials.from_authorized_user_info(creds_data)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    service = build("blogger", "v3", credentials=creds)
    body = {
        "kind": "blogger#post",
        "title": post_title,
        "content": content_html,
        "labels": ["TEACHERS", "EDUCATION", "UPDATES"]
    }

    res = service.posts().insert(blogId=target_blog_id, body=body, isDraft=False).execute()
    live_url = res.get("url")

    # 5. Add to cache
    cache = load_cache()
    if post_url not in cache:
        cache.append(post_url)
    if post_title not in cache:
        cache.append(post_title)
    save_cache(cache)

    logging.info(f"Published post to LKUni: {live_url}")

    # 6. Telegram Broadcast to Channel (@differentpaths)
    clean_banner_title = simplify_banner_title(post_title)
    tg_text = f"""🟩 {clean_banner_title} 🟩

👉 Details & Download - {live_url}

තවත් මෙවැනි තොරතුරු දැනගැනීමට ✅

👉 Join Our Telegram Channel :https://t.me/differentpaths

යාළුවන්ටත් දැනගන්න share කරන්න 👍👍👍"""

    for cid in TELEGRAM_CHAT_IDS:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": cid.strip(), "text": tg_text},
                timeout=10
            )
        except Exception:
            pass

    return {
        "status": "success",
        "url": live_url,
        "title": post_title
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Guruwaraya Education Monitor")
    parser.add_argument("--send-list", action="store_true", help="Send daily selection list to Telegram (6:00 PM)")
    parser.add_argument("--publish-index", type=int, help="Publish candidate by 1-based index")
    parser.add_argument("--publish-url", type=str, help="Publish candidate by direct URL")
    parser.add_argument("--test-blog", action="store_true", help="Publish to test blog")
    args = parser.parse_args()

    blog_id = TEST_BLOG_ID if args.test_blog else OFFICIAL_BLOG_ID

    if args.send_list:
        send_daily_selection_list()
    elif args.publish_index:
        candidates = load_candidates()
        idx = args.publish_index - 1
        if 0 <= idx < len(candidates):
            c = candidates[idx]
            print(f"Publishing candidate {args.publish_index}: {c['title']}...")
            res = publish_guruwaraya_post(c["url"], title=c["title"], institution=c["institution"], target_blog_id=blog_id)
            print("Result:", res)
        else:
            print(f"Invalid index {args.publish_index}. Found {len(candidates)} candidates.")
    elif args.publish_url:
        print(f"Publishing custom URL: {args.publish_url}...")
        res = publish_guruwaraya_post(args.publish_url, target_blog_id=blog_id)
        print("Result:", res)
    else:
        # Default: print current candidates
        cands = fetch_candidate_posts()
        print(f"Found {len(cands)} candidates:")
        for i, c in enumerate(cands[:10]):
            print(f"[{i+1}] {c['title']} ({c['institution']}) -> {c['url']}")
