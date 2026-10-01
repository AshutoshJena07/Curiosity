"""Backend API for Curiosity AI Assistant.

Run locally with: python -m uvicorn src.image_analytics.api:app --reload --reload-dir src
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import sqlite3
import struct
import threading
import warnings
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import requests
import torch
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel

from src.curiosity_core.deep_learning_pipeline import get_dl_pipeline
from src.curiosity_core.engine import CuriosityEngine

# Load .env file
load_dotenv()

# Suppress harmless internal PyTorch / EasyOCR deprecation warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Maximize CPU parallelism across all available cores for fast inference
if hasattr(torch, "set_num_threads"):
    try:
        torch.set_num_threads(os.cpu_count() or 8)
    except Exception:
        pass

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

    expires_at = datetime.fromisoformat(row["expires_at"])
    if expires_at < datetime.utcnow():
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

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")

    vendor_dir = FRONTEND_DIR / "vendor"
    if vendor_dir.exists():
        app.mount("/vendor", StaticFiles(directory=vendor_dir), name="vendor")


@app.get("/", include_in_schema=False)
def homepage() -> FileResponse:
    """Serve the local browser interface."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/favicon.svg", include_in_schema=False)
@app.get("/favicon.png", include_in_schema=False)
@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    """Serve the custom mascot favicon."""
    svg_path = FRONTEND_DIR / "favicon.svg"
    if svg_path.exists():
        return FileResponse(svg_path)
    return FileResponse(FRONTEND_DIR / "favicon.png")


@app.on_event("startup")
async def startup_event():
    """Initialize database tables and pre-warm AI models in background for fast inference."""
    init_db()

    def warm_up():
        print("[Startup] Pre-warming Deep Learning models (YOLOv8, ResNet-50 ImageNet)...")
        try:
            pipeline = get_dl_pipeline()
            pipeline.resnet_classifier._load_model()
            pipeline.yolo_detector._load_model()
            print("[Startup] YOLO & ResNet-50 ImageNet loaded successfully into RAM.")

            # Pre-warm local Ollama Qwen model into memory
            try:
                requests.post(
                    "http://127.0.0.1:11434/api/chat",
                    json={
                        "model": "qwen2.5:1.5b",
                        "messages": [{"role": "user", "content": "warmup"}],
                        "keep_alive": -1,
                        "options": {"num_predict": 1},
                    },
                    timeout=10,
                )
                print("[Startup] Local Qwen LLM pre-warmed in memory.")
            except Exception:
                pass
        except Exception as exc:
            print(f"[Startup Notice] Preload note: {exc}")

    threading.Thread(target=warm_up, daemon=True).start()


# =====================================================================
# CORE ANALYSIS & DEEP LEARNING ENDPOINTS
# =====================================================================

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": "CuriosityCore active"}


@app.post("/analyze")
async def analyze_media(
    file: UploadFile = File(None, description="Media or document file (PDF, image, audio, doc, etc.)"),
    image: UploadFile = File(None, description="Backwards compatible file upload parameter"),
    prompt: str = Form(DEFAULT_PROMPT, description="Question or instruction about the uploaded file"),
    history: str = Form("[]", description="Recent chat turns supplied by the frontend"),
    user_name: Optional[str] = Form(None, description="Current user preferred display name"),
    authorization: Optional[str] = Header(None, description="Bearer session token"),
) -> dict[str, Any]:
    """Execute the 3-stage Curiosity Core pipeline on the uploaded media and user prompt."""
    target_upload = file or image

    # Resolve user name if session token is provided
    resolved_name = (user_name or "").strip()
    if not resolved_name and authorization:
        try:
            token = authorization.replace("Bearer ", "").strip()
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.email FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.token = ? AND datetime(s.expires_at) > datetime('now')
            """, (token,))
            row = cursor.fetchone()
            conn.close()
            if row and row["email"]:
                resolved_name = row["email"].split("@")[0].replace(".", " ").title()
        except Exception:
            pass

    file_bytes = None
    filename = None
    content_type = None

    if target_upload is not None:
        file_bytes = await target_upload.read()
        filename = target_upload.filename or "uploaded_media"
        content_type = target_upload.content_type or ""

    try:
        parsed_history = json.loads(history)
        if not isinstance(parsed_history, list):
            parsed_history = []
        safe_history = [
            {"role": str(turn.get("role", "user"))[:12], "content": str(turn.get("content", ""))[:600]}
            for turn in parsed_history[-8:]
            if isinstance(turn, dict)
        ]
    except json.JSONDecodeError:
        safe_history = []

    try:
        engine_res = CuriosityEngine.execute(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            prompt=prompt,
            history=safe_history,
            user_name=resolved_name or "Explorer",
            user_id=resolved_name or "anonymous"
        )
        answer = engine_res.get("answer", "")
        dl_metrics = engine_res.get("dl_metrics")
        accuracy = engine_res.get("accuracy", 95.0)
    except Exception as exc:
        print(f"[CuriosityEngine Route Error] {exc}")
        raise HTTPException(status_code=500, detail=f"Analysis pipeline error: {exc}") from exc

    return {
        "prompt": prompt,
        "answer": answer,
        "model": "Curiosity",
        "dl_metrics": dl_metrics,
        "accuracy": accuracy
    }


@app.post("/api/detect/yolo")
async def detect_objects_yolo(
    file: UploadFile = File(..., description="Image file for YOLO object detection"),
    conf: float = Form(0.25, description="Confidence threshold"),
) -> dict[str, Any]:
    """Detect objects, bounding boxes, and counts in an image using YOLOv8."""
    content = await file.read()
    image = Image.open(BytesIO(content)).convert("RGB")
    pipeline = get_dl_pipeline()
    objects = pipeline.yolo_detector.detect(image, conf_threshold=conf)

    counts = {}
    for obj in objects:
        counts[obj.label] = counts.get(obj.label, 0) + 1

    return {
        "model": "YOLOv8",
        "total_objects": len(objects),
        "counts": counts,
        "detected_objects": [obj.to_dict() for obj in objects]
    }


@app.post("/api/classify/resnet")
async def classify_resnet_imagenet(
    file: UploadFile = File(..., description="Image file for ResNet-50 ImageNet classification"),
    top_k: int = Form(5, description="Top-K categories"),
) -> dict[str, Any]:
    """Classify an image into ImageNet (ILSVRC-1000) categories using ResNet-50."""
    content = await file.read()
    image = Image.open(BytesIO(content)).convert("RGB")
    pipeline = get_dl_pipeline()
    predictions = pipeline.resnet_classifier.predict(image, top_k=top_k)

    return {
        "model": "ResNet-50",
        "dataset": "ImageNet-1K",
        "top_prediction": predictions[0].label if predictions else None,
        "predictions": [p.to_dict() for p in predictions]
    }


# =====================================================================
# STUDIO VOICE & AUDIO SYNTHESIS CONFIGURATION
# =====================================================================

EMOTION_MAP = {
    "happy": "happy",
    "excited": "excited",
    "joy": "happy",
    "joyful": "happy",
    "bright": "happy",
    "sad": "sad",
    "emotional": "sad",
    "grief": "sad",
    "sorrow": "sad",
    "angry": "anger",
    "anger": "anger",
    "controlled": "calm",
    "firm": "calm",
    "irritated": "anger",
    "calm": "calm",
    "professional": "calm",
    "reassuring": "calm",
    "gentle": "calm",
    "comforting": "calm",
    "warm": "calm",
    "fear": "fear",
    "urgency": "fear",
    "urgent": "fear",
    "tense": "fear",
    "worried": "fear",
    "nervous": "fear",
    "surprised": "surprise",
    "surprise": "surprise",
    "whisper": "whisper",
    "secretive": "whisper",
    "quiet": "whisper",
    "sarcastic": "happy",
    "playful": "happy",
    "relieved": "calm",
    "neutral": "neutral",
}


def parse_script_emotion_segments(full_text: str) -> list[tuple[str, str]]:
    """Parse a script into (spoken_text, emotion_tag) segments.
    Strips bracket tags, speaker names, markdown dividers, headers, and bullet points.
    """
    lines = full_text.splitlines()
    segments = []
    current_emotion = "neutral"

    for line in lines:
        raw = line.strip()
        if not raw or raw == "[END]":
            continue
        if re.match(r"^[-=_*#]{2,}$", raw) or raw.startswith("#"):
            continue

        bracket_match = re.search(r"\[([A-Za-z0-9_\s\/\\-]+)\]", raw)
        if bracket_match:
            tag_text = bracket_match.group(1).lower()
            found_emotion = None
            for word in re.split(r"[\s\/\\-]+", tag_text):
                if word in EMOTION_MAP:
                    found_emotion = EMOTION_MAP[word]
                    break
            if found_emotion:
                current_emotion = found_emotion

            raw = re.sub(r"\[([A-Za-z0-9_\s\/\\-]+)\]", "", raw).strip()
            if not raw:
                continue

        spoken = re.sub(r"^[A-Za-z0-9_\s]+\s*(\([^)]*\))?\s*:\s*", "", raw)
        spoken = re.sub(r"\*?\([^)]*\)\*?", "", spoken)
        spoken = re.sub(r"^[-*•\d+\.]+\s+", "", spoken)
        spoken = re.sub(r"[*_~#`>|]+", "", spoken)
        spoken = re.sub(r"-{2,}", " ", spoken).strip()
        spoken = re.sub(r"\s*:\s*", ", ", spoken)

        if spoken and len(spoken) > 1 and not re.match(r"^[-=_\s]+$", spoken):
            segments.append((spoken, current_emotion))

    if not segments:
        clean_fallback = re.sub(r"\[([A-Za-z0-9_\s\/\\-]+)\]", "", full_text)
        clean_fallback = re.sub(r"^[A-Za-z0-9_\s]+\s*(\([^)]*\))?\s*:\s*", "", clean_fallback, flags=re.MULTILINE)
        clean_fallback = re.sub(r"\*?\([^)]*\)\*?", "", clean_fallback)
        clean_fallback = re.sub(r"^[-*•\d+\.]+\s+", "", clean_fallback, flags=re.MULTILINE)
        clean_fallback = re.sub(r"[*_~#`>|-]+", " ", clean_fallback)
        clean_fallback = re.sub(r"\s+", " ", clean_fallback).strip()
        if clean_fallback:
            segments.append((clean_fallback, "neutral"))

    return segments


def combine_wav_audio_chunks(wav_chunks: list[bytes]) -> bytes:
    """Concatenate PCM WAV audio chunks into a single valid WAV file."""
    valid_chunks = [c for c in wav_chunks if len(c) > 44]
    if not valid_chunks:
        return b""
    if len(valid_chunks) == 1:
        return valid_chunks[0]

    combined_pcm = bytearray()
    first_header = bytearray(valid_chunks[0][:44])

    for chunk in valid_chunks:
        combined_pcm.extend(chunk[44:])

    total_data_len = len(combined_pcm)
    total_file_len = total_data_len + 36

    first_header[4:8] = struct.pack("<I", total_file_len)
    first_header[40:44] = struct.pack("<I", total_data_len)

    return bytes(first_header + combined_pcm)


INWORLD_TTS_CONFIG = {
    "auth_token": os.getenv("INWORLD_TTS_AUTH", ""),
    "model_id": "inworld-tts-2",
    "delivery_mode": "BALANCED",
    "default_voice_id": "Sarah"
}

INWORLD_VOICES = [
    {"id": "Sarah", "name": "Sarah", "displayName": "Sarah (Inworld Studio Female)", "lang": "en-US", "description": "Expressive natural studio female voice"},
    {"id": "Anjali", "name": "Anjali", "displayName": "Anjali (Inworld Indian Female)", "lang": "en-IN", "description": "Confident and articulate Indian English voice"},
    {"id": "Vincent", "name": "Vincent", "displayName": "Vincent (Inworld Classy Male)", "lang": "en-US", "description": "Polished, classy male voice with smooth delivery"},
    {"id": "Ashley", "name": "Ashley", "displayName": "Ashley (Inworld Warm Female)", "lang": "en-US", "description": "Warm, mellow and conversational female voice"},
    {"id": "Carter", "name": "Carter", "displayName": "Carter (Inworld Announcer Male)", "lang": "en-US", "description": "Energetic radio announcer style male voice"},
]


def synthesize_inworld_tts(text: str, voice_id: str = "Sarah") -> bytes:
    """Synthesize speech using Inworld AI streaming TTS API into MP3 audio bytes."""
    auth_token = INWORLD_TTS_CONFIG.get("auth_token") or ""
    url = "https://api.inworld.ai/tts/v1/voice:stream"
    headers = {
        "Authorization": auth_token,
        "Content-Type": "application/json",
    }

    clean_voice_id = voice_id.replace("inworld-", "").strip() if voice_id else "Sarah"
    if not clean_voice_id:
        clean_voice_id = "Sarah"

    payload = {
        "text": text,
        "voice_id": clean_voice_id,
        "audio_config": {"audio_encoding": "MP3"},
        "delivery_mode": INWORLD_TTS_CONFIG.get("delivery_mode", "BALANCED"),
        "model_id": INWORLD_TTS_CONFIG.get("model_id", "inworld-tts-2")
    }

    try:
        res = requests.post(url, headers=headers, json=payload, stream=True, timeout=35)
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail=f"Inworld TTS API error ({res.status_code}): {res.text}")

        audio_chunks = []
        for line in res.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    b64_audio = data.get("result", {}).get("audioContent", "")
                    if b64_audio:
                        audio_chunks.append(base64.b64decode(b64_audio))
                except Exception:
                    continue

        if not audio_chunks:
            raise HTTPException(status_code=502, detail="No audio stream returned from Inworld TTS.")

        return b"".join(audio_chunks)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Inworld TTS request failed: {exc}")


HINGLISH_TTS_CONFIG = {
    "api_key": os.getenv("HINGLISH_TTS_API_KEY", os.getenv("CARTESIA_API_KEY", "")),
    "provider": "inworld",
    "model_id": "sonic-3.6",
    "voice_id": "4459a9a5-69d6-4680-b970-e13dc51845b6",
    "language": "hi",
    "custom_url": ""
}


@app.get("/tts/voices")
@app.get("/api/v1/tts/voices")
async def get_available_tts_voices():
    """Returns available voice synthesis catalog."""
    return {
        "provider": "inworld",
        "default_voice": INWORLD_TTS_CONFIG.get("default_voice_id", "Sarah"),
        "voices": INWORLD_VOICES
    }


@app.post("/tts")
async def tts_endpoint(data: dict):
    """Synthesize text into speech using Inworld AI or configured ultra-realistic audio models."""
    text = (data.get("text") or "").strip()
    explicit_emotion = (data.get("emotion") or "").strip().lower()

    if not text:
        raise HTTPException(status_code=400, detail="Text parameter cannot be empty.")

    req_provider = (data.get("provider") or "").lower().strip()
    req_voice = (data.get("voice_id") or data.get("voice") or "").strip()
    req_model = (data.get("model") or "").strip()

    is_inworld = (
        req_provider == "inworld"
        or req_voice.startswith("inworld-")
        or (not req_provider and req_model != "ultra-realistic-hinglish")
        or (req_voice and req_model != "ultra-realistic-hinglish" and req_provider not in ("cartesia", "sarvam", "elevenlabs"))
    )

    if is_inworld:
        voice_to_use = req_voice or INWORLD_TTS_CONFIG.get("default_voice_id", "Sarah")
        audio_mp3 = synthesize_inworld_tts(text, voice_id=voice_to_use)
        return Response(content=audio_mp3, media_type="audio/mpeg")

    api_key = (HINGLISH_TTS_CONFIG.get("api_key") or "").strip()
    provider = (HINGLISH_TTS_CONFIG.get("provider") or "cartesia").lower().strip()

    if not api_key or api_key == "YOUR_API_KEY_HERE":
        audio_mp3 = synthesize_inworld_tts(text, voice_id="Sarah")
        return Response(content=audio_mp3, media_type="audio/mpeg")

    def _detect_tts_language(t: str) -> str:
        devanagari = re.findall(r'[\u0900-\u097F]', t)
        words = t.split()
        english_words = sum(1 for w in words if re.fullmatch(r'[a-zA-Z0-9\'\-.,!?]+', w))
        ratio = english_words / max(len(words), 1)
        if devanagari:
            return "hi"
        if ratio >= 0.90:
            return "en"
        return "hi"

    # 1. Cartesia Provider
    if provider == "cartesia":
        headers = {
            "X-API-Key": api_key,
            "Cartesia-Version": "2026-08-14",
            "Content-Type": "application/json"
        }

        segments = parse_script_emotion_segments(text[:4000])
        wav_audio_chunks = []

        for spoken_text, parsed_emotion in segments:
            target_emotion = explicit_emotion or EMOTION_MAP.get(parsed_emotion, "neutral")
            tts_language = _detect_tts_language(spoken_text)

            payload = {
                "model_id": HINGLISH_TTS_CONFIG.get("model_id") or "sonic-multilingual",
                "transcript": spoken_text,
                "voice": {
                    "mode": "id",
                    "id": HINGLISH_TTS_CONFIG.get("voice_id") or "faf0731e-dfb9-4cfc-8119-259a79b27e12"
                },
                "language": tts_language,
                "output_format": {
                    "container": "wav",
                    "encoding": "pcm_s16le",
                    "sample_rate": 44100
                },
                "generation_config": {
                    "speed": 1.0,
                    "volume": 1.0,
                    "emotion": target_emotion
                }
            }

            try:
                res = requests.post("https://api.cartesia.ai/tts/bytes", headers=headers, json=payload, timeout=25)
                if res.status_code == 200 and len(res.content) > 0:
                    wav_audio_chunks.append(res.content)
                elif res.status_code == 401:
                    raise HTTPException(status_code=401, detail="Cartesia API Key is invalid or unauthorized.")
                else:
                    print(f"[Cartesia TTS Warning] Segment synthesis failed ({res.status_code}): {res.text}")
            except HTTPException:
                raise
            except Exception as exc:
                print(f"[Cartesia TTS Warning] Failed segment synthesis request: {exc}")

        if wav_audio_chunks:
            final_wav = combine_wav_audio_chunks(wav_audio_chunks)
            return Response(content=final_wav, media_type="audio/wav")
        else:
            raise HTTPException(status_code=502, detail="Cartesia TTS synthesis failed. Check key validity and balance.")

    # 2. Sarvam AI Provider
    elif provider == "sarvam":
        headers = {
            "api-subscription-key": api_key,
            "Content-Type": "application/json"
        }
        clean_text = text[:500].replace("*", "").strip()
        payload = {
            "inputs": [clean_text],
            "target_language_code": HINGLISH_TTS_CONFIG.get("language") or "hi-IN",
            "speaker": HINGLISH_TTS_CONFIG.get("voice_id") or "meera",
            "model": HINGLISH_TTS_CONFIG.get("model_id") or "bulbul:v1",
            "pace": 1.0,
            "speech_sample_rate": 22050,
            "enable_preprocessing": True
        }
        try:
            res = requests.post("https://api.sarvam.ai/text-to-speech", headers=headers, json=payload, timeout=25)
            if res.status_code == 200:
                data = res.json()
                audios = data.get("audios", [])
                if audios:
                    audio_bytes = base64.b64decode(audios[0])
                    return Response(content=audio_bytes, media_type="audio/wav")
            if res.status_code in (401, 403):
                raise HTTPException(status_code=401, detail="Sarvam AI API key is invalid or unauthorized.")
            raise HTTPException(status_code=res.status_code, detail=f"Sarvam AI error: {res.text}")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Sarvam AI TTS request failed: {exc}")

    # 3. ElevenLabs Provider
    elif provider == "elevenlabs":
        voice_id = HINGLISH_TTS_CONFIG.get("voice_id") or "21m00Tcm4TlvDq8ikWAM"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text[:2000],
            "model_id": HINGLISH_TTS_CONFIG.get("model_id") or "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}
        }
        try:
            res = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}", headers=headers, json=payload, timeout=30)
            if res.status_code == 200 and len(res.content) > 0:
                return Response(content=res.content, media_type="audio/mpeg")
            if res.status_code in (401, 403):
                raise HTTPException(status_code=401, detail="ElevenLabs API Key is invalid or unauthorized.")
            raise HTTPException(status_code=res.status_code, detail=f"ElevenLabs error: {res.text}")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"ElevenLabs TTS request failed: {exc}")

    # 4. Custom API Provider
    else:
        custom_url = HINGLISH_TTS_CONFIG.get("custom_url")
        if not custom_url:
            raise HTTPException(status_code=400, detail="Custom provider selected but 'custom_url' is not configured.")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "voice": HINGLISH_TTS_CONFIG.get("voice_id"),
            "language": HINGLISH_TTS_CONFIG.get("language")
        }
        try:
            res = requests.post(custom_url, headers=headers, json=payload, timeout=25)
            if res.status_code == 200:
                return Response(content=res.content, media_type=res.headers.get("content-type", "audio/wav"))
            raise HTTPException(status_code=res.status_code, detail=f"Custom TTS error: {res.text}")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Custom TTS request failed: {exc}")


@app.post("/api/v1/speech/synthesize")
async def synthesize_speech(
    text: str = Form(..., description="Text to synthesize into spoken audio")
) -> dict[str, Any]:
    """Synthesize speech metadata (returns Web Speech API / TTS routing guidance)."""
    clean_text = text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Text parameter cannot be empty.")
    return {
        "status": "ready",
        "text": clean_text,
        "backend": "inworld_ai",
        "message": "Use /tts for studio voice synthesis."
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
        conversations.append({
            "id": r["id"],
            "title": r["title"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "attachments": json.loads(r["attachments_json"])
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
            print(f"Supabase detail warning, falling back to SQLite: {exc}")

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

    return {
        "id": row["id"],
        "title": row["title"],
        "messages": json.loads(row["messages_json"]),
        "attachments": json.loads(row["attachments_json"])
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
