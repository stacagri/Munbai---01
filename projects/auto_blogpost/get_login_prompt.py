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
# Send Carriage Return \r to select
os.write(master, b"\r")

output = b""
start_time = time.time()
while time.time() - start_time < 6:
    r, _, _ = select.select([master], [], [], 0.5)
    if r:
        try:
            chunk = os.read(master, 1024)
            if not chunk:
                break
            output += chunk
        except Exception:
            break

print("=== CAPTURED AGY OAUTH URL ===")
print(output.decode("utf-8", errors="ignore"))
print("==============================")

proc.kill()
