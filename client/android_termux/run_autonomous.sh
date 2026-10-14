#!/data/data/com.termux/files/usr/bin/bash
# ========================================================
# AutoInsta - 100% Autonomous Mode on Smartphone
# ========================================================
# Runs FastAPI server, SQLite database, Gemini AI evaluation,
# and camera capture loop natively on Android via Termux.

termux-wake-lock
cd "$HOME/AutoInsta" || cd "/data/data/com.termux/files/home/AutoInsta"

echo "=========================================================="
echo "   AutoInsta Autonomous Mobile Stack                      "
echo "=========================================================="

# 1. Clean up any leftover background processes
pkill -f "autoinsta_capture.py" 2>/dev/null
pkill -f "uvicorn server.app:app" 2>/dev/null
sleep 1

# 2. Start Uvicorn server in background
echo "[*] Initializing local AutoInsta server..."
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

# 3. Graceful shutdown handler
cleanup() {
    echo ""
    echo "[*] Shutting down AutoInsta..."
    kill $CAPTURE_PID 2>/dev/null
    kill $SERVER_PID 2>/dev/null
    rm -f "$HOME/autoinsta_capture.pid"
    pkill -f "autoinsta_capture.py" 2>/dev/null
    pkill -f "uvicorn server.app:app" 2>/dev/null
    termux-wake-unlock
    echo "[✓] AutoInsta stopped successfully."
    exit 0
}
trap cleanup INT TERM

# 4. Wait for server to become responsive before opening browser or capturing
echo "[*] Waiting for server initialization (this takes ~15-25s on first start)..."
MAX_WAIT=45
WAIT_COUNT=0
while ! curl -s -f http://127.0.0.1:8000/api/status >/dev/null 2>&1; do
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT+1))
    if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
        echo "[!] Server startup timed out. Check output above."
        break
    fi
done

echo "[✓] Local server is healthy and ready!"

# 5. Start camera capture rig in background (5.0 lux threshold)
echo "[*] Starting POV camera & sensor capture loop in background..."
python client/android_termux/autoinsta_capture.py --server http://127.0.0.1:8000/api/capture/upload --min-lux 5.0 --interval 30 &
CAPTURE_PID=$!
echo $CAPTURE_PID > "$HOME/autoinsta_capture.pid"

# 6. Notification & open browser to local UI
termux-toast "AutoInsta Active (http://localhost:8000)"
sleep 1
termux-open-url "http://localhost:8000"

echo ""
echo "[✓] Web UI accessible at: http://localhost:8000"
echo "[*] AutoInsta is running autonomously. Press Ctrl+C at any time to stop."
echo "=========================================================="
echo ""

# Wait on uvicorn server process so terminal stays open
wait $SERVER_PID
