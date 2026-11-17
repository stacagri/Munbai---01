import urllib.request, ssl, pytesseract, cv2
from PIL import Image

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

img_urls = [
    ("Flyer", "https://tamilguru.lk/wp-content/uploads/2026/10/GCE-OL-Exam-Time-Table-2026-Department-of-Examinations.jpg"),
    ("English_JPG", "https://tamilguru.lk/wp-content/uploads/2026/10/GCE-OL-Examination-Time-Table-2026-English.jpg"),
    ("Sinhala_JPG", "https://tamilguru.lk/wp-content/uploads/2026/10/GCE-OL-Examination-Time-Table-2026-Sinhala.jpg"),
    ("Tamil_JPG", "https://tamilguru.lk/wp-content/uploads/2026/10/GCE-OL-Examination-Time-Table-2026-Tamil.jpg")
]

for label, url in img_urls:
    p = f"/tmp/{label}.jpg"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx) as r:
        with open(p, "wb") as f:
            f.write(r.read())
    
    img = cv2.imread(p)
    text = pytesseract.image_to_string(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
    has_wm = "tamilguru" in text.lower()
    print(f"[{label}] Contains 'tamilguru': {has_wm}")
    if has_wm:
        # Find where it appears
        data = pytesseract.image_to_data(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)), output_type=pytesseract.Output.DICT)
        for i, word in enumerate(data['text']):
            if 'tamilguru' in word.lower():
                print(f"  Found '{word}' at x={data['left'][i]}, y={data['top'][i]}, w={data['width'][i]}, h={data['height'][i]}")
