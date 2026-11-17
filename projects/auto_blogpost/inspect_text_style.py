import cv2
import numpy as np

orig = cv2.imread('/home/ubuntu/auto_blogpost/original_sample_banner.png')

# Find pixels of text "External Degree Programmes" in rows 350 to 650
# Text pixels are darker than background
crop = orig[350:650, 200:1400]
dark_mask = (crop[:, :, 0] < 120) | (crop[:, :, 1] < 120) | (crop[:, :, 2] < 120)
text_colors = crop[dark_mask]
print("Text color sample (BGR):", text_colors[:10])
print("Median text color (BGR):", np.median(text_colors, axis=0))

# Where is the year 2025 located in original?
crop_year = orig[650:800, 200:1400]
dark_mask_y = (crop_year[:, :, 0] < 120) | (crop_year[:, :, 1] < 120) | (crop_year[:, :, 2] < 120)
y_indices, x_indices = np.where(dark_mask_y)
if len(y_indices) > 0:
    print(f"Year Y range in original: {650 + y_indices.min()} to {650 + y_indices.max()}")
    print("Year color (BGR):", np.median(crop_year[dark_mask_y], axis=0))
