"""
agents/visual_agent.py — Pure image generation logic.
Locked to "the auditor" visual style.
"""

import urllib.parse
import requests
from core.config import IMAGE_WIDTH, IMAGE_HEIGHT, IMAGE_MODEL, STYLE_PREFIX, AUDITOR_VISUAL_STYLE


def build_prompt(visual_desc: str) -> str:
    """Build Pollinations prompt with auditor style baked in."""
    return f"{STYLE_PREFIX}{AUDITOR_VISUAL_STYLE}{visual_desc}"


def fetch_image(prompt: str, scene_id: int) -> bytes | None:
    """Fetch image from Pollinations. Returns raw bytes or None."""
    encoded = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={IMAGE_WIDTH}&height={IMAGE_HEIGHT}"
        f"&model={IMAGE_MODEL}&nologo=true&seed={scene_id * 42}"
    )

    try:
        resp = requests.get(url, timeout=90)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        return None

    if resp.status_code != 200:
        return None

    if "image" not in resp.headers.get("content-type", ""):
        return None

    return resp.content

