#!/usr/bin/env python3
"""
AutoInsta - Wearable / Smartwatch Simulation Client
Sends real-time heart rate telemetry to AutoInsta server.
Can simulate normal heart rate or emergency bradycardia / tachycardia events.
"""

import sys
import time
import requests
import argparse

def send_heart_rate(server_url: str, bpm: int, location: str = "Montre Connectée (Simulation)", steps: int = 4250):
    payload = {
        "heart_rate": bpm,
        "location": location,
        "steps": steps
    }
    try:
        r = requests.post(f"{server_url}/api/sensors/health", json=payload, timeout=4)
        if r.status_code == 200:
            res = r.json()
            alert = "🚨 ALERTE HOMME MORT DÉCLENCHÉE !" if res.get("alert_triggered") else "✓ Normal"
            print(f"[{time.strftime('%H:%M:%S')}] Pouls envoyé : {bpm} BPM -> Statut : {alert}")
            return res
        else:
            print(f"[!] Erreur serveur {r.status_code}: {r.text}")
    except Exception as e:
        print(f"[!] Échec de connexion au serveur ({server_url}) : {e}")
    return None

def main():
    parser = argparse.ArgumentParser(description="AutoInsta Smartwatch Simulator")
    parser.add_argument("--server", default="http://127.0.0.1:8000", help="URL de base du serveur AutoInsta")
    parser.add_argument("--bpm", type=int, default=None, help="Envoyer un BPM unique et quitter")
    parser.add_argument("--emergency", choices=["tachy", "brady"], help="Simuler une anomalie cardiaque immédiate")
    parser.add_argument("--loop", action="store_true", help="Simuler l'envoi continu du rythme cardiaque toutes les 5s")
    
    args = parser.parse_args()
    
    if args.emergency == "tachy":
        print("\n🚨 Simulation d'une tachycardie sévère (162 BPM)...")
        send_heart_rate(args.server, 162)
        return
    elif args.emergency == "brady":
        print("\n🚨 Simulation d'une bradycardie sévère (38 BPM)...")
        send_heart_rate(args.server, 38)
        return
        
    if args.bpm is not None:
        send_heart_rate(args.server, args.bpm)
        return

    if args.loop:
        print("\n[*] Démarrage de la synchronisation continue de la montre (Ctrl+C pour quitter)...")
        bpm = 72
        while True:
            send_heart_rate(args.server, bpm)
            time.sleep(5)
    else:
        # Interactive mode
        print("\n=======================================================")
        print("    SIMULATEUR DE MONTRE CONNECTÉE / WEARABLE")
        print("=======================================================")
        print("  [1] Rythme cardiaque normal (72 BPM)")
        print("  [2] Rythme d'effort / sport (120 BPM)")
        print("  [3] Alerte Tachycardie (160 BPM -> Bouton Homme Mort)")
        print("  [4] Alerte Bradycardie (35 BPM -> Bouton Homme Mort)")
        print("  [0] Quitter")
        print("=======================================================")
        choice = input("👉 Votre choix : ").strip()
        if choice == "1":
            send_heart_rate(args.server, 72)
        elif choice == "2":
            send_heart_rate(args.server, 120)
        elif choice == "3":
            send_heart_rate(args.server, 160)
        elif choice == "4":
            send_heart_rate(args.server, 35)

if __name__ == "__main__":
    main()
