"""
core/queue.py — JSON-based job queue.
Simple, no external dependencies, OpenClaw-compatible structure.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from core.config import QUEUE_FILE


# ── JOB SCHEMA ────────────────────────────────────────────────────────────────
def new_job(headline: str, source: str = "", tone: int = 0, lang: str = "en") -> dict:
    return {
        "id"        : str(uuid.uuid4())[:8],
        "headline"  : headline,
        "source"    : source,
        "tone"      : tone,   # 0 = auto
        "lang"      : lang,
        "status"    : "pending",   # pending | running | done | failed
        "steps": {
            "script" : False,
            "visual" : False,
            "voice"  : False,
            "edit"   : False,
            "qc"     : False,
        },
        "run_dir"    : "",
        "created_at" : datetime.now().isoformat(),
        "updated_at" : datetime.now().isoformat(),
        "error"      : "",
    }


# ── LOAD / SAVE ───────────────────────────────────────────────────────────────
def load() -> list:
    if not QUEUE_FILE.exists():
        return []
    try:
        with open(QUEUE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save(jobs: list):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)


# ── CRUD ──────────────────────────────────────────────────────────────────────
def push(headline: str, source: str = "", tone: int = 0, lang: str = "en") -> dict:
    """Add a new job to the queue."""
    jobs = load()
    job  = new_job(headline, source, tone, lang)
    jobs.append(job)
    save(jobs)
    return job


def push_many(items: list) -> list:
    """
    Bulk push from news_scanner output.
    items: list of dicts with 'headline', 'source', optional 'relevance'
    Skips headlines already in queue (dedup by headline text).
    """
    jobs     = load()
    existing = {j["headline"] for j in jobs}
    added    = []

    for item in items:
        headline = item.get("headline", "").strip()
        if not headline or headline in existing:
            continue
        job = new_job(
            headline = headline,
            source   = item.get("source", ""),
            tone     = item.get("tone", 0),
            lang     = item.get("lang", "en"),
        )
        jobs.append(job)
        existing.add(headline)
        added.append(job)

    save(jobs)
    return added


def pop_pending() -> Optional[dict]:
    """Get the oldest pending job (FIFO). Returns None if empty."""
    jobs = load()
    for job in jobs:
        if job["status"] == "pending":
            return job
    return None


def update(job_id: str, **kwargs):
    """Update fields on a job by id."""
    jobs = load()
    for job in jobs:
        if job["id"] == job_id:
            for k, v in kwargs.items():
                if k == "steps" and isinstance(v, dict):
                    job["steps"].update(v)
                else:
                    job[k] = v
            job["updated_at"] = datetime.now().isoformat()
            break
    save(jobs)


def mark_step(job_id: str, step: str, success: bool = True):
    """Mark a pipeline step as done or failed."""
    update(job_id, steps={step: success})


def mark_running(job_id: str):
    update(job_id, status="running")


def mark_done(job_id: str):
    update(job_id, status="done")


def mark_failed(job_id: str, error: str = ""):
    update(job_id, status="failed", error=error)


def pending_count() -> int:
    return sum(1 for j in load() if j["status"] == "pending")


def summary() -> dict:
    jobs = load()
    counts = {"pending": 0, "running": 0, "done": 0, "failed": 0}
    for j in jobs:
        s = j.get("status", "pending")
        counts[s] = counts.get(s, 0) + 1
    return counts
