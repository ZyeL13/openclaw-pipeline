"""
workers/worker_qc.py — QC worker.
Handles frame extraction, audio strip, retries, file saving.
Calls qc_agent for pure analysis logic.
"""

import json
import logging
import subprocess
import tempfile
import time
from pathlib import Path

from agents.qc_agent import analyze_frame, synthesize_report
from core.config import QC_N_FRAMES, QC_FRAME_DELAY, TARGET_DURATION

log = logging.getLogger("worker.qc")


def _get_video_info(video_path: str) -> dict:
    result = subprocess.run([
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        video_path
    ], capture_output=True, text=True)

    data         = json.loads(result.stdout)
    fmt          = data.get("format", {})
    video_stream = next((s for s in data.get("streams", []) if s["codec_type"] == "video"), {})
    audio_stream = next((s for s in data.get("streams", []) if s["codec_type"] == "audio"), {})

    return {
        "duration"   : round(float(fmt.get("duration", 0)), 2),
        "width"      : video_stream.get("width", 0),
        "height"     : video_stream.get("height", 0),
        "has_audio"  : bool(audio_stream),
        "audio_codec": audio_stream.get("codec_name", "none"),
        "video_codec": video_stream.get("codec_name", "unknown"),
        "aspect"     : f"{video_stream.get('width',0)}x{video_stream.get('height',0)}",
    }


def _extract_frames(video_path: str, tmpdir: str) -> list:
    info   = _get_video_info(video_path)
    dur    = info["duration"]
    frames = []
    for i in range(QC_N_FRAMES):
        ts  = round((dur / (QC_N_FRAMES + 1)) * (i + 1), 2)
        out = f"{tmpdir}/frame_{i+1}.jpg"
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(ts),
            "-i", video_path,
            "-vframes", "1", "-q:v", "2", out
        ], capture_output=True)
        p = Path(out)
        if p.exists():
            frames.append({"path": out, "timestamp": ts, "index": i + 1,
                           "bytes": p.read_bytes()})
    return frames


def _transcribe(audio_path: str) -> dict:
    from core.config import GROQ_API_KEY, GROQ_URL
    import requests

    if not Path(audio_path).exists():
        return {"text": "", "error": "no audio"}

    with open(audio_path, "rb") as f:
        resp = requests.post(
            f"{GROQ_URL}/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            files={"file": ("audio.wav", f, "audio/wav")},
            data={
                "model"          : "whisper-large-v3-turbo",
                "response_format": "verbose_json",
                "language"       : "en"
            },
            timeout=60
        )
    if resp.status_code != 200:
        return {"text": "", "error": f"Whisper {resp.status_code}"}

    data      = resp.json()
    text      = data.get("text", "").strip()
    dur       = data.get("duration", 0)
    wpm       = round((len(text.split()) / dur) * 60) if dur > 0 else 0
    return {
        "text"        : text,
        "duration"    : round(dur, 2),
        "word_count"  : len(text.split()),
        "words_per_min": wpm,
        "segments"    : len(data.get("segments", [])),
    }


def run(run_dir: Path) -> bool:
    """
    Run full QC on the video in run_dir.
    Saves qc_report.json. Returns True if verdict is publish/fix_minor.
    """
    video_path  = run_dir / "final_video.mp4"
    script_path = run_dir / "script_output.json"
    report_path = run_dir / "qc_report.json"

    if not video_path.exists():
        log.error(f"Video not found: {video_path}")
        return False

    log.info(f"QC start — {video_path.name}")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Metadata
        video_info = _get_video_info(str(video_path))
        dur_gap    = round(video_info["duration"] - TARGET_DURATION, 1)
        log.info(f"  Duration: {video_info['duration']}s (gap {dur_gap:+.1f}s)  {video_info['aspect']}")

        # Audio transcription
        audio_out = f"{tmpdir}/audio.wav"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", audio_out
        ], capture_output=True)
        transcript = _transcribe(audio_out)
        if transcript.get("text"):
            log.info(f"  Transcript: {transcript['text'][:80]}...")

        # Frame analysis
        frames = _extract_frames(str(video_path), tmpdir)
        log.info(f"  Analyzing {len(frames)} frames via Gemini...")
        frame_analyses = []
        for i, frame in enumerate(frames):
            log.info(f"  Frame {frame['index']} @ {frame['timestamp']}s")

            # Retry on 429
            result = None
            for attempt in range(3):
                result = analyze_frame(frame["bytes"], frame["timestamp"], frame["index"])
                if "error" in result and "429" in str(result.get("error", "")):
                    wait = 30 * (attempt + 1)
                    log.warning(f"  Rate limit, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                break
            frame_analyses.append(result)

            if i < len(frames) - 1:
                time.sleep(QC_FRAME_DELAY)

        # Load script context
        script_data = None
        if script_path.exists():
            with open(script_path) as f:
                script_data = json.load(f)

        # Synthesize report
        log.info("  Synthesizing report...")
        report = synthesize_report(video_info, transcript, frame_analyses, script_data)

    # Save
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    verdict = report.get("verdict", "unknown")
    overall = report.get("overall_score", 0)
    log.info(f"QC done — verdict={verdict}  score={overall}/10")
    log.info(f"Saved → {report_path.name}")

    return verdict in ("publish", "fix_minor")
