#!/usr/bin/env python3
"""
AutoInsta - Multiplatform Backend & Server Launcher
Called by platform-specific start scripts (Windows, Linux, macOS)
"""

import sys
import os
import time
import socket
import argparse
import webbrowser
import threading
import subprocess
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path and is current working directory
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def get_local_ip() -> str:
    """Detects LAN IP address of this machine for phone/wearable connection."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def check_and_install_dependencies():
    """Checks required dependencies and installs missing ones."""
    print("\n[*] Checking required dependencies...")
    missing = []
    
    modules = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "PIL": "pillow",
        "requests": "requests",
        "pydantic": "pydantic",
        "dotenv": "python-dotenv",
        "multipart": "python-multipart",
        "yaml": "pyyaml",
        "cryptography": "cryptography"
    }
    
    for mod, pkg in modules.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
            
    if missing:
        print(f"[!] Missing dependencies detected: {', '.join(missing)}")
        print("[*] Installing automatically via pip...")
        cmd = [sys.executable, "-m", "pip", "install", *missing]
        res = subprocess.run(cmd)
        if res.returncode == 0:
            print("[✓] All dependencies installed successfully!\n")
        else:
            print("[!] Installation error. Please run: pip install -r requirements.txt\n")
    else:
        print("[✓] All required dependencies are present.\n")

def open_browser_delayed(url: str, delay: float = 1.5):
    """Opens default web browser after server starts."""
    def _open():
        time.sleep(delay)
        print(f"[*] Opening dashboard in default browser: {url}")
        webbrowser.open(url)
    t = threading.Thread(target=_open, daemon=True)
    t.start()

def ensure_port_is_free(port: int = 8000):
    """Detects and terminates any stale process occupying the target port."""
    if sys.platform == "win32":
        try:
            cmd = f'netstat -ano | findstr :{port}'
            out = subprocess.check_output(cmd, shell=True).decode()
            pids = set()
            for line in out.strip().splitlines():
                if "LISTENING" in line.upper():
                    parts = line.strip().split()
                    pids.add(parts[-1])
            for pid in pids:
                if pid != "0" and int(pid) != os.getpid():
                    print(f"[*] Port {port} occupied by previous process #{pid}. Releasing...")
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(1)
        except Exception:
            pass
    else:
        try:
            cmd = f"lsof -ti :{port}"
            pids = subprocess.check_output(cmd, shell=True).decode().strip().splitlines()
            for pid in pids:
                if pid and int(pid) != os.getpid():
                    print(f"[*] Releasing port {port} (process #{pid})...")
                    subprocess.run(f"kill -9 {pid}", shell=True)
                    time.sleep(1)
        except Exception:
            pass

def ensure_ssl_certs():
    """Generates self-signed SSL certs if they don't already exist."""
    cert_path = PROJECT_ROOT / "certs" / "cert.pem"
    key_path = PROJECT_ROOT / "certs" / "key.pem"
    if not cert_path.exists() or not key_path.exists():
        print("[*] SSL certificate not found. Generating TLS cert with Subject Alternative Names (SAN)...")
        from scripts.generate_ssl_certs import generate_self_signed_cert
        generate_self_signed_cert()
    return cert_path, key_path

def run_server(host: str = "0.0.0.0", port: int = 8000, auto_open: bool = True, use_ssl: bool = False):
    """Starts FastAPI/Uvicorn server with optional TLS/HTTPS."""
    ensure_port_is_free(port)
    local_ip = get_local_ip()
    proto = "https" if use_ssl else "http"
    url_localhost = f"{proto}://localhost:{port}"
    url_network = f"{proto}://{local_ip}:{port}"
    
    print("\n" + "=" * 68)
    print(f" 🚀 AUTOINSTA - LOCAL SERVER & DASHBOARD STARTED ({proto.upper()}) ")
    print("=" * 68)
    print(f"  💻 PC Access          : {url_localhost}")
    print(f"  📱 Mobile LAN Access  : {url_network}")
    print(f"  📚 API Documentation  : {url_localhost}/docs")
    if use_ssl:
        print(f"  🔒 TLS Encryption     : Enabled (Self-Signed / SAN)")
    print("-" * 68)
    print("  👉 On your smartphone (Termux or browser on the same Wi-Fi):")
    print(f"     Navigate to: {url_network}")
    if use_ssl:
        print("     (Accept the self-signed certificate warning on first mobile connection)")
    print("=" * 68 + "\n")
    
    if auto_open:
        open_browser_delayed(url_localhost)
        
    import uvicorn
    if use_ssl:
        cert_path, key_path = ensure_ssl_certs()
        uvicorn.run("server.app:app", host=host, port=port, reload=True, ssl_certfile=str(cert_path), ssl_keyfile=str(key_path))
    else:
        uvicorn.run("server.app:app", host=host, port=port, reload=True)

def run_demo_simulation(port: int = 8000):
    """Runs demo simulation posting test captures periodically."""
    import requests
    import random
    from PIL import Image, ImageDraw
    import io
    
    local_ip = get_local_ip()
    url_localhost = f"http://localhost:{port}"
    
    print("\n" + "=" * 68)
    print(" 🎭 AUTOINSTA - DEMO & INTERACTIVE SIMULATION MODE ")
    print("=" * 68)
    print("  This mode runs the server AND simulates smartphone captures:")
    print("  - Automatic POV test frame injection")
    print("  - Realistic telemetry (BPM, Lux, Battery %, GPS)")
    print(f"  💻 Dashboard : {url_localhost}")
    print("=" * 68 + "\n")
    
    open_browser_delayed(url_localhost)

    def _start_uvicorn():
        import uvicorn
        uvicorn.run("server.app:app", host="0.0.0.0", port=port, log_level="warning")
        
    server_thread = threading.Thread(target=_start_uvicorn, daemon=True)
    server_thread.start()
    
    time.sleep(2)
    
    scenes = [
        ("Sunny cafe terrace", "Paris, France", 48.8566, 2.3522, 650, 72),
        ("Brisk walk session", "Parc des Buttes-Chaumont", 48.8809, 2.3828, 420, 118),
        ("Deep work on laptop", "Coworking Space", 48.8606, 2.3376, 210, 68),
        ("Night city stroll", "Seine Riverbanks", 48.8584, 2.2945, 15, 64)
    ]
    
    step = 0
    print("[*] Simulator active. Posting test capture every 25 seconds...")
    print("    (Press Ctrl+C to stop demo mode at any time)\n")
    
    try:
        while True:
            scene_name, loc_city, lat, lon, lux, base_bpm = scenes[step % len(scenes)]
            step += 1
            
            img = Image.new("RGB", (640, 480), color=(random.randint(40, 100), random.randint(50, 130), random.randint(70, 160)))
            draw = ImageDraw.Draw(img)
            draw.rectangle([20, 20, 620, 460], outline=(255, 255, 255), width=3)
            draw.text((40, 50), f"AutoInsta POV Demo - #{step}", fill=(255, 255, 255))
            draw.text((40, 90), f"Context : {scene_name}", fill=(220, 240, 255))
            draw.text((40, 130), f"Place   : {loc_city}", fill=(200, 220, 240))
            draw.text((40, 170), f"Time    : {time.strftime('%H:%M:%S')}", fill=(200, 220, 240))
            
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            buf.seek(0)
            
            files = {"file": (f"demo_shot_{step}.jpg", buf, "image/jpeg")}
            data = {
                "source": "demo_phone",
                "light_lux": str(lux),
                "battery_pct": str(max(20, 100 - step * 2)),
                "heart_rate": str(base_bpm + random.randint(-4, 5)),
                "pedometer_steps": str(step * 340),
                "latitude": str(lat),
                "longitude": str(lon),
                "city": loc_city
            }
            
            try:
                r = requests.post(
                    f"http://127.0.0.1:{port}/api/capture/upload",
                    headers={"X-API-Key": "autoinsta_device_secret_token_123"},
                    files=files,
                    data=data,
                    timeout=5
                )
                if r.status_code == 200:
                    resp_json = r.json()
                    print(f"[{time.strftime('%H:%M:%S')}] ✓ Demo capture #{resp_json.get('capture_id')} uploaded: {scene_name} ({base_bpm} BPM, {lux} Lux)")
                else:
                    print(f"[!] Upload failed with HTTP {r.status_code}")
            except Exception as e:
                print(f"[!] Upload error: {e}")
                
            time.sleep(25)
    except KeyboardInterrupt:
        print("\n[*] Demo Mode stopped.")

def run_all_in_one(port: int = 8000, use_ssl: bool = False):
    """Starts both Server and background Webcam capture in a single process."""
    ensure_port_is_free(port)
    check_and_install_dependencies()
    proto = "https" if use_ssl else "http"
    print("\n" + "=" * 68)
    print(" 📷 ALL-IN-ONE MODE: SERVER + PC WEBCAM ")
    print("=" * 68)
    print(f"  Server and local webcam capture running concurrently ({proto.upper()}).")
    print("=" * 68 + "\n")
    
    import uvicorn
    ssl_kwargs = {}
    if use_ssl:
        cert_path, key_path = ensure_ssl_certs()
        ssl_kwargs = {"ssl_certfile": str(cert_path), "ssl_keyfile": str(key_path)}
        
    server_thread = threading.Thread(
        target=lambda: uvicorn.run("server.app:app", host="0.0.0.0", port=port, log_level="warning", **ssl_kwargs),
        daemon=True
    )
    server_thread.start()
    time.sleep(2)
    open_browser_delayed(f"{proto}://localhost:{port}")
    
    try:
        from client.python_cam.cam_client import run_cam_client
        run_cam_client(server_url=f"{proto}://127.0.0.1:{port}/api/capture/upload")
    except KeyboardInterrupt:
        print("\n[*] All-in-One mode stopped.")

def run_tests():
    """Runs the complete test suite."""
    test_script = PROJECT_ROOT / "scripts" / "test" / "run_all_tests.py"
    subprocess.run([sys.executable, str(test_script)])

def run_cam():
    """Runs standalone PC webcam client."""
    cam_script = PROJECT_ROOT / "client" / "python_cam" / "cam_client.py"
    subprocess.run([sys.executable, str(cam_script)])

def manage_autostart(enable: bool):
    """Enables or disables system boot autostart."""
    autostart_script = PROJECT_ROOT / "scripts" / "autostart" / "manage_autostart.py"
    action = "--enable" if enable else "--disable"
    subprocess.run([sys.executable, str(autostart_script), action])

def interactive_menu():
    """Interactive command-line menu."""
    while True:
        print("\n" + "=" * 68)
        print("          AUTOINSTA - MAIN LAUNCHER MENU")
        print("=" * 68)
        print("  [1] Start AutoInsta HTTP (Server + Web UI) [Default]")
        print("  [2] Start AutoInsta HTTPS (Encrypted TLS for PC <-> Phone)")
        print("  [3] Start AutoInsta All-in-One (Server + PC Webcam)")
        print("  [4] Demo Simulation Mode (Periodic test frames & telemetry)")
        print("  [5] Run Full Test Suite")
        print("  [6] Install or Update Required Dependencies")
        print("  [7] Generate / Refresh SSL TLS Certificates")
        print("  [8] Toggle System Boot Autostart (Windows / macOS / Linux)")
        print("  [0] Exit")
        print("=" * 68)
        
        try:
            choice = input("Select an option [0-8] (default: 1): ").strip()
        except EOFError:
            choice = "1"
            
        if choice in ("", "1"):
            check_and_install_dependencies()
            run_server(auto_open=True, use_ssl=False)
            break
        elif choice == "2":
            check_and_install_dependencies()
            run_server(auto_open=True, use_ssl=True)
            break
        elif choice == "3":
            run_all_in_one()
            break
        elif choice == "4":
            check_and_install_dependencies()
            run_demo_simulation()
            break
        elif choice == "5":
            run_tests()
            break
        elif choice == "6":
            check_and_install_dependencies()
        elif choice == "7":
            from scripts.generate_ssl_certs import generate_self_signed_cert
            generate_self_signed_cert()
        elif choice == "8":
            enable = input("Enable autostart? (y/n): ").strip().lower().startswith("y")
            manage_autostart(enable)
        elif choice == "0":
            print("\nGoodbye!")
            sys.exit(0)
        else:
            print("[!] Invalid option. Please try again.")

def main():
    parser = argparse.ArgumentParser(description="AutoInsta Multiplatform Launcher")
    parser.add_argument("--mode", choices=["server", "demo", "test", "cam", "autostart-enable", "autostart-disable", "ssl-gen"], help="Direct execution mode")
    parser.add_argument("--host", default="0.0.0.0", help="Listen host address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Listen port (default: 8000)")
    parser.add_argument("--ssl", action="store_true", help="Enable TLS/HTTPS encryption with local certificates")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open default browser")
    parser.add_argument("--install", action="store_true", help="Check and install required dependencies")
    
    args = parser.parse_args()
    
    if args.install:
        check_and_install_dependencies()
        return

    if args.mode == "ssl-gen":
        from scripts.generate_ssl_certs import generate_self_signed_cert
        generate_self_signed_cert()
        return

    if args.mode == "demo":
        check_and_install_dependencies()
        run_demo_simulation(port=args.port)
    elif args.mode == "test":
        run_tests()
    elif args.mode == "cam":
        run_cam()
    elif args.mode == "autostart-enable":
        manage_autostart(True)
    elif args.mode == "autostart-disable":
        manage_autostart(False)
    else:
        # Check environment variable or argument for SSL
        use_ssl = args.ssl or os.getenv("USE_HTTPS", "").lower() in ("true", "1", "yes")
        check_and_install_dependencies()
        run_server(host=args.host, port=args.port, auto_open=not args.no_browser, use_ssl=use_ssl)

if __name__ == "__main__":
    main()
