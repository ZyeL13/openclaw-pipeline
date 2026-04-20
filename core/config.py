"""
core/config.py — Single source of truth for all pipeline config
"""

import os
from pathlib import Path

# ── PATHS ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent.parent
OUTPUT_DIR  = BASE_DIR / "output"
DATA_DIR    = BASE_DIR / "data"
MEMORY_DIR  = BASE_DIR / "memory"
ASSETS_DIR  = BASE_DIR / "assets"

QUEUE_FILE         = DATA_DIR / "queue.json"
BEST_PRACTICES     = MEMORY_DIR / "best_practices.json"
FAILED_CASES       = MEMORY_DIR / "failed_cases.json"
CHAIN_LOG          = MEMORY_DIR / "chain.log"

# ── LLM (Groq) ────────────────────────────────────────────────────────────────
LLM_BASE    = os.environ.get("GROQ_BASE",  "https://api.groq.com/openai/v1")
LLM_MODEL   = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
LLM_API_KEY = os.environ.get("GROQ_API_KEY")
LLM_TIMEOUT = 60
TIMEOUT = 60
# ── VISION QC ─────────────────────────────────────────────────────────────────
VISION_MODEL = "llama-3.2-11b-vision-preview"  # Groq vision model

# ── VOICE ─────────────────────────────────────────────────────────────────────
VOICE_LANG_DEFAULT = "id"    # id | en
VOICE_WPM_TARGET   = 80

# ── VIDEO ─────────────────────────────────────────────────────────────────────
VIDEO_WIDTH    = 720
VIDEO_HEIGHT   = 1280
VIDEO_DURATION = 15          # seconds (changed from 60)
VIDEO_FPS      = 30

# ── QC ────────────────────────────────────────────────────────────────────────
QC_PASS_SCORE  = 7.5
QC_MAX_RETRY   = 2
QC_N_FRAMES    = 2
QC_FRAME_DELAY = 5       # seconds between Groq vision calls (free tier safe)
TARGET_DURATION = VIDEO_DURATION

# ── PIPELINE ──────────────────────────────────────────────────────────────────
PIPELINE_STEPS = ["script", "visual", "voice", "qc", "edit"]

# ── BACKWARD COMPATIBILITY ALIASES ────────────────────────────────────────────
GROQ_API_KEY = LLM_API_KEY
GROQ_URL = LLM_BASE
GROQ_URL_PRIMARY = LLM_BASE
GROQ_URL_FALLBACK = LLM_BASE  # Same as primary for now
GROQ_MODEL_PRIMARY = LLM_MODEL
GROQ_MODEL_FALLBACKS = [LLM_MODEL]

# ── SCRIPT ────────────────────────────────────────────────────────────────────
SCRIPT_TEMPERATURE = 0.7
SCRIPT_MIN_WORDS_TOTAL = 100
SCRIPT_MIN_WORDS_SCENE = 20

# ── VISUAL ────────────────────────────────────────────────────────────────────
IMAGE_WIDTH = VIDEO_WIDTH
IMAGE_HEIGHT = VIDEO_HEIGHT
IMAGE_MODEL = "flux"  # Pollinations model
STYLE_PREFIX = "cinematic, professional photography, "
AUDITOR_VISUAL_STYLE = "cold institutional aesthetic, fluorescent lighting, precise composition"

# ── VOICE ─────────────────────────────────────────────────────────────────────
TTS_VOICE = "id-ID-ArdiNeural"  # Indonesian voice for Edge TTS
TTS_RATE = 1.0
TTS_VOLUME = 1.0

# ── EDIT ──────────────────────────────────────────────────────────────────────
SUBTITLE_FONT_SIZE = 24
SUBTITLE_FONT_COLOR = "white"
SUBTITLE_BOX_COLOR = "black"
CHAR_SCALE = 0.8
CHAR_OPACITY = 0.7
CHAR_POSITION = "bottom-right"
