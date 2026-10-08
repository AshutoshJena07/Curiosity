"""Layer 6: Persistence & Cloud Synchronization Engine for Curiosity AI.

Handles:
1. SQLite local transaction caching (data/assistant.db)
2. Asynchronous background logging to Supabase Cloud
3. Telemetry and accuracy audit trail
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, Optional
import requests

from src.curiosity.layer_0_core.config import (
    SQLITE_DB_PATH,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL
)

logger = logging.getLogger("curiosity.layer_6")


class PersistenceManager:
    """Manages SQLite cache and non-blocking Supabase cloud telemetry."""

    @classmethod
    def get_db_connection(cls) -> sqlite3.Connection:
        SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(SQLITE_DB_PATH, timeout=20.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def log_interaction_async(
        cls,
        user_prompt: str,
        assistant_response: str,
        media_category: str,
        accuracy: float,
        confidence: float,
        duration_s: float,
        filename: Optional[str] = None,
        user_id: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None
    ):
        """Dispatches telemetry logging in a background thread without blocking the user response."""
        def _worker():
            # 1. Local SQLite audit insert if interactions table exists
            try:
                conn = cls.get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        prompt TEXT,
                        media_category TEXT,
                        accuracy REAL,
                        confidence REAL,
                        duration_s REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("""
                    INSERT INTO audit_logs (user_id, prompt, media_category, accuracy, confidence, duration_s)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    str(user_id or "anonymous"),
                    user_prompt[:500],
                    media_category,
                    accuracy,
                    confidence,
                    duration_s
                ))
                conn.commit()
                conn.close()
            except Exception as exc:
                logger.debug(f"[Layer 6] Local SQLite log notice: {exc}")

            # 2. Supabase Cloud Sync
            if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
                return

            try:
                headers = {
                    "apikey": SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                }
                payload = {
                    "user_id": str(user_id or "anonymous"),
                    "user_prompt": user_prompt[:500],
                    "assistant_response": assistant_response[:2000],
                    "media_category": media_category,
                    "accuracy": float(accuracy),
                    "confidence": float(confidence),
                    "duration_s": float(duration_s),
                    "filename": filename or "none",
                    "created_at": datetime.utcnow().isoformat()
                }
                # Log to interactions / telemetry endpoint
                requests.post(
                    f"{SUPABASE_URL}/rest/v1/curiosity_telemetry",
                    headers=headers,
                    json=payload,
                    timeout=4
                )
            except Exception:
                pass

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
