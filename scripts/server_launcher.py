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
    print("\n[*] Verification des dependances requises...")
    missing = []
    
    modules = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "PIL": "pillow",
        "requests": "requests",
        "pydantic": "pydantic",
        "dotenv": "python-dotenv",
        "multipart": "python-multipart",
        "yaml": "pyyaml"
    }
    
    for mod, pkg in modules.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
            
    if missing:
        print(f"[!] Dependances manquantes detectees : {', '.join(missing)}")
        print("[*] Installation automatique via pip...")
        cmd = [sys.executable, "-m", "pip", "install", *missing]
        res = subprocess.run(cmd)
        if res.returncode == 0:
            print("[✓] Toutes les dependances ont ete installees avec succes !\n")
        else:
            print("[!] Erreur lors de l'installation. Veuillez executer : pip install -r requirements.txt\n")
    else:
        print("[✓] Toutes les dependances requises sont pretes.\n")

def open_browser_delayed(url: str, delay: float = 1.5):
    """Opens default web browser after server starts."""
    def _open():
        time.sleep(delay)
        print(f"[*] Ouverture de l'interface dans votre navigateur : {url}")
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
                    print(f"[*] Port {port} occupe par l'ancien processus #{pid}. Liberation automatique...")
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
                    print(f"[*] Liberation du port {port} (processus #{pid})...")
                    subprocess.run(f"kill -9 {pid}", shell=True)
                    time.sleep(1)
        except Exception:
            pass

def run_server(host: str = "0.0.0.0", port: int = 8000, auto_open: bool = True):
    """Starts FastAPI/Uvicorn server."""
    ensure_port_is_free(port)
    local_ip = get_local_ip()
    url_localhost = f"http://localhost:{port}"
    url_network = f"http://{local_ip}:{port}"
    
    print("\n" + "=" * 68)
    print(" 🚀 AUTOINSTA - SERVEUR LOCAL & TABLEAU DE BORD DEMARRE ")
    print("=" * 68)
    print(f"  💻 Acces depuis ce PC   : {url_localhost}")
    print(f"  📱 Acces depuis Mobile  : {url_network}")
    print(f"  📚 Documentation API    : {url_localhost}/docs")
    print("-" * 68)
    print("  👉 Sur votre smartphone (Termux ou navigateur sur le meme Wi-Fi) :")
    print(f"     Utilisez l'URL : {url_network}")
    print("=" * 68 + "\n")
    
    if auto_open:
        open_browser_delayed(url_localhost)
        
    import uvicorn
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
    print(" 🎭 MODE DEMO & SIMULATION INTERACTIVE AUTOINSTA ")
    print("=" * 68)
    print("  Ce mode demarre le serveur ET simule l'activite d'un smartphone :")
    print("  - Injection automatique de captures d'ecran / photos de test")
    print("  - Donnees capteurs realistes (BPM cardiaque, Lux, Batterie, GPS)")
    print(f"  💻 Tableau de bord : {url_localhost}")
    print("=" * 68 + "\n")
    
    open_browser_delayed(url_localhost)

    def _start_uvicorn():
        import uvicorn
        uvicorn.run("server.app:app", host="0.0.0.0", port=port, log_level="warning")
        
    server_thread = threading.Thread(target=_start_uvicorn, daemon=True)
    server_thread.start()
    
    time.sleep(2)
    
    scenes = [
        ("Terrasse de cafe ensoleillee", "Paris, France", 48.8566, 2.3522, 650, 72),
        ("Seance de marche rapide", "Parc des Buttes-Chaumont", 48.8809, 2.3828, 420, 118),
        ("Session de travail sur laptop", "Espace Coworking", 48.8606, 2.3376, 210, 68),
        ("Promenade nocturne", "Quais de Seine", 48.8584, 2.2945, 15, 64)
    ]
    
    step = 0
    print("[*] Simulateur actif. Envoi d'une capture toutes les 25 secondes...")
    print("    (Appuyez sur Ctrl+C pour arreter le mode demo a tout moment)\n")
    
    try:
        while True:
            scene_name, loc_city, lat, lon, lux, base_bpm = scenes[step % len(scenes)]
            step += 1
            
            img = Image.new("RGB", (640, 480), color=(random.randint(40, 100), random.randint(50, 130), random.randint(70, 160)))
            draw = ImageDraw.Draw(img)
            draw.rectangle([20, 20, 620, 460], outline=(255, 255, 255), width=3)
            draw.text((40, 50), f"AutoInsta POV Demo - #{step}", fill=(255, 255, 255))
            draw.text((40, 90), f"Contexte : {scene_name}", fill=(220, 240, 255))
            draw.text((40, 130), f"Lieu     : {loc_city}", fill=(200, 220, 240))
            draw.text((40, 170), f"Heure    : {time.strftime('%H:%M:%S')}", fill=(200, 220, 240))
            
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
                    headers={"X-Device-Token": "autoinsta_device_secret_token_123"},
                    files=files,
                    data=data,
                    timeout=5
                )
                if r.status_code == 200:
                    resp_json = r.json()
                    print(f"[{time.strftime('%H:%M:%S')}] ✓ Capture #{resp_json.get('capture_id')} envoyee : {scene_name} ({base_bpm} BPM, {lux} Lux)")
                else:
                    print(f"[!] Echec upload : {r.status_code}")
            except Exception as e:
                print(f"[!] Erreur envoi demo : {e}")
                
            time.sleep(25)
    except KeyboardInterrupt:
        print("\n[*] Arret du Mode Demo.")

def run_all_in_one(port: int = 8000):
    """Starts both Server and background Webcam capture in a single process."""
    ensure_port_is_free(port)
    check_and_install_dependencies()
    print("\n" + "=" * 68)
    print(" 📷 DEMARRAGE TOUT-EN-UN : SERVEUR + WEBCAM PC ")
    print("=" * 68)
    print("  Le serveur et la capture webcam locale sont lances ensemble.")
    print("=" * 68 + "\n")
    
    import uvicorn
    server_thread = threading.Thread(
        target=lambda: uvicorn.run("server.app:app", host="0.0.0.0", port=port, log_level="warning"),
        daemon=True
    )
    server_thread.start()
    time.sleep(2)
    open_browser_delayed(f"http://localhost:{port}")
    
    try:
        from client.python_cam.cam_client import run_cam_client
        run_cam_client(server_url=f"http://127.0.0.1:{port}/api/capture/upload")
    except KeyboardInterrupt:
        print("\n[*] Arret du mode Tout-en-Un.")

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
    """Interactive command-line menu without unprintable characters."""
    while True:
        print("\n" + "=" * 68)
        print("          AUTOINSTA - MENU PRINCIPAL DE DEMARRAGE")
        print("=" * 68)
        print("  [1] Demarrer AutoInsta (Serveur + Interface Web avec Camera Integree) [Recommande]")
        print("  [2] Demarrer AutoInsta Tout-en-Un (Serveur + Webcam locale en arriere-plan)")
        print("  [3] Mode Demo (Simulation photos & capteurs de test)")
        print("  [4] Executer la Suite de Tests Complete")
        print("  [5] Installer ou Mettre a jour les dependances requises")
        print("  [6] Activer l'Autodemarrage au Boot (Windows / macOS / Linux)")
        print("  [7] Desactiver l'Autodemarrage")
        print("  [0] Quitter")
        print("=" * 68)
        
        try:
            choice = input("Votre choix [1-7, 0] (defaut: 1) : ").strip()
        except EOFError:
            choice = "1"
            
        if choice in ("", "1"):
            check_and_install_dependencies()
            run_server(auto_open=True)
            break
        elif choice == "2":
            run_all_in_one()
            break
        elif choice == "3":
            check_and_install_dependencies()
            run_demo_simulation()
            break
        elif choice == "4":
            run_tests()
            break
        elif choice == "5":
            check_and_install_dependencies()
        elif choice == "6":
            manage_autostart(True)
        elif choice == "7":
            manage_autostart(False)
        elif choice == "0":
            print("\nAu revoir !")
            sys.exit(0)
        else:
            print("[!] Choix non reconnu. Veuillez reessayer.")

def main():
    parser = argparse.ArgumentParser(description="AutoInsta Multiplatform Launcher")
    parser.add_argument("--mode", choices=["server", "demo", "test", "cam", "autostart-enable", "autostart-disable"], help="Mode d'execution direct")
    parser.add_argument("--host", default="0.0.0.0", help="Adresse IP d'ecoute (defaut: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port HTTP (defaut: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Ne pas ouvrir automatiquement le navigateur")
    parser.add_argument("--install", action="store_true", help="Verifier et installer les dependances requises")
    
    args = parser.parse_args()
    
    if args.install:
        check_and_install_dependencies()
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
        # Default behavior: directly start the application and open browser!
        check_and_install_dependencies()
        run_server(host=args.host, port=args.port, auto_open=not args.no_browser)

if __name__ == "__main__":
    main()
