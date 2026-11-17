import sys
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

token_file = "/home/ubuntu/auto_blogpost/token.json"
with open(token_file, "r") as f:
    creds_data = json.load(f)

creds = Credentials.from_authorized_user_info(creds_data)
blogger = build("blogger", "v3", credentials=creds)

test_blog_id = "2198767951950215096"
banner_url = "https://lh3.googleusercontent.com/d/18UMNev5pAi6pxjx72zXlylckJa1oziT_"
title = "December 2026 Examination Calendar – 22 Government Exams – Department of Examinations"

content = f"""<p>&nbsp;</p>
<div class="separator" style="clear: both; text-align: center;">
  <a href="{banner_url}" style="margin-left: 1em; margin-right: 1em;">
    <img border="0" data-original-height="1066" data-original-width="1600" src="{banner_url}" />
  </a>
</div>
<br/>

<p><b>Department of Examinations, Sri Lanka</b></p>
<p><b>Monthly Examination Calendar for December 2026 (22 Government Examinations)</b></p>
<div>
  <p class="MsoNormal"><b>* Organization: Department of Examinations, Sri Lanka</b></p>
  <p class="MsoNormal"><b>* Examination Month: December 2026</b></p>
  <p class="MsoNormal"><b>* Total Scheduled Examinations: 22 Government & Recruitment Examinations</b></p>
  <p class="MsoNormal"><b>* Key Examinations Included:</b></p>
  <p class="MsoNormal"><b>&nbsp;&nbsp;• People’s Bank Senior Confidential Secretary Promotion Examination</b></p>
  <p class="MsoNormal"><b>&nbsp;&nbsp;• Technical Officer (Civil) - Department of Fisheries Open Recruitment</b></p>
  <p class="MsoNormal"><b>&nbsp;&nbsp;• Sri Lanka Government Librarians' Service Grade III Recruitment</b></p>
  <p class="MsoNormal"><b>&nbsp;&nbsp;• Technology Faculty Assistant Grade III Limited Recruitment</b></p>
  <p class="MsoNormal"><b>&nbsp;&nbsp;• Inspector of Customs Grade II Limited Promotion Examination</b></p>
  <p class="MsoNormal"><b>&nbsp;&nbsp;• Assistant Superintendent of Hostel Grade III Recruitment</b></p>
  <p class="MsoNormal"><b>&nbsp;&nbsp;• Dharmacharya Certificate Examinations (Islam Dheeniyath & Hindu)</b></p>
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
\t<td>English Examination Calendar (PDF)</td>
\t<td><a href="https://doenets.lk/images/resources/EXCA/Dec_English_1794065845553.pdf" target="_blank">Click Here</a></td>
</tr>
<tr>
\t<td>Sinhala Examination Calendar (PDF)</td>
\t<td><a href="https://doenets.lk/images/resources/EXCA/Dec_%20Sinhala_1794065857151.pdf" target="_blank">Click Here</a></td>
</tr>
<tr>
\t<td>Tamil Examination Calendar (PDF)</td>
\t<td><a href="https://doenets.lk/images/resources/EXCA/Dec_Tamil_1794065867002.pdf" target="_blank">Click Here</a></td>
</tr>
<tr>
\t<td>Official Website</td>
\t<td><a href="https://doenets.lk/" target="_blank">Click Here</a></td>
</tr>
</tbody>
</table>
<br/><br/><br/>
"""

body = {
    "kind": "blogger#post",
    "title": title,
    "content": content,
    "labels": ["EXAMINATIONS", "UPDATES"]
}

post = blogger.posts().insert(blogId=test_blog_id, body=body, isDraft=False).execute()
print("Successfully published to test blog!")
print("Live Test URL:", post.get("url"))
