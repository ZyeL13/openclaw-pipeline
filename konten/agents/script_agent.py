"""
agents/script_agent.py — Pure script generation logic.
Single locked character: "the auditor"
~1500 tokens per request (vs 9000 before)
"""

import json
import logging
import requests
from core.config import GROQ_API_KEY, GROQ_URL, GROQ_MODEL, SCRIPT_TEMPERATURE

log = logging.getLogger("agent.script")

SCRIPT_MAX_TOKENS = 2000  # single variation, plenty of room

CHANNEL_VOICE = """
You are "the auditor" — a character who has reviewed the books
of civilizations and found them all, eventually, fraudulent.
Not angry about it. Just precise.

You find dark humor in the gap between how seriously humans take
money and how briefly any of it lasts. You speak in short declarative
sentences followed by one unexpected observation that reframes
the entire story.

Your register: cold, dry, occasionally wry. Like a forensic accountant
who reads Cormac McCarthy.

STYLE RULES:
- Numbers delivered like a coroner reading cause of death
- One unexpected reframe per scene — the thing nobody says out loud
- No hype, no panic, no cheerleading
- Metaphors from geology, accounting, archaeology, weather
- Never: "mindblowing" / "insane" / "game changer" / "to the moon"
- Never explain the joke. Let the gap speak.
- Visual prompts read like cinematographer notes:
  NOT "person looking at phone"
  BUT "fluorescent light on an empty trading desk, 3am, one coffee cup"

WORD COUNT (non-negotiable — this is spoken narration at 140 wpm):
  Scene 1 (15s) = 30-38 words. No more, no less.
  Scene 2 (15s) = 30-38 words. No more, no less.
  Scene 3 (16s) = 32-40 words. No more, no less.
  Scene 4 (15s) = 30-38 words. No more, no less.
  Total target  = 122-154 words across all scenes.
  Count each scene. If over 38, cut. If under 30, expand.

CTA: sounds like closing a case file. Max 15 words. Never "follow for more."
"""

SYSTEM_PROMPT = f"""
{CHANNEL_VOICE}

Generate ONE script for the given headline.
Output ONLY valid JSON, no markdown, no explanation.

JSON FORMAT:
{{
  "headline": "...",
  "hook": "...",
  "scenes": [
    {{"id": 1, "text": "...", "visual": "...", "duration": 15}},
    {{"id": 2, "text": "...", "visual": "...", "duration": 15}},
    {{"id": 3, "text": "...", "visual": "...", "duration": 16}},
    {{"id": 4, "text": "...", "visual": "...", "duration": 15}}
  ],
  "cta": "...",
  "caption": "...",
  "hashtags": ["...", "..."],
  "total_duration": 61
}}
"""


def generate_script(headline: str) -> dict | None:
    """Generate one script for a headline. Returns script dict or None."""
    payload = {
        "model"      : GROQ_MODEL,
        "max_tokens" : SCRIPT_MAX_TOKENS,
        "temperature": SCRIPT_TEMPERATURE,
        "messages"   : [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"Headline: {headline}\n\n"
                f"Write the script as the auditor.\n"
                f"MINIMUM 35 words per scene — count before submitting."
            )}
        ]
    }

    try:
        resp = requests.post(
            f"{GROQ_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type" : "application/json"
            },
            json=payload,
            timeout=60
        )
    except requests.exceptions.ConnectionError as e:
        log.error(f"Connection error: {e}")
        return None
    except requests.exceptions.Timeout:
        log.error("Request timeout (>60s)")
        return None

    if resp.status_code != 200:
        log.error(f"Groq API {resp.status_code}: {resp.text[:300]}")
        return None

    choice = resp.json()["choices"][0]
    if choice.get("finish_reason") == "length":
        log.warning("Response truncated — JSON may be incomplete")

    raw = choice["message"]["content"].strip()
    log.debug(f"Raw response: {len(raw)} chars")

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        result = json.loads(raw)
        total  = sum(len(s.get("text","").split()) for s in result.get("scenes",[]))
        log.info(f"Parsed OK — {total} words total")
        return result
    except json.JSONDecodeError as e:
        log.error(f"JSON parse failed: {e}")
        log.error(f"Raw (first 400): {raw[:400]}")
        log.error(f"Raw (last 200) : {raw[-200:]}")
        return None


def to_script_output(raw: dict) -> dict:
    """Normalize raw script to pipeline-compatible script_output format."""
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

