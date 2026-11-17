import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

orig = cv2.imread('/home/ubuntu/auto_blogpost/original_sample_banner.png')
h, w, _ = orig.shape

# 1. Clean the green bar: Y = 160 to 304
# Exact green color in RGB: (0, 94, 32) -> BGR: (32, 94, 0)
orig[160:305, :] = [32, 94, 0]

# 2. Clean the middle area: Y = 305 to 808
# Let's inspect rows 305 to 808:
# The background in the original is a clean subtle gradient:
# top is (252, 237, 187) [BGR], bottom is (255, 251, 250) [BGR]
# Left border (X = 0 to 8) is black [0, 0, 0]
# Right border (X = 1592 to 1600) is black [0, 0, 0]
for y in range(305, 808):
    ratio = (y - 305) / (808 - 305)
    # interpolate BGR
    b = int(252 + ratio * (255 - 252))
    g = int(237 + ratio * (251 - 237))
    r = int(187 + ratio * (250 - 187))
    orig[y, 8:1592] = [b, g, r]

# Note: Yellow bar (808:917) and Bottom bar (917:1066) remain 100% INTACT with 'www.LkUni.com'!

clean_template_path = '/home/ubuntu/auto_blogpost/thumb_clean_template.png'
cv2.imwrite(clean_template_path, orig)
print("Saved clean template to:", clean_template_path)
