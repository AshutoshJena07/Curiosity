"""Supabase Cloud Audit & Analytics Logger for Curiosity Core.

Asynchronously logs all user queries, model responses, media metadata,
accuracy indicators, and latency into Supabase Cloud PostgreSQL.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
import requests
from typing import Any, Dict, Optional

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")


def _get_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }


def log_interaction_to_supabase_async(
    user_prompt: str,
    assistant_response: str,
    media_category: str = "text_only",
    filename: Optional[str] = None,
    accuracy: float = 95.0,
    duration_s: float = 1.0,
    user_id: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Non-blocking background thread to sync interaction and accuracy to Supabase."""
    def _worker():
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            return

        payload = {
            "id": str(uuid.uuid4()),
            "user_id": str(user_id or "anonymous_explorer"),
            "title": (user_prompt[:40] if user_prompt else "Media Analysis").strip(),
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt,
                    "filename": filename,
                    "category": media_category
                },
                {
                    "role": "assistant",
                    "content": assistant_response,
                    "accuracy": f"{accuracy:.1f}%",
                    "latency_s": round(duration_s, 2),
                    "model": "Curiosity (Local Core Engine)"
                }
            ],
            "attachments": [
                {
                    "filename": filename or "none",
                    "category": media_category,
                    "accuracy_score": accuracy,
                    "metadata": extra_metadata or {}
                }
            ]
        }

        try:
            url = f"{SUPABASE_URL}/rest/v1/conversations"
            resp = requests.post(url, headers=_get_headers(), json=payload, timeout=5)
            if resp.status_code in (200, 201, 204):
                print(f"[Supabase Logger] Successfully logged interaction (Accuracy: {accuracy:.1f}%, Time: {duration_s:.2f}s)")
            else:
                print(f"[Supabase Logger Notice] Status {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:
            print(f"[Supabase Logger Background Error] {exc}")

    # Fire and forget in daemon thread
    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
