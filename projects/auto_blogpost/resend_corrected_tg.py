import requests

BOT_TOKEN = "9269727444:AAHwsO8xw7__8BWWfxSGNDWuUnwF7lQ6FVw"
CHATS = ["1499235921", "@differentpaths"]

msg = """🟩 Application For Bachelor of Business Administration (BBA) External Degree - 2026 - University of Peradeniya 🟩

🟡 පේරාදෙණිය විශ්වවිද්‍යාලය, දුරස්ථ හා අඛණ්ඩ අධ්‍යාපන මධ්‍යස්ථානය (CDCE) 🟡

🟡 2026 අධ්‍යයන වර්ෂය සඳහා ව්‍යාපාර පරිපාලනවේදී (BBA) බාහිර උපාධි පාඨමාලාව සඳහා අයදුම්පත් කැඳවීම 🟡

Course Details ✅

👉 Mode of Delivery: Blended (Online & Face-to-Face)
👉 Medium: English
👉 Duration: Minimum 03 Years
👉 Entry Qualifications: Pass in one sitting at G.C.E. (A/L) examination in any stream
👉 Structure: Diploma (Yr 1) ➔ Higher Diploma (Yr 2) ➔ BBA Degree (Yr 3)
👉 Application Processing Fee: Rs. 1,500/-

👉 අවම වශයෙන් වසර 3 ක කාලසීමාව
👉 ඕනෑම විෂය ධාරාවකින් උසස් පෙළ (A/L) එකවර සමතුන්ට අයදුම් කළ හැක
👉 ඉංග්‍රීසි මාධ්‍යයෙන් හැදෑරිය හැක

👉 සම්පූර්ණ විස්තරය : https://www.lkuni.com/2026/11/application-for-bachelor-of-business.html

👉 Closing Date - 30/11/2026

තවත් මෙවැනි අධ්‍යාපනික තොරතුරු දැනගැනීමට ✅

👉 Join Our Telegram Group : https://t.me/different_paths

යාළුවන්ටත් දැනගන්න share කරන්න 👍👍👍"""

for c in CHATS:
    res = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": c, "text": msg, "disable_web_page_preview": False},
        timeout=15
    )
    print(f"Sent to {c}:", res.status_code, res.text)
