#!/data/data/com.termux/files/usr/bin/python
"""
AutoInsta - Termux Android Lifelogging Client
Captures photos opportunistically using Termux:API and sends them to the AutoInsta server.
"""

import os
import sys
import time
import subprocess
import requests
import json

SERVER_URL = os.getenv("AUTOINSTA_SERVER", "http://192.168.1.50:8000/api/capture/upload")
API_KEY = os.getenv("AUTOINSTA_KEY", "autoinsta_device_secret_token_123")
INTERVAL_SECONDS = int(os.getenv("AUTOINSTA_INTERVAL", "45"))
CAMERA_ID = os.getenv("AUTOINSTA_CAMERA", "0") # 0 = Back camera, 1 = Front camera
MIN_LUX = float(os.getenv("AUTOINSTA_MIN_LUX", "5.0"))

def get_light_level():
    """Reads light sensor via Termux API to prevent capturing in dark pockets."""
    try:
        res = subprocess.run(["termux-sensor", "-s", "Light", "-n", "1"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            # Find Light sensor values
            for sensor_name, val in data.items():
                if "light" in sensor_name.lower():
                    values = val.get("values", [0])
                    if values:
                        return float(values[0])
    except Exception:
        pass
    return 50.0 # Default fallback if sensor is unavailable

def capture_photo(output_path="/data/data/com.termux/files/home/autoinsta_temp.jpg"):
    """Takes a single snapshot using Termux Camera API."""
    try:
        if os.path.exists(output_path):
            os.remove(output_path)
        cmd = ["termux-camera-photo", "-c", str(CAMERA_ID), output_path]
        subprocess.run(cmd, check=True, timeout=10)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return output_path
    except Exception as e:
        print(f"[!] Camera capture failed: {e}")
    return None

def upload_capture(image_path):
    """POSTs image to AutoInsta FastAPI backend."""
    headers = {"X-API-Key": API_KEY}
    with open(image_path, "rb") as f:
        files = {"file": ("android_pov.jpg", f, "image/jpeg")}
        data = {"source": "android_termux"}
        try:
            r = requests.post(SERVER_URL, files=files, data=data, headers=headers, timeout=15)
            if r.status_code == 200:
                print(f"[+] Successfully uploaded POV capture! ID: {r.json().get('capture_id')}")
            else:
                print(f"[!] Server error ({r.status_code}): {r.text}")
        except Exception as e:
            print(f"[!] Upload failed: {e}")

def main():
    print("========================================")
    print(" AutoInsta Android Lifelogging Client ")
    print("========================================")
    print(f"Target Server : {SERVER_URL}")
    print(f"Interval      : {INTERVAL_SECONDS}s")
    print(f"Camera ID     : {CAMERA_ID} (0=back, 1=front)")
    print("========================================")

    while True:
        try:
            # Check light sensor to avoid dark pocket shots
            lux = get_light_level()
            if lux < MIN_LUX:
                print(f"[-] Ambient light too low ({lux:.1f} lux < {MIN_LUX} lux) - likely in pocket. Sleeping.")
                time.sleep(INTERVAL_SECONDS)
                continue

            print("[*] Taking POV capture...")
            img_path = capture_photo()
            if img_path:
                upload_capture(img_path)
            
            time.sleep(INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\n[*] Exiting AutoInsta client.")
            break
        except Exception as e:
            print(f"[!] Loop exception: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
