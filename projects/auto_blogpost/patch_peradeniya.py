import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    t = json.load(f)

c = Credentials.from_authorized_user_info(t)
s = build("blogger", "v3", credentials=c)

POST_ID = "852211792188563571"
BLOG_ID = "3109655798381913489"

head_url = "https://lh3.googleusercontent.com/d/10Y4idWLaaFnJTEpsmOFtLDtMLOz_BS7r"
flyer_url = "https://lh3.googleusercontent.com/d/1b8H7UOIImy23TEItI08ucxh1R3ncy36b"

correct_content = f"""<div class="separator" style="clear: both; text-align: center;">
<a href="{head_url}" style="margin-left: 1em; margin-right: 1em;">
<img border="0" data-original-height="1066" data-original-width="1600" src="{head_url}"/>
</a>
</div>
<br/>
<p><b>Applications are invited from interested candidates for Bachelor of Business Administration (BBA) External Degree Programme 2026 offered by Centre for Distance and Continuing Education (CDCE), University of Peradeniya.</b></p>
<p class="MsoNormal"></p>
<div><b>Course Details ✅</b></div>
<div><br/></div>
<div>
<p class="MsoNormal"><b>👉 Mode of Delivery: Blended (Online & Face-to-Face)</b></p>
<p class="MsoNormal"><b>👉 Medium: English</b></p>
<p class="MsoNormal"><b>👉 Duration: Minimum 03 Years</b></p>
<p class="MsoNormal"><b>👉 Entry Qualifications: Pass in one sitting at G.C.E. (A/L) examination in any stream</b></p>
<p class="MsoNormal"><b>👉 Structure: Diploma (Yr 1) ➔ Higher Diploma (Yr 2) ➔ BBA Degree (Yr 3)</b></p>
<p class="MsoNormal"><b>👉 Application Processing Fee: Rs. 1,500/-</b></p>
<p class="MsoNormal"><b>👉 Closing Date: 30th November 2026</b></p>
</div>
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
<th>Details</th>
<th>Links</th>
</tr>
<tr>
<td>Closing Date</td>
<td>2026.11.30</td>
</tr>
<tr>
<td>Notice / Advertisement (Image)</td>
<td><a href="{flyer_url}" target="_blank">Click Here</a></td>
</tr>
<tr>
<td>Course Details</td>
<td><a href="https://cdce.pdn.ac.lk/course_bba.php" target="_blank">Click Here</a></td>
</tr>
<tr>
<td>Apply Now</td>
<td><a href="https://cdce.pdn.ac.lk/tools/cdceonline_2023/views/register.php" target="_blank">Click Here</a></td>
</tr>
</tbody>
</table>
<br/>
"""

patched = s.posts().patch(
    blogId=BLOG_ID,
    postId=POST_ID,
    body={"content": correct_content}
).execute()

print("Patched post successfully! URL:", patched.get("url"))
