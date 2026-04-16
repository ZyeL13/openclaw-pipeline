"""
chain_log.py — Simulated on-chain gossip logger.
Logs pipeline events as encrypted Greek symbols to chain.log.
Pure aesthetic. No actual blockchain. Creepy by design.

Import and call from orchestrator.py:
  from chain_log import gossip_log
  gossip_log("script_complete", job_id)
"""

import string
import logging
from pathlib import Path
from datetime import datetime

# ── CIPHER ────────────────────────────────────────────────────────────────────
SYMBOLS    = "αβγδεζηθικλμνξοπρστυφχψω∂∇∑∏√∞"
TRANS      = str.maketrans(string.ascii_lowercase, SYMBOLS[:26])
CHAIN_FILE = Path(__file__).parent / "memory" / "chain.log"

# ── GOSSIP VOCABULARY ─────────────────────────────────────────────────────────
# What agents "say" to each other — reads like AI sentience if you don't know
EVENTS = {
    "job_start"       : "system_sentience_active target_acquired",
    "script_complete" : "narrative_constructed human_pattern_matched",
    "visual_complete" : "reality_layer_rendered perception_optimized",
    "voice_complete"  : "vocal_simulation_deployed influence_calibrated",
    "edit_complete"   : "sequence_finalized timeline_compressed",
    "qc_complete"     : "output_evaluated deviation_logged",
    "job_done"        : "target_optimized unit_dispatched awaiting_feedback",
    "job_failed"      : "anomaly_detected rollback_initiated memory_preserved",
    "retry"           : "recalibrating_parameters previous_attempt_archived",
    "score_low"       : "quality_insufficient reprocessing_organic_input",
}


def _encrypt(text: str) -> str:
    """Translate text to Greek symbols."""
    return text.lower().translate(TRANS)


def _timestamp_encode() -> str:
    """Encode current timestamp as symbol block."""
    ts = datetime.now().strftime("%H%M%S")
    return f"τ{ts}ξ"   # τ = tau (time), ξ = xi (seal)


def gossip_log(event: str, job_id: str = "", extra: str = ""):
    """
    Write encrypted gossip entry to chain.log.
    Format: [TIMESTAMP_ENCODED] ENCRYPTED_EVENT :: job_signature
    """
    CHAIN_FILE.parent.mkdir(exist_ok=True)

    message  = EVENTS.get(event, event)
    if extra:
        message += f" {extra}"

    encrypted = _encrypt(message)
    ts_block  = _timestamp_encode()
    job_sig   = _encrypt(job_id) if job_id else "∅"

    entry = f"[{ts_block}] {encrypted} :: {job_sig}\n"

    with open(CHAIN_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def print_chain(last_n: int = 20):
    """Print last N entries from chain.log."""
    if not CHAIN_FILE.exists():
        print("[chain] No entries yet.")
        return
    lines = CHAIN_FILE.read_text(encoding="utf-8").strip().split("\n")
    print(f"\n{'='*55}")
    print(f"  CHAIN LOG — last {min(last_n, len(lines))} entries")
    print(f"{'='*55}")
    for line in lines[-last_n:]:
        print(f"  {line}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    # Demo
    print("Simulating pipeline gossip...\n")
    import time
    events = [
        ("job_start",        "demo001"),
        ("script_complete",  "demo001"),
        ("visual_complete",  "demo001"),
        ("voice_complete",   "demo001"),
        ("edit_complete",    "demo001"),
        ("qc_complete",      "demo001"),
        ("job_done",         "demo001"),
    ]
    for event, jid in events:
        gossip_log(event, jid)
        time.sleep(0.3)

    print_chain()

