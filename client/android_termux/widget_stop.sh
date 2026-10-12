#!/data/data/com.termux/files/usr/bin/bash
# Termux:Widget Quick Launch - Stop AutoInsta
if [ -f "$HOME/autoinsta.pid" ]; then
    kill $(cat "$HOME/autoinsta.pid") 2>/dev/null
    rm -f "$HOME/autoinsta.pid"
fi
pkill -f "autoinsta_capture.py"
termux-wake-unlock
termux-toast "AutoInsta: Capture Arrêtée"
