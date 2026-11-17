import pty
import os
import subprocess
import time
import select

master, slave = pty.openpty()
proc = subprocess.Popen(
    ['/home/ubuntu/.local/bin/agy'],
    stdin=slave,
    stdout=slave,
    stderr=slave,
    close_fds=True
)
os.close(slave)

time.sleep(2)
os.write(master, b"\r")

output = b""
start_time = time.time()
while time.time() - start_time < 5:
    r, _, _ = select.select([master], [], [], 0.5)
    if r:
        try:
            chunk = os.read(master, 2048)
            if not chunk: break
            output += chunk
        except Exception:
            break

# Scroll down to see the code prompt
os.write(master, b"\x1b[B\x1b[B\x1b[B\x1b[B\x1b[B\x1b[B\x1b[B\x1b[B\x1b[B\x1b[B")
time.sleep(1)
while True:
    r, _, _ = select.select([master], [], [], 0.5)
    if r:
        chunk = os.read(master, 2048)
        if not chunk: break
        output += chunk
    else:
        break

raw_text = output.decode("utf-8", errors="ignore")
print("=== FULL RAW OUTPUT ===")
print(raw_text)

proc.kill()
