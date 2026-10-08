"""Backend API for Curiosity AI Assistant.

Run locally with: python -m uvicorn src.image_analytics.api:app --reload --reload-dir src
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import secrets
import sqlite3
import struct
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.curiosity import CuriosityEngine

# Setup logger
logger = logging.getLogger("curiosity.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Load .env file
load_dotenv()

# =====================================================================
# SUPABASE CLOUD CONFIGURATION & SYNC
# =====================================================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")


def get_supabase_headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation,resolution=merge-duplicates"
    }


def sync_conversation_to_supabase(data: dict) -> bool:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return False
    try:
        url = f"{SUPABASE_URL}/rest/v1/conversations"
        resp = requests.post(url, headers=get_supabase_headers(), json=data, timeout=4)
        return resp.status_code in (200, 201)
    except Exception as exc:
        print(f"Supabase sync notice: {exc}")
        return False


def delete_conversation_from_supabase(conversation_id: str, user_id: int) -> bool:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return False
    try:
        url = f"{SUPABASE_URL}/rest/v1/conversations?id=eq.{conversation_id}&user_id=eq.{user_id}"
        resp = requests.delete(url, headers=get_supabase_headers(), timeout=4)
        return resp.status_code in (200, 204)
    except Exception:
        return False


# =====================================================================
# DATABASE SETTING & PERSISTENCE (SQLITE LOCAL CACHE)
# =====================================================================

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "assistant.db"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=20.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA synchronous = NORMAL;")

    # 1. Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # 3. Conversations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        messages_json TEXT NOT NULL,
        attachments_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()


# =====================================================================
# AUTH & SECURITY HELPERS
# =====================================================================

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return f"{salt}${pw_hash}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, pw_hash = hashed.split("$")
        test_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
        return test_hash == pw_hash
    except Exception:
        return False


def get_current_user(authorization: str = Header(None)) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token.")
    token = authorization.split(" ")[1]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, expires_at FROM sessions WHERE token = ?", (token,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Session expired or invalid token.")

    try:
        raw_exp = row["expires_at"]
        expires_at = datetime.fromisoformat(raw_exp)
        now = datetime.now(expires_at.tzinfo) if expires_at.tzinfo else datetime.utcnow()
        is_expired = expires_at < now
    except Exception:
        is_expired = False

    if is_expired:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        raise HTTPException(status_code=401, detail="Session token expired.")

    return row["user_id"]


# =====================================================================
# REQUEST SCHEMAS
# =====================================================================

class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class SupabaseLoginRequest(BaseModel):
    access_token: str


class ConversationSaveRequest(BaseModel):
    id: str
    title: str
    messages: list
    attachments: list


# =====================================================================
# FASTAPI APPLICATION SETUP
# =====================================================================

DEFAULT_PROMPT = "Describe this image in detail and highlight key observations."

app = FastAPI(
    title="Curiosity AI Pipeline",
    description="Multi-modal analysis, OCR, YOLO, ResNet-50, and Executive Synthesis engine.",
    version="2.0.0",
)

# Enable CORS for frontend and cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")

    vendor_dir = FRONTEND_DIR / "vendor"
    if vendor_dir.exists():
        app.mount("/vendor", StaticFiles(directory=vendor_dir), name="vendor")


AUDIO_DIR = Path(__file__).resolve().parents[2] / "data" / "generated_audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/generated_audio", StaticFiles(directory=AUDIO_DIR), name="generated_audio")


@app.get("/api/v1/audio/{filename}")
@app.get("/audio/generated/{filename}")
async def serve_generated_audio(filename: str):
    file_path = AUDIO_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return FileResponse(file_path, media_type="audio/mpeg", filename=filename)


@app.get("/", include_in_schema=False)
def homepage() -> Response:
    """Serve the local browser interface."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return Response(content="Curiosity AI Pipeline running. Build frontend to access UI.", media_type="text/plain")


@app.get("/favicon.svg", include_in_schema=False)
@app.get("/favicon.png", include_in_schema=False)
@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Serve the custom mascot favicon."""
    svg_path = FRONTEND_DIR / "favicon.svg"
    if svg_path.exists():
        return FileResponse(svg_path)
    png_path = FRONTEND_DIR / "favicon.png"
    if png_path.exists():
        return FileResponse(png_path)
    return Response(status_code=204)


@app.on_event("startup")
async def startup_event():
    """Initialize database tables."""
    init_db()


# =====================================================================
# CORE ANALYSIS ENDPOINT (PLACEHOLDER - LOGIC TO BE REBUILT)
# =====================================================================

@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "model": "Curiosity-YOLO11-EasyOCR-ResNet50",
        "yolo": "yolo11n",
        "ocr": "EasyOCR",
        "pdf": "PyMuPDF"
    }


@app.post("/analyze")
async def analyze_media(
    file: UploadFile = File(None, description="Media or document file (PDF, image, audio, doc, etc.)"),
    image: UploadFile = File(None, description="Backwards compatible file upload parameter"),
    prompt: str = Form(DEFAULT_PROMPT, description="Question or instruction about the uploaded file"),
    history: str = Form("[]", description="Recent chat turns supplied by the frontend"),
    user_name: Optional[str] = Form(None, description="Current user preferred display name"),
    voice: Optional[str] = Form(None, description="Preferred neural voice (ritu or shubh)"),
    emotion: Optional[str] = Form(None, description="Preferred emotion preset"),
    authorization: Optional[str] = Header(None, description="Bearer session token"),
) -> dict[str, Any]:
    """Execute end-to-end multimodal analysis using Curiosity 8-Layer Architecture."""
    target_upload = file or image
    file_bytes = None
    filename = None
    content_type = None

    if target_upload:
        try:
            file_bytes = await target_upload.read()
            filename = target_upload.filename
            content_type = target_upload.content_type
            if not file_bytes:
                file_bytes = None
                filename = None
                content_type = None
        except Exception as read_err:
            logger.warning(f"Failed to read uploaded file: {read_err}")
            file_bytes = None

    parsed_history = []
    if history:
        try:
            parsed_history = json.loads(history)
        except Exception:
            parsed_history = []

    # Authenticate user if token provided
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        try:
            user_id = get_current_user(authorization)
        except Exception:
            user_id = None

    effective_user_id = str(user_id) if user_id else (f"user_{user_name.strip()}" if (user_name and user_name.strip()) else "guest_user")

    try:
        result = CuriosityEngine.execute(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            prompt=prompt,
            history=parsed_history,
            user_name=user_name,
            user_id=effective_user_id,
            voice=voice,
            emotion=emotion
        )
        return result
    except Exception as exc:
        logger.exception(f"CuriosityEngine execution failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}")


# =====================================================================
# VOICE SYNTHESIS (SARVAM AI + DEFAULT BROWSER VOICES)
# =====================================================================

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", os.getenv("SARVAM_API_SUBSCRIPTION_KEY", "sk_ifnmvwzp_6GQ219edjduibgcIRX3QxiV2"))
SARVAM_MODEL = os.getenv("SARVAM_MODEL", "bulbul:v3")
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

SARVAM_VOICES = [
    {
        "id": "ritu",
        "name": "ritu",
        "displayName": "Ritu (Female)",
        "lang": "hi-IN / en-IN",
        "description": "Expressive and lively female voice"
    },
    {
        "id": "shubh",
        "name": "shubh",
        "displayName": "Shubh (Male)",
        "lang": "hi-IN / en-IN",
        "description": "Articulate and natural male voice"
    }
]


SARVAM_EMOTIONS = [
    {
        "id": "neutral",
        "label": "Natural & Balanced",
        "emoji": "🌟",
        "description": "Balanced, conversational everyday speech",
        "temperature": 0.60,
        "pace_multiplier": 1.00
    },
    {
        "id": "cheerful",
        "label": "Happy & Cheerful",
        "emoji": "😊",
        "description": "Joyful, warm, smiling tone with enthusiastic cadence",
        "temperature": 0.85,
        "pace_multiplier": 1.05
    },
    {
        "id": "excited",
        "label": "Excited & Vibrant",
        "emoji": "🤩",
        "description": "High-energy, celebratory and animated inflection",
        "temperature": 0.95,
        "pace_multiplier": 1.12
    },
    {
        "id": "calm",
        "label": "Calm & Gentle",
        "emoji": "😌",
        "description": "Soothing, gentle pauses and relaxed intonation",
        "temperature": 0.50,
        "pace_multiplier": 0.90
    },
    {
        "id": "empathetic",
        "label": "Empathetic & Caring",
        "emoji": "🥺",
        "description": "Compassionate, comforting and heartfelt voice",
        "temperature": 0.65,
        "pace_multiplier": 0.92
    },
    {
        "id": "dramatic",
        "label": "Dramatic & Storyteller",
        "emoji": "🎭",
        "description": "Theatrical narrative, expressive pitch dynamics and pauses",
        "temperature": 0.92,
        "pace_multiplier": 0.96
    },
    {
        "id": "professional",
        "label": "Formal & Professional",
        "emoji": "💼",
        "description": "Crisp, authoritative, boardroom-level clarity",
        "temperature": 0.35,
        "pace_multiplier": 1.00
    },
    {
        "id": "urgent",
        "label": "Urgent & High-Energy",
        "emoji": "⚡",
        "description": "Fast-paced, prompt, alert and compelling delivery",
        "temperature": 0.80,
        "pace_multiplier": 1.18
    },
    {
        "id": "somber",
        "label": "Somber & Reflective",
        "emoji": "😔",
        "description": "Deep, reflective cadence with melancholic pauses",
        "temperature": 0.45,
        "pace_multiplier": 0.85
    },
    {
        "id": "curious",
        "label": "Curious & Inquisitive",
        "emoji": "🧐",
        "description": "Engaged, questioning tone with lively vocal lift",
        "temperature": 0.78,
        "pace_multiplier": 1.02
    }
]

EMOTION_MAP = {e["id"]: e for e in SARVAM_EMOTIONS}


@app.get("/tts/voices")
@app.get("/api/v1/tts/voices")
async def get_available_tts_voices():
    """Returns available voice synthesis catalog featuring strictly Ritu and Shubh with emotions."""
    return {
        "provider": "sarvam",
        "model": SARVAM_MODEL,
        "default_voice": "ritu",
        "default_emotion": "neutral",
        "voices": SARVAM_VOICES,
        "emotions": SARVAM_EMOTIONS
    }


def _apply_emotion_prosody(text: str, emotion_id: str) -> str:
    """Format and punctuate text to enhance emotional prosody inference in bulbul:v3."""
    if not text:
        return text
    t = text.strip()
    if emotion_id in ("cheerful", "excited"):
        # Ensure energetic terminal punctuation
        if t and t[-1] not in ".!?":
            t += "!"
    elif emotion_id in ("calm", "somber", "dramatic"):
        # Replace abrupt commas with gentle pauses where suitable
        t = re.sub(r',\s+', '... ', t)
    return t


@app.post("/tts")
async def tts_endpoint(data: dict):
    """Synthesize text into speech using Sarvam AI bulbul:v3 (Ritu or Shubh) with emotion control."""
    text = (data.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text parameter cannot be empty.")

    req_voice = (data.get("voice_id") or data.get("voice") or "").strip().lower()

    # Clean voice identifier: strictly ritu or shubh
    speaker = "shubh" if "shubh" in req_voice else "ritu"

    # Emotion handling
    req_emotion = (data.get("emotion") or "neutral").strip().lower()
    emotion_info = EMOTION_MAP.get(req_emotion, EMOTION_MAP["neutral"])

    # Temperature calculation (randomness / expressiveness in bulbul:v3, 0.01 to 1.0)
    user_temp = data.get("temperature")
    if user_temp is not None:
        try:
            temperature = float(user_temp)
        except (ValueError, TypeError):
            temperature = emotion_info["temperature"]
    else:
        temperature = emotion_info["temperature"]
    temperature = max(0.01, min(1.0, temperature))

    # Pace calculation (speed, 0.5 to 2.0 in bulbul:v3)
    user_pace = data.get("pace") or data.get("speed")
    if user_pace is not None:
        try:
            base_pace = float(user_pace)
        except (ValueError, TypeError):
            base_pace = 1.0
    else:
        base_pace = 1.0
    pace = max(0.5, min(2.0, round(base_pace * emotion_info.get("pace_multiplier", 1.0), 2)))

    api_key = SARVAM_API_KEY
    if not api_key:
        return {"status": "error", "message": "Sarvam API key not configured."}

    clean_text = re.sub(r'[*_~#`>|]+', ' ', text)
    clean_text = re.sub(r'-{2,}', ' ', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()[:1000]

    # Apply emotion prosodic conditioning
    clean_text = _apply_emotion_prosody(clean_text, req_emotion)

    # Use explicit target_language_code if provided, default strictly to "hi-IN"
    target_lang = (data.get("target_language_code") or data.get("language_code") or "hi-IN").strip()
    if not target_lang:
        target_lang = "hi-IN"

    # 1. Attempt synthesis via official SarvamAI bulbul:v3 SDK
    try:
        from sarvamai import SarvamAI
        client = SarvamAI(api_subscription_key=api_key)
        stream = client.text_to_speech.convert_stream(
            text=clean_text,
            language_code=target_lang,
            speaker=speaker,
            model="bulbul:v3",
            pace=pace,
            temperature=temperature,
            speech_sample_rate=24000,
            output_audio_codec="mp3"
        )
        audio_bytes = b"".join(stream)
        if audio_bytes and len(audio_bytes) > 100:
            return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as sdk_err:
        logger.warning(f"Sarvam AI SDK bulbul:v3 stream failed: {sdk_err}, falling back to REST endpoint...")

    # 2. Resilient fallback via Sarvam AI REST API
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": [clean_text],
        "target_language_code": target_lang,
        "speaker": speaker,
        "model": "bulbul:v3",
        "pace": pace,
        "temperature": temperature,
        "speech_sample_rate": 24000,
        "enable_preprocessing": True
    }

    try:
        res = requests.post(SARVAM_TTS_URL, headers=headers, json=payload, timeout=25)
        if res.status_code == 200:
            res_data = res.json()
            audios = res_data.get("audios", [])
            if audios and len(audios[0]) > 0:
                audio_bytes = base64.b64decode(audios[0])
                return Response(content=audio_bytes, media_type="audio/wav")
        if res.status_code in (401, 403):
            raise HTTPException(status_code=401, detail="Sarvam AI API key is invalid or unauthorized.")
        raise HTTPException(status_code=res.status_code, detail=f"Sarvam AI TTS error: {res.text}")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Sarvam AI TTS request failed: {exc}")



@app.post("/api/v1/speech/synthesize")
async def synthesize_speech(
    text: str = Form(..., description="Text to synthesize into spoken audio")
) -> dict[str, Any]:
    """Synthesize speech metadata (returns Web Speech API / Sarvam TTS routing guidance)."""
    clean_text = text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Text parameter cannot be empty.")
    return {
        "status": "ready",
        "text": clean_text,
        "backend": "sarvam_ai",
        "message": "Use /tts for Sarvam AI studio voice synthesis."
    }


# =====================================================================
# AUTHENTICATION ROUTES
# =====================================================================

@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    email = req.email.strip().lower()
    password = req.password
    if not email or len(password) < 6:
        raise HTTPException(status_code=400, detail="Invalid email or password must be at least 6 characters.")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        pw_hash = hash_password(password)
        cursor.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, pw_hash))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Email is already registered.")

    conn.close()
    return {"status": "success", "message": "User registered successfully."}


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    email = req.email.strip().lower()
    password = req.password

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = secrets.token_hex(32)
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)", (token, user["id"], expires_at))
    conn.commit()
    conn.close()

    return {"token": token, "email": email}


@app.post("/api/auth/supabase-login")
async def supabase_login(req: SupabaseLoginRequest):
    token = req.access_token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="Supabase access token required.")

    user_url = f"{SUPABASE_URL}/auth/v1/user"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}"
    }
    try:
        resp = requests.get(user_url, headers=headers, timeout=6)
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Supabase credentials.")
        user_info = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Failed to authenticate with Supabase: {exc}")

    email = user_info.get("email") or user_info.get("user_metadata", {}).get("email")
    if not email:
        user_name = user_info.get("user_metadata", {}).get("user_name") or user_info.get("id")
        if user_name:
            email = f"{user_name}@users.noreply.github.com"
        else:
            raise HTTPException(status_code=400, detail="No email returned from OAuth provider.")
    email = email.strip().lower()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    if not user:
        random_pw = secrets.token_hex(20)
        cursor.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, hash_password(random_pw)))
        conn.commit()
        user_id = cursor.lastrowid
    else:
        user_id = user["id"]

    session_token = secrets.token_hex(32)
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
    cursor.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)", (session_token, user_id, expires_at))
    conn.commit()
    conn.close()

    metadata = user_info.get("user_metadata", {})
    name = metadata.get("full_name") or metadata.get("name") or metadata.get("user_name") or email.split("@")[0]

    return {"token": session_token, "email": email, "name": name}


@app.post("/api/auth/logout")
async def logout(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Authorization token required.")
    token = authorization.split(" ")[1]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()

    return {"status": "success", "message": "Session invalidated."}


@app.get("/api/auth/me")
async def get_me(authorization: str = Header(None)):
    user_id = get_current_user(authorization)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"id": user_id, "email": user["email"]}


# =====================================================================
# CONVERSATION HISTORY ROUTES (HYBRID SUPABASE CLOUD + SQLITE FALLBACK)
# =====================================================================

@app.get("/api/conversations")
async def list_conversations(authorization: str = Header(None)):
    user_id = get_current_user(authorization)

    # 1. Try Supabase Cloud Postgres
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        try:
            url = f"{SUPABASE_URL}/rest/v1/conversations?user_id=eq.{user_id}&order=updated_at.desc"
            resp = requests.get(url, headers=get_supabase_headers(), timeout=4)
            if resp.status_code == 200:
                rows = resp.json()
                if rows:
                    return [
                        {
                            "id": r["id"],
                            "title": r.get("title") or "Untitled Session",
                            "created_at": r.get("created_at"),
                            "updated_at": r.get("updated_at"),
                            "attachments": r.get("attachments") or []
                        }
                        for r in rows
                    ]
        except Exception as exc:
            print(f"Supabase list warning, falling back to SQLite: {exc}")

    # 2. Local SQLite fallback
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, created_at, updated_at, attachments_json FROM conversations WHERE user_id = ? ORDER BY updated_at DESC", 
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    conversations = []
    for r in rows:
        try:
            attachments = json.loads(r["attachments_json"]) if r["attachments_json"] else []
        except Exception:
            attachments = []
        conversations.append({
            "id": r["id"],
            "title": r["title"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "attachments": attachments
        })
    return conversations


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, authorization: str = Header(None)):
    user_id = get_current_user(authorization)

    # 1. Try Supabase Cloud Postgres
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        try:
            url = f"{SUPABASE_URL}/rest/v1/conversations?id=eq.{conversation_id}&user_id=eq.{user_id}"
            resp = requests.get(url, headers=get_supabase_headers(), timeout=4)
            if resp.status_code == 200:
                rows = resp.json()
                if rows:
                    row = rows[0]
                    return {
                        "id": row["id"],
                        "title": row.get("title") or "Untitled Session",
                        "messages": row.get("messages") or [],
                        "attachments": row.get("attachments") or []
                    }
        except Exception as exc:
            logger.warning(f"Supabase detail warning, falling back to SQLite: {exc}")

    # 2. Local SQLite fallback
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, messages_json, attachments_json FROM conversations WHERE id = ? AND user_id = ?", 
        (conversation_id, user_id)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    try:
        messages = json.loads(row["messages_json"]) if row["messages_json"] else []
    except Exception:
        messages = []
    try:
        attachments = json.loads(row["attachments_json"]) if row["attachments_json"] else []
    except Exception:
        attachments = []

    return {
        "id": row["id"],
        "title": row["title"],
        "messages": messages,
        "attachments": attachments
    }


@app.post("/api/conversations")
async def save_conversation(req: ConversationSaveRequest, authorization: str = Header(None)):
    user_id = get_current_user(authorization)
    now = datetime.utcnow().isoformat()

    # 1. Always save to Local SQLite for immediate local persistence
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM conversations WHERE id = ? AND user_id = ?", (req.id, user_id))
        exists = cursor.fetchone()

        messages_str = json.dumps(req.messages)
        attachments_str = json.dumps(req.attachments)

        if exists:
            cursor.execute(
                "UPDATE conversations SET title = ?, messages_json = ?, attachments_json = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                (req.title, messages_str, attachments_str, now, req.id, user_id)
            )
        else:
            cursor.execute(
                "INSERT INTO conversations (id, user_id, title, messages_json, attachments_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (req.id, user_id, req.title, messages_str, attachments_str, now, now)
            )
        conn.commit()
    except sqlite3.Error as exc:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")
    conn.close()

    # 2. Async/Best-effort sync to Supabase Cloud PostgreSQL
    supabase_record = {
        "id": req.id,
        "user_id": str(user_id),
        "title": req.title,
        "messages": req.messages,
        "attachments": req.attachments,
        "updated_at": now
    }
    sync_conversation_to_supabase(supabase_record)

    return {"status": "success", "message": "Conversation saved."}


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, authorization: str = Header(None)):
    user_id = get_current_user(authorization)

    # 1. Delete from SQLite
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id))
    conn.commit()
    conn.close()

    # 2. Delete from Supabase Cloud
    delete_conversation_from_supabase(conversation_id, user_id)

    return {"status": "success", "message": "Conversation deleted."}
