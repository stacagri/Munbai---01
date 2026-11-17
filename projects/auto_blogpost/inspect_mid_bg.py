import cv2
import numpy as np

orig = cv2.imread('/home/ubuntu/auto_blogpost/original_sample_banner.png')
# Check background color around corners of middle area (e.g. row 350, col 50)
print("Middle top-left (350, 50):", orig[350, 50])
print("Middle top-right (350, 1550):", orig[350, 1550])
print("Middle bottom-left (780, 50):", orig[780, 50])
print("Middle bottom-right (780, 1550):", orig[780, 1550])

# Check if middle background is uniform or patterned
mid_bg_crop = orig[320:800, 10:150]
print("Unique colors in left margin of middle:", np.unique(mid_bg_crop.reshape(-1, 3), axis=0)[:5])
