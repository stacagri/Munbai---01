import os
import sys
import json
from PIL import Image, ImageDraw, ImageFont

sys.path.append('/home/ubuntu/auto_blogpost')
from auto_blogger import upload_to_google_drive, BASE_DIR, TEMPLATE_IMG
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# 1. Generate Custom Head Banner
output_path = "/home/ubuntu/moe_sleas_banner.png"
im = Image.open(TEMPLATE_IMG).convert("RGB")
draw = ImageDraw.Draw(im)

font_sans_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font_serif_bold = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"

# Green Bar
draw.rectangle([0, 160, 1600, 304], fill=(0, 94, 32))
inst_text = "MINISTRY OF EDUCATION, SRI LANKA"
inst_font = ImageFont.truetype(font_sans_bold, 54)
bbox = draw.textbbox((0, 0), inst_text, font=inst_font)
iw = bbox[2] - bbox[0]
ih = bbox[3] - bbox[1]
ix = (1600 - iw) // 2
iy = 160 + (144 - ih) // 2 - (bbox[1] // 2)
draw.text((ix, iy), inst_text, fill=(255, 255, 255), font=inst_font)

# Royal Blue Title
title_text = "SLEAS Annual Transfers"
title_font = ImageFont.truetype(font_serif_bold, 92)
bbox = draw.textbbox((0, 0), title_text, font=title_font)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]
tx = (1600 - tw) // 2
ty = 370 + (260 - th) // 2
draw.text((tx, ty), title_text, fill=(0, 38, 179), font=title_font)

# Year
year_str = "2027 (2026)"
year_font = ImageFont.truetype(font_serif_bold, 84)
y_bbox = draw.textbbox((0, 0), year_str, font=year_font)
yw = y_bbox[2] - y_bbox[0]
yx = (1600 - yw) // 2
yy = 695
draw.text((yx, yy), year_str, fill=(0, 0, 0), font=year_font)

im.save(output_path, "PNG", quality=95)
print("Banner saved:", output_path)

# Upload to Drive
banner_url = upload_to_google_drive(output_path, file_name="thumb-size.png", folder_name="MOE_SLEAS_Annual_Transfers_2027")
print("Banner CDN URL:", banner_url)

# 2. Build Post HTML
post_title = "Sri Lanka Education Administrative Service (SLEAS) Annual Transfers 2027 – Ministry of Education"
content = f"""<p>&nbsp;</p>
<div class="separator" style="clear: both; text-align: center;">
  <a href="{banner_url}" style="margin-left: 1em; margin-right: 1em;">
    <img border="0" data-original-height="1066" data-original-width="1600" src="{banner_url}" />
  </a>
</div>
<br/>

<p><b>Ministry of Education, Higher Education and Vocational Education</b></p>
<p><b>Sri Lanka Education Administrative Service (SLEAS) Annual Transfers 2027 – Review Committee Decisions & Appeals</b></p>
<div>
  <p class="MsoNormal"><b>* Organization: Ministry of Education, Higher Education and Vocational Education</b></p>
  <p class="MsoNormal"><b>* Service / Grades: Sri Lanka Education Administrative Service (SLEAS) - Grades I, II & III</b></p>
  <p class="MsoNormal"><b>* Effective Date of Implementation: 01 January 2027</b></p>
  <p class="MsoNormal"><b>* Key Instructions:</b></p>
  <p class="MsoNormal"><b>&nbsp;&nbsp;• Review Committee Decisions for SLEAS Annual Transfers 2027 have been released.</b></p>
  <p class="MsoNormal"><b>&nbsp;&nbsp;• Officers who are dissatisfied with decisions may submit appeals to the Public Service Commission within 14 days.</b></p>
  <p class="MsoNormal"><b>&nbsp;&nbsp;• Use only Annexures 05 and 06 of Ministry Circular No. 23/2026 for appeals.</b></p>
  <p class="MsoNormal"><b>&nbsp;&nbsp;• Only officers who previously submitted applications to the Review Committee are eligible to appeal.</b></p>
</div>
<br/>

<style>
#simple_table {{
\tfont-family: arial, sans-serif;
\tborder-collapse: collapse; 
\twidth: 100%;
\tbackground-color: #000000;
\tcolor:#33fcff;
}}
#simple_table td, #simple_table th {{
\ttext-align: left;
\tpadding: 8px;
\tborder: 1px solid #ffffff;
}}
#simple_table tr:nth-child(even) {{
\tbackground-color: #1d1b1b;
}}
#simple_table tr:hover {{
\tbackground-color: #9e0000;
}}
#simple_table tr > th {{
\tbackground: #00fbff;
\tcolor: #000000;
}}
</style>

<table id="simple_table">
<tbody>
<tr>
\t<th>Details</th>
\t<th>Links</th>
</tr>
<tr>
\t<td>English Notice & Application (PDF)</td>
\t<td><a href="https://moe.gov.lk/wp-content/uploads/2026/11/English-01.pdf" target="_blank">Click Here</a></td>
</tr>
<tr>
\t<td>Sinhala Notice & Application (PDF)</td>
\t<td><a href="https://moe.gov.lk/wp-content/uploads/2026/11/Snhala-01.pdf" target="_blank">Click Here</a></td>
</tr>
<tr>
\t<td>Tamil Notice & Application (PDF)</td>
\t<td><a href="https://moe.gov.lk/wp-content/uploads/2026/11/Tamil-01.pdf" target="_blank">Click Here</a></td>
</tr>
<tr>
\t<td>Annexure 02 Transfer List (PDF)</td>
\t<td><a href="https://moe.gov.lk/wp-content/uploads/2026/11/Annexure-02.pdf" target="_blank">Click Here</a></td>
</tr>
<tr>
\t<td>Official Source</td>
\t<td><a href="https://moe.gov.lk/" target="_blank">Ministry of Education</a></td>
</tr>
</tbody>
</table>
<br/><br/><br/>
"""

# 3. Publish to Test Blog
token_file = "/home/ubuntu/auto_blogpost/token.json"
with open(token_file, "r") as f:
    creds_data = json.load(f)
creds = Credentials.from_authorized_user_info(creds_data)
blogger = build("blogger", "v3", credentials=creds)

test_blog_id = "2198767951950215096"
body = {
    "kind": "blogger#post",
    "title": post_title,
    "content": content,
    "labels": ["MOE", "TRANSFERS", "UPDATES"]
}

post = blogger.posts().insert(blogId=test_blog_id, body=body, isDraft=False).execute()
print("Published to test blog successfully!")
print("Post URL:", post.get("url"))
