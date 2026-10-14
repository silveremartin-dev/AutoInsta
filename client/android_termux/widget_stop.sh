#!/data/data/com.termux/files/usr/bin/bash
# ========================================================
# AutoInsta Widget Quick Launch - STOP 1-CLIC
# ========================================================
if [ -f "$HOME/autoinsta_capture.pid" ]; then
    kill $(cat "$HOME/autoinsta_capture.pid") 2>/dev/null
    rm -f "$HOME/autoinsta_capture.pid"
fi

if [ -f "$HOME/autoinsta_server.pid" ]; then
    kill $(cat "$HOME/autoinsta_server.pid") 2>/dev/null
    rm -f "$HOME/autoinsta_server.pid"
fi

# Sécurité : arrêt de tous les processus résiduels
pkill -f "autoinsta_capture.py" 2>/dev/null
pkill -f "uvicorn server.app:app" 2>/dev/null

termux-wake-unlock
termux-toast "AutoInsta: Entièrement Arrêté"
echo "[✓] AutoInsta arrêté avec succès."
