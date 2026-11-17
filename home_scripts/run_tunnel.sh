#!/bin/bash
LOG_FILE="/home/ubuntu/cloudflared.log"
URL_FILE="/home/ubuntu/tunnel_url.txt"

# Run cloudflared and extract URL
/home/ubuntu/cloudflared tunnel --url http://127.0.0.1:8080 > "$LOG_FILE" 2>&1 &
PID=$!

for i in {1..30}; do
    URL=$(grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' "$LOG_FILE" | head -n 1)
    if [ -n "$URL" ]; then
        echo "$URL" > "$URL_FILE"
        echo "Tunnel URL: $URL"
        break
    fi
    sleep 1
done

wait $PID
