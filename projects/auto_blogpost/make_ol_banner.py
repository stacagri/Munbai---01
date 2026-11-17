import os
from PIL import Image, ImageDraw, ImageFont

TEMPLATE = "/home/ubuntu/auto_blogpost/thumb_pristine_template.png"
OUTPUT = "/home/ubuntu/auto_blogpost/thumb_ol_2026.png"

im = Image.open(TEMPLATE).convert("RGB")
draw = ImageDraw.Draw(im)

font_sans_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font_serif_bold = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
if not os.path.exists(font_serif_bold):
    font_serif_bold = font_sans_bold

# 1. Institution Name in Green Bar (Y: 160 to 304, height: 144)
inst_name = "DEPARTMENT OF EXAMINATIONS, SRI LANKA"
inst_font_size = 56
inst_font = ImageFont.truetype(font_sans_bold, inst_font_size)

while inst_font_size > 26:
    bbox = draw.textbbox((0, 0), inst_name, font=inst_font)
    if (bbox[2] - bbox[0]) <= 1500:
        break
    inst_font_size -= 2
    inst_font = ImageFont.truetype(font_sans_bold, inst_font_size)

bbox = draw.textbbox((0, 0), inst_name, font=inst_font)
iw = bbox[2] - bbox[0]
ih = bbox[3] - bbox[1]
ix = (1600 - iw) // 2
iy = 160 + (144 - ih) // 2 - (bbox[1] // 2)
draw.text((ix, iy), inst_name, fill=(255, 255, 255), font=inst_font)

# 2. Course Name in Deep Royal Blue (RGB: 0, 38, 179)
course_name = "G.C.E. O/L Examination\nTime Table"
target_font_size = 90
course_font = ImageFont.truetype(font_serif_bold, target_font_size)

lines = course_name.split("\n")
line_h = int(target_font_size * 1.35)
total_h = len(lines) * line_h
start_y = 350 + (320 - total_h) // 2

for i, line in enumerate(lines):
    bbox = draw.textbbox((0, 0), line, font=course_font)
    lw = bbox[2] - bbox[0]
    lx = (1600 - lw) // 2
    ly = start_y + (i * line_h)
    draw.text((lx, ly), line, fill=(0, 38, 179), font=course_font)

# 3. Year in Black Serif (RGB: 0, 0, 0)
year_str = "2026"
year_font = ImageFont.truetype(font_serif_bold, 86)
y_bbox = draw.textbbox((0, 0), year_str, font=year_font)
yw = y_bbox[2] - y_bbox[0]
yx = (1600 - yw) // 2
yy = 695
draw.text((yx, yy), year_str, fill=(0, 0, 0), font=year_font)

im.save(OUTPUT, "PNG", quality=95)
print("Saved O/L 2026 banner to:", OUTPUT)
