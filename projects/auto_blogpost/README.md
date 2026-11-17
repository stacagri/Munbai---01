# Auto BlogPost Script: TamilGuru Courses -> LKUni Style -> Blogger

This script scrapes the latest course post from **[TamilGuru Courses](https://tamilguru.lk/category/courses/)**, transforms its layout and formatting to match **[LKUni](https://www.lkuni.com/)** (complete with banner image, course details, clean bullets, and the signature `#simple_table` Cyan/Black theme), and publishes it to your Blogger blog **[lkunitest.blogspot.com](https://lkunitest.blogspot.com/)** (Blog ID: `2198767951950215096`).

---

## What the Script Does

1. **Scrapes the First Post**:
   - Detects the newest post under `https://tamilguru.lk/category/courses/` (e.g. *Agro Technology Degree Intake 2026 - University of Colombo*).
   - Extracts post title, flyer images, duration, medium, entry requirements, exit points, and links.
2. **Transforms into LKUni (`www.lkuni.com`) Formatting**:
   - Centered banner image inside standard Blogger separator.
   - Bold intro summary: `Applications are invited from interested candidates for...`
   - Heading: `Course Details ✅`
   - Clean bulleted requirements.
   - Secondary notice flyer image.
   - The signature LKUni `#simple_table` style (Cyan `#00fbff` header, `#1d1b1b` alternating background, `#33fcff` cyan text, red hover) with rows for:
     * Notice (English / Sinhala / Tamil)
     * Closing Date
     * Course Details (`Click Here`)
     * Apply Now (`Click Here`)
     * Official Source (`Click Here`)
3. **Posts to Blogger**:
   - Keeps track of posted URLs in `posted_cache.json` so duplicate posts are never created.
   - Supports 3 publishing methods:
     * **Webhook (Google Apps Script)** — *Easiest & Fastest (no API console setup)*
     * **Official Blogger API v3** — *Using OAuth2 client_secret.json*
     * **Email-to-Blogger** — *Using Blogger's built-in secret posting address*

---

## How to Run

### 1. Dry Run / Preview HTML (No Posting)
```bash
python3 auto_blogger.py --dry-run
```
This generates `latest_post.html`, which you can open in any browser to preview the exact look.

---

### 2. Posting Method A: Google Apps Script Webhook (Recommended & Easiest)
1. Go to [Google Apps Script](https://script.google.com/) while logged into the Google account that owns `lkunitest.blogspot.com`.
2. Click **New project**.
3. On the left side, click **Services (+)** &rarr; select **Blogger API v3** &rarr; click **Add**.
4. Paste the contents of `google_apps_script.js` into the editor.
5. Click **Deploy** &rarr; **New deployment** &rarr; select type **Web app**:
   - Execute as: **Me**
   - Who has access: **Anyone**
6. Click **Deploy**, grant permissions, and copy the **Web app URL**.
7. Run the script:
```bash
python3 auto_blogger.py --mode webhook --webhook-url "https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec"
```

---

### 3. Posting Method B: Blogger Email-to-Post
1. In your Blogger dashboard for `lkunitest`:
   - Go to **Settings** &rarr; scroll to **Email** &rarr; **Posting using email**.
   - Set a secret word, e.g., `publish.mysecretword@blogger.com`.
   - Select **Publish email immediately**.
2. Run:
```bash
python3 auto_blogger.py --mode email \
  --blogger-email "yourname.mysecretword@blogger.com" \
  --smtp-user "your_gmail@gmail.com" \
  --smtp-pass "your_16_char_gmail_app_password"
```

---

### 4. Posting Method C: Official Google Blogger API v3
1. Enable Blogger API in [Google Cloud Console](https://console.cloud.google.com/).
2. Create an **OAuth 2.0 Client ID (Desktop Application)** and download `client_secret.json` to this folder.
3. Run:
```bash
python3 auto_blogger.py --mode api --client-secret client_secret.json
```
On the first run, a browser opens to authenticate. A `token.json` file is saved and subsequent runs are completely automated.
