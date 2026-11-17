import cv2
import pytesseract
from PIL import Image

img_path = "/home/ubuntu/auto_blogpost/flyer_for_email.jpg"
text = pytesseract.image_to_string(Image.open(img_path))
print("Length of OCR text:", len(text))
for line in text.split("\n"):
    if any(k in line.lower() for k in ["tamil", "guru", "lk", "www", "http", ".com"]):
        print("Matching line:", repr(line))
