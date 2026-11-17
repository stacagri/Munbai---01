import pymupdf

for name in ["English", "Sinhala"]:
    doc = pymupdf.open(f"/tmp/{name}.pdf")
    page = doc[0]
    for block in page.get_text("blocks"):
        txt = block[4]
        if "tamilguru" in txt.lower():
            print(f"[{name}] Block rect: {block[:4]}")
            print(f"[{name}] Text: {repr(txt)}")
