import os, base64, requests

KEY = os.getenv("GEMINI_API_KEY", "REDACTED_GCP_API_KEY")

for name in ["Flyer", "English_JPG", "Sinhala_JPG"]:
    with open(f"/tmp/{name}.jpg", "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    prompt = "Look at this image very carefully. Does this image have any watermark, website URL, or logo of 'tamilguru' or 'tamilguru.lk'? If yes, describe where it is located (e.g. coordinates, top, bottom, center, corners) and what it looks like."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={KEY}"
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": b64}}
            ]
        }]
    }
    res = requests.post(url, json=payload, timeout=30)
    print(f"=== {name} ===")
    print(res.json()["candidates"][0]["content"]["parts"][0]["text"])
