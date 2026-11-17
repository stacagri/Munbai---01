import pty
import os
import subprocess
import time
import select
import termios
import struct
import fcntl

master, slave = pty.openpty()
winsize = struct.pack('HHHH', 60, 500, 0, 0)
fcntl.ioctl(slave, termios.TIOCSWINSZ, winsize)

p = subprocess.Popen(['/home/ubuntu/.local/bin/agy'], stdin=slave, stdout=slave, stderr=slave)
os.close(slave)
time.sleep(2)
os.write(master, b'\r')

all_chunks = []
start = time.time()
while time.time() - start < 6:
    r, _, _ = select.select([master], [], [], 0.5)
    if r:
        try:
            chunk = os.read(master, 4096)
            if not chunk:
                break
            all_chunks.append(chunk)
        except Exception:
            break

p.kill()

raw = b''.join(all_chunks)
with open('/home/ubuntu/auto_blogpost/raw_capture.txt', 'wb') as f:
    f.write(raw)

print(f"Total bytes captured: {len(raw)}")
