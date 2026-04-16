"""
agents/visual_agent.py — Image generation with beat-aware visual styles.
Each scene beat (introduce/doubt/twist/punchline) gets distinct visual language.
"""

import urllib.parse
import requests
from core.config import IMAGE_WIDTH, IMAGE_HEIGHT, IMAGE_MODEL, STYLE_PREFIX, AUDITOR_VISUAL_STYLE

# ── BEAT-AWARE STYLE MODIFIERS ────────────────────────────────────────────────
# Each beat in the scene progression gets a distinct cinematographic approach
BEAT_STYLE = {
    "introduce" : (
        "cold empty institutional space, fluorescent overhead light, "
        "wide establishing shot, clinical distance, "
    ),
    "doubt"     : (
        "close-up detail shot, shadow falling across surface, "
        "something slightly wrong in frame, oblique angle, "
    ),
    "twist"     : (
        "extreme wide or extreme close, scale suddenly apparent, "
        "negative space used deliberately, tonal shift visible, "
    ),
    "punchline" : (
        "single object centered in frame, maximum negative space, "
        "still life aesthetic, weight of finality, "
    ),
}

# Fallback styles when beat is not specified — rotate per scene index
INDEX_STYLE = [
    "wide shot, empty architecture, long corridor, ambient light, ",
    "close-up texture, surface detail, grain visible, shadow edge, ",
    "aerial view, scale shift, urban geometry, cold palette, ",
    "single subject, negative space, minimalist frame, cinematic still, ",
]


def build_prompt(visual_desc: str, beat: str = "", scene_index: int = 0) -> str:
    """
    Build Pollinations prompt with auditor aesthetic + beat-aware style.
    
    Priority:
    1. beat-specific style (introduce/doubt/twist/punchline)
    2. index-based rotation fallback
    3. always: STYLE_PREFIX + AUDITOR_VISUAL_STYLE
    """
    if beat and beat in BEAT_STYLE:
        beat_modifier = BEAT_STYLE[beat]
    else:
        beat_modifier = INDEX_STYLE[scene_index % len(INDEX_STYLE)]

    return f"{STYLE_PREFIX}{AUDITOR_VISUAL_STYLE}{beat_modifier}{visual_desc}"


def fetch_image(prompt: str, scene_id: int, seed: int = None) -> bytes | None:
    """Fetch image from Pollinations. Returns raw bytes or None."""
    if seed is None:
        seed = scene_id * 42

    encoded = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={IMAGE_WIDTH}&height={IMAGE_HEIGHT}"
        f"&model={IMAGE_MODEL}&nologo=true&seed={seed}"
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


def fetch_best(prompt: str, scene_id: int) -> bytes | None:
    """
    Generate 2 images with different seeds, return the larger one.
    Larger file size = more detail = generally better quality.
    Falls back to single image if second fetch fails.
    """
    img1 = fetch_image(prompt, scene_id, seed=scene_id * 42)
    if img1 is None:
        return None

    img2 = fetch_image(prompt, scene_id, seed=scene_id * 137)
    if img2 is None:
        return img1

    # Pick larger — proxy for detail density
    best = img1 if len(img1) >= len(img2) else img2
    return best

