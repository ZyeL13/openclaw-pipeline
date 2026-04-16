"""
workers/worker_visual.py — Image generation worker.
Uses image.pollinations.ai API with retry logic.
"""
import json
import logging
import time
from pathlib import Path
from agents.visual_agent import build_prompt, fetch_best
from core.config import IMAGE_WIDTH, IMAGE_HEIGHT, IMAGE_MODEL

log = logging.getLogger("worker.visual")

MAX_RETRIES = 2

def _call_api(prompt: str, output_path: Path, scene_id: int) -> bool:
    """
    Call pollinations.ai to generate image.
    Returns True if image saved successfully.
    """
    try:
        # Fetch best of 2 images with different seeds
        image_bytes = fetch_best(prompt, scene_id)
        
        if image_bytes and len(image_bytes) > 1024:  # >1KB
            output_path.write_bytes(image_bytes)
            size_kb = len(image_bytes) // 1024
            log.info(f"  {output_path.name} ({size_kb}KB)")
            return True
        else:
            log.warning(f"  Empty or invalid image returned")
            return False
    except Exception as e:
        log.warning(f"  Request failed: {e}")
        return False

def run(script_data: dict, run_dir: Path) -> bool:
    """
    Generate scene images based on script visuals.
    Returns True if ALL required images are generated.
    """
    scenes_dir = run_dir / "scenes"
    scenes_dir.mkdir(exist_ok=True)
    
    scenes = script_data.get("scenes", [])
    log.info(f"Generating {len(scenes)} scene images")
    
    success_count = 0
    for i, scene in enumerate(scenes):
        scene_id = scene.get("id", i + 1)
        beat = scene.get("beat", "unknown")
        text = scene.get("text", "")
        
        log.info(f"  scene_{scene_id} beat='{beat}'")
        
        # Build prompt using agent
        visual_prompt = build_prompt(text, beat, scene_id)
        
        output_path = scenes_dir / f"scene_{scene_id}.png"
        
        # Try with retry
        success = False
        for attempt in range(MAX_RETRIES + 1):
            if attempt > 0:
                log.info(f"  Retry {attempt}/{MAX_RETRIES}...")
                time.sleep(5)
            
            if _call_api(visual_prompt, output_path, scene_id):
                success = True
                break
        
        if success:
            success_count += 1
        else:
            log.warning(f"  scene_{scene_id} all attempts failed")
            # Hapus file kosong jika gagal
            output_path.unlink(missing_ok=True)
    
    log.info(f"Visual done: {success_count}/{len(scenes)}")
    return success_count == len(scenes)
