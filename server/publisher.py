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
                    now_dt = datetime.now()
                    if now_dt - last_time < cooldown:
                        remaining = int((cooldown - (now_dt - last_time)).total_seconds() / 60)
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

    def publish(self, capture_id: int, image_path: Path, caption: str, hashtags: list, ignore_cooldown: bool = False) -> Dict[str, Any]:
        # Cooldown & daily rate limits strictly protect Instagram accounts from platform bans
        if not ignore_cooldown and self.mode in ["instagrapi", "meta_graph"]:
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
            return self._publish_local_only(capture_id, image_path, full_caption)
        elif self.mode == "dry_run":
            return self._publish_dry_run(capture_id, full_caption)
        elif self.mode == "instagrapi":
            if not settings.instagram_username or not settings.instagram_password:
                logger.info(f"No Instagram account configured. Defaulting capture #{capture_id} to local private archive.")
                return self._publish_local_only(capture_id, image_path, full_caption)
            return self._publish_instagrapi(capture_id, image_path, full_caption)
        elif self.mode == "meta_graph":
            return self._publish_meta_graph(capture_id, image_path, full_caption)
        else:
            return self._publish_local_only(capture_id, image_path, full_caption)

    def _build_sidecar_text(self, capture_id: int, full_caption: str) -> str:
        """Builds a rich, formatted metadata text sidecar containing date, sensors, caption and tags."""
        cap = db.get_capture(capture_id) or {}
        sensors = cap.get("sensor_metadata") or {}
        timestamp = cap.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"📅 Date & Heure : {timestamp}",
            f"📸 Cliché AutoInsta #{capture_id}"
        ]

        # Detailed Sensor metrics
        sensor_details = []
        if sensors.get("latitude") and sensors.get("longitude"):
            sensor_details.append(f"GPS : {sensors.get('latitude')}, {sensors.get('longitude')}")
        if sensors.get("city"):
            sensor_details.append(f"Ville : {sensors.get('city')}")
        if sensors.get("battery_pct") is not None:
            sensor_details.append(f"Batterie : {sensors.get('battery_pct')}%")
        if sensors.get("mic_db") or sensors.get("ambient_noise"):
            sensor_details.append(f"Micro Ambiance : {sensors.get('mic_db') or sensors.get('ambient_noise')} dB")
        if sensors.get("heart_rate_bpm"):
            sensor_details.append(f"Pouls : {sensors.get('heart_rate_bpm')} BPM")
        if sensors.get("steps") or sensors.get("step_cadence"):
            sensor_details.append(f"Pas : {sensors.get('steps') or sensors.get('step_cadence')}")

        if sensor_details:
            lines.append("📡 Capteurs : " + " | ".join(sensor_details))
        else:
            lines.append("📡 Capteurs : Aucun capteur actif")

        # Caption and Tags
        lines.append("")
        lines.append("📝 Légende :")
        clean_text = cap.get("caption") or full_caption or "Aucune légende saisie."
        lines.append(clean_text)

        # Tags
        tags = cap.get("hashtags") or []
        if tags:
            lines.append("")
            lines.append("🏷️ Tags : " + ", ".join([f"#{t.lstrip('#')}" for t in tags]))

        return "\n".join(lines) + "\n"

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
        sidecar.write_text(self._build_sidecar_text(capture_id, full_caption), encoding="utf-8")

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

    def _publish_local_only(self, capture_id: int, image_path: Path, full_caption: str) -> Dict[str, Any]:
        """Archives photo and caption locally into settings.export_directory (data/my_private_photos)."""
        local_post_id = f"local_vault_{int(time.time())}"
        target_dir = settings.export_directory
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_filename = f"POV_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image_path.name}"
        dest_path = target_dir / dest_filename
        try:
            import shutil
            shutil.copy2(image_path, dest_path)
            sidecar = target_dir / f"{dest_filename}.txt"
            sidecar.write_text(self._build_sidecar_text(capture_id, full_caption), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to copy to export_directory: {e}")

        logger.info(f"[COFFRE-FORT LOCAL] Cliché #{capture_id} exporté dans {dest_path}")
        db.mark_published(capture_id, local_post_id, "local_only")
        db.log_event("INFO", f"Cliché #{capture_id} conservé dans le coffre privé local ({dest_filename}).")
        return {
            "success": True,
            "mode": "local_only",
            "post_id": local_post_id,
            "exported_to": str(dest_path),
            "message": f"Archivé dans votre Coffre Privé Local ({dest_filename}).",
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
            "message": "Simulation réussie (aucun envoi réel externe).",
            "caption": full_caption
        }

    def _publish_instagrapi(self, capture_id: int, image_path: Path, full_caption: str) -> Dict[str, Any]:
        if not self._init_instagrapi():
            err = "Connexion Instagram échouée. Vérifiez vos identifiants ou le challenge de sécurité."
            db.mark_publish_failed(capture_id, err)
            return {"success": False, "error": err, "message": err}

        try:
            if settings.target_type == "story":
                media = self.ig_client.photo_upload_to_story(str(image_path))
            else:
                media = self.ig_client.photo_upload(str(image_path), caption=full_caption)

            post_id = str(media.pk) if hasattr(media, "pk") else f"ig_{int(time.time())}"
            db.mark_published(capture_id, post_id, "instagrapi")
            db.log_event("INFO", f"Published post {post_id} to Instagram via instagrapi")
            return {
                "success": True,
                "mode": "instagrapi",
                "post_id": post_id,
                "message": f"Publié avec succès sur votre compte Instagram (@{settings.instagram_username}) !"
            }
        except Exception as e:
            err = f"Erreur de publication Instagram: {str(e)}"
            logger.error(err, exc_info=True)
            db.mark_publish_failed(capture_id, err)
            return {"success": False, "error": err, "message": err}

    def _publish_meta_graph(self, capture_id: int, image_path: Path, full_caption: str) -> Dict[str, Any]:
        token = settings.meta_access_token
        fb_page_id = settings.facebook_page_id
        ig_acc_id = settings.instagram_account_id

        if not token:
            err = "Clé META_ACCESS_TOKEN requise pour le mode Meta Graph API (Facebook / Instagram Pro)."
            db.mark_publish_failed(capture_id, err)
            return {"success": False, "error": err, "message": err}

        # 1. Publication directe sur Page Facebook (Upload direct du fichier binaire sans tunnel !)
        if fb_page_id:
            try:
                url = f"https://graph.facebook.com/v19.0/{fb_page_id}/photos"
                with open(image_path, "rb") as f:
                    files = {"source": f}
                    data = {
                        "caption": full_caption,
                        "access_token": token,
                        "published": "true"
                    }
                    resp = requests.post(url, files=files, data=data, timeout=30)

                res_data = resp.json()
                if resp.status_code == 200 and ("id" in res_data or "post_id" in res_data):
                    post_id = str(res_data.get("id") or res_data.get("post_id"))
                    db.mark_published(capture_id, post_id, "meta_graph")
                    db.log_event("INFO", f"Published post {post_id} to Facebook Page via Meta Graph API")
                    return {
                        "success": True,
                        "mode": "meta_graph",
                        "post_id": post_id,
                        "message": f"Cliché publié avec succès sur votre Page Facebook (#{post_id}) !"
                    }
                else:
                    err = res_data.get("error", {}).get("message") or f"Erreur Facebook Graph API HTTP {resp.status_code}"
                    logger.error(f"Facebook Graph API failed: {err}")
                    db.mark_publish_failed(capture_id, err)
                    return {"success": False, "error": err, "message": err}
            except Exception as e:
                err = f"Erreur lors de l'appel Facebook Graph API: {str(e)}"
                logger.error(err, exc_info=True)
                db.mark_publish_failed(capture_id, err)
                return {"success": False, "error": err, "message": err}

        # 2. Instagram Pro via Graph API (Nécessite un tunnel ou image URL publique)
        if ig_acc_id:
            err = "Instagram Graph API requiert une URL d'image publique (tunnel ngrok/Cloudflare). Pour Instagram direct, utilisez le mode 'Instagram Mobile (Instagrapi)'."
            logger.warning(err)
            db.mark_publish_failed(capture_id, err)
            return {"success": False, "error": err, "message": err}

        err = "Veuillez renseigner FACEBOOK_PAGE_ID ou INSTAGRAM_ACCOUNT_ID dans vos paramètres Meta."
        db.mark_publish_failed(capture_id, err)
        return {"success": False, "error": err, "message": err}

    def unpublish(self, capture_id: int, cap_data: dict) -> Dict[str, Any]:
        """Unpublishes a capture: removes local exported files / deletes Instagram post."""
        publish_mode = cap_data.get("publish_mode") or self.mode
        post_id = cap_data.get("published_post_id")
        filename = cap_data.get("filename")
        removed_files = []

        # 1. Clean up exported files from export_directory
        try:
            target_dir = settings.export_directory
            if target_dir.exists() and filename:
                for f in target_dir.glob(f"*{filename}*"):
                    try:
                        f.unlink()
                        removed_files.append(f.name)
                        logger.info(f"Removed exported file on unpublish: {f.name}")
                    except Exception as e:
                        logger.warning(f"Failed to delete exported file {f}: {e}")
        except Exception as e:
            logger.warning(f"Error while cleaning export files on unpublish: {e}")

        # 2. If Instagram instagrapi, attempt to delete post
        if publish_mode == "instagrapi" and post_id:
            try:
                if self._init_instagrapi() and self.ig_client:
                    self.ig_client.media_delete(str(post_id))
                    logger.info(f"Deleted post {post_id} from Instagram.")
            except Exception as e:
                logger.warning(f"Failed to delete post {post_id} from Instagram: {e}")

        # 3. If Facebook via Meta Graph API, attempt to delete photo
        if publish_mode == "meta_graph" and post_id and settings.meta_access_token:
            try:
                del_url = f"https://graph.facebook.com/v19.0/{post_id}?access_token={settings.meta_access_token}"
                requests.delete(del_url, timeout=10)
                logger.info(f"Deleted post {post_id} from Facebook.")
            except Exception as e:
                logger.warning(f"Failed to delete post {post_id} from Facebook: {e}")

        return {
            "success": True,
            "removed_files": removed_files,
            "mode": publish_mode,
            "message": "Cliché dépublié avec succès."
        }

    def dispatch_best_pending_candidate(self) -> Optional[Dict[str, Any]]:
        """Selects the highest scoring candidate from pending queue and publishes it if cooldown is elapsed."""
        # 1. Cooldown & daily rate limits
        if self.mode in ["instagrapi", "meta_graph"]:
            can_post, reason = self.can_publish_now()
            if not can_post:
                return {"success": False, "reason": reason}

        # 2. Get best pending candidate
        best_cap = db.get_best_pending_candidate(min_score=settings.min_social_score)
        if not best_cap:
            return None

        cap_id = best_cap["id"]
        image_path = Path(best_cap["filepath"])
        caption = best_cap.get("caption") or "Authentic moments."
        hashtags = best_cap.get("hashtags") or []
        score = best_cap.get("social_score")
        score_str = f"{score}/10" if score is not None else "N/A"

        logger.info(f"Tournament Winner elected: Capture #{cap_id} with score {score_str}.")
        db.log_event("INFO", f"Tournoi de sélection : Cliché #{cap_id} (Score: {score_str}) élu et publié automatiquement.")

        # Publish winning candidate
        res = self.publish(cap_id, image_path, caption, hashtags, ignore_cooldown=False)
        return res

publisher = InstagramPublisher()
