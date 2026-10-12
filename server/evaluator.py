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
        self._init_client()

    def _init_client(self):
        self.client = None
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. VLM will run in mock/simulation mode.")
            return

        try:
            # Try new google-genai SDK first
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            self.sdk_type = "google-genai"
            logger.info("Initialized Google GenAI client.")
        except Exception as e:
            try:
                # Fallback to google-generativeai
                import google.generativeai as gai
                gai.configure(api_key=self.api_key)
                self.legacy_model = gai.GenerativeModel(self.model_name)
                self.sdk_type = "google-generativeai"
                logger.info("Initialized legacy google.generativeai client.")
            except Exception as e2:
                logger.error(f"Failed to initialize Gemini SDK: {e2}")
                self.client = None

    def check_emergency_heart_rate(self, bpm: Optional[int], location_str: str = ""):
        """Trigger emergency alert if heart rate exceeds safe thresholds."""
        if not settings.hr_alert_enabled or bpm is None or bpm <= 0:
            return

        alert_type = None
        if bpm < settings.hr_min_bpm:
            alert_type = f"BRADYCARDIA_ALERT (Low: {bpm} BPM < {settings.hr_min_bpm})"
        elif bpm > settings.hr_max_bpm:
            alert_type = f"TACHYCARDIA_ALERT (High: {bpm} BPM > {settings.hr_max_bpm})"

        if alert_type:
            logger.warning(f"EMERGENCY HEALTH TRIGGERED: {alert_type} at {location_str}")
            # Dispatch alert
            details = f"Detected {bpm} BPM. Location: {location_str or 'Unknown'}"
            status = "SENT"
            
            # Send to webhook if configured
            if settings.hr_webhook_url:
                try:
                    import requests
                    requests.post(
                        settings.hr_webhook_url,
                        json={"alert": alert_type, "bpm": bpm, "location": location_str, "timestamp": time.time()},
                        timeout=5
                    )
                except Exception as e:
                    logger.error(f"Failed to post emergency webhook: {e}")
                    status = f"FAILED: {e}"

            from server.database import db
            db.record_emergency_alert(bpm, alert_type, location_str, status, details)

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
        
        # Check emergency heart rate if enabled
        bpm = sensor_metadata.get("heart_rate_bpm")
        loc_display = sensor_metadata.get("city") or sensor_metadata.get("location_name") or ""
        if bpm:
            self.check_emergency_heart_rate(int(bpm), loc_display)

        # Build sensor context string for Gemini prompt
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
            context_lines.append(f"- Activity State: {sensor_metadata.get('activity_state')}")

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
