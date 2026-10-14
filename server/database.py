import sqlite3
import json
import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from server.config import settings

class Database:
    def __init__(self, db_path: Path = settings.db_path):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS captures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    filepath TEXT NOT NULL,
                    source TEXT DEFAULT 'android',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'PENDING',
                    safety_pass BOOLEAN,
                    quality_pass BOOLEAN,
                    social_score REAL,
                    scene_description TEXT,
                    caption TEXT,
                    hashtags TEXT,
                    vlm_reasoning TEXT,
                    recommended_action TEXT,
                    sensor_metadata TEXT,
                    published_at DATETIME,
                    published_post_id TEXT,
                    publish_mode TEXT,
                    publish_error TEXT
                )
            """)
            # Add sensor_metadata column if migrating existing database
            try:
                cursor.execute("ALTER TABLE captures ADD COLUMN sensor_metadata TEXT")
            except Exception:
                pass
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emergency_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    bpm INTEGER,
                    alert_type TEXT,
                    location TEXT,
                    status TEXT,
                    details TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level TEXT,
                    message TEXT,
                    details TEXT
                )
            """)
            conn.commit()

    def add_capture(self, filename: str, filepath: str, source: str = "android", sensor_metadata: Optional[Dict[str, Any]] = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            meta_json = json.dumps(sensor_metadata or {})
            local_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO captures (filename, filepath, source, timestamp, status, sensor_metadata) VALUES (?, ?, ?, ?, 'PENDING', ?)",
                (filename, str(filepath), source, local_now, meta_json)
            )
            conn.commit()
            return cursor.lastrowid

    def update_evaluation(self, capture_id: int, eval_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            hashtags_str = json.dumps(eval_data.get("hashtags", [])) if isinstance(eval_data.get("hashtags"), list) else str(eval_data.get("hashtags", ""))
            
            cursor.execute("""
                UPDATE captures SET
                    status = ?,
                    safety_pass = ?,
                    quality_pass = ?,
                    social_score = ?,
                    scene_description = ?,
                    caption = ?,
                    hashtags = ?,
                    vlm_reasoning = ?,
                    recommended_action = ?
                WHERE id = ?
            """, (
                eval_data.get("status", "EVALUATED"),
                eval_data.get("safety_pass"),
                eval_data.get("quality_pass"),
                eval_data.get("social_score"),
                eval_data.get("scene_description"),
                eval_data.get("caption"),
                hashtags_str,
                eval_data.get("reasoning"),
                eval_data.get("recommended_action"),
                capture_id
            ))
            conn.commit()

    def mark_published(self, capture_id: int, post_id: str, mode: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE captures SET
                    status = 'PUBLISHED',
                    published_at = CURRENT_TIMESTAMP,
                    published_post_id = ?,
                    publish_mode = ?
                WHERE id = ?
            """, (post_id, mode, capture_id))
            conn.commit()

    def mark_unpublished(self, capture_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE captures SET
                    status = 'UNPUBLISHED',
                    published_at = NULL,
                    published_post_id = NULL
                WHERE id = ?
            """, (capture_id,))
            conn.commit()

    def clear_all_captures(self):
        """Clears all historical captures and alerts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM captures")
            cursor.execute("DELETE FROM emergency_alerts")
            conn.commit()

    def delete_capture(self, capture_id: int) -> bool:
        """Deletes a specific capture by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM captures WHERE id = ?", (capture_id,))
            conn.commit()
            return cursor.rowcount > 0

    def mark_publish_failed(self, capture_id: int, error_msg: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE captures SET
                    status = 'PUBLISH_FAILED',
                    publish_error = ?
                WHERE id = ?
            """, (error_msg, capture_id))
            conn.commit()

    def update_caption(self, capture_id: int, caption: str, hashtags: Optional[List[str]] = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if hashtags is not None:
                cursor.execute("UPDATE captures SET caption = ?, hashtags = ? WHERE id = ?", (caption, json.dumps(hashtags), capture_id))
            else:
                cursor.execute("UPDATE captures SET caption = ? WHERE id = ?", (caption, capture_id))
            conn.commit()

    def update_status(self, capture_id: int, status: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE captures SET status = ? WHERE id = ?", (status, capture_id))
            conn.commit()

    def record_emergency_alert(self, bpm: int, alert_type: str, location: str, status: str, details: str = "") -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO emergency_alerts (bpm, alert_type, location, status, details) VALUES (?, ?, ?, ?, ?)",
                (bpm, alert_type, location, status, details)
            )
            conn.commit()
            return cursor.lastrowid

    def list_emergency_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM emergency_alerts ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def get_capture(self, capture_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM captures WHERE id = ?", (capture_id,))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                if d.get("hashtags"):
                    try:
                        d["hashtags"] = json.loads(d["hashtags"])
                    except Exception:
                        d["hashtags"] = [d["hashtags"]]
                if d.get("sensor_metadata"):
                    try:
                        d["sensor_metadata"] = json.loads(d["sensor_metadata"])
                    except Exception:
                        d["sensor_metadata"] = {}
                return d
            return None

    def get_best_pending_candidate(self, min_score: float = 7.0) -> Optional[Dict[str, Any]]:
        """Finds the highest-scoring candidate among pending captures for tournament selection."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM captures 
                WHERE status = 'PENDING_APPROVAL'
                ORDER BY 
                  CASE WHEN social_score IS NULL THEN 0 ELSE social_score END DESC,
                  id DESC 
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                d = dict(row)
                if d.get("hashtags"):
                    try:
                        d["hashtags"] = json.loads(d["hashtags"])
                    except Exception:
                        d["hashtags"] = [d["hashtags"]]
                if d.get("sensor_metadata"):
                    try:
                        d["sensor_metadata"] = json.loads(d["sensor_metadata"])
                    except Exception:
                        d["sensor_metadata"] = {}
                return d
            return None

    def list_captures(self, limit: int = 50, offset: int = 0, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status_filter:
                cursor.execute("SELECT * FROM captures WHERE status = ? ORDER BY id DESC LIMIT ? OFFSET ?", (status_filter, limit, offset))
            else:
                cursor.execute("SELECT * FROM captures ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                if d.get("hashtags"):
                    try:
                        d["hashtags"] = json.loads(d["hashtags"])
                    except Exception:
                        pass
                if d.get("sensor_metadata"):
                    try:
                        d["sensor_metadata"] = json.loads(d["sensor_metadata"])
                    except Exception:
                        d["sensor_metadata"] = {}
                results.append(d)
            return results

    def get_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM captures")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM captures WHERE status = 'PUBLISHED'")
            published = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM captures WHERE status LIKE 'REJECT%' OR status = 'UNPUBLISHED'")
            rejected = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM captures WHERE status NOT IN ('PUBLISHED', 'UNPUBLISHED') AND status NOT LIKE 'REJECT%'")
            pending = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(social_score) FROM captures WHERE social_score IS NOT NULL")
            avg_score = cursor.fetchone()[0] or 0.0

            cursor.execute("""
                SELECT COUNT(*) FROM captures 
                WHERE status = 'PUBLISHED' 
                AND published_at >= datetime('now', '-24 hours')
            """)
            published_today = cursor.fetchone()[0]

            return {
                "total_captures": total,
                "total_pending": pending,
                "total_published": published,
                "total_rejected": rejected,
                "average_social_score": round(avg_score, 2),
                "published_last_24h": published_today
            }

    def log_event(self, level: str, message: str, details: str = ""):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO system_logs (level, message, details) VALUES (?, ?, ?)",
                (level, message, details)
            )
            conn.commit()

db = Database()
