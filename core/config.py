"""
core/config.py — Single source of truth for all pipeline config
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Auto-load .env dari root project
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── PATHS ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
OUTPUT_DIR  = BASE_DIR / "output"
DATA_DIR    = BASE_DIR / "data"
MEMORY_DIR  = BASE_DIR / "memory"
ASSETS_DIR  = BASE_DIR / "assets"
QUEUE_FILE         = DATA_DIR / "queue.json"
BEST_PRACTICES     = MEMORY_DIR / "best_practices.json"
FAILED_CASES       = MEMORY_DIR / "failed_cases.json"
CHAIN_LOG          = MEMORY_DIR / "chain.log"

# ── LLM (Groq + ClawRouter Fallback) ─────────────────────────────────────────
LLM_BASE_PRIMARY = os.environ.get("GROQ_BASE", "https://api.groq.com/openai/v1")
LLM_BASE_FALLBACK = os.environ.get("CLAWROUTER_BASE", "http://127.0.0.1:8402/v1")

# Model untuk Groq
LLM_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# Model untuk ClawRouter - pilih dari free models
# Available free models: 
# - free/gpt-oss-120b, free/gpt-oss-20b, free/nemotron-ultra-253b
# - free/nemotron-3-super-120b, free/nemotron-super-49b, free/deepseek-v3.2
# - free/mistral-large-3-675b, free/qwen3-coder-480b, free/devstral-2-123b
# - free/glm-4.7, free/llama-4-maverick
LLM_MODEL_FALLBACK = os.environ.get("CLAWROUTER_MODEL", "free/deepseek-v3.2")

LLM_API_KEY = os.environ.get("GROQ_API_KEY", "")
LLM_TIMEOUT = 60
TIMEOUT     = 60

# ── Helper: Return config berdasarkan provider ───────────────────────────────
def get_llm_config(use_fallback: bool = False) -> tuple:
    """Return (base_url, model, api_key) tuple based on fallback flag."""
    if use_fallback:
        return LLM_BASE_FALLBACK, LLM_MODEL_FALLBACK,
    return LLM_BASE_PRIMARY, LLM_MODEL, LLM_API_KEY

# ── VISION QC ─────────────────────────────────────────────────────────────────
VISION_MODEL = "llama-3.2-11b-vision-preview"

# ── VOICE ─────────────────────────────────────────────────────────────────────
VOICE_LANG_DEFAULT = "en"
VOICE_WPM_TARGET   = 80

# ── VIDEO ─────────────────────────────────────────────────────────────────────
VIDEO_WIDTH    = 720
VIDEO_HEIGHT   = 1280
VIDEO_DURATION = 15
VIDEO_FPS      = 30

# ── QC ────────────────────────────────────────────────────────────────────────
QC_PASS_SCORE  = 7.5
QC_MAX_RETRY   = 2
QC_N_FRAMES    = 2
QC_FRAME_DELAY = 5
TARGET_DURATION = VIDEO_DURATION

# ── PIPELINE ──────────────────────────────────────────────────────────────────
PIPELINE_STEPS = ["script", "visual", "voice", "qc", "edit"]

# ── BACKWARD COMPATIBILITY ALIASES ────────────────────────────────────────────
GROQ_API_KEY = LLM_API_KEY
GROQ_URL = LLM_BASE_PRIMARY
GROQ_URL_PRIMARY = LLM_BASE_PRIMARY
GROQ_URL_FALLBACK = LLM_BASE_FALLBACK
GROQ_MODEL_PRIMARY = LLM_MODEL
GROQ_MODEL_FALLBACKS = [LLM_MODEL_FALLBACK]

# ── SCRIPT ────────────────────────────────────────────────────────────────────
SCRIPT_TEMPERATURE = 0.7
SCRIPT_MIN_WORDS_TOTAL = 22      # FIX: sesuai durasi 15s @ 80 WPM
SCRIPT_MIN_WORDS_SCENE = 6

# ── VISUAL ────────────────────────────────────────────────────────────────────
IMAGE_WIDTH = VIDEO_WIDTH
IMAGE_HEIGHT = VIDEO_HEIGHT
IMAGE_MODEL = "flux-dev"
STYLE_PREFIX = "cinematic, professional photography, "
AUDITOR_VISUAL_STYLE = "cold institutional aesthetic, fluorescent lighting, precise composition"

# ── VOICE ─────────────────────────────────────────────────────────────────────
TTS_VOICE = "id-ID-ArdiNeural"
TTS_RATE = 1.0
TTS_VOLUME = 1.0

# ── EDIT ──────────────────────────────────────────────────────────────────────
SUBTITLE_FONT_SIZE = 24
SUBTITLE_FONT_COLOR = "white"
SUBTITLE_BOX_COLOR = "black"
CHAR_SCALE = 0.8
CHAR_OPACITY = 0.7
CHAR_POSITION = "bottom-right"
