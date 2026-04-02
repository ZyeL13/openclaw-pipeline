"""
agents/edit_agent.py — Pure FFmpeg video assembly logic.
No file I/O decisions. No logging.
"""

import textwrap
import subprocess
from pathlib import Path
from core.config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS,
    SUBTITLE_FONT_SIZE, SUBTITLE_FONT_COLOR, SUBTITLE_BOX_COLOR
)


def get_audio_duration(audio_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0", audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except Exception:
        return 61.0


def make_scene_clip(img_path: str, duration: float, out_path: str) -> bool:
    """PNG → video clip with Ken Burns zoom. Returns True on success."""
    zoom_speed   = 0.0005
    total_frames = int(duration * VIDEO_FPS)

    vf = (
        f"scale={VIDEO_WIDTH*2}:{VIDEO_HEIGHT*2},"
        f"zoompan=z='min(zoom+{zoom_speed},1.05)':"
        f"d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={VIDEO_FPS},"
        f"format=yuv420p"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", img_path,
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        out_path
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=120)
    return result.returncode == 0


def concat_clips(clip_paths: list, list_file: str, out_path: str) -> bool:
    with open(list_file, "w") as f:
        for p in clip_paths:
            f.write(f"file '{Path(p).resolve()}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c", "copy", out_path
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    return result.returncode == 0


def add_audio(video_path: str, audio_path: str, out_path: str) -> bool:
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path, "-i", audio_path,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-shortest", out_path
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    return result.returncode == 0


def _clean_subtitle(text: str, max_chars: int = 42) -> str:
    """
    Clean and wrap subtitle text for FFmpeg drawtext.
    - Use textwrap for proper word boundaries (no mid-word splits)
    - Max 2 lines
    - Escape FFmpeg special chars
    """
    # Remove characters that break FFmpeg drawtext
    for ch in ["'", ":", "[", "]", "\\", "\n", "\r"]:
        text = text.replace(ch, " ")
    # Collapse multiple spaces
    text = " ".join(text.split())

    # Wrap at word boundaries
    lines = textwrap.wrap(text, width=max_chars)
    lines = lines[:2]  # max 2 lines

    return "\\n".join(lines)


def add_subtitles(video_path: str, scenes: list, audio_duration: float, out_path: str) -> bool:
    total_scenes = len(scenes)
    scene_dur    = audio_duration / total_scenes
    filters      = []

    for i, scene in enumerate(scenes):
        start      = i * scene_dur
        end        = start + scene_dur - 0.3
        raw_text   = scene.get("text", "")
        if not raw_text:
            continue

        # Clean and wrap properly
        text = _clean_subtitle(raw_text)

        filters.append(
            f"drawtext=text='{text}':"
            f"fontsize={SUBTITLE_FONT_SIZE}:"
            f"fontcolor={SUBTITLE_FONT_COLOR}:"
            f"borderw=2:bordercolor=black:"           # outline — readable on any bg
            f"box=1:boxcolor={SUBTITLE_BOX_COLOR}:boxborderw=10:"
            f"x=(w-text_w)/2:"
            f"y=h*0.75-text_h:"                       # 75% down — above social UI
            f"enable='between(t,{start:.2f},{end:.2f})'"
        )

    vf = ",".join(filters) if filters else "null"
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy", out_path
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=180)
    return result.returncode == 0


def upgrade_audio_quality(mp3_path: str, out_path: str) -> bool:
    """Upgrade 48kbps mono → 128kbps stereo."""
    cmd = [
        "ffmpeg", "-y", "-i", mp3_path,
        "-codec:a", "libmp3lame",
        "-b:a", "128k", "-ac", "2", "-ar", "44100",
        out_path
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0

