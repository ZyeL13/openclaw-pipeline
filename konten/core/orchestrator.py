"""
core/orchestrator.py — Pipeline flow manager.
Pulls jobs from queue, runs workers in sequence, updates status.
"""

import logging
from pathlib import Path
from datetime import datetime

from core import queue as Q
from core.config import OUTPUT_DIR

from workers.worker_script import run as run_script
from workers.worker_visual import run as run_visual
from workers.worker_voice  import run as run_voice
from workers.worker_edit   import run as run_edit
from workers.worker_qc     import run as run_qc

log = logging.getLogger("orchestrator")


def _make_run_dir(job_id: str) -> Path:
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUTPUT_DIR / f"{ts}_{job_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "scenes").mkdir(exist_ok=True)
    return run_dir


def run_job(job: dict) -> bool:
    """
    Execute full pipeline for one job.
    Returns True if all steps succeeded.
    """
    job_id   = job["id"]
    headline = job["headline"]
    tone     = job["tone"]
    lang     = job.get("lang", "en")

    log.info(f"[{job_id}] START — {headline[:60]}")
    log.info(f"[{job_id}] tone={tone}  lang={lang}")

    run_dir = _make_run_dir(job_id)
    Q.mark_running(job_id)
    Q.update(job_id, run_dir=str(run_dir))

    # ── STEP 1: SCRIPT ────────────────────────────────────────────────────────
    log.info(f"[{job_id}] Step 1/5 — script")
    script_data = run_script(headline=headline, tone=tone, run_dir=run_dir)
    if not script_data:
        Q.mark_failed(job_id, "script generation failed")
        log.error(f"[{job_id}] FAILED at script")
        return False
    Q.mark_step(job_id, "script")

    # ── STEP 2: VISUAL ────────────────────────────────────────────────────────
    log.info(f"[{job_id}] Step 2/5 — visual")
    visual_ok = run_visual(script_data=script_data, run_dir=run_dir)
    if not visual_ok:
        Q.mark_failed(job_id, "visual generation failed")
        log.error(f"[{job_id}] FAILED at visual")
        return False
    Q.mark_step(job_id, "visual")

    # ── STEP 3: VOICE ─────────────────────────────────────────────────────────
    log.info(f"[{job_id}] Step 3/5 — voice")
    voice_ok = run_voice(script_data=script_data, lang=lang, run_dir=run_dir)
    if not voice_ok:
        Q.mark_failed(job_id, "voice generation failed")
        log.error(f"[{job_id}] FAILED at voice")
        return False
    Q.mark_step(job_id, "voice")

    # ── STEP 4: EDIT ──────────────────────────────────────────────────────────
    log.info(f"[{job_id}] Step 4/5 — edit")
    edit_ok = run_edit(script_data=script_data, run_dir=run_dir)
    if not edit_ok:
        Q.mark_failed(job_id, "video assembly failed")
        log.error(f"[{job_id}] FAILED at edit")
        return False
    Q.mark_step(job_id, "edit")

    # ── STEP 5: QC ────────────────────────────────────────────────────────────
    log.info(f"[{job_id}] Step 5/5 — qc")
    qc_ok = run_qc(run_dir=run_dir)
    Q.mark_step(job_id, "qc", success=qc_ok)  # QC failure does not block publish

    Q.mark_done(job_id)
    log.info(f"[{job_id}] DONE → {run_dir}")
    return True


def run_next(skip_qc: bool = False) -> bool:
    """Pull and process the next pending job. Returns False if queue empty."""
    job = Q.pop_pending()
    if not job:
        log.info("Queue empty — nothing to process")
        return False
    return run_job(job)


def run_all(max_jobs: int = 10) -> dict:
    """Process up to max_jobs pending jobs sequentially."""
    results = {"done": 0, "failed": 0, "skipped": 0}

    for _ in range(max_jobs):
        job = Q.pop_pending()
        if not job:
            break
        success = run_job(job)
        if success:
            results["done"] += 1
        else:
            results["failed"] += 1

    summary = Q.summary()
    log.info(f"run_all done: {results} | queue: {summary}")
    return results
