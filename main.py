"""
main.py — OpenClaw entry point

Usage:
  python main.py                  # launch intent bot (default)
  python main.py --run-queue      # process pending jobs in queue
  python main.py --scan           # run news scanner → push to queue
  python main.py --job <id>       # re-run specific job by ID prefix
  python main.py --debug          # pass debug flag to intent bot
"""

import sys
import json
import argparse
from pathlib import Path

# ── ARGS ─────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(
    prog="openclaw",
    description="OpenClaw — Autonomous AI Video Pipeline"
)
parser.add_argument("--run-queue", action="store_true", help="Process queue")
parser.add_argument("--scan",      action="store_true", help="Run news scanner")
parser.add_argument("--job",       type=str, default=None, help="Re-run job by ID prefix")
parser.add_argument("--debug",     action="store_true", help="Debug mode")
args = parser.parse_args()

# ── HELPERS ───────────────────────────────────────────────────────────────────
def load_queue() -> list:
    q = Path("data/queue.json")
    if not q.exists():
        return []
    with open(q, "r", encoding="utf-8") as f:
        return json.load(f)

def run_intent_bot():
    """Launch interactive intent bot."""
    # Pass --debug flag through if set
    extra = ["--debug"] if args.debug else []
    import subprocess, sys
    subprocess.run([sys.executable, "intent_bot.py"] + extra)

def run_queue():
    """Hand off pending jobs to orchestrator."""
    try:
        from core.orchestrator import Orchestrator
    except ImportError:
        print("[ERROR] core/orchestrator.py tidak ditemukan.")
        sys.exit(1)

    queue = load_queue()
    pending = [j for j in queue if j["status"] == "pending"]

    if not pending:
        print("[INFO] Queue kosong — tidak ada job pending.")
        return

    print(f"[INFO] {len(pending)} job pending ditemukan.\n")
    orch = Orchestrator()
    for job in pending:
        print(f"[RUN] Job {job['id'][:8]}... — {job['brief_technical'][:60]}")
        orch.run(job)

def run_scanner():
    """Run news scanner and push results to queue."""
    try:
        import news_scanner
        news_scanner.run()
    except ImportError:
        print("[ERROR] news_scanner.py tidak ditemukan.")
        sys.exit(1)

def run_specific_job(job_id_prefix: str):
    """Re-run a specific job from queue by ID prefix."""
    try:
        from core.orchestrator import Orchestrator
    except ImportError:
        print("[ERROR] core/orchestrator.py tidak ditemukan.")
        sys.exit(1)

    queue = load_queue()
    matches = [j for j in queue if j["id"].startswith(job_id_prefix)]

    if not matches:
        print(f"[ERROR] Job dengan prefix '{job_id_prefix}' tidak ditemukan.")
        sys.exit(1)

    job = matches[0]
    print(f"[RUN] Re-running job {job['id'][:8]}...")

    # Reset steps and status for re-run
    job["status"] = "pending"
    job["steps"] = {s: False for s in job["steps"]}
    job["retry_count"] = 0

    orch = Orchestrator()
    orch.run(job)

# ── ENTRY ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if args.run_queue:
        run_queue()
    elif args.scan:
        run_scanner()
    elif args.job:
        run_specific_job(args.job)
    else:
        # Default: intent bot
        run_intent_bot()

