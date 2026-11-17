#!/usr/bin/env python3
"""
Auto BlogPost Script & Scraper for LKUni (https://www.lkuni.com/)
- Scrapes https://tamilguru.lk/category/courses/ or any arbitrary educational link
- Prevents duplicates using posted_cache.json AND live Blogger API post check
- Custom 1600x1066 head banner generated
- Google Drive subfolder & native CDN image hosting
- Gemini Vision flyer OCR & translation to clean English
- Fast table (#simple_table) and text bullet points (Zero competitor watermarks)
- Telegram broadcasting to channel (@differentpaths) and user
"""

import os
import sys
import io
import json
import time
import ssl
import re
import base64
import argparse
import logging
import datetime
from difflib import SequenceMatcher
import urllib.request
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
import pymupdf
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==============================================================================
# CONFIGURATION
# ==============================================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "REDACTED_GCP_API_KEY")
OFFICIAL_BLOG_ID = "3109655798381913489"  # https://www.lkuni.com/
TEST_BLOG_ID = "2198767951950215096"      # https://lkunitest.blogspot.com/
DEFAULT_BLOG_ID = OFFICIAL_BLOG_ID

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9269727444:AAHwsO8xw7__8BWWfxSGNDWuUnwF7lQ6FVw")
TELEGRAM_CHAT_IDS = [cid.strip() for cid in os.getenv("TELEGRAM_CHAT_IDS", "1499235921,@differentpaths").split(",") if cid.strip()]
AUTHORIZED_USERS = [1499235921]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, "posted_cache.json")
TEMPLATE_IMG = os.path.join(BASE_DIR, "thumb_template.png")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# ==============================================================================
# CACHE & DUPLICATE CHECK HELPERS
# ==============================================================================
def is_date_expired(closing_date_str: str) -> bool:
    """
    Checks if a closing date string is already expired compared to current local date.
    Returns True if expired, False if valid or if date cannot be determined.
    """
    if not closing_date_str:
        return False
    try:
        # Match YYYY.MM.DD or YYYY-MM-DD or YYYY/MM/DD
        m = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", closing_date_str)
        if m:
            y, mth, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            c_date = datetime.date(y, mth, d)
            today = datetime.date.today()
            return c_date < today
    except Exception as e:
        logging.warning(f"Error checking closing date expiry for '{closing_date_str}': {e}")
    return False

def clean_external_url(url: str) -> str:
    """Returns clean URL if it is not a competitor / tamilguru URL, else None."""
    if not url:
        return None
    url = url.strip()
    if not url.startswith("http"):
        return None
    lu = url.lower()
    if any(k in lu for k in ["tamilguru", "tamilguru.lk"]):
        return None
    return url

def find_original_media_from_source(source_url: str, course_name: str = "") -> dict:
    """
    Visits the original official source website and attempts to find unwatermarked
    official flyer images AND official PDF documents directly from the source.
    Returns {"flyer": url or None, "pdfs": [(name, url), ...]}
    """
    result = {"flyer": None, "pdfs": []}
    if not source_url:
        return result
    source_url = clean_external_url(source_url)
    if not source_url:
        return result

    visited_pages = set()
    pages_to_check = [source_url]

    try:
        req = urllib.request.Request(source_url, headers=HEADERS)
        html = urllib.request.urlopen(req, context=SSL_CTX, timeout=12).read().decode("utf-8")
        soup = BeautifulSoup(html, "html.parser")

        parsed_orig = urlparse(source_url)
        is_root_or_hub = (parsed_orig.path.strip("/") == "" or any(k in parsed_orig.path.lower() for k in ["category", "courses", "featured"]))

        if is_root_or_hub and course_name:
            keywords = [w.lower() for w in course_name.split() if len(w) > 3 and w.lower() not in ["university", "department", "faculty", "institute", "intake"]]
            for a in soup.find_all("a", href=True):
                href = urljoin(source_url, a["href"])
                lh = href.lower()
                txt = a.get_text(separator=" ", strip=True).lower()
                if urlparse(href).netloc == parsed_orig.netloc and href not in pages_to_check:
                    if keywords and all(k in txt or k in lh for k in keywords):
                        pages_to_check.insert(0, href)
                    elif any(k in lh for k in ["external", "featured-courses", "course", "diploma", "degree"]):
                        pages_to_check.append(href)

        for page in pages_to_check[:6]:
            if page in visited_pages:
                continue
            visited_pages.add(page)

            try:
                if page == source_url:
                    page_soup = soup
                else:
                    req_p = urllib.request.Request(page, headers=HEADERS)
                    html_p = urllib.request.urlopen(req_p, context=SSL_CTX, timeout=10).read().decode("utf-8")
                    page_soup = BeautifulSoup(html_p, "html.parser")

                # If checking a hub page, check if it links to the specific course
                if page != source_url and course_name:
                    keywords = [w.lower() for w in course_name.split() if len(w) > 3 and w.lower() not in ["university", "department", "faculty", "institute", "intake"]]
                    for a in page_soup.find_all("a", href=True):
                        h = urljoin(page, a["href"])
                        t = (a.get_text(strip=True) + " " + h).lower()
                        if keywords and all(k in t for k in keywords) and h not in visited_pages:
                            pages_to_check.insert(1, h)

                # Look for direct official flyer links or images
                if not result["flyer"]:
                    for img in page_soup.find_all("img"):
                        src = img.get("src") or img.get("data-src") or img.get("data-original")
                        if src:
                            abs_src = urljoin(page, src)
                            ls = abs_src.lower()
                            if any(k in ls for k in ["paper-add", "paper-ad", "paper_ad", "paper_add", "adv_", "_ad", "-ad", "advertisement", "flyer"]):
                                if not any(skip in ls for skip in ["logo", "icon", "banner", "tamilguru", "layout-", "365x240", "84x56", "150x150", "300x"]):
                                    result["flyer"] = abs_src
                                    break

                if not result["flyer"]:
                    for a in page_soup.find_all("a", href=True):
                        href = urljoin(page, a["href"])
                        lh = href.lower()
                        if any(lh.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                            if any(k in lh for k in ["paper-add", "paper-ad", "paper_ad", "adv_", "_ad", "-ad", "advertisement", "flyer"]):
                                if not any(skip in lh for skip in ["logo", "icon", "banner", "tamilguru", "layout-", "365x240", "84x56", "150x150", "300x"]):
                                    result["flyer"] = href
                                    break

                # Look for direct official PDF documents
                for a in page_soup.find_all("a", href=True):
                    href = urljoin(page, a["href"])
                    lh = href.lower()
                    if lh.endswith(".pdf"):
                        if not any(skip in lh for skip in ["tamilguru", "by-laws", "results"]):
                            name = a.get_text(strip=True) or "Download PDF"
                            if not any(href == p[1] for p in result["pdfs"]):
                                result["pdfs"].append((name, href))
            except Exception:
                pass
    except Exception as e:
        logging.warning(f"Could not scrape source page '{source_url}' for original media: {e}")

    return result

def load_posted_cache() -> list:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_posted_cache(cache: list):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

def fetch_recent_blogger_posts(blog_id: str = OFFICIAL_BLOG_ID, max_results: int = 50, max_age_days: int = 120) -> list:
    """Fetches list of recent post dicts ({title, url, published}) from Blogger API."""
    token_file = os.path.join(BASE_DIR, "token.json")
    if not os.path.exists(token_file):
        return []
    try:
        with open(token_file, "r") as f:
            creds_data = json.load(f)
        creds = Credentials.from_authorized_user_info(creds_data)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_file, "w") as f:
                f.write(creds.to_json())
        service = build("blogger", "v3", credentials=creds)
        res = service.posts().list(blogId=blog_id, maxResults=max_results, fetchBodies=False).execute()
        items = res.get("items", [])
        posts = []
        now = datetime.datetime.now(datetime.timezone.utc)
        for p in items:
            pub_str = p.get("published", "")
            # Filter out very old archived posts (e.g. from 2023/2024/2025)
            if max_age_days and pub_str:
                try:
                    pub_dt = datetime.datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                    if (now - pub_dt).days > max_age_days:
                        continue
                except Exception:
                    pass
            posts.append({
                "title": p.get("title", ""),
                "url": p.get("url", ""),
                "published": pub_str
            })
        return posts
    except Exception as e:
        logging.warning(f"Could not fetch Blogger posts: {e}")
        return []

def fetch_recent_blogger_titles(blog_id: str = OFFICIAL_BLOG_ID, max_results: int = 50) -> list:
    """Fetches list of recent post titles from Blogger API to prevent duplicates."""
    posts = fetch_recent_blogger_posts(blog_id=blog_id, max_results=max_results)
    return [p["title"] for p in posts]

INSTITUTION_ALIASES = {
    "rajarata": ["rajarata", "rusl"],
    "wayamba": ["wayamba", "wusl"],
    "colombo": ["colombo", "uoc", "uciars", "ucsc"],
    "peradeniya": ["peradeniya", "uop", "cdce"],
    "kelaniya": ["kelaniya", "uok", "pgiar"],
    "moratuwa": ["moratuwa", "uom", "itum"],
    "sri_jayewardenepura": ["jayewardenepura", "usj", "sjp"],
    "ruhuna": ["ruhuna", "uor"],
    "jaffna": ["jaffna", "uoj"],
    "eastern": ["eastern", "eusl"],
    "south_eastern": ["south eastern", "seusl"],
    "sabaragamuwa": ["sabaragamuwa", "susl"],
    "uva_wellassa": ["uva wellassa", "uwu"],
    "open_university": ["open university", "ousl"],
    "ocean_university": ["ocean university", "ocu"],
    "buddhist_pali": ["buddhist and pali", "buddhist & pali", "bpu"],
    "biksu": ["biksu", "buss"],
    "kdu": ["kotelawala", "kdu"],
    "sliate": ["sliate", "ati"],
    "nie": ["national institute of education", "nie"],
    "moe": ["ministry of education", "moe"],
    "doenets": ["department of examinations", "doenets"]
}

def detect_inst_key(text: str) -> str:
    """Detects canonical institution key from title/text."""
    t_low = text.lower()
    for key, aliases in INSTITUTION_ALIASES.items():
        for a in aliases:
            if re.search(r'\b' + re.escape(a) + r'\b', t_low):
                return key
    return None

def detect_level(text: str) -> str:
    """Detects educational qualification level to prevent PhD matching Diploma."""
    t_low = text.lower()
    if any(re.search(r'\b' + k + r'\b', t_low) for k in ['phd', 'mphil', 'doctorate', 'doctoral']):
        return 'phd'
    if any(re.search(r'\b' + k + r'\b', t_low) for k in ['master', 'masters', 'msc', 'mba', 'mcom', 'med', 'llm', 'postgraduate', 'pgd', 'pgdip', 'meng', 'msceng']):
        return 'master'
    if any(re.search(r'\b' + k + r'\b', t_low) for k in ['bachelor', 'bachelors', 'bsc', 'ba', 'bba', 'bcom', 'bed', 'llb', 'undergraduate']):
        return 'bachelor'
    if any(re.search(r'\b' + k + r'\b', t_low) for k in ['diploma', 'hnd', 'nvq', 'certificate', 'cert']):
        return 'diploma'
    return None

def extract_year_val(text: str, url: str = None, published: str = None):
    """Extracts 4-digit intake year from title, URL, or published timestamp."""
    m = re.search(r'\b(202\d)\b', text or '')
    if m:
        return int(m.group(1))
    if url:
        m = re.search(r'/(202\d)/\d\d/', url)
        if m:
            return int(m.group(1))
    if published:
        m = re.search(r'^(202\d)', published)
        if m:
            return int(m.group(1))
    return None

def normalize_title(title: str) -> str:
    """Normalizes title for similarity matching across TamilGuru and Guruwaraya."""
    t = title.lower()

    # Strip trailing action calls, deadlines, and promotional suffixes
    t = re.split(r'[-|–]\s*(?:apply\s+(?:before|online|by)|closing\s+date|sinhala|25\s+districts|check\s+(?:online|with)|final\s+results|\d+\s+specializations|district\s+wise)', t, flags=re.I)[0]

    # Normalize degree acronyms with dots
    t = re.sub(r'\bb\.?\s*ed\b', 'bed', t)
    t = re.sub(r'\bm\.?\s*ed\b', 'med', t)
    t = re.sub(r'\bll\.?\s*m\b', 'llm', t)
    t = re.sub(r'\bll\.?\s*b\b', 'llb', t)
    t = re.sub(r'\bb\.?\s*sc\b', 'bsc', t)
    t = re.sub(r'\bb\.?\s*a\b', 'ba', t)

    # Normalize common institution synonyms so variations match perfectly
    t = re.sub(r"\bopen university of sri lanka\b", "ousl", t)
    t = re.sub(r"\bopen university\b", "ousl", t)
    t = re.sub(r"\buniversity of colombo\b", "uoc", t)
    t = re.sub(r"\buniversity of peradeniya\b", "uop", t)
    t = re.sub(r"\buniversity of kelaniya\b", "uok", t)
    t = re.sub(r"\bbuddhist\s*(?:&|and)\s*pali\s*university\b", "bpu", t)
    t = re.sub(r"\bnational institute of education\b", "nie", t)
    t = re.sub(r"\bocean university(?: of sri lanka)?\b", "ocu", t)
    t = re.sub(r"\bsabaragamuwa university(?: of sri lanka)?\b", "susl", t)
    t = re.sub(r"\bministry of education\b", "moe", t)
    t = re.sub(r"\bdepartment of examinations\b", "doenets", t)
    t = re.sub(r"\bsri lanka principals service\b", "slps", t)
    t = re.sub(r"\bsri lanka teachers service\b", "slts", t)
    t = re.sub(r"\bsri lanka education administrative service\b", "sleas", t)
    t = re.sub(r"\bnational child protection authority\b", "ncpa", t)

    # Strip punctuation
    t = re.sub(r"[^\w\s]", " ", t)

    # Strip generic educational stopwords and qualification fillers
    stopwords = r"\b(application|applications|apply|admission|admissions|calling|for|degree|degrees|intake|intakes|programmes?|courses?|offered|by|bachelor|bachelors|honours?|general|special|online|specializations?|released|updates?)\b"
    t = re.sub(stopwords, " ", t)
    return " ".join(t.split())

def find_blogger_match(candidate_title: str, existing_posts: list) -> tuple:
    """
    Checks if candidate title matches any existing post on Blogger.
    existing_posts can be a list of strings or list of dicts with 'title', 'url', 'published'.
    Returns (is_duplicate: bool, matched_title: str or None, matched_url: str or None).
    """
    if not candidate_title or not existing_posts:
        return False, None, None

    c_inst = detect_inst_key(candidate_title)
    c_lvl = detect_level(candidate_title)
    c_year = extract_year_val(candidate_title)

    c_norm = normalize_title(candidate_title)
    generic_words = {
        "university", "sri", "lanka", "department", "institute", "national",
        "higher", "education", "general", "studies", "service", "programmes",
        "programme", "courses", "course", "degrees", "degree"
    }
    c_words = {w for w in c_norm.split() if len(w) >= 3 and not w.isdigit() and w not in generic_words}

    for item in existing_posts:
        ext = item["title"] if isinstance(item, dict) else item
        url = item.get("url") if isinstance(item, dict) else None
        pub = item.get("published") if isinstance(item, dict) else None

        # 1. Institution Check: If both specify an institution, they must match
        e_inst = detect_inst_key(ext)
        if c_inst and e_inst and c_inst != e_inst:
            continue

        # 2. Level Check: PhD vs Master vs Bachelor vs Diploma
        e_lvl = detect_level(ext)
        if c_lvl and e_lvl and c_lvl != e_lvl:
            continue

        # 3. Year / Intake Check: Difference > 1 year is never a duplicate
        e_year = extract_year_val(ext, url=url, published=pub)
        if c_year and e_year and abs(c_year - e_year) > 1:
            continue

        # 4. Old post age check (> 180 days)
        if pub:
            try:
                pub_dt = datetime.datetime.fromisoformat(pub.replace("Z", "+00:00"))
                if (datetime.datetime.now(datetime.timezone.utc) - pub_dt).days > 180 and c_year and c_year >= 2026:
                    continue
            except Exception:
                pass

        e_norm = normalize_title(ext)
        e_words = {w for w in e_norm.split() if len(w) >= 3 and not w.isdigit() and w not in generic_words}

        if not c_words or not e_words:
            sim = SequenceMatcher(None, c_norm, e_norm).ratio()
            if sim >= 0.75:
                return True, ext, url
            continue

        intersection = c_words.intersection(e_words)
        ratio = len(intersection) / len(c_words)
        sim = SequenceMatcher(None, c_norm, e_norm).ratio()

        if ratio >= 0.65 or (ratio >= 0.50 and sim >= 0.55):
            return True, ext, url

    return False, None, None

def is_duplicate_on_blogger(candidate_title: str, existing_titles: list) -> tuple:
    """
    Checks if candidate title matches any existing title on Blogger.
    Returns (True, matched_title) or (False, None) for backward compatibility.
    """
    is_dup, matched_title, _ = find_blogger_match(candidate_title, existing_titles)
    return is_dup, matched_title

# ==============================================================================
# CUSTOM HEAD IMAGE GENERATOR (1600x1066 LKUNI STYLE)
# ==============================================================================
def create_custom_head_image(institute_name: str, course_title: str, year: str) -> str:
    output_path = os.path.join(BASE_DIR, "thumb-size.png")
    if not os.path.exists(TEMPLATE_IMG):
        raise FileNotFoundError(f"Template image {TEMPLATE_IMG} not found!")

    im = Image.open(TEMPLATE_IMG).convert("RGB")
    draw = ImageDraw.Draw(im)

    font_sans_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_serif_bold = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
    if not os.path.exists(font_serif_bold):
        font_serif_bold = font_sans_bold

    # 1. Institution Name in Green Bar (Y: 160 to 304, height: 144)
    draw.rectangle([0, 160, 1600, 304], fill=(0, 94, 32))

    inst_clean = institute_name.upper().strip()
    inst_font_size = 56
    try:
        inst_font = ImageFont.truetype(font_sans_bold, inst_font_size)
    except Exception:
        inst_font = ImageFont.load_default()

    while inst_font_size > 26:
        bbox = draw.textbbox((0, 0), inst_clean, font=inst_font)
        text_w = bbox[2] - bbox[0]
        if text_w <= 1500:
            break
        inst_font_size -= 2
        try:
            inst_font = ImageFont.truetype(font_sans_bold, inst_font_size)
        except Exception:
            break

    bbox = draw.textbbox((0, 0), inst_clean, font=inst_font)
    inst_w = bbox[2] - bbox[0]
    inst_h = bbox[3] - bbox[1]
    inst_x = (1600 - inst_w) // 2
    inst_y = 160 + (144 - inst_h) // 2 - (bbox[1] // 2)
    draw.text((inst_x, inst_y), inst_clean, fill=(255, 255, 255), font=inst_font)

    # 2. Course Name in Deep Royal Blue (RGB: 0, 38, 179)
    course_clean = course_title.strip()
    words = course_clean.split()
    lines = []
    curr_line = []

    target_font_size = 86
    try:
        course_font = ImageFont.truetype(font_serif_bold, target_font_size)
    except Exception:
        course_font = ImageFont.load_default()

    for w in words:
        test_line = " ".join(curr_line + [w])
        bbox = draw.textbbox((0, 0), test_line, font=course_font)
        if (bbox[2] - bbox[0]) <= 1450:
            curr_line.append(w)
        else:
            if curr_line:
                lines.append(" ".join(curr_line))
                curr_line = [w]
            else:
                lines.append(w)
                curr_line = []
    if curr_line:
        lines.append(" ".join(curr_line))

    if len(lines) > 2:
        target_font_size = 68
        try:
            course_font = ImageFont.truetype(font_serif_bold, target_font_size)
        except Exception:
            course_font = ImageFont.load_default()
        lines = []
        curr_line = []
        for w in words:
            test_line = " ".join(curr_line + [w])
            bbox = draw.textbbox((0, 0), test_line, font=course_font)
            if (bbox[2] - bbox[0]) <= 1450:
                curr_line.append(w)
            else:
                if curr_line:
                    lines.append(" ".join(curr_line))
                    curr_line = [w]
                else:
                    lines.append(w)
                    curr_line = []
        if curr_line:
            lines.append(" ".join(curr_line))

    num_lines = len(lines)
    line_height = int(target_font_size * 1.35)
    total_course_h = num_lines * line_height

    course_start_y = 340 + (330 - total_course_h) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=course_font)
        lw = bbox[2] - bbox[0]
        lx = (1600 - lw) // 2
        ly = course_start_y + (i * line_height)
        draw.text((lx, ly), line, fill=(0, 38, 179), font=course_font)

    # 3. Year in Black Serif (RGB: 0, 0, 0)
    year_str = year.strip() if year else "2026"
    try:
        year_font = ImageFont.truetype(font_serif_bold, 84)
    except Exception:
        year_font = ImageFont.load_default()
    y_bbox = draw.textbbox((0, 0), year_str, font=year_font)
    yw = y_bbox[2] - y_bbox[0]
    yx = (1600 - yw) // 2
    yy = 695
    draw.text((yx, yy), year_str, fill=(0, 0, 0), font=year_font)

    im.save(output_path, "PNG", quality=95)
    logging.info(f"Custom head image generated: {output_path}")
    return output_path

# ==============================================================================
# GEMINI VISION FLYER TRANSCRIBER & OCR
# ==============================================================================
def scan_flyer_with_gemini_vision(img_path: str) -> dict:
    """Scans flyer with Gemini Vision to extract key facts in clean English."""
    if not GEMINI_API_KEY or not os.path.exists(img_path):
        return None

    try:
        with open(img_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logging.warning(f"Failed to read image for vision scan: {e}")
        return None

    prompt = """Analyze this educational flyer image.
Extract the key course details to generate a clean, professional summary for a university admission post.

Format requirements:
1. Institution & Faculty/Department heading line (e.g. 'University of Kelaniya (UoK) - Faculty of Social Sciences - Department of Philosophy')
2. Admission calling line (e.g. 'Application for Admission of Students to the following Diploma Course 2027 (2026) Intake 10')
3. Numbered course title (e.g. '01. Diploma in Counselling')
4. Concise bullet points explaining key course details:
   * Qualification: (concise summary)
   * Duration:
   * Mode: (e.g. Online and On-site / Online / Physical / Blended)
   * Medium: (e.g. English / Sinhala)
   * Course Fee: (only if mentioned)
   * Closing Date: (YYYY.MM.DD)

CRITICAL RULES:
- All output text must be in clean, professional ENGLISH.
- Translate any Sinhala or Tamil text accurately into English.
- Completely ignore and NEVER include competitor watermark text or brand names (e.g. 'tamilguru', 'tamilguru.lk').
- If a field is not stated in the flyer, omit it. Do NOT write 'N/A' or 'Not Specified'.
- Standardize the closing date to YYYY.MM.DD format.

Output strictly valid JSON with this schema:
{
  "institution_header": "University / Institute Name and Faculty/Department",
  "calling_title": "Application for Admission of Students to...",
  "course_title": "01. [Course Name]",
  "course_name": "Course Name in English",
  "bullet_items": [
    "* Qualification: ...",
    "* Duration: ...",
    "* Mode: ...",
    "* Medium: ...",
    "* Closing Date: YYYY.MM.DD"
  ],
  "closing_date": "YYYY.MM.DD",
  "sinhala_institute": "ආයතනයේ නම",
  "sinhala_calling": "පාඨමාලාව සඳහා අයදුම්පත් කැඳවීම",
  "sinhala_bullets": [
    "👉 [සිංහල කරුණ 1]",
    "👉 [සිංහල කරුණ 2]"
  ]
}
"""

    for model_name in ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": b64_data
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "response_mime_type": "application/json"
                }
            }
            res = requests.post(url, json=payload, timeout=35)
            if res.status_code == 200:
                result_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                data = json.loads(result_text)
                cleaned_bullets = []
                for b in data.get("bullet_items", []):
                    b_lower = b.lower()
                    if "not specified" in b_lower or "n/a" in b_lower or "not mentioned" in b_lower:
                        continue
                    cleaned_bullets.append(b)
                data["bullet_items"] = cleaned_bullets
                logging.info(f"[Gemini Vision OCR] Successfully scanned flyer with {model_name} ({len(cleaned_bullets)} bullet points).")
                return data
            else:
                logging.warning(f"[Gemini Vision] {model_name} returned status {res.status_code}")
        except Exception as e:
            logging.warning(f"[Gemini Vision] Error with {model_name}: {e}")

    return None

# ==============================================================================
# GEMINI AI CONTENT SYNTHESIZER
# ==============================================================================
def synthesize_post_with_ai(raw_title: str, paragraphs: list, raw_table: dict, default_inst: str, default_course: str, default_year: str) -> dict:
    """Uses Gemini AI to generate clean LKUni English title, intro, and bullets."""
    if not GEMINI_API_KEY:
        return None

    raw_text_blocks = []
    for p_type, p_tag in paragraphs[:15]:
        t = p_tag.get_text(separator=" ", strip=True) if hasattr(p_tag, "get_text") else str(p_tag)
        if t and len(t) > 10 and not any(skip in t.lower() for skip in ["whatsapp", "telegram", "facebook", "tamilguru"]):
            raw_text_blocks.append(t)

    joined_text = "\n".join(raw_text_blocks[:10])

    prompt = f"""You are generating an educational course post for LKUni (https://www.lkuni.com/).
LKUni style is ULTRA-SIMPLE, MINIMAL, and CONCISE. NO ESSAYS, NO LONG PARAGRAPHS. DO NOT copy-paste competitor body text.

Format strictly as:
1. professional_title: e.g. "Application For [Course Name] - [Year] - [Institute]"
2. institution_header: e.g. "University of Kelaniya (UoK) - Faculty of Social Sciences - Department of Philosophy"
3. calling_title: e.g. "Application for Admission of Students to the following Diploma Course 2027 (2026) Intake 10"
4. course_title: e.g. "01. Diploma in Counselling"
5. bullet_items: Clean point-by-point explanation:
   * Qualification: ...
   * Duration: ...
   * Mode: ...
   * Medium: ...
   * Closing Date: YYYY.MM.DD
6. CRITICAL: Output clean English. Completely ignore watermarks and competitor brands like 'tamilguru'.
7. closing_date: format YYYY.MM.DD

RAW TITLE: {raw_title}
RAW CONTENT:
{joined_text}

Generate valid JSON:
{{
  "professional_title": "Application For [Course Name] - [Year] - [Institute]",
  "institution_header": "[Institute Name] - [Faculty]",
  "calling_title": "Application for Admission of Students to [Course] [Year]",
  "course_title": "01. [Course Name]",
  "institute_clean": "Official Institute Name in English",
  "course_clean": "Official Course Name in English",
  "year": "2026",
  "bullet_items": [
    "* Qualification: ...",
    "* Duration: ...",
    "* Mode: ...",
    "* Closing Date: YYYY.MM.DD"
  ],
  "closing_date": "YYYY.MM.DD",
  "sinhala_institute": "ආයතනයේ නිල නාමය සිංහලෙන්",
  "sinhala_calling": "[වසර] අධ්‍යයන වර්ෂය සඳහා [පාඨමාලාවේ නම] අයදුම්පත් කැඳවීම",
  "sinhala_bullets": [
    "👉 [සිංහල කරුණ 1]",
    "👉 [සිංහල කරුණ 2]"
  ]
}}
"""

    for model_name in ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"}
            }
            res = requests.post(url, json=payload, timeout=25)
            if res.status_code == 200:
                result_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                data = json.loads(result_text)
                logging.info(f"[AI Content Synthesizer] Generated post: '{data.get('professional_title')}'")
                return data
        except Exception as e:
            logging.warning(f"[AI Content Synthesizer] Error with {model_name}: {e}")

    return None

# ==============================================================================
# UNIVERSAL SCRAPER FOR ANY COURSE / ADMISSION URL
# ==============================================================================
def get_unposted_course_urls(check_blogger: bool = True) -> list:
    """
    Scrapes https://tamilguru.lk/category/courses/ and checks BOTH
    posted_cache.json AND live Blogger API post titles on www.lkuni.com.
    """
    list_url = "https://tamilguru.lk/category/courses/"
    logging.info(f"Checking for new course announcements on {list_url}...")
    try:
        req = urllib.request.Request(list_url, headers=HEADERS)
        html = urllib.request.urlopen(req, context=SSL_CTX).read().decode("utf-8")
        soup = BeautifulSoup(html, "html.parser")

        articles = soup.find_all("article")
        course_items = []
        for a in articles:
            classes = a.get("class", [])
            if "category-courses" in classes:
                link_tag = a.find("a", href=True)
                title_tag = a.find(["h1", "h2", "h3"])
                if link_tag:
                    href = link_tag["href"]
                    if href.startswith("https://tamilguru.lk/") and "/category/" not in href and "/tag/" not in href and "/page/" not in href and href != "https://tamilguru.lk/":
                        t_text = title_tag.get_text(strip=True) if title_tag else ""
                        if href not in [item[0] for item in course_items]:
                            course_items.append((href, t_text))

        cache = set(load_posted_cache())
        blogger_titles = fetch_recent_blogger_titles() if check_blogger else []

        unposted = []
        for href, title in reversed(course_items):
            if href in cache:
                continue
            if blogger_titles:
                is_dup, matched = is_duplicate_on_blogger(title, blogger_titles)
                if is_dup:
                    logging.info(f"Skipping '{title}' -> Already published on LKUni as '{matched}'")
                    # Also record in cache to save future Blogger lookups
                    if href not in cache:
                        cache.add(href)
                        save_posted_cache(list(cache))
                    continue
            unposted.append(href)

        return unposted
    except Exception as e:
        logging.error(f"Error fetching course list: {e}")
        return []

def get_course_post(custom_url: str = None) -> dict:
    """
    Universal Scraper: Handles ANY website URL (tamilguru.lk or external sites).
    """
    url = custom_url
    if not url:
        unposted = get_unposted_course_urls(check_blogger=True)
        if not unposted:
            logging.info("[Courses Monitor] All current courses in https://tamilguru.lk/category/courses/ are already published on www.lkuni.com.")
            return None
        url = unposted[0]

    logging.info(f"Target Post URL: {url}")
    parsed_domain = urlparse(url).netloc.lower()
    is_tamilguru = "tamilguru.lk" in parsed_domain

    req = urllib.request.Request(url, headers=HEADERS)
    html = urllib.request.urlopen(req, context=SSL_CTX).read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # 1. Title Extraction
    title = None
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    if not title:
        title_elem = soup.find("h1", class_=re.compile(r"entry-title|post-title|title"))
        if not title_elem:
            title_elem = soup.find("h1")
        if not title_elem:
            title_elem = soup.find("title")
        if title_elem:
            title = title_elem.get_text(strip=True)
    if not title:
        title = "Course Intake Announcement"

    # Clean site brand names from end of title
    title = re.sub(r"\s*([\|\-–—]\s*(tamilguru(\.lk)?|lkuni|daily\s*news|sunday\s*observer|studentlanka|edulanka).*)$", "", title, flags=re.IGNORECASE).strip()

    # 2. Main Content Container
    entry_content = soup.find(["article", "main", "div"], class_=re.compile(r"entry-content|post-content|article-content|story-content|post-body|main-content"))
    if not entry_content:
        entry_content = soup.find("article") or soup.find("main") or soup.find("body") or soup

    # 3. Image Extraction (Resolving relative URLs)
    raw_images = []
    for img in entry_content.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or img.get("data-original")
        if src:
            abs_src = urljoin(url, src)
            if not abs_src.startswith("data:") and not any(skip in abs_src.lower() for skip in ["logo", "icon", "avatar", "whatsapp", "telegram", "facebook", "twitter"]):
                if abs_src not in raw_images:
                    raw_images.append(abs_src)

    # 4. Extract Institute & Year for Head Banner
    institute_name = "Department of Examinations" if ("examination" in title.lower() or "o/l" in title.lower() or "a/l" in title.lower()) else "University of Colombo"
    course_name = title
    year = "2026"

    m_year = re.search(r"\b(202\d(?:/202\d)?)\b", title)
    if m_year:
        year = m_year.group(1)

    if "-" in title:
        parts = title.split("-", 1)
        course_name = parts[0].replace("Intake", "").strip()
        institute_name = parts[1].strip()
    elif "–" in title:
        parts = title.split("–", 1)
        course_name = parts[0].replace("Intake", "").strip()
        institute_name = parts[1].strip()

    # 5. Extract Paragraphs
    paragraphs = []
    for elem in entry_content.find_all(["p", "ul", "ol", "h2", "h3", "h4"]):
        if elem.find_parent("table"):
            continue
        txt = elem.get_text(separator=" ", strip=True)
        if not txt or len(txt) < 5:
            continue
        if any(skip in txt.lower() for skip in ["advertisement", "continue reading", "whatsapp", "telegram", "share this", "leave a reply"]):
            continue
        paragraphs.append((elem.name, elem))

    # 6. Table & Link Harvesting
    table_data = {
        "Notice_Images": [],
        "PDF_Downloads": [],
        "Course Details": None,
        "Apply Now": None,
        "Source": None,
        "Closing Date": None,
        "Website": None,
    }

    # First check tables
    for t in entry_content.find_all("table"):
        for tr in t.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                val_cell = cells[1]
                links = val_cell.find_all("a", href=True)

                if any(k in label for k in ["time table (image)", "paper notice", "ad", "notice", "flyer"]):
                    for a in links:
                        href = urljoin(url, a["href"])
                        clean_h = clean_external_url(href)
                        if clean_h and any(clean_h.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                            table_data["Notice_Images"].append((a.get_text(strip=True), clean_h))
                elif "pdf" in label or "brochure" in label:
                    for a in links:
                        href = urljoin(url, a["href"])
                        clean_h = clean_external_url(href)
                        if clean_h:
                            table_data["PDF_Downloads"].append((a.get_text(strip=True), clean_h))
                elif any(k in label for k in ["course detail", "more detail", "course page"]) and links:
                    table_data["Course Details"] = clean_external_url(urljoin(url, links[0]["href"]))
                elif any(k in label for k in ["application", "apply", "online application"]) and links:
                    table_data["Apply Now"] = clean_external_url(urljoin(url, links[0]["href"]))
                elif "source" in label and links:
                    table_data["Source"] = clean_external_url(urljoin(url, links[0]["href"]))
                elif "website" in label:
                    table_data["Website"] = clean_external_url(urljoin(url, links[0]["href"])) if links else clean_external_url(val_cell.get_text(strip=True))
                elif "closing date" in label:
                    table_data["Closing Date"] = val_cell.get_text(strip=True)

    # If no table or missing links, scan all <a> tags across entry_content
    for a in entry_content.find_all("a", href=True):
        href = clean_external_url(urljoin(url, a["href"]))
        if not href:
            continue
        a_txt = a.get_text(strip=True).lower()
        if href.lower().endswith(".pdf") or "download pdf" in a_txt or "brochure" in a_txt:
            if not any(href == item[1] for item in table_data["PDF_Downloads"]):
                name = a.get_text(strip=True) or "Download PDF"
                table_data["PDF_Downloads"].append((name, href))
        elif any(k in a_txt for k in ["apply online", "apply now", "online application", "register now"]) and not table_data["Apply Now"]:
            table_data["Apply Now"] = href
        elif any(k in a_txt for k in ["course details", "syllabus", "more details", "course page"]) and not table_data["Course Details"]:
            table_data["Course Details"] = href
        elif any(k in a_txt for k in ["official website", "visit website"]) and not table_data["Website"]:
            table_data["Website"] = href

    # Filter out any competitor links
    for k in ["Course Details", "Apply Now", "Source", "Website"]:
        if table_data.get(k):
            table_data[k] = clean_external_url(table_data[k])

    if not table_data["Website"] and table_data.get("Course Details"):
        # Derive website root domain
        parsed_c = urlparse(table_data["Course Details"])
        if parsed_c.scheme and parsed_c.netloc:
            table_data["Website"] = f"{parsed_c.scheme}://{parsed_c.netloc}/"

    if not table_data["Source"]:
        if table_data.get("Course Details"):
            table_data["Source"] = table_data["Course Details"]
        elif table_data.get("Website"):
            table_data["Source"] = table_data["Website"]
        elif is_tamilguru:
            if "examination" in title.lower() or "o/l" in title.lower():
                table_data["Source"] = "https://www.doenets.lk/"
            elif "colombo" in title.lower() or "uciars" in title.lower():
                table_data["Source"] = "https://uciars.cmb.ac.lk/"
        else:
            table_data["Source"] = f"{urlparse(url).scheme}://{parsed_domain}/"

    # Attempt to locate unwatermarked original flyer & PDFs directly from official source / course page
    original_flyer_from_source = None
    target_source_for_flyer = table_data.get("Course Details") or table_data.get("Source") or table_data.get("Website")
    if target_source_for_flyer:
        try:
            official_media = find_original_media_from_source(target_source_for_flyer, course_name=course_name)
            original_flyer_from_source = official_media.get("flyer")
            if original_flyer_from_source:
                logging.info(f"[Original Flyer] Located official flyer from source: {original_flyer_from_source}")
            # If official PDFs were found on official website, add them to table_data
            if official_media.get("pdfs"):
                for p_name, p_href in official_media["pdfs"]:
                    if not any(p_href == item[1] for item in table_data["PDF_Downloads"]):
                        table_data["PDF_Downloads"].append((p_name, p_href))
        except Exception as ofe:
            logging.warning(f"Error finding original media from source: {ofe}")

    # 7. AI Post Synthesis
    ai_syn = synthesize_post_with_ai(
        raw_title=title,
        paragraphs=paragraphs,
        raw_table=table_data,
        default_inst=institute_name,
        default_course=course_name,
        default_year=year
    )

    institution_header = None
    calling_title = None
    course_title_formatted = None
    intro_bold = None
    bullet_items = []
    sinhala_institute = None
    sinhala_calling = None
    sinhala_bullets = []
    if ai_syn:
        title = ai_syn.get("professional_title") or title
        institute_name = ai_syn.get("institute_clean") or institute_name
        course_name = ai_syn.get("course_clean") or course_name
        year = ai_syn.get("year") or year
        institution_header = ai_syn.get("institution_header")
        calling_title = ai_syn.get("calling_title")
        course_title_formatted = ai_syn.get("course_title")
        intro_bold = ai_syn.get("intro_bold")
        bullet_items = ai_syn.get("bullet_items") or []
        sinhala_institute = ai_syn.get("sinhala_institute")
        sinhala_calling = ai_syn.get("sinhala_calling")
        sinhala_bullets = ai_syn.get("sinhala_bullets") or []
        if ai_syn.get("closing_date") and not table_data.get("Closing Date"):
            table_data["Closing Date"] = ai_syn.get("closing_date")

    # 8. Gemini Vision OCR on Flyer Image
    # Scrape flyer from page for OCR (OCR only scans text and does not copy watermarks)
    flyer_candidate_url = None
    if raw_images:
        scored = []
        for u in raw_images:
            s = 0
            lu = u.lower()
            if any(w in lu for w in ["-e.jpg", "_e.jpg", "english"]):
                s += 15
            if any(w in lu for w in ["-ad-", "_ad_", "advertisement", "notice", "paper", "gazette", "flyer", "poster"]):
                s += 10
            if any(w in lu for w in ["syllabus", "structure", "intake"]):
                s += 5
            scored.append((s, u))
        scored.sort(key=lambda x: x[0], reverse=True)
        flyer_candidate_url = scored[0][1]

    if not flyer_candidate_url and original_flyer_from_source:
        flyer_candidate_url = original_flyer_from_source

    if flyer_candidate_url:
        try:
            req = urllib.request.Request(flyer_candidate_url, headers=HEADERS)
            img_bytes = urllib.request.urlopen(req, context=SSL_CTX).read()
            local_flyer = os.path.join(BASE_DIR, "flyer_scraped.jpg")
            with open(local_flyer, "wb") as f:
                f.write(img_bytes)

            vision_data = scan_flyer_with_gemini_vision(local_flyer)
            if vision_data:
                if vision_data.get("institution_header"):
                    institution_header = vision_data["institution_header"]
                if vision_data.get("calling_title"):
                    calling_title = vision_data["calling_title"]
                if vision_data.get("course_title"):
                    course_title_formatted = vision_data["course_title"]
                if vision_data.get("bullet_items") and len(vision_data["bullet_items"]) >= 3:
                    bullet_items = vision_data["bullet_items"]
                if vision_data.get("sinhala_bullets"):
                    sinhala_bullets = vision_data["sinhala_bullets"]
                if vision_data.get("sinhala_institute"):
                    sinhala_institute = vision_data["sinhala_institute"]
                if vision_data.get("sinhala_calling"):
                    sinhala_calling = vision_data["sinhala_calling"]
                if vision_data.get("closing_date") and not table_data.get("Closing Date"):
                    table_data["Closing Date"] = vision_data["closing_date"]
                if vision_data.get("course_name") and len(vision_data["course_name"]) > 5:
                    course_name = vision_data["course_name"]
        except Exception as ve:
            logging.warning(f"Error scanning flyer with vision: {ve}")

    # Fallback headers if not extracted
    if not institution_header:
        institution_header = institute_name
    if not calling_title:
        calling_title = f"Application for Admission of Students to {course_name} ({year})"
    if not course_title_formatted:
        course_title_formatted = f"01. {course_name}"

    return {
        "url": url,
        "title": title,
        "institute_name": institute_name,
        "course_name": course_name,
        "year": year,
        "institution_header": institution_header,
        "calling_title": calling_title,
        "course_title_formatted": course_title_formatted,
        "original_flyer_source": original_flyer_from_source,
        "paragraphs": paragraphs,
        "raw_images": raw_images,
        "table_data": table_data,
        "intro_bold": intro_bold,
        "bullet_items": bullet_items,
        "sinhala_institute": sinhala_institute,
        "sinhala_calling": sinhala_calling,
        "sinhala_bullets": sinhala_bullets,
        "labels": ["COURSES", "UPDATES"]
    }

# ==============================================================================
# GOOGLE DRIVE CDN UPLOADER & BLOGGER PUBLISHER
# ==============================================================================
def get_or_create_drive_folder(drive_service, folder_name: str, parent_id: str = None) -> str:
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']

    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        folder_metadata['parents'] = [parent_id]
    created = drive_service.files().create(body=folder_metadata, fields='id').execute()
    return created.get('id')

def upload_to_google_drive(image_path: str, file_name: str = None, folder_name: str = None) -> str:
    """Uploads image to Google Drive, returns Google CDN thumbnail URL."""
    token_file = os.path.join(BASE_DIR, "token.json")
    if not os.path.exists(token_file):
        logging.error("token.json not found for Drive upload!")
        return None

    try:
        with open(token_file, "r") as f:
            creds_data = json.load(f)
        creds = Credentials.from_authorized_user_info(creds_data)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_file, "w") as f:
                f.write(creds.to_json())

        drive_service = build("drive", "v3", credentials=creds)

        parent_folder_id = get_or_create_drive_folder(drive_service, "LKUni_Blog_Uploads")
        target_folder_id = parent_folder_id
        if folder_name:
            target_folder_id = get_or_create_drive_folder(drive_service, folder_name, parent_id=parent_folder_id)

        actual_file_name = file_name or os.path.basename(image_path)
        file_metadata = {
            'name': actual_file_name,
            'parents': [target_folder_id]
        }
        media = MediaFileUpload(image_path, resumable=True)
        uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = uploaded_file.get('id')

        # Make file publicly readable
        drive_service.permissions().create(
            fileId=file_id,
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()

        cdn_url = f"https://lh3.googleusercontent.com/d/{file_id}"
        logging.info(f"Drive image uploaded: {cdn_url} (Folder: {folder_name or 'Root'})")
        return cdn_url
    except Exception as e:
        logging.error(f"Error uploading to Google Drive: {e}")
        return None

# ==============================================================================
# TELEGRAM NOTIFICATIONS
# ==============================================================================
def send_telegram_notification(data: dict, post_url: str):
    """Sends beautifully formatted Telegram message matching LKUni standards."""
    title = data.get("title", "Course Announcement")
    inst_si = data.get("sinhala_institute") or data.get("institute_name", "විශ්වවිද්‍යාලය")
    calling_si = data.get("sinhala_calling") or f"{data.get('year', '2026')} අධ්‍යයන වර්ෂය සඳහා අයදුම්පත් කැඳවීම"
    table_data = data.get("table_data", {})
    closing_date = table_data.get("Closing Date")

    eng_bullets = []
    for b in data.get("bullet_items", []):
        line = b.strip()
        if not line.startswith("👉"):
            line = f"👉 {line}"
        eng_bullets.append(line)

    si_bullets = []
    for b in data.get("sinhala_bullets", []):
        line = b.strip()
        if not line.startswith("👉"):
            line = f"👉 {line}"
        si_bullets.append(line)

    lines = [
        f"🟩 {title} 🟩",
        "",
        f"🟡 {inst_si} 🟡",
        "",
        f"🟡 {calling_si} 🟡",
        "",
        "Course Details ✅",
        ""
    ]
    if eng_bullets:
        lines.extend(eng_bullets)
        lines.append("")

    if si_bullets:
        lines.extend(si_bullets)
        lines.append("")

    lines.append(f"👉 සම්පූර්ණ විස්තරය : {post_url}")
    if closing_date:
        lines.append(f"👉 Closing Date - {closing_date}")
    lines.append("")
    lines.append("තවත් මෙවැනි අධ්‍යාපනික තොරතුරු දැනගැනීමට ✅")
    lines.append("")
    lines.append("👉 Join Our Telegram Group : https://t.me/different_paths")
    lines.append("")
    lines.append("යාළුවන්ටත් දැනගන්න share කරන්න 👍👍👍")

    msg_text = "\n".join(lines)

    for cid in TELEGRAM_CHAT_IDS:
        cid = cid.strip()
        if not cid:
            continue
        try:
            tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": cid,
                "text": msg_text,
                "disable_web_page_preview": False
            }
            res = requests.post(tg_url, json=payload, timeout=15)
            if res.status_code == 200:
                logging.info(f"Telegram notification delivered to {cid}")
            else:
                logging.warning(f"Telegram returned {res.status_code} for {cid}: {res.text}")
        except Exception as e:
            logging.error(f"Error sending Telegram update to {cid}: {e}")

# ==============================================================================
# BLOGGER PUBLISHER
# ==============================================================================
def publish_via_blogger(data: dict, target_blog_id: str = None) -> dict:
    blog_id = target_blog_id or DEFAULT_BLOG_ID
    title = data.get("title", "Course Announcement")
    table_data = data.get("table_data", {})
    official_source = table_data.get("Source")

    # Clean subfolder name on Drive
    subfolder_name = re.sub(r'[\\/*?:"<>|]', "", title).strip()[:60]

    # Generate head banner
    head_img_path = create_custom_head_image(data["institute_name"], data["course_name"], data["year"])
    head_url = upload_to_google_drive(head_img_path, file_name="thumb-size.png", folder_name=subfolder_name)

    # Upload flyer to Drive (ONLY if from official source, never upload watermarked competitor images)
    flyer_img_path = os.path.join(BASE_DIR, "flyer_scraped.jpg")
    flyer_url = None
    if data.get("original_flyer_source") and os.path.exists(flyer_img_path):
        flyer_url = upload_to_google_drive(flyer_img_path, file_name="flyer.jpg", folder_name=subfolder_name)

    # Build LKUni Table Rows (Strictly original links only - zero competitor/tamilguru links)
    # Order:
    # 1. Document / Detail links first
    # 2. Apply Online link before the source
    # 3. Official Website (source ) at the very end of the table
    regular_rows = []
    apply_rows = []

    # 1. More Details (Course Page)
    if table_data.get("Course Details"):
        regular_rows.append(f'<tr>\n<td>More Details (Course Page)</td>\n<td><a href="{table_data["Course Details"]}" target="_blank">Click Here</a></td>\n</tr>')

    # 2. Notice / Advertisement image ONLY if official original image was located
    if flyer_url:
        regular_rows.append(f'<tr>\n<td>Notice / Advertisement (Image)</td>\n<td><a href="{flyer_url}" target="_blank">Click Here</a></td>\n</tr>')

    # 3. PDF Downloads (STRICT RULE: ONLY from official source domains, NEVER from competitor/tamilguru)
    if table_data.get("PDF_Downloads"):
        clean_pdf_list = []
        for name, p_url in table_data["PDF_Downloads"]:
            clean_u = clean_external_url(p_url)
            # Ensure PDF link is strictly an official website URL and not a competitor re-upload
            if clean_u and not any(comp in clean_u.lower() for comp in ["tamilguru", "tamilguru.lk", "wp-content/uploads"]):
                clean_pdf_list.append((name, clean_u))
        if clean_pdf_list:
            pdf_links = " | ".join([f'<a href="{url}" target="_blank">{name}</a>' for name, url in clean_pdf_list])
            regular_rows.append(f"<tr>\n<td>PDF Download</td>\n<td>{pdf_links}</td>\n</tr>")

    # 4. Closing Date
    if table_data.get("Closing Date"):
        regular_rows.append(f'<tr>\n<td>Closing Date</td>\n<td>{table_data["Closing Date"]}</td>\n</tr>')

    # 5. Online Application (Placed right before the source)
    if table_data.get("Apply Now"):
        apply_rows.append(f'<tr>\n<td>Apply Online</td>\n<td><a href="{table_data["Apply Now"]}" target="_blank">Click Here</a></td>\n</tr>')

    # 6. Official Website / Source at the very end of the table
    source_rows = []
    source_url = table_data.get("Website") or (table_data.get("Source") if table_data.get("Source") != table_data.get("Course Details") else None)
    if source_url:
        clean_w_disp = urlparse(source_url).netloc or source_url
        source_rows.append(f'<tr>\n<td>Official Website (source )</td>\n<td><a href="{source_url}" target="_blank">{clean_w_disp}</a></td>\n</tr>')

    table_rows = regular_rows + apply_rows + source_rows
    table_rows_html = "\n".join(table_rows)

    # Build full LKUni HTML layout
    arranged_content = ""
    if head_url:
        arranged_content += f"""<div class="separator" style="clear: both; text-align: center;">
<a href="{head_url}" style="margin-left: 1em; margin-right: 1em;">
<img border="0" data-original-height="1066" data-original-width="1600" src="{head_url}"/>
</a>
</div>
<br/>
"""

    # Post Body: Minimal & Clean point-by-point explanation recreated from OCR/details
    inst_header = data.get("institution_header") or data.get("institute_name")
    call_title = data.get("calling_title") or f"Application for Admission of Students to {data.get('course_name')} ({data.get('year', '2026')})"
    c_title = data.get("course_title_formatted") or f"01. {data.get('course_name')}"

    arranged_content += f"""<p><b>{inst_header}</b></p>
<p><b>{call_title}</b></p>
<p><b>{c_title}</b></p>
<div>
"""
    for b in data.get("bullet_items", []):
        b_clean = b.strip()
        if not (b_clean.startswith("*") or b_clean.startswith("👉") or b_clean.startswith("•")):
            b_clean = f"* {b_clean}"
        arranged_content += f'<p class="MsoNormal"><b>{b_clean}</b></p>\n'

    arranged_content += """</div>
<br/>
"""
    arranged_content += f"""<style>
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
<th>Details</th>
<th>Links</th>
</tr>
{table_rows_html}
</tbody>
</table>
<br/>
"""

    token_file = os.path.join(BASE_DIR, "token.json")
    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            creds_data = json.load(f)
        creds = Credentials.from_authorized_user_info(creds_data)
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(token_file, "w") as f:
                    f.write(creds.to_json())
            except Exception as e:
                logging.warning(f"Error refreshing OAuth token: {e}")

        service = build("blogger", "v3", credentials=creds)
        inserted = service.posts().insert(
            blogId=blog_id,
            body={
                "title": title,
                "content": arranged_content,
                "labels": data.get("labels", ["COURSES"])
            },
            isDraft=False
        ).execute()

        post_url = inserted.get('url')
        logging.info(f"Post published successfully to Blogger! ID: {inserted.get('id')} URL: {post_url}")

        # Send Telegram notification
        try:
            send_telegram_notification(data, post_url)
        except Exception as te:
            logging.error(f"Error in Telegram notification: {te}")

        # Cleanup temporary files
        for tmp_f in [flyer_img_path, os.path.join(BASE_DIR, "flyer_scraped.jpg")]:
            if tmp_f and os.path.exists(tmp_f):
                try: os.remove(tmp_f)
                except Exception: pass

        return {
            "status": "success",
            "id": inserted.get("id"),
            "url": post_url,
            "title": title
        }
    else:
        raise FileNotFoundError("token.json not found! Cannot publish to Blogger.")

def trash_lkuni_post(post_id: str, blog_id: str = OFFICIAL_BLOG_ID) -> dict:
    """Moves a post to Blogger Trash using Google Blogger API."""
    token_file = os.path.join(BASE_DIR, "token.json")
    if not os.path.exists(token_file):
        return {"status": "error", "message": "token.json not found"}
    try:
        with open(token_file, "r") as f:
            creds_data = json.load(f)
        creds = Credentials.from_authorized_user_info(creds_data)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_file, "w") as f:
                f.write(creds.to_json())
        service = build("blogger", "v3", credentials=creds)

        # Retrieve title and url first
        try:
            post = service.posts().get(blogId=blog_id, postId=post_id).execute()
            title = post.get("title", f"Post {post_id}")
            url = post.get("url", "")
        except Exception:
            title = f"Post {post_id}"
            url = ""

        # Move to trash
        service.posts().delete(blogId=blog_id, postId=post_id, useTrash=True).execute()
        logging.info(f"Post {post_id} ('{title}') moved to Blogger trash.")

        # Remove from caches if present
        for cfile in [CACHE_FILE, os.path.join(BASE_DIR, "guruwaraya_posted_cache.json")]:
            if os.path.exists(cfile):
                try:
                    with open(cfile, "r") as fp:
                        c_data = json.load(fp)
                    if isinstance(c_data, list):
                        new_c = [x for x in c_data if (url and url not in str(x)) and post_id not in str(x)]
                        with open(cfile, "w") as fp:
                            json.dump(new_c, fp, indent=2)
                except Exception:
                    pass

        return {"status": "success", "title": title, "id": post_id, "url": url}
    except Exception as e:
        logging.error(f"Error trashing post {post_id}: {e}")
        return {"status": "error", "message": str(e)}

# ==============================================================================
# ENTRYPOINTS FOR CRON & BOT
# ==============================================================================
def process_and_publish_url(url: str, target_blog_id: str = OFFICIAL_BLOG_ID, force: bool = False) -> dict:
    """Takes any arbitrary URL, verifies uniqueness, checks closing date, and publishes to LKUni."""
    logging.info(f"[Process URL] Starting processing for: {url}")
    post_data = get_course_post(custom_url=url)
    if not post_data:
        return {"status": "error", "message": "Failed to extract content from URL."}

    # Verify Closing Date - If expired, do not post to blog unless force is True
    closing_date = post_data.get("table_data", {}).get("Closing Date")
    if is_date_expired(closing_date) and not force:
        logging.info(f"[Expired Notice] Closing date {closing_date} has already expired. Skipping blog post.")
        cache = load_posted_cache()
        if url not in cache:
            cache.append(url)
            save_posted_cache(cache)
        return {
            "status": "expired",
            "title": post_data["title"],
            "closing_date": closing_date,
            "message": f"Notice closing date ({closing_date}) is already expired. Post skipped."
        }

    # Verify duplicate on Blogger
    blogger_titles = fetch_recent_blogger_titles(blog_id=target_blog_id)
    is_dup, matched_title = is_duplicate_on_blogger(post_data["title"], blogger_titles)
    if is_dup:
        logging.info(f"[Duplicate Detected] '{post_data['title']}' matches existing '{matched_title}'")
        cache = load_posted_cache()
        if url not in cache:
            cache.append(url)
            save_posted_cache(cache)
        return {
            "status": "duplicate",
            "title": post_data["title"],
            "matched_title": matched_title,
            "message": f"This post already exists on www.lkuni.com: '{matched_title}'"
        }

    res = publish_via_blogger(post_data, target_blog_id=target_blog_id)
    if res.get("status") == "success":
        cache = load_posted_cache()
        if url not in cache:
            cache.append(url)
            save_posted_cache(cache)
        res["title"] = post_data["title"]
    return res

def check_and_publish_latest(target_blog_id: str = OFFICIAL_BLOG_ID, gap_seconds: int = 120, max_posts: int = 5) -> dict:
    """
    Checks tamilguru.lk, verifies against lkuni.com, and publishes all new active courses
    during the 8:00 PM run with a 2-minute gap (gap_seconds=120) between published posts.
    """
    unposted = get_unposted_course_urls(check_blogger=True)
    if not unposted:
        return {
            "status": "no_updates",
            "message": "No new updates detected. All latest courses are already published on www.lkuni.com."
        }

    logging.info(f"[Check & Publish] Found {len(unposted)} candidate unposted course(s). Starting batch processing...")
    results = []
    published_count = 0

    for idx, next_url in enumerate(unposted):
        if published_count >= max_posts:
            logging.info(f"[Batch Limit Reached] Published {published_count} posts in this run. Stopping.")
            break

        # If a post was already published in this run, wait 2 minutes (120s) before publishing the next one
        if published_count > 0:
            logging.info(f"[Delay Gap] Waiting {gap_seconds}s (2 minutes) before publishing next course to LKUni...")
            time.sleep(gap_seconds)

        logging.info(f"[Check & Publish] Candidate ({idx + 1}/{len(unposted)}): {next_url}")
        result = process_and_publish_url(next_url, target_blog_id=target_blog_id)
        results.append(result)

        if result.get("status") == "success":
            published_count += 1
            logging.info(f"[Success] Successfully published #{published_count}: {result.get('title')}")
        elif result.get("status") in ["expired", "duplicate"]:
            cache = load_posted_cache()
            if next_url not in cache:
                cache.append(next_url)
                save_posted_cache(cache)
            logging.info(f"[Skipped] Candidate ({result.get('status')}): {result.get('message')}")

    if published_count == 0:
        return {
            "status": "no_new_active_courses",
            "message": "Processed candidate courses but all were either expired or already published.",
            "results": results
        }

    return {
        "status": "success",
        "published_count": published_count,
        "total_processed": len(results),
        "results": results
    }

# ==============================================================================
# MAIN CLI
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="LKUni Tamil Courses Auto Blogger & Daily Monitor")
    parser.add_argument("--url", default=None, help="Specific post URL to scrape and post")
    parser.add_argument("--test-blog", action="store_true", help="Post to test blog instead of official")
    parser.add_argument("--check-only", action="store_true", help="Check for updates without posting")
    parser.add_argument("--force", action="store_true", help="Force publish even if closing date is expired")
    parser.add_argument("--send-list", action="store_true", help="Send today's selection list to Telegram (8:00 PM cron default)")
    parser.add_argument("--auto-publish", action="store_true", help="Batch auto-publish active courses directly")
    args = parser.parse_args()

    target_blog_id = TEST_BLOG_ID if args.test_blog else OFFICIAL_BLOG_ID

    if args.url:
        res = process_and_publish_url(args.url, target_blog_id=target_blog_id, force=args.force)
        print("Result:", res)
        return

    if args.check_only:
        unposted = get_unposted_course_urls(check_blogger=True)
        print(f"Unposted courses found: {len(unposted)}")
        for u in unposted:
            print(f"- {u}")
        return

    if args.auto_publish:
        res = check_and_publish_latest(target_blog_id=target_blog_id)
        logging.info(f"Auto-publish batch completed: {res}")
        return

    # Default scheduled run (8:00 PM) - Send daily TamilGuru course selection list to Telegram
    from tamilguru_bot import send_tamilguru_selection_list
    logging.info("Running 8:00 PM daily TamilGuru course selection list broadcast...")
    res = send_tamilguru_selection_list(chat_id=1499235921)
    logging.info(f"8:00 PM Telegram course selection list sent: {res}")

if __name__ == "__main__":
    main()
