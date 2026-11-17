import pty
import os
import subprocess
import time
import select
import termios
import struct
import fcntl

master, slave = pty.openpty()

# Set terminal window size to 60 rows, 160 cols
winsize = struct.pack("HHHH", 60, 160, 0, 0)
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
# Press Enter to select 1. Google OAuth
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

print("=== RAW OUTPUT WITH BIG WINSZ ===")
print(output.decode("utf-8", errors="ignore"))
print("=================================")

proc.kill()
