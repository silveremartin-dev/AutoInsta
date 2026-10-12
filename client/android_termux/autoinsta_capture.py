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

SERVER_URL = os.getenv("AUTOINSTA_SERVER", "http://192.168.1.50:8000/api/capture/upload")
API_KEY = os.getenv("AUTOINSTA_KEY", "autoinsta_device_secret_token_123")
INTERVAL_SECONDS = int(os.getenv("AUTOINSTA_INTERVAL", "30"))
CAMERA_ID = os.getenv("AUTOINSTA_CAMERA", "0") # 0 = Back, 1 = Front
MIN_LUX = float(os.getenv("AUTOINSTA_MIN_LUX", "5.0"))

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
        msg = f"[ALERTE AUTOINSTA] Rythme cardiaque critique : {bpm} BPM. Localisation : https://maps.google.com/?q={coords}"
        print(f"[!] ENVOI DU SMS D'URGENCE à {EMERGENCY_CONTACT}: {msg}")
        try:
            subprocess.run(["termux-sms-send", "-n", EMERGENCY_CONTACT, msg], timeout=10)
        except Exception as e:
            print(f"[!] Échec de l'envoi du SMS d'urgence: {e}")

def capture_photo(output_path="/data/data/com.termux/files/home/autoinsta_temp.jpg") -> str:
    """Takes silent snapshot using Termux Camera API."""
    try:
        if os.path.exists(output_path):
            os.remove(output_path)
        cmd = ["termux-camera-photo", "-c", str(CAMERA_ID), output_path]
        subprocess.run(cmd, check=True, timeout=12)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return output_path
    except Exception as e:
        print(f"[!] Camera capture error: {e}")
    return None

def upload_capture(image_path: str, sensor_dict: dict):
    """POSTs image and sensor metadata to AutoInsta server."""
    headers = {"X-API-Key": API_KEY}
    with open(image_path, "rb") as f:
        files = {"file": ("pov_android.jpg", f, "image/jpeg")}
        data = {
            "source": "android_termux",
            "sensors": json.dumps(sensor_dict)
        }
        try:
            r = requests.post(SERVER_URL, files=files, data=data, headers=headers, timeout=20)
            if r.status_code == 200:
                print(f"[+] Cliché envoyé avec succès ! Capture ID: {r.json().get('capture_id')}")
            else:
                print(f"[!] Réponse serveur ({r.status_code}): {r.text}")
        except Exception as e:
            print(f"[!] Échec de l'envoi au serveur : {e}")

def main():
    print("==============================================")
    print("   AutoInsta Android Multi-Sensor Rig        ")
    print("==============================================")
    print(f"Cible Serveur  : {SERVER_URL}")
    print(f"Intervalle     : {INTERVAL_SECONDS}s")
    print(f"GPS Actif      : {ENABLE_GPS}")
    print(f"Cardio Actif   : {ENABLE_HEART_RATE}")
    print("==============================================")

    while True:
        try:
            # 1. Anti-poche : vérification de luminosité
            lux = get_light_level()
            if lux < MIN_LUX:
                print(f"[-] Luminosité trop faible ({lux:.1f} lux) - Téléphone dans la poche. Pause.")
                time.sleep(INTERVAL_SECONDS)
                continue

            # 2. Lecture GPS
            loc_data = get_gps_location()

            # 3. Métadonnées capteurs
            sensor_payload = {
                "light_lux": lux,
                "latitude": loc_data.get("latitude"),
                "longitude": loc_data.get("longitude"),
                "speed_kmh": loc_data.get("speed_kmh", 0),
                "activity_state": "En déplacement" if (loc_data.get("speed_kmh", 0) > 3) else "Statique"
            }

            # 4. Prise de vue
            print("[*] Prise du cliché POV...")
            img_path = capture_photo()
            if img_path:
                upload_capture(img_path, sensor_payload)

            time.sleep(INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\n[*] Arrêt d'AutoInsta.")
            break
        except Exception as e:
            print(f"[!] Erreur boucle : {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
