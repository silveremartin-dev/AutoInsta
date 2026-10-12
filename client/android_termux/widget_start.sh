#!/data/data/com.termux/files/usr/bin/bash
# Termux:Widget Quick Launch - Start AutoInsta
termux-wake-lock
cd "$HOME/AutoInsta" || cd "/data/data/com.termux/files/home"
python client/android_termux/autoinsta_capture.py > "$HOME/autoinsta.log" 2>&1 &
echo $! > "$HOME/autoinsta.pid"
termux-toast "AutoInsta: Capture Active"
