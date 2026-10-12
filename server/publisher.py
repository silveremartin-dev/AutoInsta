import os
import time
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta
from server.config import settings
from server.database import db

logger = logging.getLogger("autoinsta.publisher")

class InstagramPublisher:
    def __init__(self):
        self.mode = settings.publish_mode
        self.ig_client = None
        self.session_file = settings.storage_dir.parent / "ig_session.json"

    def can_publish_now(self) -> Tuple[bool, str]:
        stats = db.get_stats()
        if stats["published_last_24h"] >= settings.max_daily_posts:
            return False, f"Daily post limit reached ({stats['published_last_24h']}/{settings.max_daily_posts})."

        # Check last published timestamp
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT published_at FROM captures 
                WHERE status = 'PUBLISHED' 
                ORDER BY published_at DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if row and row[0]:
                try:
                    last_time = datetime.fromisoformat(row[0])
                    cooldown = timedelta(minutes=settings.min_interval_minutes)
                    if datetime.utcnow() - last_time < cooldown:
                        remaining = int((cooldown - (datetime.utcnow() - last_time)).total_seconds() / 60)
                        return False, f"Cooldown active. Next post allowed in {remaining} minutes."
                except Exception:
                    pass

        return True, "Ready to publish."

    def _init_instagrapi(self):
        if self.ig_client is not None:
            return True
        try:
            from instagrapi import Client
            cl = Client()
            cl.delay_range = [2, 5]
            
            if self.session_file.exists():
                try:
                    cl.load_settings(self.session_file)
                    cl.login(settings.instagram_username, settings.instagram_password)
                    self.ig_client = cl
                    logger.info("Logged in to Instagram using saved session.")
                    return True
                except Exception as e:
                    logger.warning(f"Could not reuse session, performing fresh login: {e}")

            if not settings.instagram_username or not settings.instagram_password:
                logger.error("Instagram username/password not configured for instagrapi.")
                return False

            cl.login(settings.instagram_username, settings.instagram_password)
            cl.dump_settings(self.session_file)
            self.ig_client = cl
            logger.info("Logged in to Instagram and saved new session.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize instagrapi client: {e}")
            return False

    def publish(self, capture_id: int, image_path: Path, caption: str, hashtags: list) -> Dict[str, Any]:
        can_post, reason = self.can_publish_now()
        if not can_post:
            logger.warning(f"Publish prevented for capture #{capture_id}: {reason}")
            return {"success": False, "reason": reason}

        full_caption = caption.strip()
        if hashtags:
            formatted_tags = " ".join([f"#{t.lstrip('#')}" for t in hashtags])
            full_caption += f"\n\n.\n.\n{formatted_tags}"

        if self.mode in ["google_photos", "folder_sync"]:
            return self._publish_google_photos(capture_id, image_path, full_caption)
        elif self.mode in ["local_only", "private_vault"]:
            return self._publish_local_only(capture_id, full_caption)
        elif self.mode == "dry_run":
            return self._publish_dry_run(capture_id, full_caption)
        elif self.mode == "instagrapi":
            if not settings.instagram_username or not settings.instagram_password:
                logger.info(f"No Instagram account configured. Defaulting capture #{capture_id} to local private archive.")
                return self._publish_local_only(capture_id, full_caption)
            return self._publish_instagrapi(capture_id, image_path, full_caption)
        elif self.mode == "meta_graph":
            return self._publish_meta_graph(capture_id, image_path, full_caption)
        else:
            return self._publish_local_only(capture_id, full_caption)

    def _publish_google_photos(self, capture_id: int, image_path: Path, full_caption: str) -> Dict[str, Any]:
        """Copies photo into a user-specified synced folder (Google Photos / Drive / Nextcloud)."""
        import shutil
        target_dir = settings.export_directory
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_filename = f"POV_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image_path.name}"
        dest_path = target_dir / dest_filename
        shutil.copy2(image_path, dest_path)

        # Write sidecar description
        sidecar = target_dir / f"{dest_filename}.txt"
        sidecar.write_text(full_caption, encoding="utf-8")

        post_id = f"gphotos_{dest_filename}"
        logger.info(f"[SYNCHRO PRIVÉE] Cliché #{capture_id} exporté vers le dossier synchronisé : {dest_path}")
        db.mark_published(capture_id, post_id, "google_photos")
        db.log_event("INFO", f"Cliché exporté vers le dossier privé synchronisé ({dest_filename})")
        return {
            "success": True,
            "mode": "google_photos",
            "post_id": post_id,
            "exported_to": str(dest_path),
            "caption": full_caption
        }

    def _publish_local_only(self, capture_id: int, full_caption: str) -> Dict[str, Any]:
        local_post_id = f"local_vault_{int(time.time())}"
        logger.info(f"[COFFRE-FORT LOCAL] Cliché #{capture_id} archivé en local sans diffusion externe.")
        db.mark_published(capture_id, local_post_id, "local_only")
        db.log_event("INFO", f"Cliché #{capture_id} conservé dans le coffre privé local (mode 100% hors-ligne/local).")
        return {
            "success": True,
            "mode": "local_only",
            "post_id": local_post_id,
            "caption": full_caption
        }

    def _publish_dry_run(self, capture_id: int, full_caption: str) -> Dict[str, Any]:
        simulated_post_id = f"sim_{int(time.time())}"
        logger.info(f"[DRY RUN] Published capture #{capture_id} to Instagram.")
        logger.info(f"[DRY RUN] Caption:\n{full_caption}")
        db.mark_published(capture_id, simulated_post_id, "dry_run")
        db.log_event("INFO", f"Simulated post {simulated_post_id} created for capture #{capture_id}")
        return {
            "success": True,
            "mode": "dry_run",
            "post_id": simulated_post_id,
            "caption": full_caption
        }

    def _publish_instagrapi(self, capture_id: int, image_path: Path, full_caption: str) -> Dict[str, Any]:
        if not self._init_instagrapi():
            err = "Instagrapi login failed. Check credentials or challenge."
            db.mark_publish_failed(capture_id, err)
            return {"success": False, "error": err}

        try:
            if settings.target_type == "story":
                media = self.ig_client.photo_upload_to_story(str(image_path))
            else:
                media = self.ig_client.photo_upload(str(image_path), caption=full_caption)

            post_id = str(media.pk) if hasattr(media, "pk") else f"ig_{int(time.time())}"
            db.mark_published(capture_id, post_id, "instagrapi")
            db.log_event("INFO", f"Published post {post_id} to Instagram via instagrapi")
            return {"success": True, "mode": "instagrapi", "post_id": post_id}
        except Exception as e:
            err = f"Instagrapi upload error: {str(e)}"
            logger.error(err, exc_info=True)
            db.mark_publish_failed(capture_id, err)
            return {"success": False, "error": err}

    def _publish_meta_graph(self, capture_id: int, image_path: Path, full_caption: str) -> Dict[str, Any]:
        # Official Meta Graph API flow requires a publicly accessible image URL
        # e.g., POST https://graph.facebook.com/v19.0/{ig_user_id}/media
        token = settings.meta_access_token
        acc_id = settings.instagram_account_id

        if not token or not acc_id:
            err = "META_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID required for meta_graph mode."
            db.mark_publish_failed(capture_id, err)
            return {"success": False, "error": err}

        # Note: Meta Graph API requires an image_url accessible on the internet
        err = "Meta Graph API requires a public image URL. Configure tunnel (e.g. ngrok/Cloudflare) or use instagrapi."
        logger.warning(err)
        db.mark_publish_failed(capture_id, err)
        return {"success": False, "error": err}

publisher = InstagramPublisher()
