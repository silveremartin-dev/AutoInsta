import time
import argparse
import requests
import io
import json
from pathlib import Path

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None


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
    return {"city": "Office", "country": "", "speed_kmh": 0.0}

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
    require_motion: bool = True,
    insecure_ssl: bool = True
):
    print(f"[*] Starting AutoInsta PC Client (Webcam + Sensors)")
    print(f"[*] Target Server : {server_url}")
    print(f"[*] Camera Index  : {cam_index}")
    print(f"[*] Interval      : {interval_seconds}s")
    
    if not CV2_AVAILABLE:
        print("[!] OpenCV is not installed on this system.")
        print("    Run: pip install opencv-python")
        return

    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print(f"[!] Error: Unable to open webcam at index {cam_index}.")
        return

    loc_cache = get_approx_location()
    prev_gray = None
    print(f"[✓] PC Camera client active. Sending frame every {interval_seconds}s.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("[!] Failed to capture frame from webcam.")
                time.sleep(2)
                continue

            # 1. Darkness suppression
            if is_frame_dark(frame):
                print("[-] Lens occluded or dark room. Snapshot skipped.")
                time.sleep(interval_seconds)
                continue

            # 2. Motion suppression
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if require_motion and not detect_motion(prev_gray, gray):
                print("[-] Scene static (no movement). Snapshot skipped.")
                prev_gray = gray
                time.sleep(interval_seconds)
                continue
            prev_gray = gray

            # 3. Encode JPEG
            success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not success:
                continue

            image_bytes = buffer.tobytes()

            sensors_payload = {
                "city": loc_cache.get("city", "Workspace"),
                "country": loc_cache.get("country", ""),
                "latitude": loc_cache.get("latitude"),
                "longitude": loc_cache.get("longitude"),
                "speed_kmh": 0.0,
                "activity_state": "Work / Desk"
            }

            headers = {"X-API-Key": api_key}
            files = {"file": ("pc_pov.jpg", image_bytes, "image/jpeg")}
            data = {
                "source": source_name,
                "sensors": json.dumps(sensors_payload)
            }

            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                response = requests.post(
                    server_url,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=10,
                    verify=not insecure_ssl if server_url.startswith("https") else True
                )
                if response.status_code == 200:
                    res_json = response.json()
                    print(f"[+] PC frame uploaded successfully! Capture ID #{res_json.get('capture_id')}")
                else:
                    print(f"[!] Server response ({response.status_code}): {response.text}")
            except Exception as e:
                print(f"[!] Connection failed: {e}")

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\n[*] Stopping PC client.")
    finally:
        cap.release()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoInsta Standalone PC Webcam Client")
    parser.add_argument("--server", default="http://localhost:8000/api/capture/upload")
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--cam", type=int, default=0)
    parser.add_argument("--key", default="autoinsta_device_secret_token_123")
    args = parser.parse_args()

    run_cam_client(server_url=args.server, cam_index=args.cam, interval_seconds=args.interval, api_key=args.key)
