"""Layer 0: Global configuration parameters for Curiosity AI."""

from __future__ import annotations

import os
from pathlib import Path
import torch
from dotenv import load_dotenv

load_dotenv()

# Project Paths
BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
HF_CACHE_DIR = BASE_DIR / "hf_cache"

# Hardware Device Selection
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Deep Learning Models Configuration
YOLO_MODEL_NAME = "yolo11n.pt"  # Ultralytics YOLOv11 nano model
RESNET_TOP_K = 5
YOLO_CONFIDENCE_THRESHOLD = 0.25

# OCR Configuration
EASYOCR_LANGUAGES = ["en", "hi"]
EASYOCR_GPU = torch.cuda.is_available()

# Ollama / Local LLM Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_CHAT_URL = f"{OLLAMA_BASE_URL}/api/chat"
DEFAULT_TEXT_MODEL = os.getenv("DEFAULT_TEXT_MODEL", "qwen2.5:1.5b")
DEFAULT_VISION_MODEL = os.getenv("DEFAULT_VISION_MODEL", "qwen2.5vl:3b")

# Sarvam AI TTS Configuration
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", os.getenv("SARVAM_API_SUBSCRIPTION_KEY", "sk_ifnmvwzp_6GQ219edjduibgcIRX3QxiV2"))
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_DEFAULT_VOICE = os.getenv("SARVAM_DEFAULT_VOICE", "ritu")
SARVAM_DEFAULT_MODEL = os.getenv("SARVAM_MODEL", "bulbul:v3")

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# SQLite Local Database
SQLITE_DB_PATH = DATA_DIR / "assistant.db"
