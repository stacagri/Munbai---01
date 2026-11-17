import os, json, base64, requests

KEY = os.getenv("GEMINI_API_KEY", "REDACTED_GCP_API_KEY")

with open("/home/ubuntu/auto_blogpost/original_sample_banner.png", "rb") as f:
    b64_orig = base64.b64encode(f.read()).decode("utf-8")

with open("/home/ubuntu/auto_blogpost/test_ndt_thumb.png", "rb") as f:
    b64_new = base64.b64encode(f.read()).decode("utf-8")

prompt = """Compare these two banner images.
Image 1 is the authentic reference template from www.lkuni.com.
Image 2 is our newly generated image.

Does Image 2 now preserve the exact layout, the yellow www.LkUni.com bar at the bottom, the green institute bar, the deep blue title text, and the year?
Rate the match on a scale of 1 to 10 and mention any final polish needed.
"""

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={KEY}"
payload = {
    "contents": [{
        "parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/png", "data": b64_orig}},
            {"inline_data": {"mime_type": "image/png", "data": b64_new}}
        ]
    }]
}
res = requests.post(url, json=payload, timeout=30)
print(res.json()["candidates"][0]["content"]["parts"][0]["text"])
