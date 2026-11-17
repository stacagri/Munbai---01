import base64
import json
import requests

API_KEY = "REDACTED_GCP_API_KEY"

with open("/home/ubuntu/auto_blogpost/peradeniya_1.jpg", "rb") as f:
    b64_img = base64.b64encode(f.read()).decode("utf-8")

prompt = """Carefully read and transcribe all text from this educational course advertisement image.
Extract the key course details, entry qualifications, course structure, duration, medium, fee, and closing date.
IMPORTANT: Ignore and DO NOT include any watermarks or branding such as 'tamilguru' or 'tamilguru.lk'.

Output a structured JSON object:
{
  "institute": "Exact Institute Name",
  "degree_name": "Full Degree Name",
  "year": "2026",
  "entry_qualifications": ["Qualification 1", "Qualification 2"],
  "course_details": [
    "👉 Key detail 1",
    "👉 Key detail 2",
    "👉 Key detail 3",
    "👉 Key detail 4",
    "👉 Key detail 5"
  ],
  "sinhala_institute": "ආයතනයේ නම සිංහලෙන්",
  "sinhala_calling": "පාඨමාලා විස්තරය සිංහලෙන්",
  "sinhala_details": [
    "👉 සිංහල විස්තරය 1",
    "👉 සිංහල විස්තරය 2",
    "👉 සිංහල විස්තරය 3"
  ],
  "closing_date": "Closing date if mentioned"
}
"""

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={API_KEY}"
payload = {
    "contents": [{
        "parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/jpeg", "data": b64_img}}
        ]
    }],
    "generationConfig": {"response_mime_type": "application/json"}
}

res = requests.post(url, json=payload, timeout=30)
if res.status_code == 200:
    print("Gemini Vision Success!")
    txt = res.json()["candidates"][0]["content"]["parts"][0]["text"]
    print(txt)
    with open("/home/ubuntu/auto_blogpost/gemini_extracted.json", "w") as out_f:
        out_f.write(txt)
else:
    print("Error:", res.status_code, res.text)
