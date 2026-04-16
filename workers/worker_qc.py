"""
workers/worker_qc.py — QC execution layer.
Handles: ffprobe, frame extraction, Whisper transcription,
         retry logic, report saving, verdict print.

Calls agents/qc_agent.py for pure analysis logic.
"""

import json
import logging
import subprocess
import tempfile
import time
from pathlib import Path

import requests

from agents.qc_agent import analyze_frame, synthesize_report
from core.config import (
    GROQ_URL, GROQ_API_KEY,
    QC_N_FRAMES, QC_FRAME_DELAY, QC_PASS_SCORE,
    TARGET_DURATION
)

log = logging.getLogger("worker.qc")


# ── FFPROBE ───────────────────────────────────────────────────────────────────
def _get_video_info(video_path: str) -> dict:
    result = subprocess.run([
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        video_path
    ], capture_output=True, text=True)

    if not result.stdout:
        return {}

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


# ── FRAME EXTRACTION ──────────────────────────────────────────────────────────
def _extract_frames(video_path: str, tmpdir: str, n: int) -> list:
    info = _get_video_info(video_path)
    dur  = info.get("duration", 0)
    if dur == 0:
        return []

    frames = []
    for i in range(n):
        ts  = round((dur / (n + 1)) * (i + 1), 2)
        out = f"{tmpdir}/frame_{i+1}.jpg"
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(ts),
            "-i", video_path,
            "-vframes", "1", "-q:v", "2", out
        ], capture_output=True)
        p = Path(out)
        if p.exists():
            frames.append({
                "path":      out,
                "bytes":     p.read_bytes(),
                "timestamp": ts,
                "index":     i + 1
            })
    return frames


# ── WHISPER TRANSCRIPTION ─────────────────────────────────────────────────────
def _transcribe(audio_path: str) -> dict:
    if not Path(audio_path).exists():
        return {"text": "", "word_count": 0, "words_per_min": 0, "error": "no_audio"}

    try:
        with open(audio_path, "rb") as f:
            resp = requests.post(
                f"{GROQ_URL}/audio/transcriptions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                files={"file": ("audio.wav", f, "audio/wav")},
                data={
                    "model"          : "whisper-large-v3-turbo",
                    "response_format": "verbose_json",
                    "language"       : "id"     # change to "en" for English content
                },
                timeout=60
            )
    except Exception as e:
        return {"text": "", "word_count": 0, "words_per_min": 0, "error": str(e)}

    if resp.status_code != 200:
        return {"text": "", "word_count": 0, "words_per_min": 0,
                "error": f"Whisper {resp.status_code}"}

    data = resp.json()
    text = data.get("text", "").strip()
    dur  = data.get("duration", 0)
    wpm  = round((len(text.split()) / dur) * 60) if dur > 0 else 0

    return {
        "text"         : text,
        "duration"     : round(dur, 2),
        "word_count"   : len(text.split()),
        "words_per_min": wpm,
        "segments"     : len(data.get("segments", [])),
    }


# ── VERDICT PRINTER ───────────────────────────────────────────────────────────
def _print_report(report: dict) -> None:
    verdict  = report.get("verdict", "unknown").upper()
    overall  = report.get("overall_score", 0)
    risk     = report.get("publish_risk", "?").upper()
    reason   = report.get("acc_reject_reason", "")

    icons = {
        "PUBLISH"  : "✅",
        "FIX_MINOR": "⚠️ ",
        "FIX_MAJOR": "🔧",
        "REJECT"   : "❌"
    }
    icon = icons.get(verdict, "❓")

    print(f"\n{'='*56}")
    print(f"  QC REPORT")
    print(f"{'='*56}")
    print(f"  {icon} {verdict:<12}  {overall}/10  risk={risk}")
    print(f"  Reason: {reason}")
    print()

    sections = [
        ("duration_score", "Duration"),
        ("audio_score",    "Audio   "),
        ("visual_score",   "Visual  "),
        ("sync_score",     "Sync    "),
        ("hook_strength",  "Hook    "),
        ("pacing_score",   "Pacing  "),
    ]
    for key, label in sections:
        s     = report.get(key, {})
        score = s.get("score", 0)
        note  = s.get("note", "")
        try:
            bar = "█" * int(score) + "░" * (10 - int(score))
        except (TypeError, ValueError):
            bar = "░" * 10
        print(f"  {label}: {str(score).rjust(2)}/10  {bar}  {note}")

    issues = report.get("top_issues", [])
    if issues:
        print(f"\n  TOP ISSUES:")
        for i in issues:
            print(f"    • {i}")

    wins = report.get("quick_wins", [])
    if wins:
        print(f"\n  QUICK WINS:")
        for w in wins:
            print(f"    → {w}")

    print(f"{'='*56}\n")


# ── MAIN WORKER ───────────────────────────────────────────────────────────────
def run(run_dir: Path) -> bool:
    """
    Execute full QC pipeline on run_dir.
    Saves qc_report.json.
    Returns True if verdict is publish or fix_minor (score >= QC_PASS_SCORE).
    """
    video_path  = run_dir / "final_video.mp4"
    script_path = run_dir / "script_output.json"
    report_path = run_dir / "qc_report.json"

    if not video_path.exists():
        log.error(f"Video not found: {video_path}")
        return False

    if not GROQ_API_KEY:
        log.error("GROQ_API_KEY not set.")
        return False

    log.info(f"QC start — {video_path}")

    with tempfile.TemporaryDirectory() as tmpdir:

        # 1. Metadata
        video_info = _get_video_info(str(video_path))
        dur_gap    = round(video_info.get("duration", 0) - TARGET_DURATION, 1)
        log.info(
            f"  Duration: {video_info.get('duration')}s "
            f"(gap {dur_gap:+.1f}s)  {video_info.get('aspect')}"
        )

        # 2. Extract audio → transcribe
        audio_out = f"{tmpdir}/audio.wav"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", audio_out
        ], capture_output=True)

        log.info("  Transcribing audio...")
        transcript = _transcribe(audio_out)
        if transcript.get("text"):
            log.info(
                f"  {transcript['word_count']} words @ "
                f"{transcript['words_per_min']} wpm"
            )
            log.info(f"  Preview: \"{transcript['text'][:80]}...\"")
        elif transcript.get("error"):
            log.warning(f"  Transcription failed: {transcript['error']}")

        # 3. Extract frames → analyze with retry
        frames = _extract_frames(str(video_path), tmpdir, QC_N_FRAMES)
        log.info(f"  Analyzing {len(frames)} frames via Groq vision...")

        frame_analyses = []
        for i, frame in enumerate(frames):
            log.info(f"  Frame {frame['index']} @ {frame['timestamp']}s")

            result = None
            for attempt in range(3):
                result = analyze_frame(
                    frame["bytes"],
                    frame["timestamp"],
                    frame["index"]
                )
                err = result.get("error", "")
                if err == "429":
                    wait = 20 * (attempt + 1)
                    log.warning(f"  Rate limit — waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if err:
                    log.warning(f"  Frame {frame['index']} error: {err}")
                break

            frame_analyses.append(result)

            # Delay between frames to stay under rate limit
            if i < len(frames) - 1:
                time.sleep(QC_FRAME_DELAY)

        # 4. Load script context
        script_data = None
        if script_path.exists():
            try:
                with open(script_path, encoding="utf-8") as f:
                    script_data = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        # 5. Synthesize report
        log.info("  Synthesizing full report...")
        report = synthesize_report(video_info, transcript, frame_analyses, script_data)

    # 6. Save
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    if "error" in report and len(report) == 1:
        log.error(f"QC report generation failed: {report['error']}")
        return False

    verdict = report.get("verdict", "unknown")
    overall = report.get("overall_score", 0)
    log.info(f"QC done — verdict={verdict}  score={overall}/10")

    _print_report(report)

    # Pass = publish or fix_minor AND score above threshold
    passed = verdict in ("publish", "fix_minor") and float(overall) >= QC_PASS_SCORE
    return passed

