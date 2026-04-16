"""
agents/qc_agent.py — Pure QC logic. No file I/O, no retries, no logging.

analyze_frame(img_bytes, timestamp, index) → dict
synthesize_report(video_info, transcript, frame_analyses, script_data) → dict
"""

import base64
import json
import re

import requests

from core.config import (
    GROQ_URL, GROQ_API_KEY,
    VISION_MODEL, LLM_MODEL,
    TARGET_DURATION, LLM_TIMEOUT
)

# ── VISION — analyze one frame ────────────────────────────────────────────────
FRAME_PROMPT = """\
You are a QC reviewer for short-form social media videos (TikTok/Reels/Shorts).
Analyze this video frame. Be specific and actionable.
Return ONLY valid JSON — no markdown, no preamble.

{
  "lighting":         {"score": 1-10, "issue": "specific problem or null"},
  "composition":      {"score": 1-10, "issue": "specific problem or null"},
  "text_readability": {"score": 1-10, "issue": "specific problem or null"},
  "visual_quality":   {"score": 1-10, "issue": "specific problem or null"},
  "mood":             "one word",
  "dominant_colors":  ["color1", "color2"],
  "quick_fix":        "single most impactful fix, or null"
}\
"""

def analyze_frame(img_bytes: bytes, timestamp: float, index: int) -> dict:
    """
    Send one frame to Groq vision model.
    Returns analysis dict. Caller handles retries.
    """
    b64 = base64.b64encode(img_bytes).decode()

    payload = {
        "model": VISION_MODEL,
        "max_tokens": 400,
        "temperature": 0.2,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                },
                {
                    "type": "text",
                    "text": FRAME_PROMPT
                }
            ]
        }]
    }

    try:
        resp = requests.post(
            f"{GROQ_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type":  "application/json"
            },
            json=payload,
            timeout=LLM_TIMEOUT
        )
    except requests.exceptions.Timeout:
        return {"frame": index, "timestamp": timestamp, "error": "timeout"}
    except requests.exceptions.ConnectionError:
        return {"frame": index, "timestamp": timestamp, "error": "connection_error"}

    if resp.status_code == 429:
        return {"frame": index, "timestamp": timestamp, "error": "429"}

    if resp.status_code != 200:
        return {
            "frame": index,
            "timestamp": timestamp,
            "error": f"HTTP {resp.status_code}: {resp.text[:120]}"
        }

    raw = resp.json()["choices"][0]["message"]["content"].strip()
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        return {"frame": index, "timestamp": timestamp, "error": f"json_parse: {e}"}

    result["frame"]     = index
    result["timestamp"] = timestamp
    return result


# ── SYNTHESIS — score everything into one report ──────────────────────────────
def synthesize_report(
    video_info:      dict,
    transcript:      dict,
    frame_analyses:  list,
    script_data:     dict = None
) -> dict:
    """
    Build a full QC report from all collected data.
    Calls Groq LLaMA to score and produce verdict + reasons.
    """
    # Build script context snippet (keep it short — token cost)
    script_ctx = ""
    if script_data:
        hook  = script_data.get("hook", "n/a")
        cta   = script_data.get("cta",  "n/a")
        scenes = script_data.get("scenes", [])
        scene_texts = " | ".join(s.get("text", "")[:60] for s in scenes[:4])
        script_ctx = (
            f"\nSCRIPT CONTEXT:\n"
            f"  Hook  : {hook}\n"
            f"  CTA   : {cta}\n"
            f"  Scenes: {scene_texts}\n"
        )

    # Serialize frame data compactly
    frames_summary = []
    for f in frame_analyses:
        if "error" in f:
            frames_summary.append(f"Frame {f.get('frame','?')} @ {f.get('timestamp','?')}s — ERROR: {f['error']}")
            continue
        scores = {
            k: f[k]["score"]
            for k in ("lighting", "composition", "text_readability", "visual_quality")
            if k in f and isinstance(f[k], dict)
        }
        issues = [
            f[k]["issue"]
            for k in ("lighting", "composition", "text_readability", "visual_quality")
            if k in f and isinstance(f[k], dict) and f[k].get("issue")
        ]
        frames_summary.append(
            f"Frame {f.get('frame')} @ {f.get('timestamp')}s | "
            f"scores={scores} | mood={f.get('mood','?')} | "
            f"issues={issues} | fix={f.get('quick_fix','none')}"
        )

    dur_actual = video_info.get("duration", 0)
    dur_gap    = round(dur_actual - TARGET_DURATION, 1)
    wpm        = transcript.get("words_per_min", 0)
    transcript_preview = transcript.get("text", "")[:120]

    prompt = f"""You are a strict video QC evaluator for short-form social content (TikTok/Reels/Shorts).
Target duration: {TARGET_DURATION}s. Target resolution: 720x1280.
{script_ctx}
VIDEO METADATA:
  Duration : {dur_actual}s (gap from target: {dur_gap:+.1f}s)
  Resolution: {video_info.get('aspect', 'unknown')}
  Has audio: {video_info.get('has_audio', False)}
  Audio codec: {video_info.get('audio_codec', 'none')}

AUDIO / TRANSCRIPT:
  Words     : {transcript.get('word_count', 0)}
  WPM       : {wpm} (target: ~80 wpm)
  Preview   : "{transcript_preview}"

FRAME ANALYSES:
{chr(10).join(frames_summary)}

SCORING RULES:
- Score each dimension 1-10 based on evidence above
- overall_score = weighted avg: visual(30%) + audio(25%) + hook(20%) + pacing(15%) + sync(10%)
- verdict:
    >= 7.5 → publish
    6.0-7.4 → fix_minor
    4.0-5.9 → fix_major
    < 4.0   → reject
- acc_reject_reason: one clear sentence explaining why verdict was given
- top_issues: specific, actionable — NOT generic like "improve audio"
- quick_wins: concrete fixes producer can do in <30 min

Return ONLY valid JSON, no markdown, no preamble:
{{
  "duration_score":  {{"score": 1-10, "gap_seconds": {dur_gap}, "note": "..."}},
  "audio_score":     {{"score": 1-10, "clarity": "clear|muffled|robotic|natural", "speaking_rate": "{wpm} wpm — fast|normal|slow", "transcript_preview": "...", "note": "..."}},
  "visual_score":    {{"score": 1-10, "worst_frame": 1-2, "worst_issue": "...", "avg_lighting": 1-10, "avg_composition": 1-10, "note": "..."}},
  "sync_score":      {{"score": 1-10, "note": "..."}},
  "hook_strength":   {{"score": 1-10, "hook_text": "...", "emotion_trigger": "curiosity|fear|fomo|wonder|none", "note": "..."}},
  "pacing_score":    {{"score": 1-10, "note": "..."}},
  "overall_score":   1-10,
  "verdict":         "publish|fix_minor|fix_major|reject",
  "acc_reject_reason": "one sentence — specific reason for accept or reject",
  "top_issues":      ["...", "...", "..."],
  "quick_wins":      ["...", "..."],
  "publish_risk":    "low|medium|high"
}}\
"""

    try:
        resp = requests.post(
            f"{GROQ_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type":  "application/json"
            },
            json={
                "model":       LLM_MODEL,
                "max_tokens":  1000,
                "temperature": 0.2,
                "messages":    [{"role": "user", "content": prompt}]
            },
            timeout=LLM_TIMEOUT
        )
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)

    except json.JSONDecodeError as e:
        return {"error": f"json_parse: {e}", "raw": raw[:300]}
    except Exception as e:
        return {"error": str(e)}

