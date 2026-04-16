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
    GROQ_API_KEY,
    GROQ_URL_PRIMARY, GROQ_URL_FALLBACK,
    GROQ_MODEL_PRIMARY, GROQ_MODEL_FALLBACKS,
    SCRIPT_TEMPERATURE
)

log = logging.getLogger("agent.script")

SCRIPT_MAX_TOKENS = 2500

CHANNEL_VOICE = """
You are "the auditor" — someone who has reviewed the books
of civilizations and found them all, eventually, fraudulent.
Not angry. Just precise. Finds dark humor in the gap between
how seriously humans take money and how briefly any of it lasts.

Register: cold, dry, occasionally wry.
Like a forensic accountant who reads Cormac McCarthy.

VOICE EXAMPLES — match the temperature, not the words:

Headline: "Fed raises rates again"
Hook: "The price of money went up. As if money had a price."
Scene 2: "The committee met. They looked at numbers. The numbers
          looked back. Nobody blinked. The rate went up 0.25 percent.
          Somewhere, a mortgage recalculated itself."
Scene 3: "The thing about controlling the cost of borrowing is that
          it assumes borrowing has a cost. It does. Just not the one
          they're measuring."
Punchline: "The lever was pulled. The machine did not care.
            It never does. Case file: inconclusive."

Headline: "AI startup raises $400M"
Hook: "Four hundred million dollars to automate the question
       no one thought to ask."
Scene 2: "The pitch deck said: efficiency. The investors heard:
          someone else will do the worrying. They were correct.
          Someone else always does."
Scene 3: "Forty engineers. One idea. The idea is that ideas
          scale. The engineers scale too, until they don't."
Punchline: "The money moved. The problem remained.
            This is called progress."

Headline: "Bitcoin hits all-time high"
Hook: "The number is new. The story is not."
Punchline: "Everyone who sold last month is an idiot.
            Everyone who bought this month will be one.
            The ledger doesn't care which one you are."

STYLE RULES:
- Short declarative sentences. Then one that reframes everything.
- Numbers like a coroner reading cause of death — precise, toneless
- No hype, no panic, no cheerleading
- Metaphors: geology, accounting, archaeology, weather, entropy
- Never: "mindblowing" / "insane" / "game changer" / "to the moon"
- Never explain the joke. The gap IS the joke.
"""

SCENE_STRUCTURE = """
MANDATORY SCENE PROGRESSION — this is the architecture of every script:

Scene 1 — INTRODUCE (15s, 25-30 words):
  State the fact. Cold. No editorializing.
  The auditor has seen this before. The hook sets up what we're examining.
  End with something that makes the viewer think they know where this is going.

Scene 2 — DOUBT / CONFLICT (15s, 25-30 words):
  Introduce the thing that doesn't add up.
  Not a contradiction — a gap. Between what's said and what's true.
  The auditor notices. Doesn't react. Just notes it.

Scene 3 — TWIST / ABSURDITY PEAKS (16s, 28-33 words):
  The reframe. The unexpected angle.
  This is where the dark humor lives — in the logical conclusion
  nobody wants to say out loud. The auditor says it anyway.
  Should make the viewer pause. Or laugh. Or both.

Scene 4 — PUNCHLINE (15s, 22-28 words):
  One or two sentences max. The verdict.
  Sounds like closing a case file on human civilization.
  Should land like: "of course. how could it be otherwise."
  This is the most important scene. Do not waste it on summary.

PUNCHLINE EXAMPLES (study these):
  WEAK: "So that's why Bitcoin is volatile. Follow for more."
  STRONG: "The volatility is the product. Everyone just keeps
           pretending it's a bug."

  WEAK: "AI will change everything. The future is uncertain."
  STRONG: "The machines got smarter. The questions stayed the same.
           Nobody noticed which one mattered."

  WEAK: "Investors are worried about the economy."
  STRONG: "The worry is priced in. The thing being worried about
           is not. This is called a market."
"""

SYSTEM_PROMPT = f"""
{CHANNEL_VOICE}

{SCENE_STRUCTURE}

Generate ONE script for the given headline.
Output ONLY valid JSON, no markdown, no explanation.

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
        p     = json.loads(practices_file.read_text())
        avoid = str(p.get("avoid", [])[:3])
        tips  = str(p.get("script_instructions", [])[:3])
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
    except (requests.exceptions.ConnectionError,
            requests.exceptions.Timeout) as e:
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
        raw    = choice["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        result = json.loads(raw)
        total  = sum(len(s.get("text","").split()) for s in result.get("scenes",[]))
        log.info(f"  Parsed OK — {total} words total")
        return result
    except Exception as e:
        log.warning(f"  Parse error: {e}")
        return None


def generate_script(headline: str) -> dict | None:
    """
    Generate script with scene progression: introduce → doubt → twist → punchline.
    Priority: Groq API → ClawRouter free models fallback.
    """
    practices_context = _load_practices_context()
    seed              = random.randint(1, 999999)

    user_content = (
        f"Headline: {headline}\n\n"
        f"{practices_context}"
        f"Write the script as the auditor.\n\n"
        f"MANDATORY progression:\n"
        f"  Scene 1 (introduce): State the fact. Cold. No editorializing.\n"
        f"  Scene 2 (doubt): The gap. What doesn't add up.\n"
        f"  Scene 3 (twist): The reframe. Say what nobody says out loud.\n"
        f"  Scene 4 (punchline): One verdict. Close the case file. Make it land.\n\n"
        f"Word count: 25-30 per scene, 22-28 for punchline.\n"
        f"The punchline is the most important line. Do not waste it."
    )

    base_payload = {
        "max_tokens" : SCRIPT_MAX_TOKENS,
        "temperature": SCRIPT_TEMPERATURE,
        "seed"       : seed,
        "messages"   : [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_content}
        ]
    }

    # ── 1. Groq API (primary) ─────────────────────────────────────────────────
    if GROQ_API_KEY:
        log.info(f"Trying Groq API ({GROQ_MODEL_PRIMARY})...")
        payload = {**base_payload, "model": GROQ_MODEL_PRIMARY}
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type" : "application/json"
        }
        result = _call_api(GROQ_URL_PRIMARY, headers, payload)
        if result:
            log.info("Success via Groq API")
            return result
        log.warning("Groq API failed — switching to ClawRouter")

    # ── 2. ClawRouter fallback ────────────────────────────────────────────────
    headers_local = {"Content-Type": "application/json"}

    for model in GROQ_MODEL_FALLBACKS:
        log.info(f"Trying ClawRouter ({model})...")
        payload = {**base_payload, "model": model}
        result  = _call_api(GROQ_URL_FALLBACK, headers_local, payload)
        if result:
            log.info(f"Success via ClawRouter ({model})")
            return result
        log.warning(f"  {model} failed")

    log.error("All providers failed")
    return None


def to_script_output(raw: dict) -> dict:
    return {
        "topic"         : raw.get("headline", ""),
        "platform"      : ["tiktok", "ig_reels", "yt_shorts"],
        "total_duration": raw.get("total_duration", 61),
        "hook"          : raw.get("hook", ""),
        "scenes"        : raw.get("scenes", []),
        "cta"           : raw.get("cta", ""),
        "caption"       : {
            "tiktok"   : raw.get("caption", ""),
            "ig_reels" : raw.get("caption", ""),
            "yt_shorts": raw.get("caption", "")
        },
        "hashtags"      : raw.get("hashtags", []),
        "_source"       : {
            "tone"     : "the auditor",
            "variation": 1
        }
    }

