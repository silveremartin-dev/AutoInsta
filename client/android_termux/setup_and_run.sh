#!/data/data/com.termux/files/usr/bin/bash
# AutoInsta Termux Setup & Run Script

echo "[*] Updating Termux packages..."
pkg update -y && pkg upgrade -y

echo "[*] Installing Python & Termux-API tools..."
pkg install -y python termux-api jq

echo "[*] Installing Python requests..."
pip install requests

echo "[*] Starting AutoInsta Client..."
# Change the IP to your PC / server IP on local network or Tailscale / public domain
export AUTOINSTA_SERVER="http://192.168.1.50:8000/api/capture/upload"
export AUTOINSTA_KEY="autoinsta_device_secret_token_123"
export AUTOINSTA_INTERVAL="30"
export AUTOINSTA_CAMERA="0"

python autoinsta_capture.py
