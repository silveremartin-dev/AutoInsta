import os
import yaml
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = BASE_DIR / config_path
        self.raw_data: Dict[str, Any] = {}
        self.load()

    def load(self):
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.raw_data = yaml.safe_load(f) or {}
        else:
            self.raw_data = {}

        # Server
        server_cfg = self.raw_data.get("server", {})
        self.server_host = os.getenv("SERVER_HOST", server_cfg.get("host", "0.0.0.0"))
        self.server_port = int(os.getenv("SERVER_PORT", server_cfg.get("port", 8000)))
        self.storage_dir = BASE_DIR / server_cfg.get("storage_dir", "data/captures")
        self.db_path = BASE_DIR / server_cfg.get("db_path", "data/autoinsta.db")
        self.client_api_key = os.getenv("CLIENT_API_KEY", server_cfg.get("client_api_key", "autoinsta_device_secret_token_123"))

        # Ensure directories exist
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Granular Sensors
        sensors_cfg = self.raw_data.get("sensors", {})
        self.enable_camera = bool(sensors_cfg.get("enable_camera", True))
        self.enable_gps = bool(sensors_cfg.get("enable_gps", True))
        self.enable_accelerometer = bool(sensors_cfg.get("enable_accelerometer", True))
        self.enable_light_sensor = bool(sensors_cfg.get("enable_light_sensor", True))
        self.enable_microphone = bool(sensors_cfg.get("enable_microphone", False))
        self.enable_barometer = bool(sensors_cfg.get("enable_barometer", False))
        self.enable_battery = bool(sensors_cfg.get("enable_battery", True))
        self.enable_pedometer = bool(sensors_cfg.get("enable_pedometer", False))
        self.enable_heart_rate = bool(sensors_cfg.get("enable_heart_rate", False))

        # Heart rate emergency alert & Dead Man's Switch
        hr_alert_cfg = sensors_cfg.get("heart_rate_alert", {})
        self.hr_alert_enabled = bool(hr_alert_cfg.get("enabled", False))
        self.hr_min_bpm = int(hr_alert_cfg.get("min_bpm", 45))
        self.hr_max_bpm = int(hr_alert_cfg.get("max_bpm", 145))
        self.hr_countdown_seconds = int(hr_alert_cfg.get("countdown_seconds", 10))
        self.hr_sound_alarm = bool(hr_alert_cfg.get("sound_alarm", True))
        self.hr_vibration_alarm = bool(hr_alert_cfg.get("vibration_alarm", True))
        self.hr_channels = hr_alert_cfg.get("channels", ["sms", "telegram", "webhook"])

        # SOS Secrets (From .env)
        self.emergency_phone = os.getenv("EMERGENCY_PHONE", "")
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.emergency_webhook_url = os.getenv("EMERGENCY_WEBHOOK_URL", hr_alert_cfg.get("webhook_url", ""))
        self.facebook_page_id = os.getenv("FACEBOOK_PAGE_ID", "")

        # Gemini / VLM
        vlm_cfg = self.raw_data.get("vlm", {})
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.vlm_model = vlm_cfg.get("model", "gemini-1.5-flash")
        self.temperature = float(vlm_cfg.get("temperature", 0.7))
        self.min_social_score = float(vlm_cfg.get("min_social_score", 7.0))
        self.strict_privacy = bool(vlm_cfg.get("strict_privacy", True))
        self.require_quality_pass = bool(vlm_cfg.get("require_quality_pass", True))
        self.persona = vlm_cfg.get("persona", "spontaneous_chic")
        self.language = vlm_cfg.get("language", "fr")
        self.persona_instructions = vlm_cfg.get("persona_instructions", "")

        # Publisher
        pub_cfg = self.raw_data.get("publisher", {})
        self.publish_mode = os.getenv("PUBLISH_MODE", pub_cfg.get("mode", "dry_run"))
        self.require_manual_confirmation = bool(pub_cfg.get("require_manual_confirmation", True))
        self.target_type = pub_cfg.get("target_type", "feed")
        self.min_interval_minutes = int(pub_cfg.get("min_interval_minutes", 60))
        self.max_daily_posts = int(pub_cfg.get("max_daily_posts", 4))

        # Credentials
        self.instagram_username = os.getenv("INSTAGRAM_USERNAME", "")
        self.instagram_password = os.getenv("INSTAGRAM_PASSWORD", "")
        self.meta_access_token = os.getenv("META_ACCESS_TOKEN", "")
        self.instagram_account_id = os.getenv("INSTAGRAM_ACCOUNT_ID", "")

# Global settings instance
settings = Config()
