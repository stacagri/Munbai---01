import cv2
import pytesseract
from PIL import Image

orig = cv2.imread('/home/ubuntu/auto_blogpost/original_sample_banner.png')
print("Original shape:", orig.shape)
ocr_text = pytesseract.image_to_string(Image.fromarray(cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)))
print("Original OCR text:\n", ocr_text)

# Also check template OCR text
tpl = cv2.imread('/home/ubuntu/auto_blogpost/thumb_template.png')
tpl_text = pytesseract.image_to_string(Image.fromarray(cv2.cvtColor(tpl, cv2.COLOR_BGR2RGB)))
print("Template OCR text:\n", tpl_text)
