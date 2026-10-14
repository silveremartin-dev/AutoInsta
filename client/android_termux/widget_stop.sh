#!/data/data/com.termux/files/usr/bin/bash
# ========================================================
# AutoInsta Widget Quick Launch - STOP 1-CLICK
# ========================================================
if [ -f "$HOME/autoinsta_capture.pid" ]; then
    kill $(cat "$HOME/autoinsta_capture.pid") 2>/dev/null
    rm -f "$HOME/autoinsta_capture.pid"
fi

if [ -f "$HOME/autoinsta_server.pid" ]; then
    kill $(cat "$HOME/autoinsta_server.pid") 2>/dev/null
    rm -f "$HOME/autoinsta_server.pid"
fi

# Kill all residual processes
pkill -f "autoinsta_capture.py" 2>/dev/null
pkill -f "uvicorn server.app:app" 2>/dev/null

termux-wake-unlock
termux-toast "AutoInsta: Fully Stopped"
echo "[✓] AutoInsta stopped successfully."
