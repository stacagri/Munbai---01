import cv2
import numpy as np

orig = cv2.imread('/home/ubuntu/auto_blogpost/original_sample_banner.png')

# 1. Clean green bar (row 160 to 304)
# In the green bar, we can just fill solid (32, 94, 0) because the green bar is solid green!
orig[160:305, :] = [32, 94, 0]

# 2. Inpaint text inside the middle box:
# Find dark pixels corresponding to the text in middle area (row 340 to 800)
mid = orig[330:800, 50:1550]
# The text is dark blue and black:
text_mask = (mid[:, :, 0] < 120) | (mid[:, :, 1] < 100) | (mid[:, :, 2] < 100)
# Exclude the rectangular border itself if present:
# The border is at the edges of the box, text is mostly col 200 to 1400
kernel = np.ones((5, 5), np.uint8)
mask_dilated = cv2.dilate(text_mask.astype(np.uint8) * 255, kernel, iterations=2)

# Inpaint using TELEA
inpainted_mid = cv2.inpaint(mid, mask_dilated, 7, cv2.INPAINT_TELEA)
orig[330:800, 50:1550] = inpainted_mid

# Save pristine template
cv2.imwrite('/home/ubuntu/auto_blogpost/thumb_pristine_template.png', orig)
print("Saved thumb_pristine_template.png successfully!")
