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
                    published_at DATETIME,
                    published_post_id TEXT,
                    publish_mode TEXT,
                    publish_error TEXT
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

    def add_capture(self, filename: str, filepath: str, source: str = "android") -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO captures (filename, filepath, source, status) VALUES (?, ?, ?, 'PENDING')",
                (filename, str(filepath), source)
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
                return d
            return None

    def list_captures(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
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
                results.append(d)
            return results

    def get_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM captures")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM captures WHERE status = 'PUBLISHED'")
            published = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM captures WHERE status = 'REJECTED'")
            rejected = cursor.fetchone()[0]

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
