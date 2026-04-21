"""
core/orchestrator.py — Pipeline flow manager.
Pulls jobs from queue, runs workers in sequence, updates status.
Auto-retry if QC score < threshold (max 2 retries per job).
"""
import json
import shutil
import logging
import subprocess
import time
from pathlib import Path
from datetime import datetime

from core import job_queue as core_queue
from core.config import OUTPUT_DIR, BASE_DIR, QC_PASS_SCORE
from workers.worker_script import run as run_script
from workers.worker_visual import run as run_visual
from workers.worker_voice import run as run_voice
from workers.worker_edit import run as run_edit
from workers.worker_qc import run as run_qc

log = logging.getLogger("orchestrator")
MAX_RETRIES = 2

def make_run_dir(job_id: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    run_dir = OUTPUT_DIR / f"{ts}_{job_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "scenes").mkdir(exist_ok=True)
    return run_dir

def _read_qc_score(run_dir: Path) -> float:
    """Read overall_score from qc_report.json. Returns 0 if not found."""
    qc_path = run_dir / "qc_report.json"
    if not qc_path.exists():
        return 0.0
    try:
        report = json.loads(qc_path.read_text())
        return float(report.get("overall_score", 0))
    except Exception:
        return 0.0

def _trigger_kirim(run_dir: Path, job_id: str):
    """Trigger kirim.sh from project root."""
    kirim = BASE_DIR / "kirim.sh"
    if kirim.exists():
        log.info(f"[{job_id}] Sending via kirim.sh...")
        subprocess.run(["bash", str(kirim), str(run_dir)])
    else:
        log.warning(f"[{job_id}] kirim.sh not found at {kirim}")
def run_job(job: dict) -> bool:
    """Execute full pipeline for one job."""
    job_id = job["id"]
    headline = job.get("headline") or job.get("brief_human") or job.get("brief_technical") or "No headline"
    lang = job.get("lang", "en")
    retry_count = job.get("retry_count", 0)

    log.info(f"[{job_id}] START — {headline[:60]}")
    log.info(f"[{job_id}] lang={lang}  retry={retry_count}/{MAX_RETRIES}")

    run_dir = make_run_dir(job_id)
    core_queue.mark_running(job_id)
    core_queue.update(job_id, run_dir=str(run_dir))

    # STEP 1: SCRIPT
    log.info(f"[{job_id}] Step 1/5 — script")
    script_data = run_script(headline=headline, tone=0, run_dir=run_dir)
    if not script_data:
        core_queue.mark_failed(job_id, "script generation failed")
        log.error(f"[{job_id}] FAILED at script")
        return False
    core_queue.mark_step(job_id, "script")

    # STEP 2: VISUAL
    log.info(f"[{job_id}] Step 2/5 — visual")
    visual_ok = run_visual(script_data=script_data, run_dir=run_dir)
    if not visual_ok:
        core_queue.mark_failed(job_id, "visual generation failed")
        log.error(f"[{job_id}] FAILED at visual")
        return False
    core_queue.mark_step(job_id, "visual")

    # STEP 3: VOICE
    log.info(f"[{job_id}] Step 3/5 — voice")
    voice_ok = run_voice(script_data=script_data, lang=lang, run_dir=run_dir)
    if not voice_ok:
        core_queue.mark_failed(job_id, "voice generation failed")
        log.error(f"[{job_id}] FAILED at voice")
        return False
    core_queue.mark_step(job_id, "voice")

    # STEP 4: EDIT
    log.info(f"[{job_id}] Step 4/5 — edit")
    edit_ok = run_edit(script_data=script_data, run_dir=run_dir)
    if not edit_ok:
        core_queue.mark_failed(job_id, "video assembly failed")
        log.error(f"[{job_id}] FAILED at edit")
        return False
    core_queue.mark_step(job_id, "edit")
    # COOLDOWN sebelum QC
    log.info(f"[{job_id}] Waiting 60s before QC...")
    time.sleep(60)

    # STEP 5: QC
    log.info(f"[{job_id}] Step 5/5 — qc")
    run_qc(run_dir=run_dir)
    core_queue.mark_step(job_id, "qc", success=True)

    score = _read_qc_score(run_dir)
    log.info(f"[{job_id}] QC score: {score}/10 (threshold: {QC_PASS_SCORE})")

    # AUTO RETRY jika skor rendah tapi ada output
    if 0 < score < QC_PASS_SCORE:
        if retry_count >= MAX_RETRIES:
            log.warning(f"[{job_id}] Score {score}/10 below threshold after {retry_count} retries — accepting anyway")
        else:
            log.warning(f"[{job_id}] Score {score}/10 below threshold — deleting and retrying (attempt {retry_count + 1}/{MAX_RETRIES})")
            shutil.rmtree(run_dir, ignore_errors=True)
            core_queue.update(job_id,
                status="pending",
                error=f"Score {score}/10 — auto retry {retry_count + 1}",
                retry_count=retry_count + 1,
                steps={s: False for s in ["script", "visual", "voice", "edit", "qc"]}
            )
            return False

    # DONE
    core_queue.mark_done(job_id)
    log.info(f"[{job_id}] DONE → {run_dir.name}  score={score}/10")
    _trigger_kirim(run_dir, job_id)
    return True

def run_next() -> bool:
    """Pull and process the next pending job."""
    job = core_queue.pop_pending()
    if not job:
        log.info("Queue empty — nothing to process")
        return False
    return run_job(job)

def run_all(max_jobs: int = 10) -> dict:
    """Process up to max_jobs pending jobs sequentially."""
    results = {"done": 0, "failed": 0}
    for _ in range(max_jobs):
        job = core_queue.pop_pending()
        if not job:
            break
        success = run_job(job)
        if success:
            results["done"] += 1
        else:
            results["failed"] += 1
    log.info(f"run_all done: {results} | queue: {core_queue.summary()}")
    return results
