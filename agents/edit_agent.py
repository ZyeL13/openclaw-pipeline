"""
agents/edit_agent.py — FFmpeg video assembly (simplified).
"""
import subprocess
import logging
from pathlib import Path
from core.config import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS

log = logging.getLogger("agent.edit")
FFMPEG_TIMEOUT = 300

def get_audio_duration(audio_path: str) -> float:
    path = Path(audio_path)
    if not path.exists() or path.stat().st_size < 1024:
        log.warning(f"Audio file too small or missing: {path}")
        return 15.0
    cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        dur = float(result.stdout.strip())
        return dur if dur > 0 else 15.0
    except Exception as e:
        log.error(f"ffprobe failed: {e}")
        return 15.0

def make_scene_clip(img_path: str, duration: float, out_path: str) -> bool:
    zoom_speed = 0.0005
    total_frames = int(duration * VIDEO_FPS)
    vf = (
        f"scale={VIDEO_WIDTH*2}:{VIDEO_HEIGHT*2},"
        f"zoompan=z='min(zoom+{zoom_speed},1.05)':"
        f"d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={VIDEO_FPS},"
        f"format=yuv420p"
    )
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-vf", vf, "-t", str(duration), "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p", out_path]
    result = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT)
    if result.returncode != 0:
        log.error(f"make_scene_clip failed: {result.stderr.decode()[-200:]}")
    return result.returncode == 0

def concat_clips(clip_paths: list, list_file: str, out_path: str) -> bool:
    with open(list_file, "w") as f:
        for p in clip_paths:
            f.write(f"file '{Path(p).absolute()}'\n")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", out_path]
    result = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT)
    Path(list_file).unlink(missing_ok=True)
    if result.returncode != 0:
        log.error(f"concat failed: {result.stderr.decode()[-200:]}")
    return result.returncode == 0

def add_audio(video_path: str, audio_path: str, out_path: str) -> bool:
    cmd = ["ffmpeg", "-y", "-i", video_path, "-i", audio_path, "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0", "-shortest", out_path]
    result = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT)
    if result.returncode != 0:
        log.error(f"add_audio failed: {result.stderr.decode()[-200:]}")
    return result.returncode == 0
