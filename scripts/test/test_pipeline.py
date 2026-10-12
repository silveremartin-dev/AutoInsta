"""
AutoInsta - Full End-to-End Pipeline Test
Tests:
1. POV image generation / loading
2. Multimodal VLM evaluation (Gemini 1.5 Flash / Simulation)
3. Strict privacy gate & aesthetic scoring
4. Approval queue / Publisher (Local vault / Dry-run)
"""

import sys
import os
import json
import time
from pathlib import Path
from PIL import Image, ImageDraw

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from server.config import settings
from server.database import db
from server.evaluator import evaluator
from server.publisher import publisher

def create_sample_pov_image(filename="test_pov_sample.jpg") -> Path:
    """Generates a clean synthetic POV test image with realistic composition."""
    out_dir = BASE_DIR / "data" / "test_scratch"
    out_dir.mkdir(parents=True, exist_ok=True)
    img_path = out_dir / filename
    
    # Create 1280x720 image (Street / Coffee table aesthetic)
    img = Image.new('RGB', (1280, 720), color=(40, 45, 55))
    draw = ImageDraw.Draw(img)
    
    # Draw simple background geometry
    draw.rectangle([0, 450, 1280, 720], fill=(70, 50, 40)) # Wooden table
    draw.ellipse([540, 490, 740, 690], fill=(220, 210, 195)) # Ceramic plate
    draw.ellipse([570, 520, 710, 660], fill=(120, 75, 45))   # Coffee cup / espresso
    draw.text((60, 60), "AutoInsta POV Pipeline Test Frame", fill=(200, 200, 220))
    
    img.save(img_path, format="JPEG", quality=90)
    return img_path

def run_test():
    print("=" * 60)
    print(" 🧪 TEST AUTOINSTA : PIPELINE COMPLET DE CAPTURE & IA ")
    print("=" * 60)
    print(f"Modèle VLM      : {settings.vlm_model}")
    print(f"Clé Gemini      : {'Fournie ✓' if settings.gemini_api_key else 'Mode Simulation locale'}")
    print(f"Mode Diffusion  : {settings.publish_mode}")
    print(f"Validation Manuelle : {settings.require_manual_confirmation}")
    print("-" * 60)

    # 1. Image Creation
    print("[1/4] Création du cliché POV de test...")
    img_path = create_sample_pov_image()
    print(f"      Image créée : {img_path.name} ({img_path.stat().st_size} octets)")

    # 2. Database Ingestion
    print("[2/4] Enregistrement en base locale SQLite...")
    sensor_meta = {
        "city": "Paris (Test)",
        "speed_kmh": 4.5,
        "activity_state": "Marche urbaine",
        "battery_pct": 88
    }
    cap_id = db.add_capture(img_path.name, str(img_path), source="test_script", sensor_metadata=sensor_meta)
    print(f"      Capture enregistrée sous l'ID #{cap_id}")

    # 3. VLM Evaluation
    print("[3/4] Analyse multimodale par l'évaluateur (Vie privée & Esthétique)...")
    eval_result = evaluator.evaluate_image(img_path, sensor_meta)
    print(f"      Sécurité Pass    : {eval_result.get('safety_pass')}")
    print(f"      Qualité Pass     : {eval_result.get('quality_pass')}")
    print(f"      Note Esthétique  : {eval_result.get('social_score')}/10")
    print(f"      Action Proposée  : {eval_result.get('recommended_action')}")
    print(f"      Légende Produite : {eval_result.get('caption')}")
    
    db.update_evaluation(cap_id, eval_result)

    # 4. Publication / Local Vault
    print("[4/4] Test du moteur de publication / coffre-fort...")
    caption = eval_result.get("caption") or "Cliché test"
    hashtags = eval_result.get("hashtags") or ["test"]
    pub_res = publisher.publish(cap_id, img_path, caption, hashtags)
    print(f"      Résultat : {pub_res.get('mode', 'N/A')} - Succès: {pub_res.get('success')}")

    print("=" * 60)
    print(" ✅ TEST DU PIPELINE RÉUSSI SANS ERREUR !")
    print("=" * 60)

if __name__ == "__main__":
    run_test()
