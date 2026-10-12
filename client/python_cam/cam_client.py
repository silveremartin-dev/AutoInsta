import time
import argparse
import requests
import io
import cv2
import json
import numpy as np
from pathlib import Path

def get_approx_location():
    """Gets approximate geographic location via IP geolocation for PC version."""
    try:
        r = requests.get("http://ip-api.com/json", timeout=3)
        if r.status_code == 200:
            data = r.json()
            return {
                "city": data.get("city"),
                "country": data.get("country"),
                "latitude": data.get("lat"),
                "longitude": data.get("lon"),
                "speed_kmh": 0.0
            }
    except Exception:
        pass
    return {"city": "Bureau", "country": "", "speed_kmh": 0.0}

def is_frame_dark(frame, threshold=20):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return np.mean(gray) < threshold

def detect_motion(prev_gray, curr_gray, threshold=25.0):
    if prev_gray is None:
        return True
    frame_diff = cv2.absdiff(prev_gray, curr_gray)
    mean_diff = np.mean(frame_diff)
    return mean_diff > threshold

def run_cam_client(
    server_url: str = "http://localhost:8000/api/capture/upload",
    cam_index: int = 0,
    interval_seconds: int = 30,
    api_key: str = "autoinsta_device_secret_token_123",
    source_name: str = "pc_cam",
    require_motion: bool = True
):
    print(f"[*] Démarrage du Client AutoInsta PC (Webcam + Capteurs)")
    print(f"[*] Cible Serveur : {server_url}")
    print(f"[*] Caméra Source : {cam_index}")
    print(f"[*] Intervalle    : {interval_seconds}s")
    
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print(f"[!] Erreur : Impossible d'ouvrir la caméra {cam_index}")
        return

    prev_gray = None
    loc_cache = get_approx_location()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(2)
                continue

            if is_frame_dark(frame):
                print("[-] Cliché ignoré : luminosité trop faible / caméra couverte.")
                time.sleep(interval_seconds)
                continue

            curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if require_motion and prev_gray is not None:
                has_motion = detect_motion(prev_gray, curr_gray)
                if not has_motion:
                    print("[-] Cliché ignoré : aucun mouvement significatif devant la caméra.")
                    time.sleep(interval_seconds)
                    continue

            prev_gray = curr_gray

            # Encodage JPEG
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            image_bytes = io.BytesIO(buffer)

            # Capteurs PC
            sensors_payload = {
                "city": loc_cache.get("city", "Poste de travail"),
                "country": loc_cache.get("country", ""),
                "latitude": loc_cache.get("latitude"),
                "longitude": loc_cache.get("longitude"),
                "speed_kmh": 0.0,
                "activity_state": "Travail / Bureau"
            }

            headers = {"X-API-Key": api_key}
            files = {"file": ("pc_pov.jpg", image_bytes, "image/jpeg")}
            data = {
                "source": source_name,
                "sensors": json.dumps(sensors_payload)
            }

            try:
                response = requests.post(server_url, files=files, data=data, headers=headers, timeout=10)
                if response.status_code == 200:
                    res_json = response.json()
                    print(f"[+] Cliché PC envoyé avec succès ! Capture ID #{res_json.get('capture_id')}")
                else:
                    print(f"[!] Réponse serveur ({response.status_code}): {response.text}")
            except Exception as e:
                print(f"[!] Échec de connexion : {e}")

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\n[*] Arrêt du client PC.")
    finally:
        cap.release()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoInsta POV PC Client")
    parser.add_argument("--server", default="http://localhost:8000/api/capture/upload")
    parser.add_argument("--camera", default=0)
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--no-motion", action="store_true")
    args = parser.parse_args()

    cam_source = int(args.camera) if str(args.camera).isdigit() else args.camera
    run_cam_client(
        server_url=args.server,
        cam_index=cam_source,
        interval_seconds=args.interval,
        require_motion=not args.no_motion
    )
