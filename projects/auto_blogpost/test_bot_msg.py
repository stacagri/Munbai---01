import telegram_listener

res = telegram_listener.send_message(
    chat_id=1499235921,
    text="🤖 *LKUni Blog Automation Bot is Online!*\n\n• Use *🔍 /check* to check tamilguru.lk on demand\n• Send *any link* to convert it to an official LKUni post\n• Daily scan continues at 8:00 PM Sri Lanka Time",
    reply_markup=telegram_listener.REPLY_KEYBOARD
)
print("Telegram Send Result:", res.get("ok"))
