"""
workers/worker_upload.py — YouTube Shorts uploader.
Uploads final_video.mp4 to YouTube as unlisted Shorts.
Requires token.json from auth_youtube.py (run once).

Upload only if QC score >= threshold.
"""

import json
import logging
import time
from pathlib import Path

log = logging.getLogger("worker.upload")

TOKEN_FILE      = Path(__file__).parent.parent / "token.json"
CLIENT_SECRETS  = Path(__file__).parent.parent / "client_secrets.json"
SCOPES          = ["https://www.googleapis.com/auth/youtube.upload"]

# Upload settings
DEFAULT_PRIVACY = "public"    # public | unlisted | private
CATEGORY_ID     = "28"        # Science & Technology
QC_UPLOAD_THRESHOLD = 8.0     # only upload if score >= this


def _get_credentials():
    """Load and refresh credentials from token.json."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        if not TOKEN_FILE.exists():
            log.error("token.json not found — run auth_youtube.py first")
            return None

        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json())
            log.info("Token refreshed")

        return creds
    except Exception as e:
        log.error(f"Auth failed: {e}")
        return None


def _build_metadata(script_data: dict, qc_data: dict = None) -> dict:
    """Build YouTube video metadata from script."""
    topic    = script_data.get("topic", "")
    hook     = script_data.get("hook", "")
    cta      = script_data.get("cta", "")
    hashtags = script_data.get("hashtags", [])
    caption  = script_data.get("caption", {})

    # Title: hook (max 100 chars)
    title = hook[:97] + "..." if len(hook) > 100 else hook
    if not title:
        title = topic[:100]

    # Description
    yt_caption = caption.get("yt_shorts", caption.get("tiktok", ""))
    desc_parts = []
    if yt_caption:
        desc_parts.append(yt_caption)
    if cta:
        desc_parts.append(f"\n{cta}")
    desc_parts.append("\n\n" + " ".join(f"#{h}" for h in hashtags[:10]))
    desc_parts.append("\n#Shorts #AI #Crypto")
    description = "\n".join(desc_parts)

    # Tags
    tags = hashtags + ["Shorts", "AI", "Crypto", "Bitcoin", "Technology"]

    return {
        "title"      : title,
        "description": description[:5000],
        "tags"       : tags[:500],
        "categoryId" : CATEGORY_ID,
    }


def upload(
    video_path : Path,
    script_data: dict,
    privacy    : str = DEFAULT_PRIVACY,
    qc_score   : float = 0.0
) -> str | None:
    """
    Upload video to YouTube.
    Returns YouTube video URL or None on failure.
    """
    if not video_path.exists():
        log.error(f"Video not found: {video_path}")
        return None

    # Check QC threshold
    if qc_score > 0 and qc_score < QC_UPLOAD_THRESHOLD:
        log.warning(f"QC score {qc_score} below upload threshold {QC_UPLOAD_THRESHOLD} — skipping upload")
        return None

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        log.error("pip install google-api-python-client --break-system-packages")
        return None

    creds = _get_credentials()
    if not creds:
        return None

    try:
        youtube  = build("youtube", "v3", credentials=creds)
        metadata = _build_metadata(script_data)

        log.info(f"Uploading: {video_path.name}")
        log.info(f"  Title  : {metadata['title']}")
        log.info(f"  Privacy: {privacy}")

        body = {
            "snippet": {
                "title"      : metadata["title"],
                "description": metadata["description"],
                "tags"       : metadata["tags"],
                "categoryId" : metadata["categoryId"],
            },
            "status": {
                "privacyStatus"             : privacy,
                "selfDeclaredMadeForKids"   : False,
                "madeForKids"               : False,
            }
        }

        media = MediaFileUpload(
            str(video_path),
            mimetype    = "video/mp4",
            resumable   = True,
            chunksize   = 1024 * 1024  # 1MB chunks
        )

        request  = youtube.videos().insert(
            part = "snippet,status",
            body = body,
            media_body = media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                log.info(f"  Upload progress: {progress}%")

        video_id  = response["id"]
        video_url = f"https://youtube.com/shorts/{video_id}"

        log.info(f"Upload complete → {video_url}")
        return video_url

    except Exception as e:
        log.error(f"Upload failed: {e}")
        return None


def run(run_dir: Path, script_data: dict, qc_score: float = 0.0, privacy: str = DEFAULT_PRIVACY) -> str | None:
    """
    Worker entry point.
    Returns YouTube URL or None.
    """
    video_path = run_dir / "final_video.mp4"

    if not TOKEN_FILE.exists():
        log.warning("token.json not found — skipping YouTube upload")
        log.warning("Run: python auth_youtube.py")
        return None

    url = upload(video_path, script_data, privacy=privacy, qc_score=qc_score)

    if url:
        # Save URL to run_dir
        result = {"youtube_url": url, "privacy": privacy, "qc_score": qc_score}
        (run_dir / "upload_result.json").write_text(json.dumps(result, indent=2))
        log.info(f"Saved upload result → upload_result.json")

    return url

