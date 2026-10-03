import time
import argparse
import requests
import io
import cv2
import numpy as np
from pathlib import Path

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
    source_name: str = "python_cam",
    require_motion: bool = True
):
    print(f"[*] Starting AutoInsta POV Camera Client")
    print(f"[*] Server Target: {server_url}")
    print(f"[*] Camera Source: {cam_index}")
    print(f"[*] Capture Interval: {interval_seconds}s")
    
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print(f"[!] Error: Could not open camera {cam_index}")
        return

    prev_gray = None

    try:
        while True:
            # Capture frame
            ret, frame = cap.read()
            if not ret:
                print("[!] Error reading frame from camera.")
                time.sleep(2)
                continue

            # Check darkness / pocket occlusion
            if is_frame_dark(frame):
                print("[-] Skipped: Frame too dark (pocket/occlusion).")
                time.sleep(interval_seconds)
                continue

            curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if require_motion and prev_gray is not None:
                has_motion = detect_motion(prev_gray, curr_gray)
                if not has_motion:
                    print("[-] Skipped: No significant scene change detected.")
                    time.sleep(interval_seconds)
                    continue

            prev_gray = curr_gray

            # Encode as JPEG
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            image_bytes = io.BytesIO(buffer)

            # Upload to AutoInsta Server
            headers = {"X-API-Key": api_key}
            files = {"file": ("pov_frame.jpg", image_bytes, "image/jpeg")}
            data = {"source": source_name}

            try:
                response = requests.post(server_url, files=files, data=data, headers=headers, timeout=10)
                if response.status_code == 200:
                    res_json = response.json()
                    print(f"[+] Uploaded POV frame successfully! Capture ID #{res_json.get('capture_id')}")
                else:
                    print(f"[!] Server returned status {response.status_code}: {response.text}")
            except Exception as e:
                print(f"[!] Connection failed: {e}")

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\n[*] Stopping camera client.")
    finally:
        cap.release()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoInsta POV Camera & RTSP Client")
    parser.add_argument("--server", default="http://localhost:8000/api/capture/upload", help="AutoInsta upload endpoint")
    parser.add_argument("--camera", default=0, help="Camera index (0, 1...) or RTSP/HTTP video stream URL")
    parser.add_argument("--interval", type=int, default=30, help="Interval in seconds between frames")
    parser.add_argument("--key", default="autoinsta_device_secret_token_123", help="Client API Key")
    parser.add_argument("--source", default="python_cam", help="Source identifier")
    parser.add_argument("--no-motion", action="store_true", help="Disable motion filter")
    args = parser.parse_args()

    # Try casting camera index to int if it's a digit
    cam_source = int(args.camera) if str(args.camera).isdigit() else args.camera

    run_cam_client(
        server_url=args.server,
        cam_index=cam_source,
        interval_seconds=args.interval,
        api_key=args.key,
        source_name=args.source,
        require_motion=not args.no_motion
    )
