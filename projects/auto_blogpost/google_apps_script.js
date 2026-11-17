/**
 * Google Apps Script Webhook for Instant Blogger Posting
 * 
 * SETUP INSTRUCTIONS (Takes 1 minute):
 * 1. Open https://script.google.com/
 * 2. Click "New Project".
 * 3. In the left menu, click "Services" (+ icon) -> select "Blogger API v3" -> click "Add".
 * 4. Paste this code and replace BLOG_ID if needed.
 * 5. Click "Deploy" -> "New deployment".
 * 6. Select type: "Web app".
 *    - Description: Blogger Publisher
 *    - Execute as: Me (your Google account)
 *    - Who has access: Anyone
 * 7. Click "Deploy", authorize access, and copy the Web App URL.
 * 8. Run: python auto_blogger.py --mode webhook --webhook-url "<YOUR_WEB_APP_URL>"
 */

var BLOG_ID = "2198767951950215096"; // lkunitest.blogspot.com

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var title = data.title || "New Course Intake";
    var content = data.content || "";
    var labels = data.labels || ["COURSES"];

    var newPost = {
      title: title,
      content: content,
      labels: labels
    };

    var inserted = Blogger.Posts.insert(newPost, BLOG_ID, {
      isDraft: false
    });

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      postId: inserted.id,
      url: inserted.url
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput("Blogger Webhook is Active! Send a POST request to publish.");
}
