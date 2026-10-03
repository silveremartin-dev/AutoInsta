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

        # Gemini / VLM
        vlm_cfg = self.raw_data.get("vlm", {})
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.vlm_model = vlm_cfg.get("model", "gemini-1.5-flash")
        self.temperature = float(vlm_cfg.get("temperature", 0.7))
        self.min_social_score = float(vlm_cfg.get("min_social_score", 7.0))
        self.require_safety_pass = bool(vlm_cfg.get("require_safety_pass", True))
        self.require_quality_pass = bool(vlm_cfg.get("require_quality_pass", True))
        self.persona = vlm_cfg.get("persona", "spontaneous_chic")
        self.language = vlm_cfg.get("language", "en")
        self.persona_instructions = vlm_cfg.get("persona_instructions", "")

        # Publisher
        pub_cfg = self.raw_data.get("publisher", {})
        self.publish_mode = os.getenv("PUBLISH_MODE", pub_cfg.get("mode", "dry_run"))
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
