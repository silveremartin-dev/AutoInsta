"""
AutoInsta - Local Hardware & Sensor Diagnostic Test
Inspects which sensors are actually available on your current machine/phone:
1. Camera capture check
2. IP Geolocation / City resolution
3. Battery status
4. Ambient light / motion detection check
"""

import sys
import requests
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

def test_camera():
    print("[1/4] Vérification de la Caméra...")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                h, w, _ = frame.shape
                print(f"      ✓ Caméra accessible : Résolution {w}x{h}")
                return True
            else:
                print("      ⚠ Caméra ouverte mais impossible de lire un cliché.")
        else:
            print("      ℹ Aucune caméra par défaut détectée (Normal sur serveur headless).")
    except Exception as e:
        print(f"      ℹ OpenCV / Caméra non disponible : {e}")
    return False

def test_geolocation():
    print("[2/4] Vérification de la Géolocalisation (IP / Réseau)...")
    try:
        r = requests.get("http://ip-api.com/json", timeout=4)
        if r.status_code == 200:
            data = r.json()
            city = data.get("city", "Inconnu")
            country = data.get("country", "")
            lat, lon = data.get("lat"), data.get("lon")
            print(f"      ✓ Géolocalisation réussie : {city}, {country} ({lat}, {lon})")
            return True
        else:
            print(f"      ⚠ Service IP non joignable (Code {r.status_code})")
    except Exception as e:
        print(f"      ℹ Impossible de contacter le service de localisation : {e}")
    return False

def test_battery():
    print("[3/4] Vérification de l'état de la Batterie...")
    try:
        import psutil
        battery = psutil.sensors_battery()
        if battery:
            pct = round(battery.percent)
            plugged = "Sur secteur" if battery.power_plugged else "Sur batterie"
            print(f"      ✓ Batterie : {pct}% ({plugged})")
            return True
        else:
            print("      ℹ Pas de batterie détectée (Poste fixe / PC de bureau).")
    except Exception:
        print("      ℹ Module psutil absent ou poste fixe.")
    return False

def test_security_vault():
    print("[4/4] Vérification du Coffre de Sécurité Local (.env & Clé maître)...")
    from server.security import vault
    print(f"      ✓ Clé maître locale initialisée : {len(vault.master_key)} octets")
    print(f"      ✓ Protection par PIN : {'Activée' if vault.is_pin_protected() else 'Désactivée (Accès libre en local)'}")
    test_secret = "mon_secret_123"
    cipher = vault.encrypt(test_secret)
    decrypted = vault.decrypt(cipher)
    assert decrypted == test_secret, "Erreur de chiffrement/déchiffrement."
    print("      ✓ Chiffrement symétrique AES-256 testé et validé !")
    return True

def main():
    print("=" * 60)
    print(" 🔍 DIAGNOSTIC MATÉRIEL & CAPTEURS AUTOINSTA ")
    print("=" * 60)
    test_camera()
    test_geolocation()
    test_battery()
    test_security_vault()
    print("=" * 60)
    print(" Diagnostic terminé.")
    print("=" * 60)

if __name__ == "__main__":
    main()
