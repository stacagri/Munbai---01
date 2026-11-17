import os
import sys
from PIL import Image, ImageDraw, ImageFont

sys.path.append('/home/ubuntu/auto_blogpost')
from auto_blogger import upload_to_google_drive, BASE_DIR, TEMPLATE_IMG

output_path = "/home/ubuntu/guruwaraya_sample_banner.png"
im = Image.open(TEMPLATE_IMG).convert("RGB")
draw = ImageDraw.Draw(im)

font_sans_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font_serif_bold = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"

# 1. Institution Name in Green Bar (Y: 160 to 304, height: 144)
draw.rectangle([0, 160, 1600, 304], fill=(0, 94, 32))
inst_text = "DEPARTMENT OF EXAMINATIONS, SRI LANKA"
inst_font = ImageFont.truetype(font_sans_bold, 52)
bbox = draw.textbbox((0, 0), inst_text, font=inst_font)
iw = bbox[2] - bbox[0]
ih = bbox[3] - bbox[1]
ix = (1600 - iw) // 2
iy = 160 + (144 - ih) // 2 - (bbox[1] // 2)
draw.text((ix, iy), inst_text, fill=(255, 255, 255), font=inst_font)

# 2. Exam Calendar Title in Deep Royal Blue (0, 38, 179)
title_text = "December Examination Calendar"
title_font = ImageFont.truetype(font_serif_bold, 78)
bbox = draw.textbbox((0, 0), title_text, font=title_font)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]
tx = (1600 - tw) // 2
ty = 370 + (260 - th) // 2
draw.text((tx, ty), title_text, fill=(0, 38, 179), font=title_font)

# 3. Year in Black Serif (0, 0, 0)
year_str = "2026"
year_font = ImageFont.truetype(font_serif_bold, 86)
y_bbox = draw.textbbox((0, 0), year_str, font=year_font)
yw = y_bbox[2] - y_bbox[0]
yx = (1600 - yw) // 2
yy = 695
draw.text((yx, yy), year_str, fill=(0, 0, 0), font=year_font)

im.save(output_path, "PNG", quality=95)
print("Saved custom banner:", output_path)

# Upload to Drive
cdn_url = upload_to_google_drive(output_path, file_name="thumb-size.png", folder_name="Exam_Calendar_December_2026")
print("Uploaded CDN URL:", cdn_url)
