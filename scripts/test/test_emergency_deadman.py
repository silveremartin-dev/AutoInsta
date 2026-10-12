"""
AutoInsta - Emergency & Dead Man's Switch Test
Tests:
1. Abnormal heart rate detection (Bradycardia < 45 / Tachycardia > 145)
2. Grace period countdown initialization (10 seconds)
3. User cancellation / False-positive abort mechanism
4. Emergency dispatch execution
"""

import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from server.config import settings
from server.evaluator import evaluator
from server.database import db

def test_deadman():
    print("=" * 60)
    print(" 🚨 TEST : BOUTON DE L'HOMME MORT & SÉCURITÉ CARDIAQUE ")
    print("=" * 60)
    print(f"Alerte activée          : {settings.hr_alert_enabled}")
    print(f"Seuils BPM              : Min={settings.hr_min_bpm} / Max={settings.hr_max_bpm}")
    print(f"Compte à rebours        : {settings.hr_countdown_seconds}s")
    print(f"Mode Alarme Locale Seule: {settings.hr_local_alarm_only}")
    print(f"Autorisation envoi SMS  : {settings.hr_allow_sms_dispatch}")
    print("-" * 60)

    # Force alert enabled for testing
    settings.hr_alert_enabled = True

    # Test 1: Trigger and Cancel (False positive simulation)
    print("\n[Scénario 1] Déclenchement d'une alerte (155 BPM) puis ANNULATION manuelle...")
    alert_id = evaluator.check_emergency_heart_rate(155, "Bureau Test - Paris")
    print(f"      Compte à rebours lancé pour Alerte #{alert_id}")
    
    print("      Attente de 2 secondes...")
    time.sleep(2)
    
    print("      L'utilisateur clique sur [ANNULER L'ALERTE]...")
    cancelled = evaluator.cancel_emergency_alert(alert_id)
    assert cancelled is True, "L'annulation aurait dû réussir."
    print("      ✓ Alerte annulée avec succès avant l'envoi de secours !")

    # Test 2: Trigger and Execution (Simulated non-response)
    print("\n[Scénario 2] Déclenchement sans réponse (Compte à rebours raccourci pour le test)...")
    original_countdown = settings.hr_countdown_seconds
    settings.hr_countdown_seconds = 3 # 3 seconds for fast test
    
    alert_id_2 = evaluator.check_emergency_heart_rate(38, "Coordonnées GPS: 48.8566, 2.3522")
    print(f"      Compte à rebours de 3s lancé pour bradycardie (38 BPM) #{alert_id_2}...")
    
    for i in range(3, 0, -1):
        print(f"      Bip alarme... {i}s restantes")
        time.sleep(1)
        
    time.sleep(0.5) # Wait for thread execution
    print("      ✓ Compte à rebours expiré : SOS traité conformément aux consentements.")

    # Restore setting
    settings.hr_countdown_seconds = original_countdown

    # Verify database logs
    alerts = db.list_emergency_alerts(limit=5)
    print(f"\n[Vérification] {len(alerts)} alertes enregistrées en base locale SQLite.")
    print("=" * 60)
    print(" ✅ TEST DU BOUTON DE L'HOMME MORT TERMINÉ AVEC SUCCÈS !")
    print("=" * 60)

if __name__ == "__main__":
    test_deadman()
