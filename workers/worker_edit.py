"""
workers/worker_edit.py — Edit worker with emotion-based character overlay.
Proportional subtitle timing. Config-driven overlay settings.
"""

import logging
import shutil
from pathlib import Path

from agents.edit_agent import (
    get_audio_duration, make_scene_clip,
    concat_clips, add_audio, add_subtitles,
    add_character_overlay_blended
)
from agents.refiner_agent import get_asset_for_emotion
from core.config import (
    CHAR_SCALE, CHAR_OPACITY, CHAR_POSITION,
    VIDEO_WIDTH, VIDEO_HEIGHT
)

log = logging.getLogger("worker.edit")

ASSETS_DIR = Path(__file__).parent.parent / "assets" / "auditor"


def _get_scene_id(scene: dict, idx: int) -> int:
    """Extract scene ID from either 'id' or 'scene' key."""
    return scene.get('id', scene.get('scene', idx + 1))


def run(script_data: dict, run_dir: Path) -> bool:
    scenes_dir  = run_dir / "scenes"
    voice_file  = run_dir / "voice.mp3"
    output_file = run_dir / "final_video.mp4"
    tmp_dir     = run_dir / "tmp_edit"
    tmp_dir.mkdir(exist_ok=True)

    scenes = script_data.get("scenes", [])

    # ── Validate ──────────────────────────────────────────────────────────────
    missing = []
    for idx, s in enumerate(scenes):
        sid = _get_scene_id(s, idx)
        p = scenes_dir / f"scene_{sid}.png"
        if not p.exists():
            missing.append(str(p))
    if not voice_file.exists():
        missing.append(str(voice_file))
    if missing:
        log.error(f"Missing assets: {missing}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    # ── Audio duration ────────────────────────────────────────────────────────
    audio_dur = get_audio_duration(str(voice_file))
    log.info(f"Audio: {audio_dur:.1f}s  Scenes: {len(scenes)}")

    # ── Proportional scene durations by word count, with MIN 12s per scene ───────────────
    scene_words = [len(s.get("text", "").split()) for s in scenes]
    total_words = sum(scene_words) or len(scenes)

    # Base proportional, but enforce minimum
    base_durs = [audio_dur * (w / total_words) for w in scene_words]
    min_dur   = 12.0  # seconds — minimal untuk visual + subtitle legible
    scene_durs = [max(d, min_dur) for d in base_durs]

    # If total exceeds audio_dur, scale down
    total_assigned = sum(scene_durs)
    if total_assigned > audio_dur:
        scale = audio_dur / total_assigned
        scene_durs = [d * scale for d in scene_durs]

    log.info(f"Scene durations (min 12s): {[round(d,1) for d in scene_durs]}")

    # ── Step 1: Scene clips ───────────────────────────────────────────────────
    log.info("Step 1/5 — scene clips (Ken Burns)")
    clip_paths = []

    for i, scene in enumerate(scenes):
        sid = _get_scene_id(scene, i)
        img_path = str(scenes_dir / f"scene_{sid}.png")
        out_path = str(tmp_dir / f"clip_{sid}.mp4")
        dur      = scene_durs[i]

        ok = make_scene_clip(img_path, dur, out_path)
        if ok:
            clip_paths.append(out_path)
            log.info(f"  clip_{sid}.mp4 ({dur:.1f}s)")
        else:
            log.warning(f"  clip_{sid} failed — skipping")

    if not clip_paths:
        log.error("All clips failed")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    # ── Step 2: Concat ────────────────────────────────────────────────────────
    log.info("Step 2/5 — concat")
    list_file   = str(tmp_dir / "clips.txt")
    concat_path = str(tmp_dir / "concat.mp4")

    if not concat_clips(clip_paths, list_file, concat_path):
        log.error("Concat failed")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    # ── Step 3: Add audio ─────────────────────────────────────────────────────
    log.info("Step 3/5 — add voice")
    with_audio = str(tmp_dir / "with_audio.mp4")

    if not add_audio(concat_path, str(voice_file), with_audio):
        log.error("Audio merge failed")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    # ── Step 4: Subtitles (proportional timing) ───────────────────────────────
    log.info("Step 4/5 — burn subtitles (proportional timing)")
    with_subtitle = str(tmp_dir / "with_subtitle.mp4")

    ok = add_subtitles(with_audio, scenes, audio_dur, with_subtitle,
                       scene_durs=scene_durs)
    if not ok:
        log.warning("Subtitle failed — using no-subtitle version")
        shutil.copy(with_audio, with_subtitle)

    # ── Step 5: Character overlay (emotion-based) ─────────────────────────────
    log.info("Step 5/5 — character overlay")

    if not ASSETS_DIR.exists():
        log.warning(f"Assets dir not found: {ASSETS_DIR} — skipping overlay")
        shutil.move(with_subtitle, str(output_file))
    else:
        final_path = str(output_file)
        asset_path = None

        for i, scene in enumerate(scenes):
            emotion    = scene.get("emotion", "neutral")
            asset_path = get_asset_for_emotion(emotion, str(ASSETS_DIR))
            if asset_path:
                log.info(f"  Using emotion '{emotion}' → {Path(asset_path).name}")
                break  # Use first available emotion's asset

        if asset_path:
            ok = add_character_overlay_blended(
                with_subtitle,
                asset_path,
                final_path,
                position = CHAR_POSITION,
                scale    = CHAR_SCALE,
                opacity  = CHAR_OPACITY
            )
            if ok:
                log.info(f"  Overlay added: {Path(asset_path).name}")
            else:
                log.warning("  Overlay failed — using subtitle-only")
                shutil.move(with_subtitle, final_path)
        else:
            log.warning("  No asset found for any emotion — skipping overlay")
            shutil.move(with_subtitle, final_path)

    if output_file.exists():
        size_mb = output_file.stat().st_size / (1024 * 1024)
        log.info(f"final_video.mp4 ({size_mb:.1f}MB  {audio_dur:.1f}s)")
        return True

    log.error("final_video.mp4 not created")
    return False
