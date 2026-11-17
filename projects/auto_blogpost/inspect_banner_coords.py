import cv2
import numpy as np

orig = cv2.imread('/home/ubuntu/auto_blogpost/original_sample_banner.png')
print("Dimensions:", orig.shape) # (1066, 1600, 3)

# Find the exact coordinates of the green bar, the content box, the date area, and the footer bar
# Green bar: where is green? (0, 94, 32)
green_mask = (orig[:, :, 1] > 70) & (orig[:, :, 0] < 50) & (orig[:, :, 2] < 50)
y_indices, x_indices = np.where(green_mask)
print(f"Green bar Y range: {y_indices.min()} to {y_indices.max()}")

# Yellow bar at bottom: where is yellow? (High red + high green, low blue)
yellow_mask = (orig[:, :, 1] > 150) & (orig[:, :, 2] > 150) & (orig[:, :, 0] < 80)
y_yel, x_yel = np.where(yellow_mask)
if len(y_yel) > 0:
    print(f"Yellow bar Y range: {y_yel.min()} to {y_yel.max()}, X range: {x_yel.min()} to {x_yel.max()}")
else:
    print("No yellow bar found with that threshold. Let's inspect bottom colors.")
    print("Bottom 100 rows colors (unique BGR):", np.unique(orig[966:1066, :, :].reshape(-1, 3), axis=0)[:10])
