import cv2
import numpy as np

orig = cv2.imread('/home/ubuntu/auto_blogpost/original_sample_banner.png')
print("Top bar (row 50):", orig[50, 800])
print("Green bar (row 230):", orig[230, 800])
print("Main area (row 450):", orig[450, 800])
print("Main area (row 600):", orig[600, 800])
print("Year area (row 800):", orig[800, 800])
print("Bottom bar (row 950):", orig[950, 800])
print("Bottom border (row 1050):", orig[1050, 800])

# Check bounding boxes of text in original
gray = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
# Check if bottom has any graphics or logo
print("Unique colors in row 900-1066:", np.unique(orig[900:1066, :, :].reshape(-1, 3), axis=0)[:10])
