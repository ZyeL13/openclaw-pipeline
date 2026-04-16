"""
agents/edit_agent.py — FFmpeg video assembly.
Fixed: robust audio duration, aggressive subtitle cleaning, soft-edge overlay.
"""
import re
import textwrap
import subprocess
import logging
from pathlib import Path
from core.config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS,
    SUBTITLE_FONT_SIZE, SUBTITLE_FONT_COLOR, SUBTITLE_BOX_COLOR
)
log = logging.getLogger("agent.edit")
FFMPEG_TIMEOUT = 300  # 5 minutes max per FFmpeg call

def get_audio_duration(audio_path: str) -> float:
    """
    Robust audio duration reader with validation.
    Prevent mismatch between audio and video timeline.
    """
    path = Path(audio_path)
    if not path.exists() or path.stat().st_size < 1024:
        log.warning(f"Audio file too small or missing: {path}")
        return 45.0

    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        dur = float(result.stdout.strip())
        if dur <= 0 or dur > 120:
            log.warning(f"Invalid duration {dur}s from ffprobe — using 45s")
            return 45.0
        return dur
    except Exception as e:
        log.error(f"ffprobe failed: {e}")
        return 45.0

def make_scene_clip(img_path: str, duration: float, out_path: str) -> bool:
    """PNG -> H264 video clip with Ken Burns zoom. yuv420p for compatibility."""    
    zoom_speed = 0.0005
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
        "-pix_fmt", "yuv420p",
        out_path
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT)
    if result.returncode != 0:
        log.error(f"make_scene_clip failed: {result.stderr.decode()[-200:]}")
    return result.returncode == 0

def concat_clips(clip_paths: list, list_file: str, out_path: str) -> bool:
    with open(list_file, "w") as f:
        for p in clip_paths:
            f.write(f"file '{Path(p).absolute()}'\n")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        out_path
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT)
    Path(list_file).unlink(missing_ok=True)
    if result.returncode != 0:
        log.error(f"concat failed: {result.stderr.decode()[-200:]}")
    return result.returncode == 0

def add_audio(video_path: str, audio_path: str, out_path: str) -> bool:
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path, "-i", audio_path,
        "-c:v", "copy", "-c:a", "aac",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest", out_path
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT)
    if result.returncode != 0:
        log.error(f"add_audio failed: {result.stderr.decode()[-200:]}")
    return result.returncode == 0

def _clean_subtitle(text: str, max_chars: int = 24) -> str:
    """
    Aggressive word separation + typo cleanup for FFmpeg drawtext.
    Handles: "goodnconflict" -> "good conflict", "betweennthe" -> "between the"
    """
    text = re.sub(r'[^\w\s,.\-!?]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    stuck_pairs = [
        ("goodn", "good "),
        ("badn", "bad "),
        ("thenn", "then "),
        ("betweenn", "between "),
        ("the", " the "),
        ("andn", "and "),
        ("orn", "or "),
        ("inb", "in "),
        ("withn", "with "),
        ("forr", "for "),
        ("tob", "to "),
        ("atn", "at "),
        ("ofn", "of "),
        ("vestn", "vest "),
        ("billionsn", "billions "),
        ("Anthropic", "Anthropic "),
    ]
    for wrong, right in stuck_pairs:
        text = re.sub(rf'\b{wrong}\b', right, text, flags=re.IGNORECASE)

    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z])\1{2,}', r'\1\1', text)

    lines = textwrap.wrap(text, width=max_chars, break_long_words=False, replace_whitespace=False)
    return "\\n".join(lines[:2])

def add_subtitles(video_path: str, scenes: list, audio_dur: float, out_path: str, scene_durs: list = None) -> bool:
    if scene_durs and len(scene_durs) == len(scenes):
        dur_list = scene_durs
    else:
        per = audio_dur / max(len(scenes), 1)
        dur_list = [per] * len(scenes)
    
    filters = []
    curr = 0.0

    for i, scene in enumerate(scenes):
        dur = dur_list[i]
        text = _clean_subtitle(scene.get("text", ""))
        if not text:
            curr += dur
            continue

        start = round(curr, 3)
        end = round(curr + dur - 0.2, 3)

        filters.append(
            f"drawtext=text='{text}':"
            f"fontsize={SUBTITLE_FONT_SIZE}:"
            f"fontcolor={SUBTITLE_FONT_COLOR}:"
            f"borderw=2:bordercolor=black:"
            f"box=1:boxcolor={SUBTITLE_BOX_COLOR}:boxborderw=12:"
            f"x=max(20\\,(w-text_w)/2):"
            f"y=h*0.65-text_h:"
            f"line_spacing=6:"
            f"enable='between(t,{start},{end})'"
        )
        curr += dur

    if not filters:
        import shutil
        shutil.copy(video_path, out_path)
        return True

    vf = ", ".join(filters)
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        out_path
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT)
    if result.returncode != 0:
        log.error(f"add_subtitles failed: {result.stderr.decode()[-300:]}")
    return result.returncode == 0

def add_character_overlay_blended(video_path: str, character_path: str, out_path: str, position: str = "bottom-left", scale: int = 280, opacity: float = 0.95, feather: int = 20) -> bool:
    pos_map = {
        "bottom-left": ("30", "H-h-30"),
        "bottom-right": ("W-w-30", "H-h-30"),
        "top-left": ("30", "30"),
        "top-right": ("W-w-30", "30"),
    }
    x_pos, y_pos = pos_map.get(position, ("30", "H-h-30"))
    
    filter_complex = (
        f"[1:v]scale={scale}:-1,format=rgba,"
        f"split[chr][alpha];"
        f"[alpha]extractplanes=a[luma];"
        f"[luma]boxblur={feather}:1[blurred];"
        f"[chr][blurred]alphamerge[char];"
        f"[char]colorchannelmixer=aa={opacity}[char_fade];"
        f"[0:v][char_fade]overlay={x_pos}:{y_pos}:format=auto"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", character_path,
        "-filter_complex", filter_complex,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        out_path
    ]

    result = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT)
    if result.returncode != 0:
        log.error(f"overlay failed: {result.stderr.decode()[-200:]}")
    return result.returncode == 0

def upgrade_audio_quality(mp3_path: str, out_path: str) -> bool:
    cmd = [
        "ffmpeg", "-y", "-i", mp3_path,
        "-codec:a", "libmp3lame",
        "-b:a", "128k", "-ac", "2", "-ar", "44100",
        out_path
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0
