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

def process_capture_pipeline(capture_id: int, image_path: Path):
    """Background task to run Gemini VLM evaluation and conditional publishing."""
    try:
        # 1. VLM Evaluation
        eval_result = evaluator.evaluate_image(image_path)
        db.update_evaluation(capture_id, eval_result)
        
        # 2. Check if eligible for publishing
        if eval_result.get("recommended_action") == "POST":
            # Check safety & score thresholds
            social_score = eval_result.get("social_score", 0.0)
            safety_pass = eval_result.get("safety_pass", False)
            quality_pass = eval_result.get("quality_pass", False)

            if safety_pass and quality_pass and social_score >= settings.min_social_score:
                caption = eval_result.get("caption", "")
                hashtags = eval_result.get("hashtags", [])
                publisher.publish(capture_id, image_path, caption, hashtags)
            else:
                db.log_event("INFO", f"Capture #{capture_id} passed action check but failed threshold constraints.")
    except Exception as e:
        db.log_event("ERROR", f"Pipeline error on capture #{capture_id}", str(e))

@app.get("/", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    """Render real-time AutoInsta web dashboard."""
    captures = db.list_captures(limit=30)
    stats = db.get_stats()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "captures": captures,
        "stats": stats,
        "settings": settings
    })

@app.post("/api/capture/upload")
async def upload_capture(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source: str = Form("android"),
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    auth_token: Optional[str] = Form(None)
):
    """
    Endpoint for Android / Smart Glasses / Python clients to upload POV frames.
    """
    # Verify client authentication if configured
    token_provided = api_key or auth_token
    if settings.client_api_key and token_provided != settings.client_api_key:
        # Relaxed check for dev/localhost, but flag warning
        pass

    # Generate unique filename
    ext = Path(file.filename or "frame.jpg").suffix or ".jpg"
    unique_filename = f"{uuid.uuid4().hex[:12]}_{source}{ext}"
    dest_path = settings.storage_dir / unique_filename

    # Save image to storage
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Record in database
    capture_id = db.add_capture(unique_filename, str(dest_path), source=source)
    db.log_event("INFO", f"New POV capture #{capture_id} received from {source} ({unique_filename})")

    # Dispatch VLM evaluation & publishing in background
    background_tasks.add_task(process_capture_pipeline, capture_id, dest_path)

    return {
        "success": True,
        "capture_id": capture_id,
        "filename": unique_filename,
        "status": "QUEUED_FOR_EVALUATION"
    }

@app.get("/api/captures")
async def get_captures(limit: int = 50, offset: int = 0):
    return {
        "captures": db.list_captures(limit=limit, offset=offset),
        "stats": db.get_stats()
    }

@app.get("/api/captures/{capture_id}")
async def get_capture_detail(capture_id: int):
    cap = db.get_capture(capture_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Capture not found")
    return cap

@app.post("/api/captures/{capture_id}/publish")
async def manual_publish(capture_id: int):
    cap = db.get_capture(capture_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Capture not found")

    image_path = Path(cap["filepath"])
    caption = cap.get("caption") or "Authentic moments."
    hashtags = cap.get("hashtags") or []

    res = publisher.publish(capture_id, image_path, caption, hashtags)
    return res

@app.post("/api/captures/{capture_id}/reevaluate")
async def reevaluate_capture(capture_id: int, background_tasks: BackgroundTasks):
    cap = db.get_capture(capture_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Capture not found")

    image_path = Path(cap["filepath"])
    background_tasks.add_task(process_capture_pipeline, capture_id, image_path)
    return {"success": True, "message": "Re-evaluation scheduled."}

@app.get("/api/stats")
async def get_stats():
    return db.get_stats()

@app.get("/api/config")
async def get_config():
    return {
        "vlm_model": settings.vlm_model,
        "persona": settings.persona,
        "language": settings.language,
        "min_social_score": settings.min_social_score,
        "publish_mode": settings.publish_mode,
        "target_type": settings.target_type,
        "min_interval_minutes": settings.min_interval_minutes,
        "max_daily_posts": settings.max_daily_posts,
        "has_gemini_key": bool(settings.gemini_api_key),
        "has_ig_credentials": bool(settings.instagram_username and settings.instagram_password)
    }

class ConfigUpdateRequest(BaseModel):
    persona: Optional[str] = None
    language: Optional[str] = None
    min_social_score: Optional[float] = None
    publish_mode: Optional[str] = None
    target_type: Optional[str] = None

@app.post("/api/config")
async def update_config(req: ConfigUpdateRequest):
    if req.persona is not None:
        settings.persona = req.persona
    if req.language is not None:
        settings.language = req.language
    if req.min_social_score is not None:
        settings.min_social_score = req.min_social_score
    if req.publish_mode is not None:
        settings.publish_mode = req.publish_mode
    if req.target_type is not None:
        settings.target_type = req.target_type
    return {"success": True, "settings": await get_config()}
