import pymupdf  # PyMuPDF
import cv2
import numpy as np

# Download or check the local PDFs if they exist or download them
import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urls = {
    "English": "https://tamilguru.lk/wp-content/uploads/2026/10/GCE-OL-Examination-Time-Table-2026-English.pdf",
    "Sinhala": "https://tamilguru.lk/wp-content/uploads/2026/10/GCE-OL-Examination-Time-Table-2026-Sinhala.pdf"
}

for name, url in urls.items():
    pdf_path = f"/tmp/{name}.pdf"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx) as r:
        with open(pdf_path, "wb") as f:
            f.write(r.read())
    
    doc = pymupdf.open(pdf_path)
    print(f"=== {name} PDF ({len(doc)} pages) ===")
    for i, page in enumerate(doc):
        text = page.get_text()
        print(f"Page {i+1} text length: {len(text)}")
        if "tamilguru" in text.lower():
            print(f"  [FOUND TEXT WATERMARK] on page {i+1}!")
        images = page.get_images()
        print(f"  Page {i+1} images count: {len(images)}")
