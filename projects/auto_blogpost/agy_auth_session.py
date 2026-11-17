import pty
import os
import subprocess
import time
import select
import termios
import struct
import fcntl
import re

URL_FILE = "/home/ubuntu/auto_blogpost/oauth_url.txt"
STATUS_FILE = "/home/ubuntu/auto_blogpost/login_status.txt"
CODE_FILE = "/home/ubuntu/auto_blogpost/auth_code.txt"

for f in [URL_FILE, STATUS_FILE, CODE_FILE]:
    if os.path.exists(f):
        try:
            os.remove(f)
        except Exception:
            pass

master, slave = pty.openpty()
winsize = struct.pack("HHHH", 60, 200, 0, 0)
fcntl.ioctl(slave, termios.TIOCSWINSZ, winsize)

proc = subprocess.Popen(
    ['/home/ubuntu/.local/bin/agy'],
    stdin=slave,
    stdout=slave,
    stderr=slave,
    close_fds=True
)
os.close(slave)

time.sleep(2)
# Select 1. Google OAuth
os.write(master, b"\r")

raw_output = ""
start = time.time()
full_url = None

while time.time() - start < 15:
    r, _, _ = select.select([master], [], [], 0.5)
    if r:
        try:
            chunk = os.read(master, 4096).decode("utf-8", errors="ignore")
            if not chunk:
                break
            raw_output += chunk
            if "state=" in raw_output:
                # Reconstruct URL
                url_lines = []
                capturing = False
                for line in raw_output.splitlines():
                    clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line).strip()
                    if 'https://accounts.google.com' in clean:
                        capturing = True
                    if capturing:
                        url_lines.append(clean)
                        if 'state=' in clean:
                            break
                if url_lines:
                    full_url = ''.join(url_lines)
                    break
        except Exception:
            time.sleep(0.1)

if not full_url:
    full_url = "ERROR: Failed to extract URL"

with open(URL_FILE, "w", encoding="utf-8") as f:
    f.write(full_url)

print(f"READY_URL: {full_url}", flush=True)

# Wait for auth code from CODE_FILE
code = None
print("Waiting for auth_code.txt...", flush=True)
while True:
    if os.path.exists(CODE_FILE):
        try:
            with open(CODE_FILE, "r", encoding="utf-8") as f:
                c = f.read().strip()
                if c:
                    code = c
                    break
        except Exception:
            pass
    time.sleep(1)

print(f"Submitting auth code: {code}", flush=True)
os.write(master, code.encode("utf-8") + b"\r\n")

# Capture output
post_output = ""
start = time.time()
while time.time() - start < 15:
    r, _, _ = select.select([master], [], [], 0.5)
    if r:
        try:
            chunk = os.read(master, 4096).decode("utf-8", errors="ignore")
            if not chunk:
                break
            post_output += chunk
        except Exception:
            time.sleep(0.1)

with open(STATUS_FILE, "w", encoding="utf-8") as f:
    f.write(post_output)

print("POST_LOGIN_OUTPUT:\n", post_output, flush=True)

# Start remote control
rc_start = subprocess.run(
    ['/home/ubuntu/.local/bin/agy', 'remote-control', 'start'],
    capture_output=True,
    text=True
)
print("RC_START:\n", rc_start.stdout, rc_start.stderr, flush=True)

rc_status = subprocess.run(
    ['/home/ubuntu/.local/bin/agy', 'remote-control', 'status'],
    capture_output=True,
    text=True
)
print("RC_STATUS:\n", rc_status.stdout, rc_status.stderr, flush=True)

with open(STATUS_FILE, "a", encoding="utf-8") as f:
    f.write("\n\n=== REMOTE CONTROL ===\n")
    f.write(rc_start.stdout + "\n" + rc_start.stderr + "\n")
    f.write(rc_status.stdout + "\n" + rc_status.stderr + "\n")
