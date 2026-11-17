#!/usr/bin/env python3
import re
import os
import sys
import subprocess
import requests

TELEGRAM_BOT_TOKEN = "8992942076:AAGOKyMoJ6unQTcYf3cQSOxyTMT3FrwyfkY"
ADMIN_CHAT_ID = "1499235921"
PROJECT_DIR = "/home/ubuntu/RiverAlarmApp"
GRADLE_PATH = "/opt/gradle/gradle-8.5/bin/gradle"
BUILD_GRADLE_FILE = os.path.join(PROJECT_DIR, "app/build.gradle")
LIVE_TOPIC_URL = "https://ntfy.sh/kalu_ganga_alert_lk_live"

def get_current_versions():
    with open(BUILD_GRADLE_FILE, "r") as f:
        content = f.read()
    vc_match = re.search(r"versionCode\s+(\d+)", content)
    vn_match = re.search(r'versionName\s+["\']([^"\']+)["\']', content)
    version_code = int(vc_match.group(1)) if vc_match else 1
    version_name = vn_match.group(1) if vn_match else "1.0"
    return version_code, version_name

def bump_version(new_code, new_name):
    with open(BUILD_GRADLE_FILE, "r") as f:
        content = f.read()
    content = re.sub(r"versionCode\s+\d+", f"versionCode {new_code}", content)
    content = re.sub(r'versionName\s+["\'][^"\']+["\']', f'versionName "{new_name}"', content)
    with open(BUILD_GRADLE_FILE, "w") as f:
        f.write(content)

def build_apk():
    env = os.environ.copy()
    env["ANDROID_HOME"] = "/opt/android-sdk"
    res = subprocess.run([GRADLE_PATH, "assembleDebug"], cwd=PROJECT_DIR, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print("Build failed:\n", res.stderr)
        return False
    return True

def upload_and_broadcast(new_code, new_name, notes="Bug fixes & improvements"):
    apk_source = os.path.join(PROJECT_DIR, "app/build/outputs/apk/debug/app-debug.apk")
    if not os.path.exists(apk_source):
        print("APK not found at", apk_source)
        return False

    v_tag = f"v{new_name}"
    target_apk = f"/home/ubuntu/RiverAlert_Ratnapura_{v_tag}.apk"
    subprocess.run(["cp", apk_source, target_apk])

    print(f"Uploading {target_apk} to Telegram...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    with open(target_apk, "rb") as f:
        files = {"document": (f"RiverAlert_Ratnapura_{v_tag}.apk", f, "application/vnd.android.package-archive")}
        data = {
            "chat_id": ADMIN_CHAT_ID,
            "caption": f"🚀 *New Version Available: River Alert {v_tag}*\n\n{notes}\n\n_Auto-update command being broadcast to all installed devices!_",
            "parse_mode": "Markdown"
        }
        r = requests.post(url, data=data, files=files, timeout=40)
        res_data = r.json()

    if not res_data.get("ok"):
        print("Upload failed:", res_data)
        return False

    file_id = res_data["result"]["document"]["file_id"]
    r_file = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}", timeout=10)
    file_info = r_file.json()
    file_path = file_info["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    print(f"Direct CDN Download URL: {download_url}")

    # Broadcast update signal to all mobile apps
    # Format: UPDATE|versionCode|versionName|downloadUrl
    update_signal = f"UPDATE|{new_code}|{v_tag}|{download_url}"
    requests.post(LIVE_TOPIC_URL, data=update_signal.encode("utf-8"), timeout=5)
    print("✅ Auto-Update signal broadcast to all active devices!")
    return True

def main():
    curr_code, curr_name = get_current_versions()
    new_code = curr_code + 1
    # If version name is 1.0 -> 2.0, etc.
    try:
        parts = curr_name.split(".")
        if len(parts) >= 2:
            new_name = f"{parts[0]}.{int(parts[1]) + 1}"
        else:
            new_name = f"{parts[0]}.1"
    except Exception:
        new_name = f"1.{curr_code + 1}"

    print(f"Current version: {curr_name} (code: {curr_code}) -> New version: {new_name} (code: {new_code})")
    bump_version(new_code, new_name)

    print("Building new APK with Gradle...")
    if not build_apk():
        sys.exit(1)

    print("Publishing update...")
    if upload_and_broadcast(new_code, new_name):
        print(f"🎉 Successfully deployed and broadcasted River Alert v{new_name}!")
    else:
        print("Failed to deploy update.")

if __name__ == "__main__":
    main()
