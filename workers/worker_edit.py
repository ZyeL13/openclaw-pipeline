"""
workers/worker_edit.py — Edit worker (simplified).
Flow: Scene Clips → Concat → Add Audio → Output.
No subtitles, no character overlay (manual editing via CapCut).
"""
import logging
import shutil
from pathlib import Path
from agents.edit_agent import get_audio_duration, make_scene_clip, concat_clips, add_audio

log = logging.getLogger("worker.edit")

def _get_scene_id(scene: dict, idx: int) -> int:
    return scene.get('id', scene.get('scene', idx + 1))

def run(script_data: dict, run_dir: Path) -> bool:
    scenes_dir  = run_dir / "scenes"
    voice_file  = run_dir / "voice.mp3"
    output_file = run_dir / "final_video.mp4"
    tmp_dir     = run_dir / "tmp_edit"
    tmp_dir.mkdir(exist_ok=True)
    scenes = script_data.get("scenes", [])

    # Validate assets
    missing = []
    for idx, s in enumerate(scenes):
        sid = _get_scene_id(s, idx)
        if not (scenes_dir / f"scene_{sid}.png").exists():
            missing.append(f"scene_{sid}.png")
    if not voice_file.exists():
        missing.append("voice.mp3")
    if missing:
        log.error(f"Missing assets: {missing}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    # Audio duration
    audio_dur = get_audio_duration(str(voice_file))
    log.info(f"Audio: {audio_dur:.1f}s  Scenes: {len(scenes)}")

    # Proportional scene durations by word count
    scene_words = [len(s.get("text", "").split()) for s in scenes]
    total_words = sum(scene_words) or len(scenes)
    base_durs = [audio_dur * (w / total_words) for w in scene_words]
    
    # FIX: min_dur 2.0s (bukan 12s) agar total video ~15s sesuai target
    min_dur = 2.0
    scene_durs = [max(d, min_dur) for d in base_durs]

    # Scale down if total exceeds audio
    total_assigned = sum(scene_durs)
    if total_assigned > audio_dur:
        scale = audio_dur / total_assigned
        scene_durs = [d * scale for d in scene_durs]

    log.info(f"Scene durations: {[round(d, 1) for d in scene_durs]}")

    # Step 1: Scene clips
    clip_paths = []
    for i, scene in enumerate(scenes):
        sid = _get_scene_id(scene, i)
        img_path = str(scenes_dir / f"scene_{sid}.png")
        out_path = str(tmp_dir / f"clip_{sid}.mp4")
        dur = scene_durs[i]
        if make_scene_clip(img_path, dur, out_path):
            clip_paths.append(out_path)
            log.info(f"  clip_{sid}.mp4 ({dur:.1f}s)")

    if not clip_paths:
        log.error("All clips failed")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    # Step 2: Concat
    list_file   = str(tmp_dir / "clips.txt")
    concat_path = str(tmp_dir / "concat.mp4")
    if not concat_clips(clip_paths, list_file, concat_path):
        log.error("Concat failed")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    # Step 3: Add audio -> Output final
    if not add_audio(concat_path, str(voice_file), str(output_file)):
        log.error("Audio merge failed")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    # Cleanup & Report
    shutil.rmtree(tmp_dir, ignore_errors=True)
    if output_file.exists():
        size_mb = output_file.stat().st_size / (1024 * 1024)
        log.info(f"final_video.mp4 created ({size_mb:.1f}MB  {audio_dur:.1f}s)")
        return True

    log.error("final_video.mp4 not created")
    return False
