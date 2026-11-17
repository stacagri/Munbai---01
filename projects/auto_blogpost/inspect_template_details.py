import cv2
import numpy as np

im = cv2.imread('/home/ubuntu/auto_blogpost/thumb_template.png')
h, w, _ = im.shape
print(f"Template shape: {w}x{h}")

# Check unique colors or segments in template
# Check rows
print("Row 0-150 color:", im[50, 800])
print("Row 154-308 color:", im[200, 800])
print("Row 310-800 color:", im[500, 800])
print("Row 850-1066 color:", im[950, 800])
print("Row 1000 color:", im[1020, 800])
