"""
workers/worker_script.py — Worker untuk eksekusi script generation.
"""

import json
import logging
import time
from pathlib import Path
from agents.script_agent import generate_script, to_script_output
from core.config import SCRIPT_MIN_WORDS_TOTAL, SCRIPT_MIN_WORDS_SCENE

log = logging.getLogger("worker.script")

MAX_ATTEMPTS = 3
RETRY_DELAY = 15

def validate_word_count(script_data: dict) -> tuple[bool, str, dict]:
    """Validasi mendalam jumlah kata per adegan."""
    scenes = script_data.get("scenes", [])
    counts = [len(s.get("text", "").split()) for s in scenes]
    total = sum(counts)
    
    short_scenes = [i+1 for i, wc in enumerate(counts) if wc < SCRIPT_MIN_WORDS_SCENE]
    
    stats = {
        "total": total,
        "scenes": counts,
        "short_scenes": short_scenes
    }

    if short_scenes:
        return False, f"Adegan {short_scenes} terlalu singkat (min {SCRIPT_MIN_WORDS_SCENE} kata)", stats
    if total < SCRIPT_MIN_WORDS_TOTAL:
        return False, f"Total kata {total} belum mencapai target minimal {SCRIPT_MIN_WORDS_TOTAL}", stats
    
    return True, "✅ Valid", stats

def run(headline: str, tone: int, run_dir: Path) -> dict | None:
    """Menjalankan proses pembuatan naskah dengan retry logic."""
    script_file = run_dir / "script_output.json"
    best_script = None
    max_total_found = 0

    for attempt in range(MAX_ATTEMPTS):
        if attempt > 0:
            log.info(f"Menunggu {RETRY_DELAY} detik sebelum mencoba lagi...")
            time.sleep(RETRY_DELAY)

        log.info(f"Memulai Attempt {attempt+1}/{MAX_ATTEMPTS}")
        raw = generate_script(headline)
        
        if not raw:
            continue

        script_data = to_script_output(raw)
        is_valid, reason, stats = validate_word_count(script_data)
        
        log.info(f"  Statistik: {' + '.join(map(str, stats['scenes']))} = {stats['total']} kata")
        log.info(f"  Hasil: {reason}")

        # Simpan yang terbaik sebagai cadangan jika semua attempt gagal validasi
        if stats['total'] > max_total_found:
            max_total_found = stats['total']
            best_script = script_data

        if is_valid:
            log.info(f"✅ Naskah memenuhi syarat pada attempt {attempt+1}")
            best_script = script_data
            break

    if not best_script:
        log.error("❌ Gagal membuat naskah setelah semua percobaan.")
        return None

    # Proses Refinement (Opsional tapi disarankan)
    try:
        from agents.refiner_agent import refine_script
        log.info("Memperhalus naskah & menentukan emosi...")
        best_script = refine_script(best_script)
    except ImportError:
        log.warning("Refiner agent tidak ditemukan, melewati tahap perbaikan.")

    # Simpan hasil
    with open(script_file, "w", encoding="utf-8") as f:
        json.dump(best_script, f, ensure_ascii=False, indent=2)

    log.info(f"✅ Skrip disimpan di: {script_file.name} ({max_total_found} kata)")
    return best_script
