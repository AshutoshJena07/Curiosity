"""Script Performance & Audio Production Engine with 24-Hour Quota Governance.

Features:
1. Generates studio-grade neural audio recordings when a user submits a script.
2. Enforces a strict quota limit of 500 words per user per rolling 24-hour window.
3. Automatically resets/replenishes words as past performances age past 24 hours.
4. Provides clear, informative quota tracking, usage statistics, and alerts in proper English.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
import re
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.curiosity.layer_0_core.config import SQLITE_DB_PATH

logger = logging.getLogger("curiosity.script_performer")

AUDIO_OUTPUT_DIR = Path(__file__).resolve().parents[3] / "data" / "generated_audio"
AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DAILY_WORD_QUOTA = 500
QUOTA_WINDOW_HOURS = 24

PERFORMANCE_TRIGGERS = [
    "perform this",
    "peform this",
    "preform this",
    "perform this script",
    "peform this script",
    "perform script",
    "peform script",
    "perform the script",
    "perform it",
    "peform it",
    "perform",
    "peform",
    "voice this",
    "voice this script",
    "voice the script",
    "narrate this",
    "narrate this script",
    "narrate the script",
    "act this out",
    "act out this script",
    "read this script",
    "read this",
    "dramatize this",
    "voiceover",
    "voice over",
    "produce audio",
    "generate audio",
    "record this script",
    "audio performance",
    "speak this script",
    "speak this"
]


# =====================================================================
# QUOTA PERSISTENCE & ROLLING 24-HOUR TRACKING
# =====================================================================

def get_db_connection() -> sqlite3.Connection:
    SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH, timeout=20.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_quota_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS script_performance_quotas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                words_count INTEGER NOT NULL,
                performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_quotas_user_time 
            ON script_performance_quotas (user_id, performed_at);
        """)
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning(f"Quota DB init warning: {exc}")


def get_user_quota_usage(user_id: str) -> Tuple[int, int, Optional[str]]:
    """
    Calculates rolling 24-hour quota usage.
    Returns: (used_words_in_24h, remaining_words, earliest_performed_at)
    """
    init_quota_db()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT COALESCE(SUM(words_count), 0), MIN(performed_at)
            FROM script_performance_quotas
            WHERE user_id = ?
              AND performed_at >= datetime('now', '-24 hours')
        """, (str(user_id),))
        row = cur.fetchone()
        used = int(row[0]) if row and row[0] is not None else 0
        earliest_time = row[1] if row and row[1] else None
        conn.close()
        remaining = max(0, DAILY_WORD_QUOTA - used)
        return used, remaining, earliest_time
    except Exception as exc:
        logger.warning(f"Error checking user quota: {exc}")
        return 0, DAILY_WORD_QUOTA, None


def record_quota_consumption(user_id: str, words_count: int):
    """Logs words consumed for a successful script performance."""
    init_quota_db()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO script_performance_quotas (user_id, words_count, performed_at)
            VALUES (?, ?, datetime('now'))
        """, (str(user_id), words_count))
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning(f"Error logging quota consumption: {exc}")


# =====================================================================
# SCRIPT PARSING & AUDIT LOGIC
# =====================================================================

def is_quota_inquiry(prompt: str) -> bool:
    """Check if user is asking about their quota limit or remaining balance."""
    low = (prompt or "").lower().strip()
    return any(p in low for p in [
        "script quota", "quota limit", "how many words left",
        "remaining words", "script limit", "24 hours limit", "word limit",
        "check quota", "quota status", "remaining quota", "voice quota",
        "audio quota", "daily quota", "daily limit", "performance quota"
    ])


def is_script_performance_request(prompt: str, has_doc_text: bool = False) -> bool:
    """Detect whether user prompt asks to perform/voice a script or check quota."""
    low = (prompt or "").lower().strip()
    if not low:
        return False
    if is_quota_inquiry(low):
        return True
    return any(trigger in low for trigger in PERFORMANCE_TRIGGERS)


def extract_script_content(user_prompt: str, document_text: str = "") -> str:
    """Extract the raw script text from user prompt or active document."""
    prompt = (user_prompt or "").strip()
    
    # Check if prompt contains the script directly
    for trigger in PERFORMANCE_TRIGGERS:
        pattern = rf"(?i)^{re.escape(trigger)}\s*[:\-\n]\s*(.+)$"
        match = re.search(pattern, prompt, re.DOTALL)
        if match:
            extracted = match.group(1).strip()
            if len(extracted) > 10:
                return extracted

    # If prompt itself has substantial length and contains dialogue markers
    dialogue_markers = ["character", "scene", "act ", "dialogue", "narrator:", "host:", "speaker:"]
    if len(prompt) > 80 and any(m in prompt.lower() for m in dialogue_markers):
        clean = re.sub(
            rf"(?i)^(?:please\s+)?(?:{'|'.join(re.escape(t) for t in PERFORMANCE_TRIGGERS)})\s*[:\-,\n]*\s*",
            "",
            prompt
        ).strip()
        if len(clean) > 20:
            return clean

    # If a document was attached or in session memory, use document text
    if document_text and len(document_text.strip()) > 20:
        return document_text.strip()

    # Fallback to whatever remaining text is in the prompt
    clean_fallback = re.sub(
        rf"(?i)^(?:please\s+)?(?:{'|'.join(re.escape(t) for t in PERFORMANCE_TRIGGERS)})\s*[:\-,\n]*\s*",
        "",
        prompt
    ).strip()
    return clean_fallback or prompt


def clean_script_for_speech(script: str) -> str:
    """Clean script formatting so stage directions are not spoken aloud awkwardly."""
    cleaned = re.sub(r"\[.*?\]", " ", script)
    cleaned = re.sub(r"\(.*?\)", " ", cleaned)
    cleaned = re.sub(r"[#*_~`>]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


async def generate_speech_audio_async(
    text: str,
    voice: str = "en-IN-NeerjaExpressiveNeural"
) -> Tuple[str, str, float]:
    """Generate MP3 audio file using edge-tts."""
    import edge_tts

    audio_id = uuid.uuid4().hex[:12]
    filename = f"performance_{audio_id}.mp3"
    file_path = AUDIO_OUTPUT_DIR / filename

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(file_path))

    words = len(text.split())
    approx_duration = max(2.0, round((words / 140.0) * 60.0, 1))

    relative_url = f"/api/v1/audio/{filename}"
    return filename, relative_url, approx_duration


EMOTION_CONFIGS = {
    "neutral": {"temperature": 0.60, "pace_multiplier": 1.00, "label": "Natural & Balanced"},
    "cheerful": {"temperature": 0.85, "pace_multiplier": 1.05, "label": "Happy & Cheerful"},
    "excited": {"temperature": 0.95, "pace_multiplier": 1.12, "label": "Excited & Vibrant"},
    "calm": {"temperature": 0.50, "pace_multiplier": 0.90, "label": "Calm & Gentle"},
    "empathetic": {"temperature": 0.65, "pace_multiplier": 0.92, "label": "Empathetic & Caring"},
    "dramatic": {"temperature": 0.92, "pace_multiplier": 0.96, "label": "Dramatic & Storyteller"},
    "professional": {"temperature": 0.35, "pace_multiplier": 1.00, "label": "Formal & Professional"},
    "urgent": {"temperature": 0.80, "pace_multiplier": 1.18, "label": "Urgent & High-Energy"},
    "somber": {"temperature": 0.45, "pace_multiplier": 0.85, "label": "Somber & Reflective"},
    "curious": {"temperature": 0.78, "pace_multiplier": 1.02, "label": "Curious & Inquisitive"},
}


def detect_script_emotion(text: str) -> str:
    """Detect emotion from prompt instructions or script mood cues."""
    low = (text or "").lower()
    if any(k in low for k in ["excited", "josh", "utsah", "enthusiastic", "celebrat", "energetic"]):
        return "excited"
    if any(k in low for k in ["happy", "cheerful", "khushi", "hasi", "glad", "joy"]):
        return "cheerful"
    if any(k in low for k in ["dramatic", "drama", "story", "theatrical", "natak", "act ", "acting"]):
        return "dramatic"
    if any(k in low for k in ["sad", "somber", "dukhi", "cry", "melancholy", "heartbreak"]):
        return "somber"
    if any(k in low for k in ["calm", "gentle", "peaceful", "shanti", "relax", "sooth"]):
        return "calm"
    if any(k in low for k in ["empathetic", "caring", "dard", "sympathy", "compassion"]):
        return "empathetic"
    if any(k in low for k in ["urgent", "fast", "emergency", "hurry", "alert"]):
        return "urgent"
    if any(k in low for k in ["professional", "formal", "corporate", "news", "official"]):
        return "professional"
    if any(k in low for k in ["curious", "question", "sawal", "mystery"]):
        return "curious"
    return "neutral"


def generate_sarvam_audio(
    text: str,
    speaker: str = "ritu",
    emotion: str = "neutral",
    base_pace: float = 1.0
) -> Tuple[str, str, float]:
    """Generate studio MP3 audio file using Sarvam AI bulbul:v3 with rich emotion control."""
    from src.curiosity.layer_0_core.config import SARVAM_API_KEY, SARVAM_DEFAULT_MODEL
    api_key = SARVAM_API_KEY or "sk_ifnmvwzp_6GQ219edjduibgcIRX3QxiV2"

    from sarvamai import SarvamAI
    client = SarvamAI(api_subscription_key=api_key)

    audio_id = uuid.uuid4().hex[:12]
    filename = f"performance_{audio_id}.mp3"
    file_path = AUDIO_OUTPUT_DIR / filename

    # Language code strictly conditioned for high-fidelity natural prosody
    target_lang = "hi-IN"

    cfg = EMOTION_CONFIGS.get(emotion, EMOTION_CONFIGS["neutral"])
    temperature = cfg.get("temperature", 0.60)
    pace = max(0.5, min(2.0, round(base_pace * cfg.get("pace_multiplier", 1.0), 2)))

    # Apply emotional prosodic punctuation
    speech_text = text.strip()
    if emotion in ("cheerful", "excited") and speech_text and speech_text[-1] not in ".!?":
        speech_text += "!"
    elif emotion in ("calm", "somber", "dramatic"):
        speech_text = re.sub(r',\s+', '... ', speech_text)

    stream = client.text_to_speech.convert_stream(
        text=speech_text,
        language_code=target_lang,
        speaker=speaker,
        model=SARVAM_DEFAULT_MODEL or "bulbul:v3",
        pace=pace,
        temperature=temperature,
        speech_sample_rate=24000,
        output_audio_codec="mp3"
    )
    with open(file_path, "wb") as f:
        for chunk in stream:
            f.write(chunk)

    words = len(text.split())
    approx_duration = max(2.0, round((words / 140.0) * 60.0, 1))
    relative_url = f"/api/v1/audio/{filename}"
    return filename, relative_url, approx_duration


def _run_in_isolated_thread(coro_fn, *args):
    """Safely execute an async coroutine factory in a dedicated thread to prevent event loop collision."""
    def worker():
        return asyncio.run(coro_fn(*args))

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(worker).result()


def execute_script_performance(
    prompt: str,
    document_text: str = "",
    preferred_voice: Optional[str] = None,
    user_id: Optional[str] = None,
    emotion: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute script performance governed by a 500-word per 24-hour quota.
    """
    effective_user_id = str(user_id or "default_user")

    # ── 1. Check for Quota Balance Inquiry ──
    if is_quota_inquiry(prompt):
        used_words, remaining_words, earliest_performed = get_user_quota_usage(effective_user_id)
        narrative = (
            f"### Script Performance Quota Status\n\n"
            f"Here is your current 24-hour neural voice performance allowance:\n\n"
            f"- **Daily Allowance:** **{DAILY_WORD_QUOTA} words** per 24-hour rolling window\n"
            f"- **Words Consumed in Last 24 Hours:** **{used_words} words**\n"
            f"- **Available Balance Right Now:** **{remaining_words} words**\n\n"
            f"---\n\n"
            f"You may submit scripts totaling up to **{remaining_words} words** for immediate audio generation."
        )
        return {
            "success": True,
            "answer": narrative,
            "audio_url": None,
            "audio_filename": None,
            "duration": 0.0,
            "script_title": "Quota Status",
            "voice": preferred_voice or "en-IN-NeerjaExpressiveNeural"
        }

    # ── 2. Parse and Count Script Words ──
    raw_script = extract_script_content(prompt, document_text)
    if not raw_script:
        raw_script = "Curiosity stands ready to perform your script. Please provide the script text."

    clean_speech = clean_script_for_speech(raw_script)
    script_words = len(clean_speech.split())

    # ── 3. Evaluate 24-Hour Word Quota ──
    used_words, remaining_words, earliest_performed = get_user_quota_usage(effective_user_id)

    # Scenario A: Daily Quota Already Fully Exhausted
    if used_words >= DAILY_WORD_QUOTA:
        narrative = (
            f"### 24-Hour Script Performance Quota Limit Reached\n\n"
            f"You have reached your daily allowance limit for neural script performance (**500 words per 24 hours**).\n\n"
            f"- **Current 24-Hour Usage:** **{used_words} / {DAILY_WORD_QUOTA} words used**\n"
            f"- **Remaining Available Quota:** **0 words**\n"
            f"- **Quota Reset Window:** 24-hour rolling replenishment\n\n"
            f"---\n\n"
            f"Your allowance automatically replenishes 24 hours after each performed recording. "
            f"Please wait for your 24-hour window to refresh before generating further audio performances."
        )
        return {
            "success": False,
            "quota_exceeded": True,
            "answer": narrative,
            "audio_url": None,
            "audio_filename": None,
            "duration": 0.0,
            "script_title": "Quota Exceeded",
            "voice": preferred_voice or "en-IN-NeerjaExpressiveNeural"
        }

    # Scenario B: Submitted Script Exceeds Remaining Words
    if (used_words + script_words) > DAILY_WORD_QUOTA:
        excess = (used_words + script_words) - DAILY_WORD_QUOTA
        narrative = (
            f"### Script Length Exceeds Remaining 24-Hour Quota\n\n"
            f"Your submitted script contains **{script_words} words**, which exceeds your available quota allowance for this 24-hour window.\n\n"
            f"- **Available Quota Balance:** **{remaining_words} words** (out of {DAILY_WORD_QUOTA} words / 24 hours)\n"
            f"- **Submitted Script Length:** **{script_words} words**\n"
            f"- **Excess Word Count:** **{excess} words over limit**\n\n"
            f"---\n\n"
            f"**Recommended Action:**\n"
            f"Please shorten or excerpt your script to **{remaining_words} words or fewer** to generate audio immediately, "
            f"or wait for your rolling 24-hour allowance to refresh."
        )
        return {
            "success": False,
            "quota_exceeded": True,
            "answer": narrative,
            "audio_url": None,
            "audio_filename": None,
            "duration": 0.0,
            "script_title": "Quota Exceeded",
            "voice": preferred_voice or "en-IN-NeerjaExpressiveNeural"
        }

    # ── 4. Quota Approved: Execute Audio Generation ──
    from src.curiosity.layer_0_core.config import SARVAM_API_KEY
    actor_label = "Ritu (Female)"

    try:
        if SARVAM_API_KEY:
            # 1. Resolve speaker: prompt explicit keywords first, then user's selected voice setting
            if any(k in prompt.lower() for k in ["shubh", "male", "deep voice", "boy", "man"]):
                speaker = "shubh"
            elif any(k in prompt.lower() for k in ["ritu", "priya", "female", "girl", "woman", "lady"]):
                speaker = "ritu"
            elif preferred_voice and "shubh" in str(preferred_voice).lower():
                speaker = "shubh"
            else:
                speaker = "ritu"

            # 2. Resolve emotion: prompt explicit keywords first, then user's selected emotion setting
            detected_emo = detect_script_emotion(prompt)
            final_emotion = detected_emo if detected_emo != "neutral" else (emotion or "neutral")
            emotion_label = EMOTION_CONFIGS.get(final_emotion, {}).get("label", "Natural & Balanced")
            actor_label = f"{speaker.capitalize()} ({emotion_label})"
            filename, audio_url, duration = generate_sarvam_audio(clean_speech, speaker, emotion=final_emotion)
        else:
            voice = preferred_voice or "en-IN-NeerjaExpressiveNeural"
            if "male" in prompt.lower() or "deep voice" in prompt.lower():
                voice = "en-IN-PrabhatNeural"
            elif "narrator" in prompt.lower() or "dramatic" in prompt.lower():
                voice = "en-US-GuyNeural"
            actor_label = voice
            filename, audio_url, duration = _run_in_isolated_thread(
                generate_speech_audio_async, clean_speech, voice
            )
    except Exception as synth_err:
        logger.warning(f"Sarvam AI synthesis notice ({synth_err}), falling back to edge-tts...")
        voice = preferred_voice or "en-IN-NeerjaExpressiveNeural"
        actor_label = voice
        filename, audio_url, duration = _run_in_isolated_thread(
            generate_speech_audio_async, clean_speech, voice
        )

    # Deduct consumed words from user's quota
    record_quota_consumption(effective_user_id, script_words)
    new_remaining = max(0, remaining_words - script_words)

    # Derive a clean title from the script
    first_line = raw_script.split("\n")[0].strip()
    title = first_line[:45] if len(first_line) > 5 else "Script Performance Recording"
    title = re.sub(r"^[#*\-\s]+", "", title).strip()

    preview_snippet = "\n".join(raw_script.splitlines()[:6]).strip()
    if len(preview_snippet) > 300:
        preview_snippet = preview_snippet[:295] + "..."

    narrative = (
        f"### Audio Production & Script Performance\n\n"
        f"I have performed and rendered your script into a high-fidelity studio voice recording. "
        f"The audio output is embedded below with interactive playback and direct download options.\n\n"
        f"- **Production Title:** {title}\n"
        f"- **Performance Style:** Narrative Studio Drama\n"
        f"- **Voice Actor:** {actor_label}\n"
        f"- **Estimated Runtime:** ~{int(duration)} seconds\n"
        f"- **Script Length:** {script_words} words\n"
        f"- **24-Hour Quota Remaining:** {new_remaining} / {DAILY_WORD_QUOTA} words\n"
        f"- **Audio Format:** High-Definition MPEG Layer-3 (.mp3)\n\n"
        f"---\n\n"
        f"### Performed Script Excerpt\n"
        f"> {preview_snippet}\n"
    )

    return {
        "success": True,
        "answer": narrative,
        "audio_url": audio_url,
        "audio_filename": filename,
        "duration": duration,
        "script_title": title,
        "voice": actor_label,
        "script_words": script_words,
        "quota_remaining": new_remaining
    }
