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
