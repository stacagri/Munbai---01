import requests

BOT_TOKEN = "9269727444:AAHwsO8xw7__8BWWfxSGNDWuUnwF7lQ6FVw"
CHAT_ID = "1499235921"

msg_text = """🟩 Application For Bachelor of Agro-Technology (Honours) - 2026 - University of Colombo (UCIARS) 🟩

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

res = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    json={"chat_id": CHAT_ID, "text": msg_text, "disable_web_page_preview": False},
    timeout=15
)
print("Response:", res.status_code, res.text)
