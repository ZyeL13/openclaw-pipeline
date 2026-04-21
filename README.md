# 🦞 OpenClaw — Autonomous AI Video Pipeline

Pipeline otomatis untuk menghasilkan video short-form (TikTok/Reels/Shorts) secara *autonomous*.
Dari scanning berita/gagasan → naskah → visual → voiceover → edit → QC → kirim.

## 📋 Fitur Utama
- 🤖 **Intent Bot**: Chat interface untuk membuat brief video secara interaktif.
- 📰 **News Scanner**: Scan RSS feeds (Tech/Crypto) & auto-push ke antrian pipeline.
- 🎨 **Multi-Agent**: Scripting (Groq), Visuals (Pollinations), Voice (Edge-TTS).
- 🎬 **FFmpeg Editor**: Auto-assembly, zoom-pan effect, audio mixing.
- 🔍 **Quality Control**: Otomatis check durasi, visual clarity, dan audio sync.
- 📡 **Delivery**: Auto-copy ke storage & notif Telegram (`kirim.sh`).
- 🔄 **Fallback System**: ClawRouter sebagai cadangan jika Groq limit/down.

---

## 🚀 Quick Start

### 1. Persiapan Environment
Pastikan Termux/Linux terupdate dan install dependency sistem:
```bash
# Termux dependencies
pkg update && pkg install python ffmpeg curl git -y

# Install python packages
pip install requests python-dotenv edge-tts gtts filelock Pillow
```

### 2. Setup Konfigurasi
Buat file `.env` di root folder:
```bash
nano .env
```
Isi dengan variabel berikut:
```env
# Groq API (LLM & Vision)
GROQ_API_KEY=gsk_xxxxxxxxxxxx
CLAWROUTER_BASE=http://127.0.0.1:8402/v1
CLAWROUTER_MODEL=claude-sonnet-4.6

# Telegram (untuk kirim.sh)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=987654321
```

### 3. Jalankan Pipeline
```bash
# 1. Jalankan Intent Bot (buat job baru via chat)
python main.py

# 2. Scan Berita & Auto-Queue
python main.py --scan

# 3. Proses Antrian (Run Workers)
python main.py --run-queue

# 4. Retry Job Tertentu
python main.py --job <prefix_id>
```

---

## 📁 Struktur Proyek
```
konten-pipeline/
├── main.py                 # Entry point utama
├── intent_bot.py           # Chat interface untuk brief
├── news_scanner.py         # RSS Scanner & Queue Feeder
├── kirim.sh                # Script delivery (Storage + Telegram)
│
├── core/                   # Logic Inti
│   ├── config.py           # Single source of truth (Paths, Keys, Settings)
│   ├── orchestrator.py     # Flow manager & Retry logic
│   └── job_queue.py        # Safe JSON Queue with locking
│
├── agents/                 # AI Logic (Pure functions)
│   ├── script_agent.py     # LLM prompting
│   ├── visual_agent.py     # Image generation requests
│   ├── voice_agent.py      # TTS (Edge-TTS)
│   ├── qc_agent.py         # Vision analysis
│   └── edit_agent.py       # FFmpeg commands
│
├── workers/                # Execution Layer
│   ├── worker_script.py    # Script generation + Validation
│   ├── worker_visual.py    # Image download + Processing
│   ├── worker_voice.py     # Audio generation + Upgrade
│   ├── worker_edit.py      # Video assembly (No subs/overlay by default)
│   └── worker_qc.py        # Quality check scoring
│
└── assets/                 # Static files (Logos, Fonts, etc.)
```

---

## ⚙️ Konfigurasi (core/config.py)
Nilai default yang bisa diubah sesuai kebutuhan:

| Setting | Value | Keterangan |
|---------|-------|------------|
| `VIDEO_DURATION` | 15 | Durasi target video (detik) |
| `SCRIPT_MAX_WORDS_TOTAL` | 22 | Batas maksimal kata (biar pas 15s) |
| `TTS_VOICE` | `en-US-GuyNeural` | Voice persona (The Auditor) |
| `VISION_MODEL` | `llama-3.2-90b-vision-preview` | Model Groq untuk QC |
| `QC_PASS_SCORE` | 7.5 | Skor minimal QC untuk dianggap lolos |

---

## 🛠️ Troubleshooting

**Error: `ffmpeg: not found`**
> Pastikan `ffmpeg` terinstall: `pkg install ffmpeg`

**Error: `GROQ_API_KEY belum di-set`**
> Cek file `.env` sudah ada di root atau jalankan `export GROQ_API_KEY="..."`

**Error: `Rate Limit (429)`**
> Pipeline otomatis switch ke **ClawRouter** (jika config benar).
> Tunggu cooldown Groq (biasanya 1 menit).

**Video kepanjangan / QC Gagal Duration?**
> Pastikan `SCRIPT_MAX_WORDS_TOTAL` di `config.py` sesuai dengan target durasi (sekitar 20-22 kata untuk 15 detik).

---
**"The machines got smarter. The questions stayed the same."**
*Project maintained for internal automation.*
```
