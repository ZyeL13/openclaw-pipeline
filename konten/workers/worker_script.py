"""
workers/worker_script.py — Script worker.
Handles retries, file saving, logging.
"""

import json
import logging
import time
from pathlib import Path
from datetime import datetime

from agents.script_agent import generate_script, to_script_output

log = logging.getLogger("worker.script")

MAX_ATTEMPTS    = 3
MIN_WORDS_TOTAL = 100
MIN_WORDS_SCENE = 25
RETRY_DELAY     = 20  # seconds — Groq rate limit buffer


def validate_word_count(script_data: dict) -> tuple[bool, str]:
    scenes      = script_data.get("scenes", [])
    total_words = sum(len(s.get("text", "").split()) for s in scenes)
    short       = [s["id"] for s in scenes
                   if len(s.get("text", "").split()) < MIN_WORDS_SCENE]

    if total_words < MIN_WORDS_TOTAL:
        return False, f"total {total_words} words (need {MIN_WORDS_TOTAL}+)"
    if short:
        return False, f"scenes {short} below {MIN_WORDS_SCENE} words"
    return True, "ok"


def run(headline: str, tone: int, run_dir: Path) -> dict | None:
    """
    Generate script and save to run_dir.
    tone param kept for API compatibility but ignored — locked to the auditor.
    Returns script_data dict or None on failure.
    """
    script_file = run_dir / "script_output.json"

    best        = None
    best_words  = 0

    for attempt in range(MAX_ATTEMPTS):
        if attempt > 0:
            log.info(f"Waiting {RETRY_DELAY}s before retry...")
            time.sleep(RETRY_DELAY)

        log.info(f"Generating script attempt {attempt+1}/{MAX_ATTEMPTS}")
        raw = generate_script(headline)

        if not raw:
            log.warning(f"Generation returned None — attempt {attempt+1}")
            continue

        script_data = to_script_output(raw)
        total_words = sum(len(s.get("text","").split())
                         for s in script_data.get("scenes", []))

        # Track best result regardless
        if total_words > best_words:
            best       = script_data
            best_words = total_words

        ok, reason = validate_word_count(script_data)
        if ok:
            log.info(f"Word count OK ({total_words} words) on attempt {attempt+1}")
            best = script_data
            break
        else:
            log.warning(f"Word count: {reason} — best so far: {best_words}")

    if not best:
        log.error("All attempts failed")
        return None

    if best_words < MIN_WORDS_TOTAL:
        log.warning(f"Using best available: {best_words} words (below target)")

    with open(script_file, "w", encoding="utf-8") as f:
        json.dump(best, f, ensure_ascii=False, indent=2)

    log.info(f"Saved → {script_file.name}  words={best_words}")
    return best

