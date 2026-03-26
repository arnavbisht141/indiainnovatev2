#!/bin/bash
echo "Starting Nagar Mirror API & Frontend..."

# Kill existing
pkill -f uvicorn
pkill -f localtunnel
pkill -f cloudflared
sleep 1

# Start FastAPI (which now serves the built frontend too)
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

sleep 3
echo ""
echo "========================================="
echo " Your App is running locally on port 8000"
echo "========================================="
echo ""
echo "Creating a rock-solid, password-less public HTTPS link via Cloudflare Tunnel..."
cd ..

if [ ! -f "/tmp/cloudflared" ]; then
    echo "Downloading Cloudflare Tunnel client (first-time only)..."
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /tmp/cloudflared
    chmod +x /tmp/cloudflared
fi

# Run cloudflared in the background and tail the logs to show the user the link
/tmp/cloudflared tunnel --url http://localhost:8000 \
    2>&1 | awk '/https:\/\// {print "\n\n🌐 YOUR GLOBAL LINK IS READY:\n" $0 "\n\n"}' &

# Keep the script alive so the servers don't die
wait $UVICORN_PID
