"""
main.py — OpenClaw entry point
"""
import sys
import json
import argparse
from pathlib import Path
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="openclaw",
        description="OpenClaw — Autonomous AI Video Pipeline"
    )
    parser.add_argument("--run-queue", action="store_true", help="Process queue")
    parser.add_argument("--scan",      action="store_true", help="Run news scanner")
    parser.add_argument("--job",       type=str, default=None, help="Re-run job by ID prefix")
    parser.add_argument("--debug",     action="store_true", help="Debug mode")
    args = parser.parse_args()

    def load_queue() -> list:
        q = Path("data/queue.json")
        if not q.exists():
            return []
        with open(q, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_intent_bot():
        extra = ["--debug"] if args.debug else []
        import subprocess
        subprocess.run([sys.executable, "intent_bot.py"] + extra)

    def run_queue():
        from core.orchestrator import run_job
        
        queue = load_queue()
        pending = [j for j in queue if j["status"] == "pending"]

        if not pending:
            print("[INFO] Queue kosong — tidak ada job pending.")
            return

        print(f"[INFO] {len(pending)} job pending ditemukan.\n")
        for job in pending:
            brief = job.get("brief_technical", job.get("headline", ""))[:60]
            print(f"[RUN] Job {job['id'][:8]}... — {brief}")
            run_job(job)

    def run_scanner():
        try:
            import news_scanner
            news_scanner.run()
        except ImportError:
            print("[ERROR] news_scanner.py tidak ditemukan.")
            sys.exit(1)

    def run_specific_job(job_id_prefix: str):
        from core.orchestrator import run_job
        from core import job_queue as core_queue
        
        queue = load_queue()
        matches = [j for j in queue if j["id"].startswith(job_id_prefix)]

        if not matches:
            print(f"[ERROR] Job dengan prefix '{job_id_prefix}' tidak ditemukan.")
            sys.exit(1)

        job = matches[0]
        print(f"[RUN] Re-running job {job['id'][:8]}...")
        
        core_queue.update(
            job["id"],
            status="pending",
            steps={s: False for s in job["steps"]},
            retry_count=0
        )
        run_job(job)

    if args.run_queue:
        run_queue()
    elif args.scan:
        run_scanner()
    elif args.job:
        run_specific_job(args.job)
    else:
        run_intent_bot()
