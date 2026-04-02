"""
core/config.py — Single source of truth for all config.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# ── BASE PATHS ────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR   = BASE_DIR / "data"
MEMORY_DIR = BASE_DIR / "memory"

OUTPUT_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
MEMORY_DIR.mkdir(exist_ok=True)

# ── QUEUE ─────────────────────────────────────────────────────────────────────
QUEUE_FILE  = DATA_DIR / "queue.json"
TRENDS_FILE = DATA_DIR / "trends.json"

# ── MEMORY ────────────────────────────────────────────────────────────────────
BEST_PERFORMANCE_FILE = MEMORY_DIR / "best_performance.json"
FAILED_CASES_FILE     = MEMORY_DIR / "failed_cases.json"

# ── API KEYS ──────────────────────────────────────────────────────────────────
GROQ_API_KEY       = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY     = os.environ.get("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

# ── API URLS ──────────────────────────────────────────────────────────────────
GROQ_URL   = "https://api.groq.com/openai/v1"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ── MODELS ────────────────────────────────────────────────────────────────────
GROQ_MODEL         = "llama-3.3-70b-versatile"
GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"

# ── SCRIPT ────────────────────────────────────────────────────────────────────
# Character is locked to "the auditor" in script_agent.py
SCRIPT_TEMPERATURE = 0.92
TARGET_DURATION    = 61

# ── VOICE ─────────────────────────────────────────────────────────────────────
TTS_VOICE  = os.environ.get("TTS_VOICE", "en-US-AndrewNeural")
TTS_RATE   = os.environ.get("TTS_RATE",  "-5%")
TTS_VOLUME = os.environ.get("TTS_VOLUME", "+0%")

# ── VISUAL ────────────────────────────────────────────────────────────────────
IMAGE_WIDTH   = 720
IMAGE_HEIGHT  = 1280
IMAGE_MODEL   = "flux"
STYLE_PREFIX  = (
    "cinematic dark aesthetic, moody lighting, high contrast, "
    "digital art, 4k quality, no text, no watermark, "
)

# The auditor visual style — always applied
AUDITOR_VISUAL_STYLE = (
    "forensic cold light, institutional spaces, long shadows, "
    "grain film texture, no people or blurred background figures only, "
)

# ── VIDEO ─────────────────────────────────────────────────────────────────────
VIDEO_WIDTH         = 720
VIDEO_HEIGHT        = 1280
VIDEO_FPS           = 30
SUBTITLE_FONT_SIZE  = 28
SUBTITLE_FONT_COLOR = "white"
SUBTITLE_BOX_COLOR  = "black@0.6"

# ── QC ────────────────────────────────────────────────────────────────────────
QC_N_FRAMES    = 2
QC_FRAME_DELAY = 15


def validate():
    missing = []
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if missing:
        print(f"[config] WARNING: Missing env vars: {', '.join(missing)}")
    return len(missing) == 0

