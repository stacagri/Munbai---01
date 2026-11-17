import sys
sys.path.append("/home/ubuntu/birthday_bot")
import birthday_bot

people = birthday_bot.fetch_sheet_people()
p = [x for x in people if "vishaka" in x.clean_english_name.lower()][0]
birthday_bot.broadcast_birthday(p, [1499235921])
print("SAMPLE_UPDATED_DELIVERED")
