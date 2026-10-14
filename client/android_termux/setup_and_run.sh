#!/data/data/com.termux/files/usr/bin/bash
# AutoInsta Termux Setup & Run Script (Client Mode)

echo "[*] Updating Termux packages..."
pkg update -y

echo "[*] Installing Python & Termux-API tools..."
pkg install -y python termux-api jq

echo "[*] Installing Python requests..."
pip install --break-system-packages requests

echo "[*] Starting AutoInsta Client..."
export AUTOINSTA_SERVER="${AUTOINSTA_SERVER:-http://192.168.1.38:8000/api/capture/upload}"
export AUTOINSTA_KEY="${AUTOINSTA_KEY:-autoinsta_device_secret_token_123}"
export AUTOINSTA_INTERVAL="${AUTOINSTA_INTERVAL:-30}"
export AUTOINSTA_CAMERA="${AUTOINSTA_CAMERA:-0}"

python client/android_termux/autoinsta_capture.py
