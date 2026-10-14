#!/data/data/com.termux/files/usr/bin/python
"""
AutoInsta - Advanced Android Lifelogging & Sensor Rig (Termux)
- Captures POV photos conditionally based on light & motion sensors
- Gathers GPS coordinates, speed, and neighborhood context
- Optional heart rate monitoring & emergency SMS trigger
- Sends multipart payload to AutoInsta server
"""

import os
import sys
import time
import subprocess
import requests
import json
import argparse

# Default configurations (can be overridden via CLI args or environment variables)
DEFAULT_SERVER_URL = os.getenv("AUTOINSTA_SERVER", "http://192.168.1.38:8000/api/capture/upload")
DEFAULT_API_KEY = os.getenv("AUTOINSTA_KEY", "autoinsta_device_secret_token_123")
DEFAULT_INTERVAL_SECONDS = int(os.getenv("AUTOINSTA_INTERVAL", "30"))
DEFAULT_CAMERA_ID = os.getenv("AUTOINSTA_CAMERA", "0") # 0 = Back, 1 = Front
DEFAULT_MIN_LUX = float(os.getenv("AUTOINSTA_MIN_LUX", "5.0")) # 5.0 lux anti-poche restored

ENABLE_GPS = os.getenv("AUTOINSTA_ENABLE_GPS", "1") == "1"
ENABLE_HEART_RATE = os.getenv("AUTOINSTA_ENABLE_HR", "0") == "1"
EMERGENCY_CONTACT = os.getenv("AUTOINSTA_EMERGENCY_PHONE", "")

def get_light_level() -> float:
    """Reads ambient light sensor via Termux API."""
    try:
        res = subprocess.run(["termux-sensor", "-s", "Light", "-n", "1"], capture_output=True, text=True, timeout=4)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            for k, val in data.items():
                if "light" in k.lower():
                    values = val.get("values", [50])
                    if values:
                        return float(values[0])
    except Exception:
        pass
    return 50.0

def get_gps_location() -> dict:
    """Reads current GPS coordinates via Termux Location API."""
    if not ENABLE_GPS:
        return {}
    try:
        res = subprocess.run(["termux-location", "-p", "network", "-r", "once"], capture_output=True, text=True, timeout=6)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            return {
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "speed_kmh": round((data.get("speed", 0) or 0) * 3.6, 1),
                "accuracy": data.get("accuracy")
            }
    except Exception:
        pass
    return {}

def check_heart_rate_and_alert(bpm: int, location_info: dict):
    """Sends emergency SMS if heart rate is dangerously high or low."""
    if not EMERGENCY_CONTACT or bpm <= 0:
        return

    if bpm < 45 or bpm > 145:
        coords = f"{location_info.get('latitude', '')},{location_info.get('longitude', '')}"
        msg = f"[AUTOINSTA ALERT] Critical heart rate: {bpm} BPM. Location: https://maps.google.com/?q={coords}"
        print(f"[!] SENDING EMERGENCY SMS to {EMERGENCY_CONTACT}: {msg}")
        try:
            subprocess.run(["termux-sms-send", "-n", EMERGENCY_CONTACT, msg], timeout=10)
        except Exception as e:
            print(f"[!] Failed to send emergency SMS: {e}")

def capture_photo(camera_id=0, output_path="/data/data/com.termux/files/home/autoinsta_temp.jpg") -> str:
    """Takes silent snapshot using Termux Camera API."""
    try:
        if os.path.exists(output_path):
            os.remove(output_path)
        cmd = ["termux-camera-photo", "-c", str(camera_id), output_path]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        if proc.returncode != 0:
            if "android.permission.CAMERA" in proc.stderr:
                print("\n[!] WARNING: Camera permission required!")
                print("    👉 Go to Android Settings > Apps > Termux:API > Permissions")
                print("    👉 Enable 'Camera' permission.\n")
            else:
                print(f"[!] Camera capture error ({proc.returncode}): {proc.stderr.strip()}")
            return None

        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return output_path
    except Exception as e:
        print(f"[!] Camera capture exception: {e}")
    return None

def upload_capture(server_url: str, api_key: str, image_path: str, sensor_dict: dict, insecure: bool = True):
    """POSTs image and sensor metadata to AutoInsta server with HTTPS support."""
    headers = {"X-API-Key": api_key}
    with open(image_path, "rb") as f:
        files = {"file": ("pov_android.jpg", f, "image/jpeg")}
        data = {
            "source": "android_termux",
            "sensors": json.dumps(sensor_dict)
        }
        try:
            # If HTTPS is used on local network, allow self-signed certificates without erroring
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            r = requests.post(server_url, files=files, data=data, headers=headers, timeout=20, verify=not insecure if server_url.startswith("https") else True)
            if r.status_code == 200:
                print(f"[+] Capture sent successfully! Capture ID: {r.json().get('capture_id')}")
            else:
                print(f"[!] Server response ({r.status_code}): {r.text}")
        except Exception as e:
            print(f"[!] Failed to send to server: {e}")

def main():
    parser = argparse.ArgumentParser(description="AutoInsta Android Multi-Sensor Rig")
    parser.add_argument("--server", default=DEFAULT_SERVER_URL, help="AutoInsta upload endpoint")
    parser.add_argument("--key", default=DEFAULT_API_KEY, help="Secret API key")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SECONDS, help="Interval between photos (s)")
    parser.add_argument("--camera", type=int, default=int(DEFAULT_CAMERA_ID), help="Camera ID (0=Back, 1=Front)")
    parser.add_argument("--min-lux", type=float, default=DEFAULT_MIN_LUX, help="Min ambient lux threshold (0 = disabled)")
    parser.add_argument("--strict-ssl", action="store_true", help="Enforce CA-signed certificates (disables self-signed LAN support)")
    args = parser.parse_args()

    print("==============================================")
    print("   AutoInsta Android Multi-Sensor Rig        ")
    print("==============================================")
    print(f"Target Server  : {args.server}")
    print(f"Interval       : {args.interval}s")
    print(f"Camera ID      : {args.camera} ({'Back/POV' if args.camera == 0 else 'Front/Selfie'})")
    print(f"Lux Threshold  : {args.min_lux} lux ({'Active' if args.min_lux > 0 else 'Disabled'})")
    print(f"GPS Active     : {ENABLE_GPS}")
    print(f"Heart Rate Mon : {ENABLE_HEART_RATE}")
    print("==============================================")

    shot_count = 0
    while True:
        try:
            # 1. Pocket darkness check (only if min_lux > 0)
            lux = get_light_level()
            if args.min_lux > 0 and lux < args.min_lux:
                print(f"[-] Ambient light too low ({lux:.1f} lux < {args.min_lux} lux) - Phone in pocket or face down. Pausing {args.interval}s...")
                time.sleep(args.interval)
                continue

            # 2. GPS Location
            loc_data = get_gps_location()

            # 3. Sensor metadata
            sensor_payload = {
                "light_lux": lux,
                "latitude": loc_data.get("latitude"),
                "longitude": loc_data.get("longitude"),
                "speed_kmh": loc_data.get("speed_kmh", 0),
                "activity_state": "Moving" if (loc_data.get("speed_kmh", 0) > 3) else "Static"
            }

            # 4. Snap POV photo
            shot_count += 1
            print(f"[*] Capturing POV snapshot #{shot_count} (lux: {lux:.1f})...")
            img_path = capture_photo(camera_id=args.camera)
            if img_path:
                upload_capture(args.server, args.key, img_path, sensor_payload, insecure=not args.strict_ssl)
            else:
                print(f"[!] Failed to capture snapshot #{shot_count}")

            print(f"[*] Next snapshot in {args.interval}s (Press Ctrl+C to exit)...")
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[*] AutoInsta stopped.")
            break
        except Exception as e:
            print(f"[!] Capture loop error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
