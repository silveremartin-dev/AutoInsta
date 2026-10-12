import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, List
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
            social_score = eval_result.get("social_score", 0.0)
            safety_pass = eval_result.get("safety_pass", False)
            quality_pass = eval_result.get("quality_pass", False)

            if safety_pass and quality_pass and social_score >= settings.min_social_score:
                if settings.require_manual_confirmation:
                    eval_result["status"] = "PENDING_APPROVAL"
                    db.update_evaluation(capture_id, eval_result)
                    db.log_event("INFO", f"Capture #{capture_id} approved by AI, waiting for user manual confirmation.")
                    return
                else:
                    db.update_evaluation(capture_id, eval_result)
                    caption = eval_result.get("caption", "")
                    hashtags = eval_result.get("hashtags", [])
                    publisher.publish(capture_id, image_path, caption, hashtags)
                    return
        
        eval_result["status"] = "REJECTED"
        db.update_evaluation(capture_id, eval_result)
        db.log_event("INFO", f"Capture #{capture_id} rejected by VLM ({eval_result.get('recommended_action')}).")

    except Exception as e:
        db.log_event("ERROR", f"Pipeline error on capture #{capture_id}", str(e))

@app.get("/", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    """Render real-time AutoInsta web dashboard."""
    captures = db.list_captures(limit=100)
    pending_approvals = [c for c in captures if c.get("status") == "PENDING_APPROVAL"]
    stats = db.get_stats()
    alerts = db.list_emergency_alerts(limit=5)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "captures": captures,
        "pending_approvals": pending_approvals,
        "stats": stats,
        "settings": settings,
        "alerts": alerts
    })

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

    res = publisher.publish(capture_id, image_path, caption, hashtags)
    return res

@app.post("/api/captures/{capture_id}/reject")
async def reject_capture(capture_id: int):
    """Manually reject a capture."""
    cap = db.get_capture(capture_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Capture not found")

    db.update_status(capture_id, "REJECTED_MANUALLY")
    db.log_event("INFO", f"Capture #{capture_id} rejected manually by user.")
    return {"success": True, "message": f"Capture #{capture_id} rejected."}

class EditCaptionRequest(BaseModel):
    caption: str
    hashtags: Optional[List[str]] = None

@app.put("/api/captures/{capture_id}/caption")
async def edit_caption(capture_id: int, req: EditCaptionRequest):
    """Edit caption before manual approval."""
    cap = db.get_capture(capture_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Capture not found")

    db.update_caption(capture_id, req.caption, req.hashtags)
    return {"success": True, "message": "Caption updated."}

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
    return {"success": True, "sensors": await get_sensors_config()}

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
        "has_gemini_key": bool(settings.gemini_api_key),
        "has_ig_credentials": bool(settings.instagram_username and settings.instagram_password),
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

    return {"success": True, "message": "Identifiants et secrets enregistrés en sécurité dans le coffre local (.env)."}
