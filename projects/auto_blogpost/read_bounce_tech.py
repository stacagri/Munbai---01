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
for part in msg.walk():
    payload = part.get_payload(decode=True)
    if payload:
        print("PART CONTENT:", payload.decode(errors="ignore"))
