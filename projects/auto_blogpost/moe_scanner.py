import requests
from bs4 import BeautifulSoup
import time
import sys

SERVER_URL = "http://92.4.72.58:8080/upload_moe"

headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
}

def find_latest_article_url(html_content, base_pattern):
    soup = BeautifulSoup(html_content, "html.parser")
    main = soup.find("main") or soup
    for a in main.find_all("a", href=True):
        h = a["href"].strip()
        t = a.get_text(strip=True)
        if base_pattern in h and len(t) > 20:
            if not any(skip in h.lower() for skip in ["special-notices", "%e0%b7%80%e0%b7%92%e0%b7%81%e0%b7%9a%e0%b7%82-%e0%b6%b1%e0%b7%92%e0%b7%80%e0%b7%9a%e0%b6%af%e0%b6%b1", "#", "category", "tag", "page"]):
                return h
    return None

def fetch_full_notice(listing_url, base_pattern, label):
    try:
        print(f"Connecting to MOE {label} listing page...")
        r_list = requests.get(listing_url, headers=headers, timeout=25)
        if r_list.status_code != 200:
            print(f"⚠️ {label} listing returned HTTP {r_list.status_code}")
            return "", ""

        article_url = find_latest_article_url(r_list.text, base_pattern)
        if article_url:
            print(f"📄 Found latest {label} article URL: {article_url}")
            r_art = requests.get(article_url, headers=headers, timeout=25)
            if r_art.status_code == 200:
                print(f"✅ Downloaded full {label} notice page with PDFs ({len(r_art.text)} bytes)")
                return r_art.text, article_url
            else:
                print(f"⚠️ Could not fetch article: HTTP {r_art.status_code}")
        else:
            print(f"⚠️ Could not locate individual article link for {label}")

        return r_list.text, listing_url
    except Exception as e:
        print(f"❌ Error fetching {label}: {e}")
        return "", ""

def scan_and_push(publish_now=False):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Connecting to moe.gov.lk from phone...")

    # 1. Fetch full English Notice page & source URL
    en_html, en_source = fetch_full_notice(
        "https://moe.gov.lk/en/special-notices/",
        "https://moe.gov.lk/en/",
        "English"
    )

    # 2. Fetch full Sinhala Notice page & source URL
    si_html, si_source = fetch_full_notice(
        "https://moe.gov.lk/si-lk/%e0%b7%80%e0%b7%92%e0%b7%81%e0%b7%9a%e0%b7%82-%e0%b6%b1%e0%b7%92%e0%b7%80%e0%b7%9a%e0%b6%af%e0%b6%b1/",
        "https://moe.gov.lk/si-lk/",
        "Sinhala"
    )

    if not en_html and not si_html:
        print("❌ Could not download pages from moe.gov.lk.")
        return

    # 3. Push to Server
    print("📤 Pushing full notice data to LKUni VM Server...")
    payload = {
        "en_html": en_html,
        "si_html": si_html,
        "en_source_url": en_source,
        "si_source_url": si_source,
        "publish_now": publish_now
    }

    try:
        res = requests.post(SERVER_URL, json=payload, timeout=30)
        if res.status_code == 200:
            data = res.json()
            print("\n🎉 SUCCESS! Data received by VM server:")
            print(f"• English Title: {data.get('en_title')}")
            print(f"• Sinhala Title: {data.get('si_title')}")
            print(f"• English PDFs Found: {data.get('en_pdfs')}")
            print(f"• Sinhala PDFs Found: {data.get('si_pdfs')}")
            if data.get("mode") == "catchup_published":
                print(f"• Status: PUBLISHED LIVE! -> {data.get('url')}")
            else:
                print("• Status: Staged for 6:30 PM publishing!")
        else:
            print(f"Server error HTTP {res.status_code}: {res.text}")
    except Exception as e:
        print(f"❌ Error uploading to server: {e}")

if __name__ == "__main__":
    publish_immediate = "--publish-now" in sys.argv
    scan_and_push(publish_now=publish_immediate)
