"""
workers/worker_edit.py — Edit worker.
Handles temp dir, file paths, logging.
Calls edit_agent for pure FFmpeg logic.
"""

import logging
import shutil
from pathlib import Path

from agents.edit_agent import (
    get_audio_duration, make_scene_clip,
    concat_clips, add_audio, add_subtitles
)

log = logging.getLogger("worker.edit")


def run(script_data: dict, run_dir: Path) -> bool:
    """
    Assemble final video from scenes + voice.
    Returns True on success.
    """
    scenes_dir  = run_dir / "scenes"
    voice_file  = run_dir / "voice.mp3"
    output_file = run_dir / "final_video.mp4"
    tmp_dir     = run_dir / "tmp_edit"
    tmp_dir.mkdir(exist_ok=True)

    scenes = script_data.get("scenes", [])

    # ── Validate assets ───────────────────────────────────────────────────────
    missing = []
    for s in scenes:
        p = scenes_dir / f"scene_{s['id']}.png"
        if not p.exists():
            missing.append(str(p))
    if not voice_file.exists():
        missing.append(str(voice_file))
    if missing:
        log.error(f"Missing assets: {missing}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    # ── Get audio duration ────────────────────────────────────────────────────
    audio_dur = get_audio_duration(str(voice_file))
    log.info(f"Audio duration: {audio_dur:.1f}s  Scenes: {len(scenes)}")

    # ── Step 1: Make scene clips ──────────────────────────────────────────────
    log.info("Step 1/4 — scene clips (Ken Burns)")
    clip_paths = []
    per_scene  = audio_dur / len(scenes)

    for scene in scenes:
        sid      = scene["id"]
        img_path = str(scenes_dir / f"scene_{sid}.png")
        out_path = str(tmp_dir / f"clip_{sid}.mp4")

        ok = make_scene_clip(img_path, per_scene, out_path)
        if ok:
            clip_paths.append(out_path)
            log.info(f"  clip_{sid}.mp4 ({per_scene:.1f}s)")
        else:
            log.warning(f"  clip_{sid} failed — skipping")

    if not clip_paths:
        log.error("All clips failed")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    # ── Step 2: Concat ────────────────────────────────────────────────────────
    log.info("Step 2/4 — concat clips")
    list_file   = str(tmp_dir / "clips.txt")
    concat_path = str(tmp_dir / "concat.mp4")

    if not concat_clips(clip_paths, list_file, concat_path):
        log.error("Concat failed")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    # ── Step 3: Add audio ─────────────────────────────────────────────────────
    log.info("Step 3/4 — add voice")
    with_audio = str(tmp_dir / "with_audio.mp4")

    if not add_audio(concat_path, str(voice_file), with_audio):
        log.error("Audio merge failed")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    # ── Step 4: Burn subtitles ────────────────────────────────────────────────
    log.info("Step 4/4 — burn subtitles")
    ok = add_subtitles(with_audio, scenes, audio_dur, str(output_file))

    if not ok:
        log.warning("Subtitle burn failed — copying without subtitles")
        shutil.copy(with_audio, str(output_file))

    shutil.rmtree(tmp_dir, ignore_errors=True)

    if output_file.exists():
        size_mb = output_file.stat().st_size / (1024 * 1024)
        log.info(f"final_video.mp4 ({size_mb:.1f} MB  {audio_dur:.1f}s)")
        return True

    log.error("final_video.mp4 not created")
    return False
