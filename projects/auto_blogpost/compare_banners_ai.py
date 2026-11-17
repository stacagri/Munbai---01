import os, json, base64, requests

KEY = os.getenv("GEMINI_API_KEY", "REDACTED_GCP_API_KEY")

with open("/home/ubuntu/auto_blogpost/original_sample_banner.png", "rb") as f:
    b64_orig = base64.b64encode(f.read()).decode("utf-8")

with open("/home/ubuntu/auto_blogpost/thumb-size.png", "rb") as f:
    b64_curr = base64.b64encode(f.read()).decode("utf-8")

prompt = """Compare these two banner images in detail.
Image 1 is the original authentic template/banner from www.lkuni.com.
Image 2 is what was newly generated.

Explain:
1. What design elements, colors, text styles, borders, or branding are missing or incorrect in Image 2 compared to Image 1?
2. Exactly why the user said 'image came like this' regarding Image 2?
3. List the exact layout, colors, fonts, and elements that need to be fixed so Image 2 matches Image 1 100%.
"""

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={KEY}"
payload = {
    "contents": [{
        "parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/png", "data": b64_orig}},
            {"inline_data": {"mime_type": "image/png", "data": b64_curr}}
        ]
    }]
}
res = requests.post(url, json=payload, timeout=30)
print(res.json()["candidates"][0]["content"]["parts"][0]["text"])
