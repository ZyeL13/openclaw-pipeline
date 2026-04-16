"""
memory_manager.py — Synthesize QC reports into best practices.
Reads all qc_report.json from output/ folders,
uses Groq to extract patterns, saves to memory/best_practices.json.

Run manually or add to cron after every 5 videos:
  python memory_manager.py
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv
load_dotenv()

import os
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1"
GROQ_MODEL   = "llama-3.3-70b-versatile"

BASE_DIR     = Path(__file__).parent
OUTPUT_DIR   = BASE_DIR / "output"
MEMORY_DIR   = BASE_DIR / "memory"
BEST_FILE    = MEMORY_DIR / "best_practices.json"
FAILED_FILE  = MEMORY_DIR / "failed_cases.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("memory_manager")


def collect_reports() -> list:
    """Collect all QC reports + paired script data from output folders."""
    reports = []

    for qc_path in sorted(OUTPUT_DIR.glob("*/qc_report.json")):
        run_dir     = qc_path.parent
        script_path = run_dir / "script_output.json"

        try:
            qc = json.loads(qc_path.read_text())
        except Exception:
            continue

        script = {}
        if script_path.exists():
            try:
                script = json.loads(script_path.read_text())
            except Exception:
                pass

        reports.append({
            "run_id"        : run_dir.name,
            "topic"         : script.get("topic", ""),
            "tone"          : script.get("_source", {}).get("tone", ""),
            "overall_score" : qc.get("overall_score", 0),
            "verdict"       : qc.get("verdict", ""),
            "duration_gap"  : qc.get("duration_score", {}).get("gap_seconds", 0),
            "audio_score"   : qc.get("audio_score", {}).get("score", 0),
            "visual_score"  : qc.get("visual_score", {}).get("score", 0),
            "hook_score"    : qc.get("hook_strength", {}).get("score", 0),
            "top_issues"    : qc.get("top_issues", []),
            "quick_wins"    : qc.get("quick_wins", []),
            "analyzed_at"   : qc.get("analyzed_at", ""),
        })

    return reports


def synthesize(reports: list) -> dict:
    """Use Groq to extract patterns and best practices from QC history."""
    if not reports:
        return {}

    prompt = f"""You are analyzing QC reports from an AI video pipeline called "openclaw".
The pipeline generates short-form videos (TikTok/Reels/Shorts) using a locked character voice
called "the auditor" — cold, precise, finds dark humor in finance and technology.

Here are all QC reports collected so far:
{json.dumps(reports, indent=2)}

Analyze these reports and return ONLY valid JSON with this structure:

{{
  "generated_at": "{datetime.now().isoformat()}",
  "total_videos_analyzed": {len(reports)},
  "avg_overall_score": number,
  "score_trend": "improving|declining|stable",

  "recurring_issues": [
    "issue that appears in 2+ reports"
  ],

  "best_practices": [
    "specific actionable instruction for script_agent or edit_agent"
  ],

  "script_instructions": [
    "instructions to improve script quality based on patterns"
  ],

  "avoid": [
    "things that consistently caused low scores"
  ],

  "top_performing": {{
    "run_id": "...",
    "score": number,
    "what_worked": "one line"
  }},

  "worst_performing": {{
    "run_id": "...",
    "score": number,
    "what_failed": "one line"
  }}
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
                "max_tokens" : 1500,
                "temperature": 0.3,
            },
            timeout=30
        )
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        log.error(f"Synthesis failed: {e}")
        return {}


def save_failed_cases(reports: list):
    """Save failed/low-scoring runs to failed_cases.json."""
    failed = [r for r in reports if r["overall_score"] < 6 or r["verdict"] in ("reject", "fix_major")]
    FAILED_FILE.write_text(json.dumps({
        "updated_at": datetime.now().isoformat(),
        "cases"     : failed
    }, indent=2))
    log.info(f"Saved {len(failed)} failed cases → {FAILED_FILE.name}")


def run():
    log.info("Memory Manager starting...")
    MEMORY_DIR.mkdir(exist_ok=True)

    reports = collect_reports()
    log.info(f"Collected {len(reports)} QC reports")

    if not reports:
        log.info("No reports found yet — run more videos first")
        return

    # Summary stats
    scores = [r["overall_score"] for r in reports if r["overall_score"] > 0]
    avg    = round(sum(scores) / len(scores), 1) if scores else 0
    log.info(f"Average score: {avg}/10 across {len(reports)} videos")

    # Synthesize best practices
    log.info("Synthesizing best practices via Groq...")
    practices = synthesize(reports)

    if practices:
        BEST_FILE.write_text(json.dumps(practices, indent=2, ensure_ascii=False))
        log.info(f"Best practices saved → {BEST_FILE.name}")

        # Print summary
        print(f"\n{'='*50}")
        print(f"  MEMORY UPDATE")
        print(f"{'='*50}")
        print(f"  Videos analyzed : {len(reports)}")
        print(f"  Avg score       : {avg}/10")
        print(f"  Trend           : {practices.get('score_trend', 'unknown')}")
        print(f"\n  RECURRING ISSUES:")
        for issue in practices.get("recurring_issues", [])[:3]:
            print(f"    • {issue}")
        print(f"\n  BEST PRACTICES:")
        for bp in practices.get("best_practices", [])[:3]:
            print(f"    → {bp}")
        print(f"{'='*50}\n")
    else:
        log.error("Synthesis returned empty — check Groq API")

    save_failed_cases(reports)


if __name__ == "__main__":
    if not GROQ_API_KEY:
        print("[ERROR] GROQ_API_KEY not set")
        sys.exit(1)
    run()

