import urllib.request, ssl, pymupdf

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://tamilguru.lk/wp-content/uploads/2026/10/GCE-OL-Examination-Time-Table-2026-Tamil.pdf"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, context=ctx) as r:
    with open("/tmp/Tamil.pdf", "wb") as f:
        f.write(r.read())

doc = pymupdf.open("/tmp/Tamil.pdf")
for block in doc[0].get_text("blocks"):
    if "tamilguru" in block[4].lower():
        print("[Tamil] Block rect:", block[:4])
        print("[Tamil] Text:", repr(block[4]))
