import json
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

with open("/home/ubuntu/auto_blogpost/token.json") as f:
    token_data = json.load(f)

creds = Credentials.from_authorized_user_info(token_data)
service = build('blogger', 'v3', credentials=creds)

TEST_BLOG_ID = "2198767951950215096"

# Let's test with a small 100x100 png
with open("/home/ubuntu/auto_blogpost/thumb-size.png", "rb") as img_f:
    b64_data = base64.b64encode(img_f.read()).decode("utf-8")

content = f'''<p>Test Image Bridge</p><p><img src="data:image/png;base64,{b64_data}" /></p>'''

post = {
    "kind": "blogger#post",
    "title": "Image Bridge Test",
    "content": content
}

result = service.posts().insert(blogId=TEST_BLOG_ID, body=post, isDraft=False).execute()
print("Post ID:", result.get("id"))
print("URL:", result.get("url"))
print("Content snippet:", result.get("content")[:300])
if "images" in result:
    print("Images field:", result.get("images"))
else:
    print("No images field in response")
