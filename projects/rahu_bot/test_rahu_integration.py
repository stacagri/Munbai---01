import sys
sys.path.append("/home/ubuntu/birthday_bot")
from birthday_bot import fetch_sheet_people, generate_birthday_card
import datetime

people = fetch_sheet_people(force_refresh=True)
print(f"Total contacts: {len(people)}")

# Test with Vishaka as if today was Nov 5
today_matches = [p for p in people if "vishaka" in p.clean_english_name.lower()]
print(f"Sample match: {today_matches[0].clean_english_name}")

bday_lines = ["\n🎂 *Today's Birthday:*"]
for p in today_matches:
    bday_lines.append(f"🎉 HAPPY BIRTHDAY! Dear {p.clean_english_name} Teacher ✨ Wishing our dear teacher immense happiness and success! 🌸")

bday_text = "\n".join(bday_lines)
print("\nGenerated Birthday Section:\n" + bday_text)
