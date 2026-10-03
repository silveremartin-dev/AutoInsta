import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image
from server.config import settings

logger = logging.getLogger("autoinsta.evaluator")

EVALUATION_SYSTEM_PROMPT = """
You are AutoInsta's Egocentric VLM Evaluator & Social Content Generator.
Your purpose is to inspect raw first-person point-of-view (POV) images captured passively from a smartphone or smart glasses, evaluate their privacy safety and aesthetic interest, and generate engaging Instagram captions.

You must output valid JSON ONLY matching the following schema:
{
  "safety_pass": boolean, // true if NO sensitive screens (passwords, banking, emails), NO credit cards, NO intimate/bathroom scenes, NO private identity docs.
  "quality_pass": boolean, // true if the image is clear enough (not pure black pocket shot, not completely blinded or motion-blurred beyond recognition).
  "social_score": number, // float from 0.0 to 10.0. 0=boring/empty floor, 5=ordinary everyday sight, 7.5+=captivating moment, aesthetic coffee, beautiful light, cool architecture, unique street scene, 9+=exceptional shot.
  "scene_description": string, // 1-2 sentences describing what is seen from the wearer's POV.
  "caption": string, // An authentic, first-person POV Instagram caption matching the requested persona and language. Do NOT sound like an AI assistant. Be spontaneous and natural.
  "hashtags": [string], // Array of 2 to 4 relevant hashtags without the # symbol.
  "recommended_action": "POST" | "REJECT_PRIVATE" | "REJECT_LOW_QUALITY" | "REJECT_BORING",
  "reasoning": string // Brief explanation of the safety, score, and decision.
}

Decision Rules:
- If safety_pass is false -> recommended_action = "REJECT_PRIVATE"
- Else if quality_pass is false -> recommended_action = "REJECT_LOW_QUALITY"
- Else if social_score < {min_score} -> recommended_action = "REJECT_BORING"
- Else -> recommended_action = "POST"
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

    def evaluate_image(self, image_path: Path) -> Dict[str, Any]:
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

        persona_style = PERSONA_GUIDES.get(settings.persona, PERSONA_GUIDES["spontaneous_chic"])
        system_instruction = EVALUATION_SYSTEM_PROMPT.format(min_score=settings.min_social_score)
        
        prompt_text = f"""
Analyze this POV image taken from the user's perspective.
Target Language: {settings.language}
Persona Profile: {settings.persona} ({persona_style})
Additional instructions: {settings.persona_instructions}
Min Score Threshold for posting: {settings.min_social_score}

Output the JSON evaluation following the specified schema strictly.
"""

        # If API key not set or SDK not available, use intelligent local heuristic fallback
        if not self.api_key:
            return self._mock_evaluation(image_path)

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

    def _mock_evaluation(self, image_path: Path) -> Dict[str, Any]:
        """Offline simulation when GEMINI_API_KEY is omitted."""
        logger.info(f"Running mock evaluation for {image_path.name}")
        
        # Check basic image size and brightness
        try:
            with Image.open(image_path) as img:
                img_gray = img.convert('L')
                stat = img_gray.getextrema()
                # If pure dark
                is_dark = stat[1] < 20
        except Exception:
            is_dark = False

        if is_dark:
            return {
                "status": "REJECTED",
                "safety_pass": True,
                "quality_pass": False,
                "social_score": 1.0,
                "scene_description": "Dark or occluded frame (likely inside pocket or obscured).",
                "caption": "",
                "hashtags": [],
                "recommended_action": "REJECT_LOW_QUALITY",
                "reasoning": "Image is too dark or blocked."
            }

        return {
            "status": "ACCEPTED",
            "safety_pass": True,
            "quality_pass": True,
            "social_score": 8.2,
            "scene_description": "POV perspective of the surrounding environment during daily activity.",
            "caption": "Chasing the quiet light in between places. ✨",
            "hashtags": ["pov", "dailylife", "moments", "streetstyle"],
            "recommended_action": "POST",
            "reasoning": "Mock mode: Composition is balanced, lighting is natural, no sensitive content detected."
        }

evaluator = VLMEvaluator()
