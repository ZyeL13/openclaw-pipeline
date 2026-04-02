"""
agents/qc_agent.py — Pure QC analysis logic.
No file I/O. No retries. No logging.
Takes raw data, returns report dict.
"""

import json
import re
import base64
import requests
from datetime import datetime
from core.config import (
    GROQ_API_KEY, GROQ_URL, GROQ_MODEL,
    GEMINI_API_KEY, GEMINI_URL,
    TARGET_DURATION, QC_N_FRAMES, QC_FRAME_DELAY
)


def analyze_frame(img_bytes: bytes, timestamp: float, frame_index: int) -> dict:
    """Analyze one frame via Gemini Flash REST API."""
    img_b64 = base64.b64encode(img_bytes).decode()

    prompt = """Analyze this frame from a TikTok/Reels/Shorts video.
Return ONLY valid JSON, no markdown.

{
  "lighting":         {"score": 1-10, "issue": "specific problem or null"},
  "composition":      {"score": 1-10, "issue": "specific problem or null"},
  "text_readability": {"score": 1-10, "issue": "specific problem or null"},
  "visual_quality":   {"score": 1-10, "issue": "specific problem or null"},
  "mood"            : "one word",
  "dominant_colors" : ["color1", "color2"],
  "quick_fix"       : "most impactful improvement or null"
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

    try:
        resp = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json=body, timeout=30
        )
        if resp.status_code != 200:
            return {"frame": frame_index, "timestamp": timestamp,
                    "error": f"Gemini {resp.status_code}"}

        raw    = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        raw    = re.sub(r'```json|```', '', raw).strip()
        result = json.loads(raw)
        result["timestamp"] = timestamp
        result["frame"]     = frame_index
        return result
    except Exception as e:
        return {"frame": frame_index, "timestamp": timestamp, "error": str(e)}


def synthesize_report(
    video_info     : dict,
    transcript     : dict,
    frame_analyses : list,
    script_data    : dict = None
) -> dict:
    """Synthesize all signals into final QC report via Groq LLaMA."""
    script_context = ""
    if script_data:
        script_context = f"""
ORIGINAL SCRIPT:
  Hook : {script_data.get('hook', 'n/a')}
  CTA  : {script_data.get('cta', 'n/a')}
  Tone : {script_data.get('_source', {}).get('tone', 'unknown')}
"""

    prompt = f"""You are a social media video QC analyst for TikTok/Reels/Shorts.
{script_context}
VIDEO DATA:
{json.dumps({
    "video_info"    : video_info,
    "transcript"    : transcript,
    "frame_analyses": frame_analyses,
    "target_duration": TARGET_DURATION,
}, indent=2)}

Return ONLY this exact JSON, no markdown:
{{
  "duration_score": {{
    "score": 1-10, "actual_seconds": {video_info.get('duration',0)},
    "target_seconds": {TARGET_DURATION},
    "gap_seconds": number,
    "verdict": "pass|short|long", "note": "one line"
  }},
  "audio_score": {{
    "score": 1-10, "clarity": "clear|muffled|robotic|natural",
    "speaking_rate": "{transcript.get('words_per_min',0)} wpm",
    "transcript_preview": "first 100 chars",
    "note": "one line"
  }},
  "visual_score": {{
    "score": 1-10, "worst_frame": 1-{QC_N_FRAMES},
    "worst_issue": "description",
    "avg_lighting": 1-10, "avg_composition": 1-10,
    "note": "one line"
  }},
  "sync_score"  : {{"score": 1-10, "note": "one line"}},
  "hook_strength": {{
    "score": 1-10, "hook_text": "first sentence",
    "emotion_trigger": "curiosity|fear|fomo|wonder|none",
    "note": "one line"
  }},
  "pacing_score": {{"score": 1-10, "note": "one line"}},
  "overall_score" : 1-10,
  "verdict"       : "publish|fix_minor|fix_major|reject",
  "top_issues"    : ["issue 1", "issue 2", "issue 3"],
  "quick_wins"    : ["fix 1", "fix 2"],
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
                "model"      : GROQ_MODEL,
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
