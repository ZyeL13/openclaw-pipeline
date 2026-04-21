"""
core/job_queue.py — JSON-based job queue.
Simple, no external dependencies, OpenClaw-compatible structure.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional
from core.config import QUEUE_FILE

def new_job(headline: str, source: str = "", tone: int = 0, lang: str = "en") -> dict:
    job_id = hashlib.md5(headline.strip().lower().encode()).hexdigest()[:8]
    return {
        "id": job_id,
        "headline": headline,
        "source": source,
        "tone": tone,
        "lang": lang,
        "status": "pending",
        "retry_count": 0,
        "steps": {
            "script": False,
            "visual": False,
            "voice":  False,
            "edit":   False,
            "qc":     False,
        },
        "run_dir": "",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "error": "",
    }

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

def push(headline: str, source: str = "", tone: int = 0, lang: str = "en") -> dict:
    """Add job to queue. Skips if headline already exists."""
    jobs = load()    # FIX: Gunakan .get() agar tidak crash saat job lama tidak punya "headline"
    existing = next((j for j in jobs if j.get("headline") == headline), None)
    if existing:
        return existing
    job = new_job(headline, source, tone, lang)
    jobs.append(job)
    save(jobs)
    return job

def push_many(items: list) -> list:
    """Bulk push. Skips duplicates by headline text."""
    jobs = load()
    # FIX: Safe get() untuk backward compatibility
    existing = {j.get("headline") for j in jobs if j.get("headline")}
    added = []
    for item in items:
        headline = item.get("headline", "").strip()
        if not headline or headline in existing:
            continue
        job = new_job(
            headline=headline,
            source=item.get("source", ""),
            tone=item.get("tone", 0),
            lang=item.get("lang", "en"),
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
        if job.get("status") == "pending":
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
    update(job_id, steps={step: success})

def mark_running(job_id: str):
    update(job_id, status="running")

def mark_done(job_id: str):
    update(job_id, status="done")

def mark_failed(job_id: str, error: str = ""):
    update(job_id, status="failed", error=error)

def pending_count() -> int:
    return sum(1 for j in load() if j.get("status") == "pending")

def summary() -> dict:
    jobs = load()
    counts = {"pending": 0, "running": 0, "done": 0, "failed": 0}
    for j in jobs:
        s = j.get("status", "pending")
        counts[s] = counts.get(s, 0) + 1
    return counts
