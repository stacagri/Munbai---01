import pymupdf

pdf_files = ["/tmp/English.pdf", "/tmp/Sinhala.pdf", "/tmp/Tamil.pdf"]

for path in pdf_files:
    doc = pymupdf.open(path)
    cleaned = False
    for page in doc:
        # Search for text
        rects = page.search_for("tamilguru")
        for r in rects:
            print(f"Redacting rect {r} in {path}")
            # Add redaction with clean fill matching background (white)
            page.add_redact_annot(r, fill=(1, 1, 1))
            cleaned = True
        if cleaned:
            page.apply_redactions()
    
    clean_path = path.replace(".pdf", "_clean.pdf")
    doc.save(clean_path)
    print(f"Saved {clean_path}")

# Verify cleaned PDFs
for path in ["/tmp/English_clean.pdf", "/tmp/Sinhala_clean.pdf", "/tmp/Tamil_clean.pdf"]:
    doc = pymupdf.open(path)
    text = doc[0].get_text()
    print(f"[{path}] Contains 'tamilguru': {'tamilguru' in text.lower()}")
