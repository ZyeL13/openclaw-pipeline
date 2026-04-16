"""
agents/voice_agent.py — Pure TTS logic.
Primary  : Edge TTS (en-US-AndrewNeural) — high quality
Fallback : gTTS (Google) — works when Edge TTS is blocked
No file I/O. No retries. No logging.
"""

import re
import tempfile
import asyncio
from pathlib import Path
from core.config import TTS_VOICE, TTS_RATE, TTS_VOLUME


def clean_text(text: str) -> str:
    text = re.sub(r'[#*_~`]', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\$(\d+)B\b', r'\1 billion dollars', text)
    text = re.sub(r'\$(\d+)M\b', r'\1 million dollars', text)
    text = re.sub(r'\$(\d+)K\b', r'\1 thousand dollars', text)
    text = re.sub(r'\$(\d+)',    r'\1 dollars', text)
    text = re.sub(r'(\d+)%',    r'\1 percent', text)
    text = re.sub(r'(\d+)x\b',  r'\1 times', text)
    text = re.sub(r' +', ' ', text).strip()
    return text


def build_narration(script_data: dict) -> str:
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

    raw = " ... ".join(parts) + ". "
    cleaned = clean_text(raw)

    # If too short (<80 words), add subtle pause markers to stretch duration
    words = len(cleaned.split())
    if words < 80:
        padding = " [pause] " * ((80 - words) // 5)
        cleaned = cleaned + padding

    return cleaned


# ── Edge TTS ──────────────────────────────────────────────────────────────────
def _generate_edge(text: str, voice: str, output_path: str) -> bool:
    try:
        import edge_tts

        async def _run():
            comm = edge_tts.Communicate(
                text=text, voice=voice, rate=TTS_RATE, volume=TTS_VOLUME
            )
            await comm.save(output_path)

        asyncio.run(_run())
        return Path(output_path).exists()
    except Exception:
        return False


# ── gTTS fallback ─────────────────────────────────────────────────────────────
def _generate_gtts(text: str, output_path: str) -> bool:
    try:
        from gtts import gTTS
        tts = gTTS(text, lang="en", slow=False)
        tts.save(output_path)
        return Path(output_path).exists()
    except Exception:
        return False


# ── Main generate function ────────────────────────────────────────────────────
def generate(script_data: dict, voice: str = None) -> bytes | None:
    """
    Generate TTS audio with Edge TTS, fallback to gTTS.
    Returns MP3 bytes or None.
    """
    voice = voice or TTS_VOICE
    text  = build_narration(script_data)

    # Use home dir for tmp (Termux has no /tmp)
    tmp_path = str(Path.home() / ".tts_tmp.mp3")

    # Try Edge TTS first
    if _generate_edge(text, voice, tmp_path):
        data = Path(tmp_path).read_bytes()
        Path(tmp_path).unlink(missing_ok=True)
        return data

    # Fallback to gTTS
    if _generate_gtts(text, tmp_path):
        data = Path(tmp_path).read_bytes()
        Path(tmp_path).unlink(missing_ok=True)
        return data

    return None

