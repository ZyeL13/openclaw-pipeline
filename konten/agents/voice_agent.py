"""
agents/voice_agent.py — Pure TTS logic.
No file I/O. No retries. No logging.
Returns audio bytes or None.
"""

import asyncio
import re
import tempfile
from pathlib import Path
from core.config import TTS_VOICE, TTS_RATE, TTS_VOLUME

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


def clean_text(text: str) -> str:
    """Normalize text before TTS."""
    text = re.sub(r'[#*_~`]', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\$(\d+)B\b', r'\1 billion dollars', text)
    text = re.sub(r'\$(\d+)M\b', r'\1 million dollars', text)
    text = re.sub(r'\$(\d+)K\b', r'\1 thousand dollars', text)
    text = re.sub(r'\$(\d+)',    r'\1 dollars', text)
    text = re.sub(r'(\d+)%',    r'\1 percent', text)
    text = re.sub(r'(\d+)x\b',  r'\1 times', text)
    text = re.sub(r'(\d+)K\b',  r'\1 thousand', text)
    text = re.sub(r' +', ' ', text).strip()
    return text


def build_narration(script_data: dict) -> str:
    """Assemble full narration with cinematic pauses between sections."""
    parts = []

    hook = script_data.get("hook", "").strip()
    if hook:
        parts.append(hook)

    for scene in script_data.get("scenes", []):
        text = scene.get("text", "").strip()
        if text:
            parts.append(text)

    cta = script_data.get("cta", "").strip()
    if cta:
        parts.append(cta)

    raw = "... ".join(parts) + "."
    return clean_text(raw)


async def _generate_async(text: str, voice: str, output_path: str):
    communicate = edge_tts.Communicate(
        text=text, voice=voice, rate=TTS_RATE, volume=TTS_VOLUME
    )
    await communicate.save(output_path)


def generate(script_data: dict, voice: str = None) -> bytes | None:
    """Generate TTS audio. Returns MP3 bytes or None."""
    if not EDGE_TTS_AVAILABLE:
        return None

    voice    = voice or TTS_VOICE
    text     = build_narration(script_data)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        asyncio.run(_generate_async(text, voice, tmp_path))
        with open(tmp_path, "rb") as f:
            return f.read()
    except Exception:
        return None
    finally:
        Path(tmp_path).unlink(missing_ok=True)
