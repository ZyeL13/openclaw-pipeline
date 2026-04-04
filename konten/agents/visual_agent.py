"""
agents/visual_agent.py — Image generation via Pollinations.ai
Free tier: Unlimited, no token needed. 
Optimized for Termux & OpenClaw Pipeline.
"""

import os
import requests
import urllib.parse
from core.config import IMAGE_WIDTH, IMAGE_HEIGHT, STYLE_PREFIX, AUDITOR_VISUAL_STYLE

# Pollinations tidak butuh token, jadi kita biarkan kosong atau hapus saja
POLLINATIONS_BASE_URL = "https://image.pollinations.ai/prompt/"

def build_prompt(visual_desc: str) -> str:
    # Gabungkan prefix style kamu dengan deskripsi visual
    return f"{STYLE_PREFIX}{AUDITOR_VISUAL_STYLE}{visual_desc}"

def fetch_image(prompt: str, scene_id: int) -> bytes | None:
    """
    Kirim prompt ke Pollinations → download langsung image bytes.
    Pollinations bersifat synchronous, tidak perlu polling queue.
    """
    
    # 1. Encode prompt agar aman untuk URL (spasi jadi %20, dll)
    encoded_prompt = urllib.parse.quote(prompt)
    
    # 2. Susun URL dengan parameter (model Flux, nologo agar bersih)
    # Kita tambahkan seed unik per scene_id agar gambar konsisten jika di-retry
    url = (
        f"{POLLINATIONS_BASE_URL}{encoded_prompt}?"
        f"model=flux&"
        f"width={IMAGE_WIDTH}&"
        f"height={IMAGE_HEIGHT}&"
        f"nologo=true&"
        f"seed={scene_id * 42}"
    )

    try:
        # Request langsung ke image provider
        # Timeout 60 detik karena flux kadang butuh waktu render
        resp = requests.get(url, timeout=60)
        
        if resp.status_code == 200:
            # Pastikan yang kita dapat benar-benar image, bukan HTML error
            if "image" in resp.headers.get("Content-Type", ""):
                return resp.content
            else:
                return None
    except Exception as e:
        # Log error bisa dilihat di pipeline.log lewat worker
        return None

    return None

