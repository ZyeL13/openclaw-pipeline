"""
agents/voice_agent.py — Pure TTS logic.
Primary: Edge TTS (file-based save) — stable
Fallback: gTTS — works when Edge TTS is blocked
No streaming, no chunk handling, no KeyError.
"""
import re
import asyncio
from pathlib import Path
from core.config import TTS_VOICE, TTS_RATE, TTS_VOLUME

def clean_text(text: str) -> str:
    """Sanitize text for TTS."""
    text = re.sub(r'[#*_~`]', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\$(\d+)B\b', r'\1 billion dollars', text)
    text = re.sub(r'\$(\d+)M\b', r'\1 million dollars', text)
    text = re.sub(r'\$(\d+)K\b', r'\1 thousand dollars', text)
    text = re.sub(r'\$(\d+)', r'\1 dollars', text)
    text = re.sub(r'(\d+)%', r'\1 percent', text)
    text = re.sub(r'(\d+)x\b', r'\1 times', text)
    return re.sub(r' +', ' ', text).strip()

def build_narration(script_data: dict) -> str:
    """Extract narration text from script output."""
    if isinstance(script_data, str):
        return clean_text(script_data)
    
    parts = []
    hook = script_data.get("hook", "").strip()
    if hook:
        parts.append(hook)
    
    scenes = script_data.get("scenes", []) or script_data.get("script", [])
    for scene in scenes:
        text = scene.get("text") or scene.get("narration") or scene.get("voiceover") or ""
        if text.strip():
            parts.append(text.strip())
    
    cta = script_data.get("cta", "").strip()
    if cta:
        parts.append(cta)
    
    raw = " ... ".join(parts) + ". "
    cleaned = clean_text(raw)
    
    # Padding untuk durasi minimal
    words = len(cleaned.split())
    if words < 80:
        cleaned += " [pause] " * ((80 - words) // 5)
    
    return cleaned

def _generate_edge(text: str, voice: str, output_path: str) -> bool:
    """Edge TTS via comm.save() — stable, no chunk handling."""
    try:
        import edge_tts
        async def _run():
            comm = edge_tts.Communicate(text=text, voice=voice, rate=TTS_RATE, volume=TTS_VOLUME)
            await comm.save(output_path)
        asyncio.run(_run())
        return Path(output_path).exists()
    except Exception:
        return False

def _generate_gtts(text: str, output_path: str) -> bool:
    """Fallback: gTTS."""
    try:
        from gtts import gTTS
        tts = gTTS(text, lang="en", slow=False)
        tts.save(output_path)
        return Path(output_path).exists()
    except Exception:
        return False

def generate(text: str, voice: str = None) -> bytes | None:
    """
    Generate TTS audio. Input: plain text string.
    Returns MP3 bytes or None.
    """
    voice = voice or TTS_VOICE
    tmp_path = str(Path.home() / ".tts_tmp.mp3")
    
    # Try Edge TTS
    if _generate_edge(text, voice, tmp_path):
        data = Path(tmp_path).read_bytes()
        Path(tmp_path).unlink(missing_ok=True)
        return data
    
    # Fallback gTTS
    if _generate_gtts(text, tmp_path):
        data = Path(tmp_path).read_bytes()
        Path(tmp_path).unlink(missing_ok=True)
        return data
    
    return None
