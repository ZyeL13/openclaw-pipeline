"""
main.py — OpenClaw Pipeline Entry Point

Usage:
  python main.py                              # process 1 job from queue
  python main.py --max 3                      # process up to 3 jobs
  python main.py --scan                       # scan RSS → push → process 1
  python main.py --scan --max 0               # scan only, don't process
  python main.py --status                     # show queue status
  python main.py --push "headline here"       # add job to queue + process

  # Opsi C — manual assets (skip visual generation):
  python main.py --run-dir output/20260402_120000 --skip-visual
  python main.py --run-dir output/20260402_120000 --skip-visual --skip-voice
"""

import sys
import json
import argparse
import logging
from pathlib import Path

# ── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level    = logging.INFO,
    format   = "%(asctime)s [%(name)s] %(message)s",
    handlers = [
        logging.StreamHandler(),
        logging.FileHandler("pipeline.log", encoding="utf-8")
    ]
)
log = logging.getLogger("main")

# ── IMPORTS ───────────────────────────────────────────────────────────────────
from core import config, queue as Q
from core.orchestrator import run_next, run_all


# ── COMMANDS ──────────────────────────────────────────────────────────────────
def cmd_status():
    summary = Q.summary()
    jobs    = Q.load()
    print(f"\n{'='*50}")
    print(f"  QUEUE STATUS")
    print(f"{'='*50}")
    print(f"  Pending : {summary.get('pending', 0)}")
    print(f"  Running : {summary.get('running', 0)}")
    print(f"  Done    : {summary.get('done', 0)}")
    print(f"  Failed  : {summary.get('failed', 0)}")
    print(f"  Total   : {len(jobs)}")
    pending = [j for j in jobs if j["status"] == "pending"]
    if pending:
        print(f"\n  PENDING JOBS:")
        for j in pending[:5]:
            print(f"    [{j['id']}] {j['headline'][:60]}")
    print(f"{'='*50}\n")


def cmd_scan(max_jobs: int = 1):
    log.info("Scanning RSS feeds...")
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from news_scanner import scan_to_queue
        results = scan_to_queue(max_items=5)
    except ImportError:
        log.error("news_scanner.py not found in parent directory")
        return
    if not results:
        log.info("No new headlines found")
        return
    added = Q.push_many(results)
    log.info(f"Pushed {len(added)} new jobs to queue")
    if max_jobs > 0:
        run_all(max_jobs=max_jobs)


def cmd_push(headline: str):
    job = Q.push(headline)
    print(f"[OK] Job added: [{job['id']}] {headline[:60]}")


def cmd_run_dir(run_dir: Path, skip_visual: bool, skip_voice: bool):
    """
    Opsi C — run voice+edit+qc on a pre-prepared run_dir.
    Expects: run_dir/script_output.json + run_dir/scenes/scene_*.png
    Optionally skip voice if voice.mp3 already exists.
    """
    script_file = run_dir / "script_output.json"
    voice_file  = run_dir / "voice.mp3"

    if not script_file.exists():
        print(f"[ERROR] script_output.json not found in {run_dir}")
        print(f"        Create it first — see README for JSON format")
        return

    with open(script_file) as f:
        script_data = json.load(f)

    scenes_dir = run_dir / "scenes"
    scenes     = script_data.get("scenes", [])
    missing    = [s["id"] for s in scenes
                  if not (scenes_dir / f"scene_{s['id']}.png").exists()]
    if missing:
        print(f"[ERROR] Missing scene images: {[f'scene_{i}.png' for i in missing]}")
        print(f"        Copy them to {scenes_dir}/")
        return

    log.info(f"run-dir mode: {run_dir.name}")
    log.info(f"  skip_visual={skip_visual}  skip_voice={skip_voice}")
    log.info(f"  script: {script_data.get('topic','')[:60]}")
    log.info(f"  scenes: {len(scenes)}")

    # ── Voice ─────────────────────────────────────────────────────────────────
    if not skip_voice:
        if voice_file.exists():
            log.info("voice.mp3 already exists — skipping voice gen")
        else:
            from workers.worker_voice import run as run_voice
            ok = run_voice(script_data=script_data, lang="en", run_dir=run_dir)
            if not ok:
                log.error("Voice generation failed")
                return
    else:
        if not voice_file.exists():
            log.error("--skip-voice set but voice.mp3 not found")
            return

    # ── Edit ──────────────────────────────────────────────────────────────────
    from workers.worker_edit import run as run_edit
    ok = run_edit(script_data=script_data, run_dir=run_dir)
    if not ok:
        log.error("Video assembly failed")
        return

    # ── QC ────────────────────────────────────────────────────────────────────
    from workers.worker_qc import run as run_qc
    run_qc(run_dir=run_dir)

    video = run_dir / "final_video.mp4"
    if video.exists():
        size_mb = video.stat().st_size / (1024 * 1024)
        print(f"\n{'='*50}")
        print(f"  DONE → {run_dir.name}/final_video.mp4")
        print(f"  Size : {size_mb:.1f} MB")
        print(f"{'='*50}")

        # Trigger kirim.sh
        import subprocess
        kirim = Path.home() / "kirim.sh"
        if kirim.exists():
            subprocess.run(["bash", str(kirim)])
    else:
        log.error("final_video.mp4 not created")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="OpenClaw Pipeline")
    parser.add_argument("--scan",        action="store_true")
    parser.add_argument("--status",      action="store_true")
    parser.add_argument("--push",        type=str, default="")
    parser.add_argument("--max",         type=int, default=1)
    parser.add_argument("--run-dir",     type=str, default="",
                        help="Path to pre-prepared run folder (Opsi C)")
    parser.add_argument("--skip-visual", action="store_true",
                        help="Skip image generation (assets already in scenes/)")
    parser.add_argument("--skip-voice",  action="store_true",
                        help="Skip voice generation (voice.mp3 already exists)")
    args = parser.parse_args()

    config.validate()

    # ── Opsi C: manual run-dir ─────────────────────────────────────────────
    if args.run_dir:
        run_dir = Path(args.run_dir)
        if not run_dir.is_absolute():
            run_dir = Path.cwd() / run_dir
        if not run_dir.exists():
            print(f"[ERROR] Directory not found: {run_dir}")
            return
        cmd_run_dir(run_dir, skip_visual=True, skip_voice=args.skip_voice)
        return

    # ── Normal queue mode ──────────────────────────────────────────────────
    if args.status:
        cmd_status()
        return

    if args.push:
        cmd_push(args.push)
        if args.max > 0:
            run_next()
        return

    if args.scan:
        cmd_scan(max_jobs=args.max)
        return

    if Q.pending_count() == 0:
        print("[INFO] Queue empty. Run: --scan or --push 'headline'")
        cmd_status()
        return

    if args.max == 1:
        run_next()
    else:
        results = run_all(max_jobs=args.max)
        print(f"\nDone: {results['done']} succeeded, {results['failed']} failed")

    cmd_status()


if __name__ == "__main__":
    main()

