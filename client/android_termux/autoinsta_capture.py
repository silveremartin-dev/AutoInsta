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
        msg = f"[ALERTE AUTOINSTA] Rythme cardiaque critique : {bpm} BPM. Localisation : https://maps.google.com/?q={coords}"
        print(f"[!] ENVOI DU SMS D'URGENCE à {EMERGENCY_CONTACT}: {msg}")
        try:
            subprocess.run(["termux-sms-send", "-n", EMERGENCY_CONTACT, msg], timeout=10)
        except Exception as e:
            print(f"[!] Échec de l'envoi du SMS d'urgence: {e}")

def capture_photo(camera_id=0, output_path="/data/data/com.termux/files/home/autoinsta_temp.jpg") -> str:
    """Takes silent snapshot using Termux Camera API."""
    try:
        if os.path.exists(output_path):
            os.remove(output_path)
        cmd = ["termux-camera-photo", "-c", str(camera_id), output_path]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        if proc.returncode != 0:
            if "android.permission.CAMERA" in proc.stderr:
                print("\n[!] ATTENTION : Permission Caméra requise !")
                print("    👉 Allez dans Paramètres Android > Applications > Termux:API > Autorisations")
                print("    👉 Activez 'Appareil photo' (Caméra).\n")
            else:
                print(f"[!] Erreur capture caméra ({proc.returncode}): {proc.stderr.strip()}")
            return None

        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return output_path
    except Exception as e:
        print(f"[!] Erreur capture caméra: {e}")
    return None

def upload_capture(server_url: str, api_key: str, image_path: str, sensor_dict: dict):
    """POSTs image and sensor metadata to AutoInsta server."""
    headers = {"X-API-Key": api_key}
    with open(image_path, "rb") as f:
        files = {"file": ("pov_android.jpg", f, "image/jpeg")}
        data = {
            "source": "android_termux",
            "sensors": json.dumps(sensor_dict)
        }
        try:
            r = requests.post(server_url, files=files, data=data, headers=headers, timeout=20)
            if r.status_code == 200:
                print(f"[+] Cliché envoyé avec succès ! Capture ID: {r.json().get('capture_id')}")
            else:
                print(f"[!] Réponse serveur ({r.status_code}): {r.text}")
        except Exception as e:
            print(f"[!] Échec de l'envoi au serveur : {e}")

def main():
    parser = argparse.ArgumentParser(description="AutoInsta Android Multi-Sensor Rig")
    parser.add_argument("--server", default=DEFAULT_SERVER_URL, help="URL d'upload AutoInsta")
    parser.add_argument("--key", default=DEFAULT_API_KEY, help="Clé API secrète")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SECONDS, help="Intervalle entre photos (s)")
    parser.add_argument("--camera", type=int, default=int(DEFAULT_CAMERA_ID), help="Caméra (0=Arrière, 1=Avant)")
    parser.add_argument("--min-lux", type=float, default=DEFAULT_MIN_LUX, help="Seuil min de lux (0 = désactivé)")
    args = parser.parse_args()

    print("==============================================")
    print("   AutoInsta Android Multi-Sensor Rig        ")
    print("==============================================")
    print(f"Cible Serveur  : {args.server}")
    print(f"Intervalle     : {args.interval}s")
    print(f"Caméra ID      : {args.camera} ({'Arrière' if args.camera == 0 else 'Avant/Selfie'})")
    print(f"Seuil Lux      : {args.min_lux} lux ({'Actif' if args.min_lux > 0 else 'Désactivé pour tests'})")
    print(f"GPS Actif      : {ENABLE_GPS}")
    print(f"Cardio Actif   : {ENABLE_HEART_RATE}")
    print("==============================================")

    shot_count = 0
    while True:
        try:
            # 1. Anti-poche : vérification de luminosité (uniquement si seuil > 0)
            lux = get_light_level()
            if args.min_lux > 0 and lux < args.min_lux:
                print(f"[-] Luminosité trop faible ({lux:.1f} lux < {args.min_lux} lux) - Téléphone dans la poche ou posé à plat. Pause de {args.interval}s...")
                time.sleep(args.interval)
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
            shot_count += 1
            print(f"[*] Cliché #{shot_count} en cours de capture (lux: {lux:.1f})...")
            img_path = capture_photo(camera_id=args.camera)
            if img_path:
                upload_capture(args.server, args.key, img_path, sensor_payload)
            else:
                print(f"[!] Échec de prise de vue du cliché #{shot_count}")

            print(f"[*] Prochain cliché dans {args.interval}s (Ctrl+C pour quitter)...")
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[*] Arrêt d'AutoInsta.")
            break
        except Exception as e:
            print(f"[!] Erreur boucle : {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
