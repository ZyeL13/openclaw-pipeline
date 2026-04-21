"""
agents/script_agent.py — Pure script generation logic.
Priority: Groq API → ClawRouter free models (fallback)
"""
import json
import logging
import random
import requests
from pathlib import Path
from core.config import (
    SCRIPT_TEMPERATURE, SCRIPT_MIN_WORDS_TOTAL, SCRIPT_MAX_WORDS_TOTAL, SCRIPT_MAX_WORDS_SCENE
)

log = logging.getLogger("agent.script")
SCRIPT_MAX_TOKENS = 2500

# ── VOICE & STYLE (unchanged, keys cleaned) ───────────────────────────────
CHANNEL_VOICE = """
You are "the auditor" — someone who has reviewed the books
of civilizations and found them all, eventually, fraudulent.
"""

SCENE_STRUCTURE = """
MANDATORY SCENE PROGRESSION — this is the architecture of every script:
Scene 1 — INTRODUCE (15s, 4-6 words): State the fact. Cold.
Scene 2 — DOUBT / CONFLICT (15s, 4-6 words): The gap.
Scene 3 — TWIST / ABSURDITY PEAKS (16s, 5-7 words): The reframe.
Scene 4 — PUNCHLINE (15s, 4-6 words): One verdict. Close the case.
"""

# ── SYSTEM PROMPT with HARD WORD LIMIT ─────────────────────────────────────
SYSTEM_PROMPT = f"""
{CHANNEL_VOICE}
{SCENE_STRUCTURE}
[CONSTRAINT — NON-NEGOTIABLE]
- Total narration MUST be between {SCRIPT_MIN_WORDS_TOTAL} and {SCRIPT_MAX_WORDS_TOTAL} words.
- Per scene MAX {SCRIPT_MAX_WORDS_SCENE} words.
- If exceeding, CUT sentences. Do NOT add content.
- Output ONLY valid JSON, no markdown, no explanation.

JSON FORMAT:
{{
  "headline": "...",
  "hook": "...",
  "scenes": [
    {{"id": 1, "text": "...", "visual": "...", "duration": 15, "beat": "introduce"}},
    {{"id": 2, "text": "...", "visual": "...", "duration": 15, "beat": "doubt"}},
    {{"id": 3, "text": "...", "visual": "...", "duration": 16, "beat": "twist"}},
    {{"id": 4, "text": "...", "visual": "...", "duration": 15, "beat": "punchline"}}
  ],
  "cta": "...",
  "caption": "...",
  "hashtags": ["...", "..."],
  "total_duration": 61
}}
"""

def _load_practices_context() -> str:
    practices_file = Path(__file__).parent.parent / "memory" / "best_practices.json"
    if not practices_file.exists():
        return ""
    try:
        p = json.loads(practices_file.read_text())
        avoid = str(p.get("avoid", [])[:3])
        tips = str(p.get("script_instructions", [])[:3])
        if avoid or tips:
            return f"\nLEARNED FROM PAST VIDEOS:\nAvoid: {avoid}\nDo: {tips}\n"
    except Exception as e:
        log.warning(f"Failed to load best_practices: {e}")
    return ""

def _call_api(url: str, headers: dict, payload: dict) -> dict | None:
    try:
        resp = requests.post(
            f"{url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        log.warning(f"  Connection error: {e}")
        return None
    
    if resp.status_code == 429:
        log.warning("  Rate limit (429)")
        return None
    if resp.status_code != 200:
        log.warning(f"  HTTP {resp.status_code}: {resp.text[:100]}")
        return None

    try:
        choice = resp.json()["choices"][0]
        raw = choice["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        result = json.loads(raw)
        total = sum(len(s.get("text", "").split()) for s in result.get("scenes", []))
        log.info(f"  Parsed OK — {total} words total")
        return result
    except Exception as e:
        log.warning(f"  Parse error: {e}")
        return None

def generate_script(headline: str) -> dict | None:
    """Generate script with scene progression + word limit enforcement."""
    practices_context = _load_practices_context()
    seed = random.randint(1, 999999)
    
    user_content = (
        f"Headline: {headline}\n\n"
        f"{practices_context}"
        f"Write the script as the auditor.\n\n"
        f"MANDATORY progression:\n"
        f"  Scene 1 (introduce): State the fact. Cold. No editorializing.\n"
        f"  Scene 2 (doubt): The gap. What doesn't add up.\n"
        f"  Scene 3 (twist): The reframe. Say what nobody says out loud.\n"
        f"  Scene 4 (punchline): One verdict. Close the case file. Make it land.\n\n"
        f"WORD LIMIT (HARD CONSTRAINT):\n"
        f"  - Total: between {SCRIPT_MIN_WORDS_TOTAL} and {SCRIPT_MAX_WORDS_TOTAL} words\n"
        f"  - Per scene: MAX {SCRIPT_MAX_WORDS_SCENE} words\n"
        f"  - If exceeding, CUT. Do not add.\n"
    )

    base_payload = {
        "max_tokens": SCRIPT_MAX_TOKENS,
        "temperature": SCRIPT_TEMPERATURE,
        "seed": seed,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]
    }

    # Try Groq first, then fallback
    from core.config import get_llm_config
    for use_fallback in [False, True]:
        base_url, model, api_key = get_llm_config(use_fallback=use_fallback)
        provider = "ClawRouter" if use_fallback else "Groq"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {**base_payload, "model": model}
        log.info(f"Trying {provider} API ({model})...")
        result = _call_api(base_url, headers, payload)
        if result:
            log.info(f"Success via {provider}")
            return result
        if not use_fallback:
            log.warning(f"{provider} failed — trying fallback")
    
    log.error("All providers failed")
    return None

def to_script_output(raw: dict) -> dict:
    """Convert raw LLM output to pipeline format (keys cleaned)."""
    return {
        "topic": raw.get("headline", ""),
        "platform": ["tiktok", "ig_reels", "yt_shorts"],
        "total_duration": raw.get("total_duration", 61),
        "hook": raw.get("hook", ""),
        "scenes": raw.get("scenes", []),
        "cta": raw.get("cta", ""),
        "caption": {
            "tiktok": raw.get("caption", ""),
            "ig_reels": raw.get("caption", ""),
            "yt_shorts": raw.get("caption", "")
        },
        "hashtags": raw.get("hashtags", []),
        "_source": {
            "tone": "the auditor",
            "variation": 1
        }
    }
