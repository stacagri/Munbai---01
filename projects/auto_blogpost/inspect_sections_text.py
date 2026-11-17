import cv2
import pytesseract
from PIL import Image

orig = cv2.imread('/home/ubuntu/auto_blogpost/original_sample_banner.png')
yel_box = orig[808:916, :]
t = pytesseract.image_to_string(Image.fromarray(cv2.cvtColor(yel_box, cv2.COLOR_BGR2RGB)))
print("Yellow bar text:\n", repr(t))

# What is between 305 and 807?
mid_box = orig[305:808, :]
t_mid = pytesseract.image_to_string(Image.fromarray(cv2.cvtColor(mid_box, cv2.COLOR_BGR2RGB)))
print("Middle box text:\n", repr(t_mid))

# What is between 917 and 1066?
bot_box = orig[917:1066, :]
t_bot = pytesseract.image_to_string(Image.fromarray(cv2.cvtColor(bot_box, cv2.COLOR_BGR2RGB)))
print("Bottom text (917-1066):\n", repr(t_bot))
