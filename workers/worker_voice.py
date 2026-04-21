"""
workers/worker_voice.py — Voice worker.
"""
import json
import logging
import subprocess
import shutil
import time
from pathlib import Path
from datetime import datetime

from agents.voice_agent import generate, build_narration
from core.config import TTS_VOICE

log = logging.getLogger("worker.voice")
MAX_RETRIES = 2
ALT_VOICE   = "en-US-BrianNeural"

def _upgrade_audio(mp3_path: Path):
    """Upgrade 48kbps mono → 128kbps stereo."""
    tmp = mp3_path.with_suffix(".hq.mp3")
    cmd = ["ffmpeg", "-y", "-i", str(mp3_path),
           "-codec:a", "libmp3lame", "-b:a", "128k", "-ac", "2", "-ar", "44100",
           str(tmp)]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode == 0:
        shutil.move(str(tmp), str(mp3_path))
        log.info("Audio upgraded → 128kbps stereo")
    else:
        tmp.unlink(missing_ok=True)

def run(script_data: dict, lang: str, run_dir: Path) -> bool:
    """Generate voice MP3 and save to run_dir/voice.mp3."""
    voice_file = run_dir / "voice.mp3"
    
    # FIX: Build narration string DULU
    narration = build_narration(script_data)
    word_count = len(narration.split())
    
    log.info(f"Generating voice — words={word_count}  voice={TTS_VOICE}")

    audio_bytes = None
    for attempt, voice in enumerate([TTS_VOICE, ALT_VOICE]):
        if attempt > 0:
            log.warning(f"Trying alt voice: {voice}")
            time.sleep(3)

        for retry in range(MAX_RETRIES):
            # FIX: Kirim narration (string), bukan script_data (dict)
            audio_bytes = generate(narration, voice=voice)
            if audio_bytes:
                break
            log.warning(f"TTS attempt {retry+1}/{MAX_RETRIES} failed")
            time.sleep(5)

        if audio_bytes:
            break

    if not audio_bytes:
        log.error("All voice attempts failed")
        return False

    with open(voice_file, "wb") as f:
        f.write(audio_bytes)

    size_kb = len(audio_bytes) / 1024
    log.info(f"voice.mp3 saved ({size_kb:.0f} KB)")
    _upgrade_audio(voice_file)

    log_data = {
        "generated_at": datetime.now().isoformat(),
        "voice": voice,
        "word_count": word_count,
        "narration_text": narration[:200],
        "output_file": "voice.mp3"
    }
    with open(run_dir / "voice_log.json", "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2)

    return True
