import time
import requests

BOT_TOKEN = "9269727444:AAHwsO8xw7__8BWWfxSGNDWuUnwF7lQ6FVw"
CHANNEL_ID = "@differentpaths"

# Post 1: Agro-Technology
post1 = """🟩 Application For Bachelor of Agro-Technology (Honours) - 2026 - University of Colombo (UCIARS) 🟩

🟡 කොළඹ විශ්වවිද්‍යාලයීය කෘෂි තාක්‍ෂණ හා ග්‍රාමීය විද්‍යායතනය (UCIARS) 🟡

🟡 2026/2027 අධ්‍යයන වර්ෂය සඳහා කෘෂි තාක්ෂණවේදී උපාධි පාඨමාලාව සඳහා අයදුම්පත් කැඳවීම 🟡

Course Details ✅

👉 Campus Location: Weligatta, Hambantota
👉 Duration: 4 Years (Full-Time or Part-Time)
👉 Medium: English or Sinhala

👉 කෘෂි තාක්‍ෂණවේදී ගෞරව උපාධිය (Bachelor of Agro-Technology)
👉 පූර්ණකාලීන හෝ අර්ධකාලීන හැදෑරීමේ හැකියාව
👉 සිංහල හෝ ඉංග්‍රීසි මාධ්‍යයෙන් හැදෑරිය හැක

👉 සම්පූර්ණ විස්තරය : https://www.lkuni.com/2026/11/application-for-bachelor-of-agro.html

👉 Closing Date - 03/12/2026

තවත් මෙවැනි අධ්‍යාපනික තොරතුරු දැනගැනීමට ✅

👉 Join Our Telegram Group : https://t.me/different_paths

යාළුවන්ටත් දැනගන්න share කරන්න 👍👍👍"""

# Post 2: Ocean University
post2 = """🟩 Application For External Degree Programs - 2027 - Ocean University of Sri Lanka 🟩

🟡 ශ්‍රී ලංකා සාගර විශ්වවිද්‍යාලය 🟡

🟡 2027 අධ්‍යයන වර්ෂය සඳහා බාහිර උපාධි පාඨමාලා සඳහා අයදුම්පත් කැඳවීම 🟡

Course Details ✅

👉 BSc in Maritime Transportation Management and Logistics (General)
👉 BSc in Supply Chain Management (General)
👉 Duration: 03 Years
👉 Medium: English

👉 සමුද්‍ර ප්‍රවාහන කළමනාකරණය සහ ලොජිස්ටික්ස් විද්‍යාවේදී (බාහිර) උපාධිය
👉 සැපයුම් දාම කළමනාකරණ විද්‍යාවේදී (බාහිර) උපාධිය
👉 කාලසීමාව: වසර 03 (ඉංග්‍රීසි මාධ්‍යය)

👉 සම්පූර්ණ විස්තරය : https://www.lkuni.com/2026/11/application-for-external-degree.html

👉 Closing Date - 15/12/2026

තවත් මෙවැනි අධ්‍යාපනික තොරතුරු දැනගැනීමට ✅

👉 Join Our Telegram Group : https://t.me/different_paths

යාළුවන්ටත් දැනගන්න share කරන්න 👍👍👍"""

for idx, p in enumerate([post1, post2], 1):
    res = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHANNEL_ID, "text": p, "disable_web_page_preview": False},
        timeout=15
    )
    print(f"Post {idx} result:", res.status_code, res.text)
    time.sleep(2)
