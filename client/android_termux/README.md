# AutoInsta Android Client (Termux Setup)

This lightweight client runs directly on your Android phone inside **Termux** using the official **Termux:API**. It turns your phone into a passive POV lifelogging capture rig in under 2 minutes.

---

### Prerequisites

1. Install **Termux** from [F-Droid](https://f-droid.org/packages/com.termux/) or GitHub (do not use Google Play Store version as it is outdated).
2. Install **Termux:API** from [F-Droid](https://f-droid.org/packages/com.termux.api/).
3. Grant Camera and Sensor permissions to Termux:API in your Android Settings.

---

### Installation & Run

Open Termux on your phone and run:

```bash
# 1. Install prerequisites
pkg update && pkg install -y python termux-api git
pip install requests

# 2. Download the capture script or copy it onto your phone
curl -O https://raw.githubusercontent.com/silveremartin-dev/AutoInsta/main/client/android_termux/autoinsta_capture.py

# 3. Configure your server URL (replace with your server local IP, Tailscale IP, or public URL)
export AUTOINSTA_SERVER="http://192.168.1.50:8000/api/capture/upload"
export AUTOINSTA_KEY="autoinsta_device_secret_token_123"
export AUTOINSTA_INTERVAL="30" # Seconds between shots
export AUTOINSTA_CAMERA="0"   # 0 = Back camera, 1 = Front camera

# 4. Start lifelogging capture
python autoinsta_capture.py
```

---

### How it Works
1. **Light Sensor Check**: Reads the phone's ambient light sensor (`termux-sensor -s Light`). If inside a dark pocket, purse, or face-down (< 5 lux), it skips the capture to save battery.
2. **Snapshot**: Silently captures a high-resolution frame via `termux-camera-photo`.
3. **Upload**: Streams the image directly to the AutoInsta backend via HTTP POST `multipart/form-data`.
4. **Autonomous Ingestion**: Gemini 1.5 Flash evaluates the frame, filters privacy risks, scores aesthetics, generates the caption, and auto-posts to Instagram if thresholds are met.
