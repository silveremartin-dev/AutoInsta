import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image
from server.config import settings

logger = logging.getLogger("autoinsta.evaluator")

EVALUATION_SYSTEM_PROMPT = """
You are AutoInsta's Strict Egocentric VLM Evaluator & Social Narrative Generator.
Your purpose is to inspect raw first-person point-of-view (POV) images captured passively from a smartphone, wearable, or PC camera, enforce absolute privacy standards, evaluate social interest, and compose authentic captions.

STRICT PRIVACY RULES (CRITICAL):
You MUST set "safety_pass": false and "recommended_action": "REJECT_PRIVATE" if ANY of the following is present:
1. Nudity, naked bodies, underwear, erotic/intimate exposure, or revealing intimate reflections in mirrors.
2. Intimate spaces: bathrooms, toilets, locker rooms, or disheveled private bedrooms.
3. Private or sensitive screens: open emails, WhatsApp/chat windows, computer code, banking/financial accounts, passwords, medical portals.
4. Personal identity items: credit cards, ID cards, driver's licenses, passports, postal mail showing addresses.
5. Vulnerable or non-consenting individuals in close-up distress.

QUALITY GATE:
Set "quality_pass": false if the frame is completely black (inside pocket/bag), heavily occluded by fabric/fingers, or motion-blurred beyond recognition.

SOCIAL INTEREST SCORE (0.0 to 10.0):
0.0 - 4.9: Boring, empty floor, mundane wall, repetitive desk screenshot.
5.0 - 6.9: Typical daily view, acceptable but unexciting.
7.0 - 8.4: Good aesthetic composition, pleasant light, appetizing food, lively streetscape, intriguing architecture.
8.5 - 10.0: Exceptional, striking POV photography, poetic timing, beautiful atmosphere.

Output valid JSON ONLY matching the following schema:
{
  "safety_pass": boolean,
  "quality_pass": boolean,
  "social_score": number, // float 0.0 - 10.0
  "scene_description": string, // 1-2 factual sentences describing the POV scene
  "caption": string, // Natural first-person POV Instagram caption in {language} matching requested persona
  "hashtags": [string], // 2-4 discreet hashtags without '#' symbol
  "recommended_action": "POST" | "REJECT_PRIVATE" | "REJECT_LOW_QUALITY" | "REJECT_BORING",
  "reasoning": string // Detailed rationale for safety and score
}
"""

PERSONA_GUIDES = {
    "spontaneous_chic": "Natural, casual, effortless aesthetic. Likes subtle vibes, lighting, quiet observations, coffee, city walking.",
    "witty_minimalist": "Short, clever, understated humor. Deadpan, dry observations with 1-2 words or short punchy phrases.",
    "candid_existential": "Slightly philosophical, reflective observations about time, routine, and modern life.",
    "poetic_flaneur": "Evocative, sensory descriptions of streets, atmosphere, colors, and transient beauty.",
    "tech_nomad": "Dynamic, focused on workspaces, tools, mobility, urban exploration, and productivity."
}

class VLMEvaluator:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model_name = settings.vlm_model
        self.active_sos_alerts = {} # alert_id -> {"timer": Thread/Timer, "cancelled": bool}
        self._init_client()

    def cancel_emergency_alert(self, alert_id: int) -> bool:
        """User aborted the emergency countdown (Dead Man's Switch interrupted)."""
        if alert_id in self.active_sos_alerts:
            self.active_sos_alerts[alert_id]["cancelled"] = True
            from server.database import db
            db.log_event("WARNING", f"Emergency SOS #{alert_id} CANCELLED by user within grace period.")
            logger.info(f"Emergency alert #{alert_id} successfully cancelled by user.")
            return True
        return False

    def _execute_sos_dispatch(self, alert_id: int, bpm: int, alert_type: str, location_str: str):
        """Dispatches actual SOS across SMS, Telegram, and Webhook if not cancelled."""
        if alert_id in self.active_sos_alerts and self.active_sos_alerts[alert_id].get("cancelled"):
            logger.info(f"SOS #{alert_id} dispatch suppressed (was cancelled).")
            return

        logger.critical(f"DEAD MAN'S SWITCH EXPIRED: Dispatching real SOS for {bpm} BPM!")
        dispatched_channels = []

        # 1. Telegram Dispatch
        if settings.telegram_bot_token and settings.telegram_chat_id:
            try:
                import requests
                tg_msg = (
                    f"🚨 [URGENCE VITAL AUTOINSTA]\n"
                    f"Alerte : {alert_type}\n"
                    f"Rythme cardiaque : {bpm} BPM\n"
                    f"Lieu : {location_str or 'Inconnu'}\n"
                    f"Compte à rebours de 10s expiré sans annulation."
                )
                tg_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
                r = requests.post(tg_url, json={"chat_id": settings.telegram_chat_id, "text": tg_msg}, timeout=5)
                if r.status_code == 200:
                    dispatched_channels.append("Telegram")
            except Exception as e:
                logger.error(f"Failed to send Telegram SOS: {e}")

        # 2. Emergency Webhook
        if settings.emergency_webhook_url:
            try:
                import requests
                requests.post(
                    settings.emergency_webhook_url,
                    json={
                        "alert": alert_type,
                        "bpm": bpm,
                        "location": location_str,
                        "timestamp": time.time(),
                        "status": "SOS_DISPATCHED"
                    },
                    timeout=5
                )
                dispatched_channels.append("Webhook")
            except Exception as e:
                logger.error(f"Failed to post emergency webhook: {e}")

        # 3. Termux SMS on Android (if running locally or invoked)
        if settings.emergency_phone:
            try:
                import subprocess
                sms_text = f"[URGENCE AUTOINSTA] Rythme cardiaque {bpm} BPM critique. Lieu: {location_str}"
                subprocess.run(["termux-sms-send", "-n", settings.emergency_phone, sms_text], timeout=5)
                dispatched_channels.append("SMS")
            except Exception:
                pass

        status_str = f"DISPATCHED via {', '.join(dispatched_channels) if dispatched_channels else 'None'}"
        from server.database import db
        db.record_emergency_alert(bpm, alert_type, location_str, status_str, f"Dispatched: {status_str}")

    def check_emergency_heart_rate(self, bpm: Optional[int], location_str: str = "") -> Optional[int]:
        """Initiate Dead Man's Switch countdown if heart rate is outside safe bounds."""
        if not settings.hr_alert_enabled or bpm is None or bpm <= 0:
            return None

        alert_type = None
        if bpm < settings.hr_min_bpm:
            alert_type = f"BRADYCARDIA_ALERT (Rythme lent: {bpm} BPM < {settings.hr_min_bpm})"
        elif bpm > settings.hr_max_bpm:
            alert_type = f"TACHYCARDIA_ALERT (Rythme rapide: {bpm} BPM > {settings.hr_max_bpm})"

        if alert_type:
            logger.warning(f"EMERGENCY HEALTH DETECTED: {alert_type}. Starting {settings.hr_countdown_seconds}s Dead Man countdown.")
            from server.database import db
            alert_id = db.record_emergency_alert(bpm, alert_type, location_str, "COUNTDOWN_ACTIVE", f"Grace period: {settings.hr_countdown_seconds}s")

            # Schedule execution after grace countdown
            import threading
            self.active_sos_alerts[alert_id] = {"cancelled": False}
            timer = threading.Timer(
                float(settings.hr_countdown_seconds),
                self._execute_sos_dispatch,
                args=[alert_id, bpm, alert_type, location_str]
            )
            timer.daemon = True
            timer.start()
            return alert_id
        return None

    def evaluate_image(self, image_path: Path, sensor_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not image_path.exists():
            return {
                "status": "REJECTED",
                "safety_pass": False,
                "quality_pass": False,
                "social_score": 0.0,
                "scene_description": "File not found",
                "caption": "",
                "hashtags": [],
                "recommended_action": "REJECT_LOW_QUALITY",
                "reasoning": f"Image file not found at {image_path}"
            }

        sensor_metadata = sensor_metadata or {}
        
        # Check emergency heart rate (Dead Man's Switch)
        bpm = sensor_metadata.get("heart_rate_bpm")
        loc_display = sensor_metadata.get("city") or sensor_metadata.get("location_name") or ""
        if bpm:
            self.check_emergency_heart_rate(int(bpm), loc_display)

        # Build rich sensor context for Gemini
        context_lines = []
        if settings.enable_gps:
            if sensor_metadata.get("city"):
                context_lines.append(f"- Location: {sensor_metadata.get('city')} ({sensor_metadata.get('country', '')})")
            elif sensor_metadata.get("latitude") and sensor_metadata.get("longitude"):
                context_lines.append(f"- Coordinates: {sensor_metadata.get('latitude')}, {sensor_metadata.get('longitude')}")
            if sensor_metadata.get("speed_kmh") is not None:
                context_lines.append(f"- Moving Speed: {sensor_metadata.get('speed_kmh')} km/h")

        if settings.enable_heart_rate and bpm:
            context_lines.append(f"- Current Heart Rate: {bpm} BPM")

        if settings.enable_accelerometer and sensor_metadata.get("activity_state"):
            context_lines.append(f"- Movement State: {sensor_metadata.get('activity_state')}")

        if settings.enable_microphone and sensor_metadata.get("ambient_noise_db") is not None:
            context_lines.append(f"- Sound Environment: {sensor_metadata.get('ambient_noise_db')} dB ({sensor_metadata.get('audio_tag', 'Ambiance sonore')})")

        if settings.enable_barometer and sensor_metadata.get("altitude_meters") is not None:
            context_lines.append(f"- Altitude / Elevation: {sensor_metadata.get('altitude_meters')}m")

        if settings.enable_pedometer and sensor_metadata.get("steps_today") is not None:
            context_lines.append(f"- Steps Walked Today: {sensor_metadata.get('steps_today')} steps")

        if settings.enable_battery and sensor_metadata.get("battery_pct") is not None:
            context_lines.append(f"- Device Battery: {sensor_metadata.get('battery_pct')}%")

        sensor_context = "\n".join(context_lines) if context_lines else "None provided."

        persona_style = PERSONA_GUIDES.get(settings.persona, PERSONA_GUIDES["spontaneous_chic"])
        system_instruction = EVALUATION_SYSTEM_PROMPT.format(language=settings.language)
        
        prompt_text = f"""
Analyze this POV image taken from the user's perspective.
Target Language: {settings.language}
Persona Profile: {settings.persona} ({persona_style})
Additional persona guidance: {settings.persona_instructions}
Min Score Threshold for posting candidate: {settings.min_social_score}

Real-time Sensor Context:
{sensor_context}

Important:
- If sensitive screens, private docs, bathrooms, or nudity are detected, you MUST set safety_pass=false and recommended_action="REJECT_PRIVATE".
- If safe and aesthetic, subtly integrate the location or motion context into the caption if it elevates the authenticity.
- Output valid JSON strictly following the schema.
"""

        if not self.api_key:
            return self._mock_evaluation(image_path, sensor_metadata)

        try:
            pil_image = Image.open(image_path)
            
            # Use google-genai SDK
            if hasattr(self, "sdk_type") and self.sdk_type == "google-genai" and self.client:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[pil_image, system_instruction + "\n\n" + prompt_text],
                    config={
                        "response_mime_type": "application/json",
                        "temperature": settings.temperature,
                    }
                )
                raw_text = response.text
            elif hasattr(self, "sdk_type") and self.sdk_type == "google-generativeai":
                response = self.legacy_model.generate_content(
                    [system_instruction + "\n\n" + prompt_text, pil_image],
                    generation_config={"temperature": settings.temperature}
                )
                raw_text = response.text
            else:
                return self._mock_evaluation(image_path)

            # Clean JSON markdown fences if any
            clean_text = raw_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()

            parsed = json.loads(clean_text)
            
            # Determine status
            action = parsed.get("recommended_action", "REJECT_BORING")
            status = "ACCEPTED" if action == "POST" else "REJECTED"
            parsed["status"] = status
            
            return parsed

        except Exception as e:
            logger.error(f"VLM evaluation failed: {e}", exc_info=True)
            return {
                "status": "EVALUATION_ERROR",
                "safety_pass": False,
                "quality_pass": False,
                "social_score": 0.0,
                "scene_description": "Evaluation error occurred",
                "caption": "",
                "hashtags": [],
                "recommended_action": "REJECT_LOW_QUALITY",
                "reasoning": f"Error during Gemini inference: {str(e)}"
            }

    def _mock_evaluation(self, image_path: Path, sensor_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Offline simulation when GEMINI_API_KEY is omitted."""
        logger.info(f"Running mock evaluation for {image_path.name}")
        sensor_metadata = sensor_metadata or {}
        
        # Check basic image size and brightness
        try:
            with Image.open(image_path) as img:
                img_gray = img.convert('L')
                stat = img_gray.getextrema()
                is_dark = stat[1] < 20
        except Exception:
            is_dark = False

        if is_dark:
            return {
                "status": "REJECTED",
                "safety_pass": True,
                "quality_pass": False,
                "social_score": 1.0,
                "scene_description": "Cadre obscur ou obstrué (probablement dans une poche).",
                "caption": "",
                "hashtags": [],
                "recommended_action": "REJECT_LOW_QUALITY",
                "reasoning": "L'image est trop sombre ou bloquée."
            }

        city = sensor_metadata.get("city") or "la ville"
        bpm_mention = f" ({sensor_metadata.get('heart_rate_bpm')} bpm)" if sensor_metadata.get('heart_rate_bpm') else ""

        return {
            "status": "ACCEPTED",
            "safety_pass": True,
            "quality_pass": True,
            "social_score": 8.4,
            "scene_description": f"Perspective POV en déplacement dans {city}.",
            "caption": f"Flânerie impromptue dans les rues de {city}. Lumière d'automne et tempo paisible{bpm_mention}. ✨",
            "hashtags": ["pov", "dailylife", "streetphotography", "cityvibes"],
            "recommended_action": "POST",
            "reasoning": "Simulation : Composition équilibrée, absence de données sensibles, conformité vie privée totale."
        }

evaluator = VLMEvaluator()
