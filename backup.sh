#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/home/ubuntu/vm_backup"
LOCK_FILE="/tmp/vm_backup.lock"

exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') Backup already running, skipping."
    exit 0
fi

cd "$BACKUP_DIR"

# 1. Sync top-level .py and .sh scripts from /home/ubuntu
mkdir -p "$BACKUP_DIR/home_scripts"
rsync -a --delete \
    --include='*.py' \
    --include='*.sh' \
    --exclude='*' \
    /home/ubuntu/ "$BACKUP_DIR/home_scripts/"

# 2. Sync project directories (excluding secrets, venvs, logs, and build artifacts)
mkdir -p "$BACKUP_DIR/projects"
PROJECTS=("auto_blogpost" "birthday_bot" "rahu_bot" "RiverAlarmApp")

for proj in "${PROJECTS[@]}"; do
    if [ -d "/home/ubuntu/$proj" ]; then
        mkdir -p "$BACKUP_DIR/projects/$proj"
        rsync -a --delete --delete-excluded \
            --exclude='.git/' \
            --exclude='venv/' \
            --exclude='.venv/' \
            --exclude='__pycache__/' \
            --exclude='.gradle/' \
            --exclude='build/' \
            --exclude='*.log' \
            --exclude='*.lock' \
            --exclude='*.fifo' \
            --exclude='*.pyc' \
            --exclude='*.apk' \
            --exclude='*.html' \
            --exclude='*.bak*' \
            --exclude='*.pre_update' \
            --exclude='*.email_version' \
            --exclude='*.png' \
            --exclude='*.jpg' \
            --exclude='client_secret*.json' \
            --exclude='token.json' \
            --exclude='auth_code.txt' \
            --exclude='cookies*.txt' \
            --exclude='.env*' \
            --exclude='local.properties' \
            "/home/ubuntu/$proj/" "$BACKUP_DIR/projects/$proj/"
    fi
done

# 3. Export crontab
crontab -l > "$BACKUP_DIR/crontab.txt" 2>/dev/null || echo "# No crontab" > "$BACKUP_DIR/crontab.txt"

# 4. Copy readable custom systemd service files (non-symlinks)
mkdir -p "$BACKUP_DIR/systemd"
rm -f "$BACKUP_DIR/systemd/"*.service
for svc in /etc/systemd/system/*.service; do
    if [ -f "$svc" ] && [ ! -L "$svc" ] && [ -r "$svc" ]; then
        cp -f "$svc" "$BACKUP_DIR/systemd/"
    fi
done

# 5. Redact hardcoded API keys / OAuth secrets in the backup copy only (never touches live files)
python3 - <<'PYEOF'
import os, re

patterns = [
    (re.compile(r'AIza[0-9A-Za-z_-]{35}'), 'REDACTED_GCP_API_KEY'),
    (re.compile(r'AQ\.[0-9A-Za-z_-]{40,}'), 'REDACTED_GCP_API_KEY'),
    (re.compile(r'GOCSPX-[0-9A-Za-z_-]{20,}'), 'REDACTED_GOOGLE_OAUTH_SECRET'),
    (re.compile(r'[0-9]{8,15}-[0-9A-Za-z_]{20,}\.apps\.googleusercontent\.com'), 'REDACTED_GOOGLE_CLIENT_ID'),
    (re.compile(r'ghp_[0-9A-Za-z]{36}'), 'REDACTED_GITHUB_TOKEN'),
    (re.compile(r'github_pat_[0-9A-Za-z_]{20,}'), 'REDACTED_GITHUB_TOKEN'),
]

for base in ('home_scripts', 'projects'):
    if not os.path.isdir(base):
        continue
    for root, _, files in os.walk(base):
        for name in files:
            if not name.endswith(('.py', '.sh', '.json', '.txt', '.md', '.gradle', '.xml', '.java')):
                continue
            path = os.path.join(root, name)
            if os.path.islink(path):
                continue
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
                new_text = text
                for pat, repl in patterns:
                    new_text = pat.sub(repl, new_text)
                if new_text != text:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_text)
            except Exception:
                pass
PYEOF

# 6. Commit and push if there are changes
git add -A
if git diff --cached --quiet; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') No changes to back up."
    exit 0
fi

COMMIT_MSG="Auto backup $(hostname) $(date '+%Y-%m-%d %H:%M:%S %Z')"
git commit -m "$COMMIT_MSG"
git push -u origin main
echo "$(date '+%Y-%m-%d %H:%M:%S') Backup pushed: $COMMIT_MSG"
