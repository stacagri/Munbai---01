import pymupdf, os, base64, requests

KEY = os.getenv("GEMINI_API_KEY", "REDACTED_GCP_API_KEY")

for name in ["English", "Sinhala", "Tamil"]:
    doc = pymupdf.open(f"/tmp/{name}_clean.pdf")
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    img_out = f"/tmp/{name}_page.png"
    pix.save(img_out)

    with open(img_out, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    prompt = "Look at this timetable document carefully. Are there ANY watermarks, website names, or logos of 'tamilguru' anywhere in this document? If clean, answer '100% CLEAN'."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={KEY}"
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/png", "data": b64}}
            ]
        }]
    }
    res = requests.post(url, json=payload, timeout=30)
    print(f"=== {name}_clean.pdf ===")
    print(res.json()["candidates"][0]["content"]["parts"][0]["text"])
