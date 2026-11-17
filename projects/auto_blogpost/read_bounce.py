import imaplib
import email

mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login("stacagri08@gmail.com", "qljogplfupxdcmhl")
mail.select("inbox")

status, messages = mail.search(None, "ALL")
mail_ids = messages[0].split()
last_fail = mail_ids[-1]
status, data = mail.fetch(last_fail, "(RFC822)")
msg = email.message_from_bytes(data[0][1])
print("Subject:", msg.get("Subject"))
for part in msg.walk():
    if part.get_content_type() == "text/plain":
        print("Body:\n", part.get_payload(decode=True).decode(errors="ignore"))
