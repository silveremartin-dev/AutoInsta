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

# 2. Start camera capture rig in background (5.0 lux threshold)
echo "[*] Starting POV camera & sensor capture loop in background..."
python client/android_termux/autoinsta_capture.py --server http://127.0.0.1:8000/api/capture/upload --min-lux 5.0 --interval 30 &
CAPTURE_PID=$!
echo $CAPTURE_PID > "$HOME/autoinsta_capture.pid"

# 3. Notification & open browser to local UI
termux-toast "AutoInsta Active (http://localhost:8000)"
sleep 1
termux-open-url "http://localhost:8000"

echo ""
echo "[✓] Web UI accessible at: http://localhost:8000"
echo "[*] Press Ctrl+C at any time to stop AutoInsta."
echo "=========================================================="
echo ""

# 4. Graceful shutdown handler
cleanup() {
    echo ""
    echo "[*] Shutting down AutoInsta..."
    kill $CAPTURE_PID 2>/dev/null
    rm -f "$HOME/autoinsta_capture.pid"
    pkill -f "autoinsta_capture.py" 2>/dev/null
    termux-wake-unlock
    echo "[✓] AutoInsta stopped successfully."
    exit 0
}
trap cleanup INT TERM

# 5. Run Uvicorn server in foreground so Termux session stays active
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
