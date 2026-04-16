"""
qc_agent.py — Video QC Agent
Stack : FFmpeg + Groq Whisper + Gemini 2.0 Flash + Groq LLaMA
Deps  : pip install requests python-dotenv (already installed)

Run   : python qc_agent.py                          ← auto-detect latest video
        python qc_agent.py output/RUN_ID/final_video.mp4
"""

import os, sys, json, base64, subprocess, tempfile, re, time
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv
load_dotenv()

# ── CONFIG ────────────────────────────────────────────────────────────────────
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

GROQ_URL    = "https://api.groq.com/openai/v1"
GEMINI_URL  = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

N_FRAMES         = 2    # 2 frames: hemat quota, cukup untuk detect masalah
FRAME_DELAY      = 15   # detik antar request Gemini — aman di free tier
TARGET_DURATION  = 61   # target video seconds

# ── FFMPEG ────────────────────────────────────────────────────────────────────
def get_video_info(video_path: str) -> dict:
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
        "fps"        : video_stream.get("r_frame_rate", "unknown"),
        "has_audio"  : bool(audio_stream),
        "audio_codec": audio_stream.get("codec_name", "none"),
        "video_codec": video_stream.get("codec_name", "unknown"),
        "aspect"     : f"{video_stream.get('width',0)}x{video_stream.get('height',0)}",
    }

def extract_frames(video_path: str, tmpdir: str) -> list:
    """Extract N_FRAMES evenly-spaced frames."""
    info   = get_video_info(video_path)
    dur    = info["duration"]
    frames = []
    for i in range(N_FRAMES):
        ts  = round((dur / (N_FRAMES + 1)) * (i + 1), 2)
        out = f"{tmpdir}/frame_{i+1}.jpg"
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(ts),
            "-i", video_path,
            "-vframes", "1", "-q:v", "2", out
        ], capture_output=True)
        if Path(out).exists():
            frames.append({"path": out, "timestamp": ts, "index": i + 1})

    print(f"[qc] Extracted {len(frames)} frames")
    return frames

def extract_audio(video_path: str, tmpdir: str) -> str:
    out = f"{tmpdir}/audio.wav"
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-ar", "16000", "-ac", "1",
        "-c:a", "pcm_s16le", out
    ], capture_output=True)
    return out if Path(out).exists() else None

# ── GROQ WHISPER ──────────────────────────────────────────────────────────────
def transcribe_audio(audio_path: str) -> dict:
    if not audio_path or not Path(audio_path).exists():
        return {"text": "", "error": "no audio file"}

    print("[qc] Transcribing via Groq Whisper...")
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
        return {"text": "", "error": f"Whisper {resp.status_code}: {resp.text[:100]}"}

    data = resp.json()
    text = data.get("text", "").strip()

    # Word count and speaking rate analysis
    words        = len(text.split())
    audio_dur    = data.get("duration", 0)
    words_per_min = round((words / audio_dur) * 60) if audio_dur > 0 else 0

    return {
        "text"        : text,
        "duration"    : round(audio_dur, 2),
        "language"    : data.get("language", "unknown"),
        "word_count"  : words,
        "words_per_min": words_per_min,
        "segments"    : len(data.get("segments", [])),
    }

# ── GEMINI FLASH ──────────────────────────────────────────────────────────────
def analyze_frame(frame: dict) -> dict:
    """Analyze one frame with retry on 429."""
    with open(frame["path"], "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    prompt = """You are analyzing a frame from a short-form social media video (TikTok/Reels/Shorts).
Be specific and actionable. Return ONLY valid JSON, no markdown, no extra text.

{
  "lighting":         {"score": 1-10, "issue": "specific problem or null"},
  "composition":      {"score": 1-10, "issue": "specific problem or null"},
  "text_readability": {"score": 1-10, "issue": "specific problem or null"},
  "visual_quality":   {"score": 1-10, "issue": "specific problem or null"},
  "mood"            : "one word that describes visual tone",
  "dominant_colors" : ["color1", "color2"],
  "quick_fix"       : "single most impactful improvement, or null if no issues"
}"""

    body = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
                {"text": prompt}
            ]
        }],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 400}
    }

    for attempt in range(3):
        try:
            resp = requests.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json=body,
                timeout=30
            )

            if resp.status_code == 429:
                wait = 30 * (attempt + 1)  # 30s, 60s, 90s
                print(f"[qc]   Rate limit (429), waiting {wait}s...")
                time.sleep(wait)
                continue

            if resp.status_code != 200:
                return {
                    "frame"    : frame["index"],
                    "timestamp": frame["timestamp"],
                    "error"    : f"Gemini {resp.status_code}: {resp.text[:120]}"
                }

            raw    = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            raw    = re.sub(r'```json|```', '', raw).strip()
            result = json.loads(raw)
            result["timestamp"] = frame["timestamp"]
            result["frame"]     = frame["index"]
            return result

        except json.JSONDecodeError as e:
            return {"frame": frame["index"], "timestamp": frame["timestamp"],
                    "error": f"JSON parse error: {e}"}
        except Exception as e:
            if attempt == 2:
                return {"frame": frame["index"], "timestamp": frame["timestamp"],
                        "error": str(e)}
            time.sleep(5)

    return {"frame": frame["index"], "timestamp": frame["timestamp"],
            "error": "max retries exceeded"}

def analyze_all_frames(frames: list) -> list:
    print(f"[qc] Analyzing {len(frames)} frames via Gemini 2.0 Flash...")
    results = []
    for i, frame in enumerate(frames):
        print(f"[qc]   Frame {frame['index']} @ {frame['timestamp']}s")
        results.append(analyze_frame(frame))
        # Delay between requests to stay under rate limit
        if i < len(frames) - 1:
            time.sleep(FRAME_DELAY)
    return results

# ── GROQ SYNTHESIS ────────────────────────────────────────────────────────────
def synthesize_report(video_info, transcript, frame_analyses, script_path=None) -> dict:
    print("[qc] Synthesizing full report via Groq LLaMA...")

    # Load script context if available
    script_context = ""
    if script_path and Path(script_path).exists():
        with open(script_path) as f:
            s = json.load(f)
        script_context = f"""
ORIGINAL SCRIPT CONTEXT:
  Hook  : {s.get('hook', 'n/a')}
  CTA   : {s.get('cta', 'n/a')}
  Tone  : {s.get('_source', {}).get('tone', 'unknown')}
  Topic : {s.get('topic', 'n/a')}
"""

    # Count successful vs failed frame analyses
    failed_frames = [f for f in frame_analyses if "error" in f]
    good_frames   = [f for f in frame_analyses if "error" not in f]

    prompt = f"""You are a professional social media video QC analyst reviewing content for TikTok/Instagram Reels/YouTube Shorts.
Your job is to give specific, actionable feedback — not generic advice.
{script_context}
VIDEO DATA:
{json.dumps({
    "video_info"    : video_info,
    "transcript"    : transcript,
    "frame_analyses": frame_analyses,
    "target_duration": TARGET_DURATION,
}, indent=2)}

NOTES:
- {len(failed_frames)} of {len(frame_analyses)} frame analyses failed (treat as unknown, not penalize)
- Speaking rate: 130-160 wpm is natural for English voiceover
- 9:16 aspect ratio required for Shorts/Reels
- Target duration: {TARGET_DURATION}s (55-65s acceptable)

Return ONLY this exact JSON structure, no markdown, no explanation:
{{
  "duration_score": {{
    "score"         : 1-10,
    "actual_seconds": {video_info.get('duration', 0)},
    "target_seconds": {TARGET_DURATION},
    "gap_seconds"   : number (actual minus target, negative = too short),
    "verdict"       : "pass|short|long",
    "note"          : "specific one-line assessment"
  }},
  "audio_score": {{
    "score"              : 1-10,
    "clarity"            : "clear|muffled|robotic|natural",
    "speaking_rate"      : "{transcript.get('words_per_min', 0)} wpm — fast|normal|slow",
    "transcript_preview" : "first 100 chars of transcript",
    "note"               : "specific one-line assessment"
  }},
  "visual_score": {{
    "score"      : 1-10,
    "worst_frame": 1-{N_FRAMES},
    "worst_issue": "specific description of the worst visual problem",
    "avg_lighting"    : 1-10,
    "avg_composition" : 1-10,
    "note"       : "specific one-line assessment"
  }},
  "sync_score": {{
    "score": 1-10,
    "note" : "assessment of audio-visual timing alignment"
  }},
  "hook_strength": {{
    "score"         : 1-10,
    "hook_text"     : "first sentence of transcript",
    "emotion_trigger": "curiosity|fear|fomo|wonder|none",
    "note"          : "does the opening 3s earn continued watching?"
  }},
  "pacing_score": {{
    "score": 1-10,
    "note" : "is the content density right for the duration?"
  }},
  "overall_score" : 1-10,
  "verdict"       : "publish|fix_minor|fix_major|reject",
  "top_issues"    : ["specific issue 1", "specific issue 2", "specific issue 3"],
  "quick_wins"    : ["specific actionable fix 1", "specific actionable fix 2"],
  "publish_risk"  : "low|medium|high",
  "analyzed_at"   : "{datetime.now().isoformat()}"
}}"""

    try:
        resp = requests.post(
            f"{GROQ_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type" : "application/json"
            },
            json={
                "model"      : "llama-3.3-70b-versatile",
                "messages"   : [{"role": "user", "content": prompt}],
                "max_tokens" : 1200,
                "temperature": 0.2,
            },
            timeout=30
        )
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        raw = re.sub(r'```json|```', '', raw).strip()
        return json.loads(raw)
    except Exception as e:
        return {"error": str(e)}

# ── PRINT REPORT ──────────────────────────────────────────────────────────────
def print_report(report: dict, transcript: dict = None):
    if "error" in report and len(report) == 1:
        print(f"\n[ERROR] Report failed: {report['error']}")
        return

    print("\n" + "="*60)
    print("  QC REPORT")
    print("="*60)

    verdict      = report.get("verdict", "unknown").upper()
    overall      = report.get("overall_score", 0)
    risk         = report.get("publish_risk", "unknown").upper()
    verdict_icon = {
        "PUBLISH"   : "✅",
        "FIX_MINOR" : "⚠️ ",
        "FIX_MAJOR" : "🔧",
        "REJECT"    : "❌"
    }.get(verdict, "❓")

    print(f"\n  {verdict_icon} VERDICT     : {verdict}")
    print(f"     OVERALL     : {overall}/10")
    print(f"     PUBLISH RISK: {risk}\n")

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
            filled = int(score)
            bar    = "█" * filled + "░" * (10 - filled)
        except:
            bar = "░" * 10
        print(f"  {label} : {str(score).rjust(2)}/10  {bar}  {note}")

    # Duration detail
    dur = report.get("duration_score", {})
    if dur.get("gap_seconds") is not None:
        gap = dur["gap_seconds"]
        gap_str = f"+{gap}s" if gap > 0 else f"{gap}s"
        print(f"\n           Duration gap: {gap_str} from {TARGET_DURATION}s target")

    # Audio detail
    audio = report.get("audio_score", {})
    if audio.get("speaking_rate"):
        print(f"           Speaking rate: {audio['speaking_rate']}")
    if audio.get("transcript_preview"):
        print(f"           Transcript   : \"{audio['transcript_preview'][:80]}...\"")

    # Hook detail
    hook = report.get("hook_strength", {})
    if hook.get("emotion_trigger"):
        print(f"           Hook trigger : {hook['emotion_trigger'].upper()}")

    # Issues and fixes
    issues = report.get("top_issues", [])
    if issues:
        print(f"\n  TOP ISSUES:")
        for issue in issues:
            print(f"    • {issue}")

    wins = report.get("quick_wins", [])
    if wins:
        print(f"\n  QUICK WINS:")
        for win in wins:
            print(f"    → {win}")

    print("\n" + "="*60)

# ── MAIN ─────────────────────────────────────────────────────────────────────
def run(video_path: str, script_path: str = None):
    if not Path(video_path).exists():
        print(f"[ERROR] Video not found: {video_path}")
        sys.exit(1)
    if not GROQ_API_KEY:
        print("[ERROR] GROQ_API_KEY not set in .env")
        sys.exit(1)
    if not GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY not set — get free key: aistudio.google.com/app/apikey")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  QC AGENT — {Path(video_path).name}")
    print(f"{'='*60}")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Step 1: Metadata
        print("[qc] Reading video metadata...")
        video_info = get_video_info(video_path)
        dur_gap    = round(video_info['duration'] - TARGET_DURATION, 1)
        dur_flag   = "✅" if abs(dur_gap) <= 5 else "⚠️ "
        print(f"[qc]   {dur_flag} Duration  : {video_info['duration']}s (target {TARGET_DURATION}s, gap {dur_gap:+.1f}s)")
        print(f"[qc]   Resolution: {video_info['aspect']}  Codec: {video_info['video_codec']}")
        print(f"[qc]   Audio     : {video_info['audio_codec']} {'✅' if video_info['has_audio'] else '❌'}")

        # Step 2: Transcription
        audio_path = extract_audio(video_path, tmpdir)
        transcript = transcribe_audio(audio_path)
        if transcript.get("text"):
            print(f"[qc]   Words     : {transcript.get('word_count', 0)} words @ {transcript.get('words_per_min', 0)} wpm")
            print(f"[qc]   Preview   : \"{transcript['text'][:80]}...\"")

        # Step 3: Frame analysis
        frames         = extract_frames(video_path, tmpdir)
        frame_analyses = analyze_all_frames(frames)

        # Step 4: Synthesize
        report = synthesize_report(video_info, transcript, frame_analyses, script_path)

    # Save
    report_path = Path(video_path).parent / "qc_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print_report(report, transcript)
    print(f"  Full report → {report_path}")
    return report


# ── AUTO-DETECT ───────────────────────────────────────────────────────────────
def find_latest_video() -> str:
    """Find the most recently generated final_video.mp4 in output/"""
    output_dir = Path("output")
    if not output_dir.exists():
        return None
    videos = sorted(
        output_dir.glob("*/final_video.mp4"),
        key=lambda p: p.parent.name,  # folder name is timestamp, sorts correctly
        reverse=True
    )
    return str(videos[0]) if videos else None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        video = find_latest_video()
        if not video:
            print("[ERROR] No video found in output/ — run the pipeline first")
            print("Usage  : python qc_agent.py output/RUN_ID/final_video.mp4")
            sys.exit(1)
        print(f"[qc] Auto-detected latest: {video}")
    else:
        video = sys.argv[1]

    script = sys.argv[2] if len(sys.argv) > 2 else str(Path(video).parent / "script_output.json")
    run(video, script)

