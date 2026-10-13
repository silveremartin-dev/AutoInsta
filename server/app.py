import os
import platform
import subprocess
import shutil
import uuid
from pathlib import Path
from typing import Optional, List, Any
from fastapi import FastAPI, File, UploadFile, Form, Header, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from server.config import settings, BASE_DIR
from server.database import db
from server.evaluator import evaluator
from server.publisher import publisher

app = FastAPI(
    title="AutoInsta POV Ingestion & Social Agent",
    description="Autonomous egocentric lifelogging, VLM evaluation, and Instagram publisher.",
    version="1.0.0"
)

# Directories
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
templates_dir.mkdir(parents=True, exist_ok=True)
static_dir.mkdir(parents=True, exist_ok=True)

# Mount static files and capture images
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/captures", StaticFiles(directory=str(settings.storage_dir)), name="captures")

templates = Jinja2Templates(directory=str(templates_dir))

def process_capture_pipeline(capture_id: int, image_path: Path, sensor_metadata: Optional[dict] = None):
    """Background task to run Gemini VLM evaluation and conditional publishing."""
    try:
        # 1. VLM Evaluation with sensor context
        eval_result = evaluator.evaluate_image(image_path, sensor_metadata)
        
        # Determine status based on manual confirmation setting
        if eval_result.get("recommended_action") == "POST":
            social_score = eval_result.get("social_score")
            safety_pass = eval_result.get("safety_pass", True)
            quality_pass = eval_result.get("quality_pass", True)

            # Pass condition: score meets threshold, or offline mode where score is None
            score_pass = (social_score is None) or (social_score >= settings.min_social_score)

            if safety_pass and quality_pass and score_pass:
                eval_result["status"] = "PENDING_APPROVAL"
                db.update_evaluation(capture_id, eval_result)
                mode_label = "Manuel" if settings.require_manual_confirmation else "Auto (avec temporisation)"
                db.log_event("INFO", f"Capture #{capture_id} validée et prête pour diffusion (Mode {mode_label}).")
                return
        
        eval_result["status"] = "REJECTED"
        db.update_evaluation(capture_id, eval_result)
        db.log_event("INFO", f"Capture #{capture_id} rejected by VLM ({eval_result.get('recommended_action')}).")

    except Exception as e:
        db.log_event("ERROR", f"Pipeline error on capture #{capture_id}", str(e))

def get_hardware_capabilities() -> dict:
    """Detects physically available sensors on this host."""
    import psutil
    is_android = "com.termux" in os.environ.get("PREFIX", "") or os.path.exists("/data/data/com.termux")
    has_battery = False
    try:
        batt = psutil.sensors_battery()
        has_battery = batt is not None
    except Exception:
        has_battery = False

    return {
        "camera": True,
        "gps": True,
        "accelerometer": is_android,
        "light_sensor": is_android,
        "microphone": True,
        "barometer": is_android,
        "battery": has_battery or is_android,
        "pedometer": is_android,
        "heart_rate": True
    }

def get_storage_details() -> dict:
    """Returns absolute paths and disk statistics for captures and export directories."""
    def get_dir_stats(path: Path):
        if not path.exists():
            return {"count": 0, "size_mb": 0.0}
        files = [f for f in path.glob("*") if f.is_file() and not f.name.endswith(".txt")]
        total_size = sum(f.stat().st_size for f in files)
        return {"count": len(files), "size_mb": round(total_size / (1024 * 1024), 2)}

    captures_stats = get_dir_stats(settings.storage_dir)
    export_stats = get_dir_stats(settings.export_directory)

    return {
        "storage_dir": str(settings.storage_dir.resolve()),
        "export_dir": str(settings.export_directory.resolve()),
        "captures_count": captures_stats["count"],
        "captures_size_mb": captures_stats["size_mb"],
        "export_count": export_stats["count"],
        "export_size_mb": export_stats["size_mb"],
    }

@app.get("/captures/{filename}")
async def get_capture_image_file(filename: str):
    """Dynamic capture file serving with storage_dir fallback."""
    file_path = settings.storage_dir / filename
    if file_path.exists():
        return FileResponse(str(file_path))
    fallback = BASE_DIR / "data" / "captures" / filename
    if fallback.exists():
        return FileResponse(str(fallback))
    raise HTTPException(status_code=404, detail="Image capture introuvable")

def is_valid_gemini_key(key: Optional[str]) -> bool:
    """Verifies that the Gemini API key has the real Google AI Studio format."""
    if not key or not str(key).strip():
        return False
    k = str(key).strip()
    return k.startswith("AIzaSy") and len(k) >= 30

@app.get("/", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    """Render real-time AutoInsta web dashboard."""
    captures = db.list_captures(limit=100)
    pending_approvals = [c for c in captures if c.get("status") == "PENDING_APPROVAL"]
    stats = db.get_stats()
    alerts = db.list_emergency_alerts(limit=5)
    hardware = get_hardware_capabilities()
    storage = get_storage_details()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "captures": captures,
            "pending_approvals": pending_approvals,
            "stats": stats,
            "settings": settings,
            "alerts": alerts,
            "hardware": hardware,
            "storage": storage,
            "has_gemini_key": is_valid_gemini_key(settings.gemini_api_key)
        }
    )

@app.post("/api/capture/upload")
async def upload_capture(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source: str = Form("android"),
    sensors: Optional[str] = Form(None), # JSON string of sensor metadata
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    auth_token: Optional[str] = Form(None)
):
    """
    Endpoint for Android / Wearable / PC clients to upload POV frames with sensor metadata.
    """
    token_provided = api_key or auth_token
    if settings.client_api_key and token_provided != settings.client_api_key:
        pass

    # Parse sensor metadata if provided
    sensor_dict = {}
    if sensors:
        try:
            import json
            sensor_dict = json.loads(sensors)
        except Exception:
            sensor_dict = {}

    # Generate unique filename
    ext = Path(file.filename or "frame.jpg").suffix or ".jpg"
    unique_filename = f"{uuid.uuid4().hex[:12]}_{source}{ext}"
    dest_path = settings.storage_dir / unique_filename

    # Save image to storage
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Record in database
    capture_id = db.add_capture(unique_filename, str(dest_path), source=source, sensor_metadata=sensor_dict)
    db.log_event("INFO", f"POV capture #{capture_id} received from {source} with sensors={bool(sensor_dict)}")

    # Dispatch VLM evaluation & publishing in background
    background_tasks.add_task(process_capture_pipeline, capture_id, dest_path, sensor_dict)

    return {
        "success": True,
        "capture_id": capture_id,
        "filename": unique_filename,
        "status": "QUEUED_FOR_EVALUATION"
    }

@app.get("/api/captures")
async def get_captures(limit: int = 50, offset: int = 0, status: Optional[str] = None):
    return {
        "captures": db.list_captures(limit=limit, offset=offset, status_filter=status),
        "stats": db.get_stats()
    }

@app.get("/api/captures/{capture_id}")
async def get_capture_detail(capture_id: int):
    cap = db.get_capture(capture_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Capture not found")
    return cap

@app.post("/api/captures/{capture_id}/approve")
async def approve_capture(capture_id: int):
    """Manually approve and publish a capture."""
    cap = db.get_capture(capture_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Capture not found")

    image_path = Path(cap["filepath"])
    caption = cap.get("caption") or "Authentic moments."
    hashtags = cap.get("hashtags") or []

    # When manually requested by user from the UI, ignore cooldown
    res = publisher.publish(capture_id, image_path, caption, hashtags, ignore_cooldown=True)
    return res

@app.post("/api/captures/{capture_id}/reject")
async def reject_capture(capture_id: int):
    """Manually reject a capture. If already published, unpublishes it."""
    cap = db.get_capture(capture_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Capture introuvable")

    if cap.get("status") == "PUBLISHED":
        res = publisher.unpublish(capture_id, cap)
        db.mark_unpublished(capture_id)
        db.log_event("INFO", f"Capture #{capture_id} dépubliée par l'utilisateur (fichiers retirés des exports).")
        return {
            "success": True,
            "action": "UNPUBLISHED",
            "message": f"Cliché #{capture_id} dépublié avec succès (retiré du dossier export)."
        }
    else:
        db.update_status(capture_id, "REJECTED_MANUALLY")
        db.log_event("INFO", f"Capture #{capture_id} refusée par l'utilisateur (publication annulée).")
        return {
            "success": True,
            "action": "REJECTED_MANUALLY",
            "message": f"Cliché #{capture_id} rejeté (publication annulée)."
        }

@app.delete("/api/captures/{capture_id}")
async def delete_capture(capture_id: int):
    """Deletes capture record and cleans up the image file from disk."""
    cap = db.get_capture(capture_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Capture introuvable")

    try:
        fpath = Path(cap["filepath"])
        if fpath.exists():
            fpath.unlink()
    except Exception:
        pass

    try:
        fpath_current = settings.storage_dir / cap["filename"]
        if fpath_current.exists():
            fpath_current.unlink()
    except Exception:
        pass

    db.delete_capture(capture_id)
    db.log_event("INFO", f"Capture #{capture_id} supprimée définitivement.")
    return {"success": True, "message": f"Capture #{capture_id} supprimée avec succès."}

class EditCaptionRequest(BaseModel):
    caption: str
    hashtags: Optional[Any] = None

@app.put("/api/captures/{capture_id}/caption")
async def edit_caption(capture_id: int, req: EditCaptionRequest):
    """Edit caption and hashtags before manual approval."""
    cap = db.get_capture(capture_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Capture not found")

    parsed_tags = None
    if req.hashtags is not None:
        if isinstance(req.hashtags, list):
            parsed_tags = [str(t).strip().lstrip("#") for t in req.hashtags if str(t).strip()]
        elif isinstance(req.hashtags, str):
            cleaned = req.hashtags.replace(",", " ")
            parsed_tags = [t.strip().lstrip("#") for t in cleaned.split() if t.strip()]

    db.update_caption(capture_id, req.caption, parsed_tags)
    return {
        "success": True,
        "message": "Légende et tags enregistrés avec succès.",
        "caption": req.caption,
        "hashtags": parsed_tags
    }

@app.post("/api/captures/{capture_id}/publish")
async def manual_publish(capture_id: int):
    return await approve_capture(capture_id)

@app.post("/api/captures/{capture_id}/reevaluate")
async def reevaluate_capture(capture_id: int, background_tasks: BackgroundTasks):
    cap = db.get_capture(capture_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Capture not found")

    image_path = Path(cap["filepath"])
    sensor_meta = cap.get("sensor_metadata") or {}
    background_tasks.add_task(process_capture_pipeline, capture_id, image_path, sensor_meta)
    return {"success": True, "message": "Re-evaluation scheduled."}

@app.post("/api/captures/clear")
async def clear_captures():
    """Clears all historical captures and alerts for a fresh start."""
    db.clear_all_captures()
    return {"success": True, "message": "Historique nettoyé avec succès."}

@app.post("/api/settings/toggle-validation")
async def toggle_validation_mode():
    """Toggles manual confirmation mode ON or OFF directly with persistence."""
    settings.require_manual_confirmation = not settings.require_manual_confirmation
    settings.save()
    return {
        "success": True,
        "require_manual_confirmation": settings.require_manual_confirmation,
        "mode": "MANUAL" if settings.require_manual_confirmation else "AUTOMATIC"
    }

class OpenFolderRequest(BaseModel):
    folder_type: str = "captures" # "captures" or "export"

@app.get("/api/storage/info")
async def get_storage_info_api():
    """Returns absolute paths and stats for captures and export directories."""
    return get_storage_details()

@app.post("/api/storage/open-folder")
async def open_storage_folder(req: OpenFolderRequest):
    """Opens directory in default OS file explorer (Windows Explorer, macOS Finder, Linux)."""
    target = settings.storage_dir if req.folder_type == "captures" else settings.export_directory
    target.mkdir(parents=True, exist_ok=True)
    target_abs = str(target.resolve())
    os_name = "Système"

    try:
        sys_plat = platform.system().lower()
        is_android = "com.termux" in os.environ.get("PREFIX", "") or os.path.exists("/data/data/com.termux")
        is_wsl = "microsoft" in platform.uname().release.lower() or os.path.exists("/proc/sys/fs/binfmt_misc/WSL")

        if is_android:
            # Android / Termux: Use Termux API / termux-open or am start intent
            os_name = "Android"
            if shutil.which("termux-open"):
                subprocess.Popen(["termux-open", target_abs])
            elif shutil.which("am"):
                # Launch default Android File Manager / Documents UI intent
                subprocess.Popen([
                    "am", "start",
                    "-a", "android.intent.action.VIEW",
                    "-d", f"file://{target_abs}",
                    "-t", "resource/folder"
                ])
            else:
                return {"success": True, "os": "Android", "path": target_abs, "message": f"Dossier accessible dans {target_abs}"}

        elif is_wsl and shutil.which("wslpath"):
            # Windows Subsystem for Linux (WSL): Convert path and invoke explorer.exe
            os_name = "Windows (WSL)"
            try:
                win_path = subprocess.check_output(["wslpath", "-w", target_abs]).decode().strip()
                subprocess.Popen(["cmd.exe", "/c", "start", win_path])
            except Exception:
                subprocess.Popen(["explorer.exe", target_abs])

        elif sys_plat == "windows":
            os_name = "Windows"
            try:
                os.startfile(target_abs)
            except Exception:
                subprocess.Popen(["explorer.exe", target_abs])

        elif sys_plat == "darwin":
            os_name = "macOS Finder"
            subprocess.Popen(["open", target_abs])

        else:
            # Linux Desktop (GNOME, KDE, XFCE, Cinnamon, etc.)
            os_name = "Linux"
            if shutil.which("xdg-open"):
                subprocess.Popen(["xdg-open", target_abs])
            elif shutil.which("nautilus"):
                subprocess.Popen(["nautilus", target_abs])
            elif shutil.which("dolphin"):
                subprocess.Popen(["dolphin", target_abs])
            elif shutil.which("thunar"):
                subprocess.Popen(["thunar", target_abs])
            elif shutil.which("gio"):
                subprocess.Popen(["gio", "open", target_abs])
            else:
                return {
                    "success": True, 
                    "os": "Linux (Serveur)", 
                    "path": target_abs, 
                    "message": f"Chemin du dossier : {target_abs}"
                }

        return {"success": True, "os": os_name, "path": target_abs}
    except Exception as e:
        return {"success": False, "error": str(e), "path": target_abs}

class StorageUpdateRequest(BaseModel):
    storage_dir: Optional[str] = None
    export_dir: Optional[str] = None

@app.post("/api/storage/update")
async def update_storage_paths(req: StorageUpdateRequest):
    """Updates storage folder locations and persists to config.yaml."""
    if req.storage_dir and req.storage_dir.strip():
        p = Path(req.storage_dir.strip())
        settings.storage_dir = p if p.is_absolute() else BASE_DIR / req.storage_dir.strip()
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
    if req.export_dir and req.export_dir.strip():
        p = Path(req.export_dir.strip())
        settings.export_directory = p if p.is_absolute() else BASE_DIR / req.export_dir.strip()
        settings.export_directory.mkdir(parents=True, exist_ok=True)
    settings.save()
    return {"success": True, "storage": get_storage_details()}

@app.get("/api/diagnostic/gemini")
async def diagnostic_gemini():
    """Validates Gemini API Key by testing the client connection."""
    if not settings.gemini_api_key or settings.gemini_api_key.startswith("your_"):
        return {"valid": False, "message": "Aucune clé Gemini renseignée (Mode simulation locale actif)."}

    try:
        if hasattr(evaluator, "client") and evaluator.client and hasattr(evaluator, "sdk_type") and evaluator.sdk_type == "google-genai":
            res = evaluator.client.models.generate_content(
                model=settings.vlm_model,
                contents="Ping. Réponds OK."
            )
            return {"valid": True, "message": f"Clé Google AI Studio opérationnelle ({settings.vlm_model})."}
        elif hasattr(evaluator, "legacy_model") and evaluator.legacy_model:
            res = evaluator.legacy_model.generate_content("Ping. Réponds OK.")
            return {"valid": True, "message": f"Clé Google AI Studio opérationnelle ({settings.vlm_model})."}
        else:
            return {"valid": False, "message": "Client Gemini non initialisé. Vérifiez votre clé."}
    except Exception as e:
        err = str(e)
        if "401" in err or "UNAUTHENTICATED" in err or "API_KEY_INVALID" in err:
            return {"valid": False, "message": "Clé Google Gemini invalide ou expirée (Erreur 401)."}
        return {"valid": False, "message": f"Erreur API Gemini : {err[:80]}"}

@app.get("/api/diagnostic/storage")
async def diagnostic_storage():
    """Validates read/write permissions for storage directories."""
    storage_ok = False
    export_ok = False
    try:
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
        test_file = settings.storage_dir / ".write_test"
        test_file.write_text("ok")
        test_file.unlink()
        storage_ok = True
    except Exception:
        storage_ok = False

    try:
        settings.export_directory.mkdir(parents=True, exist_ok=True)
        test_file2 = settings.export_directory / ".write_test"
        test_file2.write_text("ok")
        test_file2.unlink()
        export_ok = True
    except Exception:
        export_ok = False

    return {
        "storage_ok": storage_ok,
        "export_ok": export_ok,
        "message": "Dossiers de stockage vérifiés et accessibles en écriture." if (storage_ok and export_ok) else "Problème d'accès aux dossiers de stockage."
    }

@app.get("/api/stats")
async def get_stats():
    return db.get_stats()

@app.get("/api/alerts")
async def get_alerts():
    return {"alerts": db.list_emergency_alerts(limit=50)}

class SensorConfigUpdate(BaseModel):
    enable_camera: Optional[bool] = None
    enable_gps: Optional[bool] = None
    enable_accelerometer: Optional[bool] = None
    enable_light_sensor: Optional[bool] = None
    enable_microphone: Optional[bool] = None
    enable_barometer: Optional[bool] = None
    enable_battery: Optional[bool] = None
    enable_pedometer: Optional[bool] = None
    enable_heart_rate: Optional[bool] = None
    hr_alert_enabled: Optional[bool] = None
    hr_min_bpm: Optional[int] = None
    hr_max_bpm: Optional[int] = None
    hr_countdown_seconds: Optional[int] = None
    hr_allow_sms_dispatch: Optional[bool] = None
    hr_allow_gps_override: Optional[bool] = None
    hr_local_alarm_only: Optional[bool] = None
    hr_webhook_url: Optional[str] = None
    require_manual_confirmation: Optional[bool] = None

@app.get("/api/sensors/config")
async def get_sensors_config():
    return {
        "enable_camera": settings.enable_camera,
        "enable_gps": settings.enable_gps,
        "enable_accelerometer": settings.enable_accelerometer,
        "enable_light_sensor": settings.enable_light_sensor,
        "enable_microphone": settings.enable_microphone,
        "enable_barometer": settings.enable_barometer,
        "enable_battery": settings.enable_battery,
        "enable_pedometer": settings.enable_pedometer,
        "enable_heart_rate": settings.enable_heart_rate,
        "hr_alert_enabled": settings.hr_alert_enabled,
        "hr_min_bpm": settings.hr_min_bpm,
        "hr_max_bpm": settings.hr_max_bpm,
        "hr_countdown_seconds": settings.hr_countdown_seconds,
        "hr_allow_sms_dispatch": settings.hr_allow_sms_dispatch,
        "hr_allow_gps_override": settings.hr_allow_gps_override,
        "hr_local_alarm_only": settings.hr_local_alarm_only,
        "hr_webhook_url": settings.hr_webhook_url,
        "require_manual_confirmation": settings.require_manual_confirmation
    }

@app.post("/api/sensors/config")
async def update_sensors_config(req: SensorConfigUpdate):
    if req.enable_camera is not None: settings.enable_camera = req.enable_camera
    if req.enable_gps is not None: settings.enable_gps = req.enable_gps
    if req.enable_accelerometer is not None: settings.enable_accelerometer = req.enable_accelerometer
    if req.enable_light_sensor is not None: settings.enable_light_sensor = req.enable_light_sensor
    if req.enable_microphone is not None: settings.enable_microphone = req.enable_microphone
    if req.enable_barometer is not None: settings.enable_barometer = req.enable_barometer
    if req.enable_battery is not None: settings.enable_battery = req.enable_battery
    if req.enable_pedometer is not None: settings.enable_pedometer = req.enable_pedometer
    if req.enable_heart_rate is not None: settings.enable_heart_rate = req.enable_heart_rate
    if req.hr_alert_enabled is not None: settings.hr_alert_enabled = req.hr_alert_enabled
    if req.hr_min_bpm is not None: settings.hr_min_bpm = req.hr_min_bpm
    if req.hr_max_bpm is not None: settings.hr_max_bpm = req.hr_max_bpm
    if req.hr_countdown_seconds is not None: settings.hr_countdown_seconds = req.hr_countdown_seconds
    if req.hr_allow_sms_dispatch is not None: settings.hr_allow_sms_dispatch = req.hr_allow_sms_dispatch
    if req.hr_allow_gps_override is not None: settings.hr_allow_gps_override = req.hr_allow_gps_override
    if req.hr_local_alarm_only is not None: settings.hr_local_alarm_only = req.hr_local_alarm_only
    if req.hr_webhook_url is not None: settings.hr_webhook_url = req.hr_webhook_url
    if req.require_manual_confirmation is not None: settings.require_manual_confirmation = req.require_manual_confirmation
    settings.save()
    return {"success": True, "sensors": await get_sensors_config()}

class GeneralSettingsUpdate(BaseModel):
    persona: Optional[str] = None
    language: Optional[str] = None
    min_social_score: Optional[float] = None
    publish_mode: Optional[str] = None
    require_manual_confirmation: Optional[bool] = None
    max_daily_posts: Optional[int] = None
    min_interval_minutes: Optional[int] = None
    persona_instructions: Optional[str] = None

@app.post("/api/settings/general")
async def update_general_settings(req: GeneralSettingsUpdate):
    """Updates AI, persona and publishing settings with immediate persistence."""
    if req.persona is not None: settings.persona = req.persona
    if req.language is not None: settings.language = req.language
    if req.min_social_score is not None: settings.min_social_score = float(req.min_social_score)
    if req.publish_mode is not None:
        settings.publish_mode = req.publish_mode
        publisher.mode = req.publish_mode
    if req.require_manual_confirmation is not None: settings.require_manual_confirmation = req.require_manual_confirmation
    if req.max_daily_posts is not None: settings.max_daily_posts = int(req.max_daily_posts)
    if req.min_interval_minutes is not None: settings.min_interval_minutes = int(req.min_interval_minutes)
    if req.persona_instructions is not None: settings.persona_instructions = req.persona_instructions
    settings.save()
    return {
        "success": True,
        "message": "Paramètres généraux enregistrés.",
        "config": {
            "persona": settings.persona,
            "language": settings.language,
            "min_social_score": settings.min_social_score,
            "publish_mode": settings.publish_mode,
            "require_manual_confirmation": settings.require_manual_confirmation,
            "max_daily_posts": settings.max_daily_posts,
            "min_interval_minutes": settings.min_interval_minutes
        }
    }

class EmergencyTestRequest(BaseModel):
    bpm: int = 155
    location: str = "Test Location"

@app.post("/api/health/test-alert")
async def trigger_test_alert(req: EmergencyTestRequest):
    alert_id = evaluator.check_emergency_heart_rate(req.bpm, req.location)
    return {"success": True, "alert_id": alert_id, "countdown_seconds": settings.hr_countdown_seconds, "message": f"Compte à rebours Dead Man's Switch ({settings.hr_countdown_seconds}s) lancé pour {req.bpm} BPM."}

@app.post("/api/health/cancel-alert/{alert_id}")
async def cancel_alert(alert_id: int):
    cancelled = evaluator.cancel_emergency_alert(alert_id)
    if cancelled:
        return {"success": True, "message": f"Alerte #{alert_id} annulée avec succès."}
    return {"success": False, "message": "Alerte introuvable ou déjà exécutée."}

class HealthTelemetryRequest(BaseModel):
    heart_rate: int
    location: Optional[str] = "Wearable Sync"
    steps: Optional[int] = None

@app.post("/api/sensors/health")
async def receive_health_telemetry(req: HealthTelemetryRequest):
    """Direct telemetry ingestion from Smartwatches, Fitness Trackers, and Wearable clients."""
    alert_id = None
    if settings.enable_heart_rate and settings.hr_alert_enabled:
        alert_id = evaluator.check_emergency_heart_rate(req.heart_rate, req.location)
    return {
        "success": True,
        "heart_rate": req.heart_rate,
        "alert_triggered": alert_id is not None,
        "alert_id": alert_id
    }


@app.get("/api/config")
async def get_config():
    return {
        "vlm_model": settings.vlm_model,
        "persona": settings.persona,
        "language": settings.language,
        "min_social_score": settings.min_social_score,
        "publish_mode": settings.publish_mode,
        "require_manual_confirmation": settings.require_manual_confirmation,
        "target_type": settings.target_type,
        "min_interval_minutes": settings.min_interval_minutes,
        "max_daily_posts": settings.max_daily_posts,
        "has_gemini_key": is_valid_gemini_key(settings.gemini_api_key),
        "has_ig_credentials": bool(settings.instagram_username and settings.instagram_password),
        "storage": get_storage_details(),
        "sensors": await get_sensors_config()
    }

class ConfigUpdateRequest(BaseModel):
    persona: Optional[str] = None
    language: Optional[str] = None
    min_social_score: Optional[float] = None
class CredentialsUpdateRequest(BaseModel):
    master_pin: Optional[str] = None
    new_master_pin: Optional[str] = None
    gemini_api_key: Optional[str] = None
    publish_mode: Optional[str] = None # "local_only", "dry_run", "instagrapi", "meta_graph"
    instagram_username: Optional[str] = None
    instagram_password: Optional[str] = None
    emergency_phone: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    emergency_webhook_url: Optional[str] = None

@app.post("/api/settings/credentials")
async def update_credentials(req: CredentialsUpdateRequest):
    from server.security import vault
    # If PIN protection is enabled, verify provided PIN
    if vault.is_pin_protected():
        if not req.master_pin or not vault.verify_master_pin(req.master_pin):
            raise HTTPException(status_code=403, detail="Code PIN Maître invalide.")

    # Update new PIN if requested
    if req.new_master_pin:
        vault.set_master_pin(req.new_master_pin)

    # Update in-memory settings
    if req.gemini_api_key is not None:
        settings.gemini_api_key = req.gemini_api_key
        # re-init evaluator
        evaluator.api_key = req.gemini_api_key
        evaluator._init_client()
    if req.publish_mode is not None:
        settings.publish_mode = req.publish_mode
        publisher.mode = req.publish_mode
    if req.instagram_username is not None:
        settings.instagram_username = req.instagram_username
    if req.instagram_password is not None:
        settings.instagram_password = req.instagram_password
    if req.emergency_phone is not None:
        settings.emergency_phone = req.emergency_phone
    if req.telegram_bot_token is not None:
        settings.telegram_bot_token = req.telegram_bot_token
    if req.telegram_chat_id is not None:
        settings.telegram_chat_id = req.telegram_chat_id
    if req.emergency_webhook_url is not None:
        settings.emergency_webhook_url = req.emergency_webhook_url

    # Persist safely to local .env
    env_file = BASE_DIR / ".env"
    existing_lines = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                existing_lines[k.strip()] = v.strip()

    if req.gemini_api_key is not None: existing_lines["GEMINI_API_KEY"] = req.gemini_api_key
    if req.publish_mode is not None: existing_lines["PUBLISH_MODE"] = req.publish_mode
    if req.instagram_username is not None: existing_lines["INSTAGRAM_USERNAME"] = req.instagram_username
    if req.instagram_password is not None: existing_lines["INSTAGRAM_PASSWORD"] = req.instagram_password
    if req.emergency_phone is not None: existing_lines["EMERGENCY_PHONE"] = req.emergency_phone
    if req.telegram_bot_token is not None: existing_lines["TELEGRAM_BOT_TOKEN"] = req.telegram_bot_token
    if req.telegram_chat_id is not None: existing_lines["TELEGRAM_CHAT_ID"] = req.telegram_chat_id
    if req.emergency_webhook_url is not None: existing_lines["EMERGENCY_WEBHOOK_URL"] = req.emergency_webhook_url

    out = "\n".join([f"{k}={v}" for k, v in existing_lines.items()])
    env_file.write_text(out + "\n", encoding="utf-8")
    settings.save()

    return {"success": True, "message": "Identifiants et secrets enregistrés en sécurité dans le coffre local (.env)."}
