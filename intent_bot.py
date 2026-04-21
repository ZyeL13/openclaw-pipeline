"""
intent_bot.py — Content intent capture + brief optimizer
Run: python intent_bot.py [--debug]
"""
import os
import sys
import json
import uuid
import requests
from datetime import datetime
from pathlib import Path

# Import config
sys.path.insert(0, str(Path(__file__).parent))
from core.config import LLM_API_KEY, LLM_BASE, LLM_MODEL, TIMEOUT, QUEUE_FILE

DEBUG = "--debug" in sys.argv

def check_api_key():
    if not LLM_API_KEY:
        print("[ERROR] GROQ_API_KEY belum di-set.")
        print("        Jalankan: export GROQ_API_KEY='gsk_xxxxx'")
        sys.exit(1)

def llm_call(system: str, user: str, max_tokens: int = 300) -> str:
    payload = {
        "model": LLM_MODEL,
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    }
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        r = requests.post(
            f"{LLM_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=TIMEOUT
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        print("[ERROR] Gagal konek ke Groq API. Cek internet.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"[ERROR] LLM timeout (> {TIMEOUT}s).")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        if hasattr(r, 'status_code') and r.status_code == 401:
            print("[ERROR] API Key tidak valid. Cek GROQ_API_KEY-mu.")
        else:
            print(f"[ERROR] HTTP Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] LLM call gagal: {e}")
        sys.exit(1)

SYS_CLARIFIER = """
You are a content brief assistant for OpenClaw.
Pipeline output: short-form video (TikTok/Reels/Shorts), persona: THE AUDITOR.
Given a user's initial idea, generate EXACTLY 2-3 sharp clarification questions.
Output format — plain numbered list, zero preamble."""

SYS_SUMMARIZER = """
You are a content brief compiler.
Given a user's idea and answers, write a concise human-readable brief.
Max 3 sentences. Plain prose. No bullets."""

SYS_OPTIMIZER = """
You are a production prompt compiler.
Translate the creative brief into a machine-readable instruction string.
Format: [KEY:VALUE][KEY:VALUE]...
Required keys: TASK, STYLE, TONE, TOPIC, KEY_ELEMENTS, DURATION, LANG.
STYLE is always THE_AUDITOR. DURATION is always 15S.
Output ONLY the instruction string."""

def push_to_queue(job: dict) -> None:
    """Push job to queue file."""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    queue = []
    if QUEUE_FILE.exists():
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                queue = json.load(f)
        except json.JSONDecodeError:
            queue = []
    
    queue.append(job)
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)

def divider():
    print("─" * 48)
def thinking():
    print("\n🤔 ...\n")

def run() -> None:
    check_api_key()
    print("\n" + "=" * 48)
    print("  🦞 OPENCLAW / Intent Bot")
    print("  'quit' untuk keluar kapan aja")
    print("=" * 48 + "\n")

    # 1. User Idea
    divider()
    user_prompt = input("📝 Konten apa?\n > ").strip()
    if user_prompt.lower() == "quit" or not user_prompt:
        sys.exit(0)

    thinking()

    # 2. Clarification
    divider()
    print("📋 Pertanyaan klarifikasi:\n")
    questions = llm_call(SYS_CLARIFIER, f"User idea: {user_prompt}")
    print(questions)
    print()

    # 3. Answers
    divider()
    answers = input("✏️ Jawaban:\n > ").strip()
    if answers.lower() == "quit" or not answers:
        sys.exit(0)

    thinking()

    # 4. Brief Human
    summary_ctx = (
        f"User idea: {user_prompt}\n\n"
        f"Clarification questions:\n{questions}\n\n"
        f"User answers: {answers}"
    )
    brief_human = llm_call(SYS_SUMMARIZER, summary_ctx, max_tokens=150)

    divider()
    print("📄 Brief:\n")
    print(brief_human)
    print()

    # 5. Brief Technical
    brief_technical = llm_call(
        SYS_OPTIMIZER,
        f"Brief: {brief_human}",        max_tokens=120
    )
    # Sanitize newlines
    brief_technical = " ".join(brief_technical.splitlines()).strip()

    if DEBUG:
        divider()
        print(f"🔧 [DEBUG] Technical prompt:\n{brief_technical}\n")

    # 6. Confirm
    divider()
    confirm = input("🚀 Gas? (gas / batal)\n > ").strip().lower()

    if confirm != "gas":
        print("\n❌ BATAL — Pipeline tidak dijalankan.")
        sys.exit(0)

    # Build job
    job = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.utcnow().isoformat(),
        "source": "intent_bot",
        "brief_human": brief_human,
        "brief_technical": brief_technical,
        "status": "pending",
        "retry_count": 0,
        "best_score": None,
        "steps": {
            "script": False,
            "visual": False,
            "voice":  False,
            "qc":     False,
            "edit":   False
        }
    }

    push_to_queue(job)
    short_id = job["id"][:8]
    print(f"\n✅ [OK] Job {short_id}... masuk queue.")
    print("   Jalankan: python main.py --run-queue\n")

if __name__ == "__main__":
    run()
