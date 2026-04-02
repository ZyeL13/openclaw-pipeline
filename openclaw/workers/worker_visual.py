"""
workers/worker_visual.py — Visual worker.
Handles retries, file saving, logging.
"""

import json
import logging
import time
from pathlib import Path
from datetime import datetime

from agents.visual_agent import build_prompt, fetch_image

log = logging.getLogger("worker.visual")
MAX_RETRIES = 3
RETRY_DELAY = 30


def run(script_data: dict, run_dir: Path) -> bool:
    scenes     = script_data.get("scenes", [])
    scenes_dir = run_dir / "scenes"
    scenes_dir.mkdir(exist_ok=True)

    log.info(f"Generating {len(scenes)} scene images")

    results = []
    success = 0

    for scene in scenes:
        sid    = scene.get("id", 0)
        visual = scene.get("visual", "")
        prompt = build_prompt(visual)
        out    = scenes_dir / f"scene_{sid}.png"

        img_bytes = None
        for attempt in range(MAX_RETRIES):
            log.info(f"  scene_{sid} attempt {attempt+1}/{MAX_RETRIES}")
            log.debug(f"  prompt: {prompt[:80]}")
            img_bytes = fetch_image(prompt, sid)
            if img_bytes:
                break
            log.warning(f"  scene_{sid} failed, waiting {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)

        if img_bytes:
            with open(out, "wb") as f:
                f.write(img_bytes)
            log.info(f"  scene_{sid}.png ({len(img_bytes)//1024}KB)")
            success += 1
            results.append({"scene_id": sid, "ok": True, "prompt": prompt[:80]})
        else:
            log.error(f"  scene_{sid} all attempts failed")
            results.append({"scene_id": sid, "ok": False, "prompt": prompt[:80]})

        time.sleep(20)  # Pollinations rate limit

    with open(run_dir / "visual_log.json", "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total"       : len(scenes),
            "success"     : success,
            "scenes"      : results
        }, f, indent=2)

    log.info(f"Visual done: {success}/{len(scenes)}")
    return success == len(scenes)

