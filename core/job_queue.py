"""
core/job_queue.py — JSON-based job queue.
Phase 1 Hardening: file locking, atomic write, safe read.
"""
import json
import hashlib
import tempfile
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from filelock import FileLock  # pip install filelock

from core.config import QUEUE_FILE

log = logging.getLogger("queue")
LOCK_FILE = QUEUE_FILE.with_suffix(".lock")

# ── JOB SCHEMA ───────────────────────────────────────────────────────────────
def new_job(headline: str, source: str = "", tone: int = 0, lang: str = "en") -> dict:
    """Create new job with clean keys (no trailing spaces)."""
    job_id = hashlib.md5(headline.strip().lower().encode()).hexdigest()[:8]
    return {
        "id": job_id,
        "headline": headline,
        "source": source,
        "tone": tone,
        "lang": lang,
        "status": "pending",
        "retry_count": 0,
        "max_retry": 3,  # Phase 1: explicit max retry
        "steps": {
            "script": False,
            "visual": False,
            "voice": False,
            "edit": False,
            "qc": False,
        },
        "run_dir": "",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "error": "",
    }

# ── SAFE READ/WRITE WITH LOCKING ─────────────────────────────────────────────
def _acquire_lock():
    """Context manager wrapper for FileLock."""
    return FileLock(str(LOCK_FILE), timeout=10)

def load() -> list:
    """Safe read with lock + fallback to [] on any error."""
    with _acquire_lock():
        if not QUEUE_FILE.exists():
            return []
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Validate it's a list
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, PermissionError, OSError) as e:
            log.warning(f"Queue read failed: {e} — returning empty")
            return []

def save(jobs: list):
    """Atomic write: temp file → rename, with lock."""
    with _acquire_lock():
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temp file first
        fd, tmp_path = tempfile.mkstemp(
            dir=QUEUE_FILE.parent,
            prefix=".queue_",
            suffix=".tmp"
        )
        try:
            with open(fd, "w", encoding="utf-8") as f:
                json.dump(jobs, f, ensure_ascii=False, indent=2)
            # Atomic rename
            Path(tmp_path).rename(QUEUE_FILE)
        except Exception as e:
            log.error(f"Queue write failed: {e}")
            # Cleanup temp file on failure
            Path(tmp_path).unlink(missing_ok=True)
            raise

# ── CRUD OPERATIONS ──────────────────────────────────────────────────────────
def push(headline: str, source: str = "", tone: int = 0, lang: str = "en") -> dict:
    """Add job to queue. Skips if headline already exists."""
    jobs = load()
    # FIX: Use .get() for backward compat with old jobs that may have "headline "
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
    # FIX: Safe .get() for backward compat
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
        # FIX: .get() for safe access
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
                    job[k] = v  # Direct assign for known keys
            job["updated_at"] = datetime.now().isoformat()
            break
    save(jobs)

def mark_step(job_id: str, step: str, success: bool = True):
    update(job_id, steps={step: success})

def mark_running(job_id: str):
    update(job_id, status="processing")  # Phase 1: use "processing" not "running"

def mark_done(job_id: str):
    update(job_id, status="done")

def mark_failed(job_id: str, error: str = ""):
    update(job_id, status="failed", error=error)

def pending_count() -> int:
    return sum(1 for j in load() if j.get("status") == "pending")

def summary() -> dict:
    jobs = load()
    counts = {"pending": 0, "processing": 0, "done": 0, "failed": 0}
    for j in jobs:
        s = j.get("status", "pending")
        counts[s] = counts.get(s, 0) + 1
    return counts
