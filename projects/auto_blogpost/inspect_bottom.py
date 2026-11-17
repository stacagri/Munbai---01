import cv2
import pytesseract
from PIL import Image

orig = cv2.imread('/home/ubuntu/auto_blogpost/original_sample_banner.png')
bot = orig[850:1066, :]
bot_text = pytesseract.image_to_string(Image.fromarray(cv2.cvtColor(bot, cv2.COLOR_BGR2RGB)))
print("Bottom text OCR:\n", bot_text)

# Also let's inspect the entire original image visually by checking elements
tpl = cv2.imread('/home/ubuntu/auto_blogpost/thumb_template.png')
tpl_bot = tpl[850:1066, :]
tpl_bot_text = pytesseract.image_to_string(Image.fromarray(cv2.cvtColor(tpl_bot, cv2.COLOR_BGR2RGB)))
print("Template bottom text OCR:\n", tpl_bot_text)
