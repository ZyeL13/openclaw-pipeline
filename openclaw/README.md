touch /mnt/user-data/outputs/openclaw/agents/__init__.py
touch /mnt/user-data/outputs/openclaw/workers/__init__.py
touch /mnt/user-data/outputs/openclaw/memory/.gitkeep
touch /mnt/user-data/outputs/openclaw/data/.gitkeep

cat > /mnt/user-data/outputs/openclaw/README.md << 'EOF'
# OpenClaw Pipeline

Autonomous AI video pipeline — runs from Android Termux or any Linux VPS.

## Structure

```
├── core/
│   ├── config.py        ← all env vars + constants
│   ├── queue.py         ← JSON job queue
│   └── orchestrator.py  ← pipeline flow
├── agents/              ← pure logic, no I/O
│   ├── script_agent.py
│   ├── visual_agent.py
│   ├── voice_agent.py
│   ├── edit_agent.py
│   └── qc_agent.py
├── workers/             ← retries + file I/O + logging
│   ├── worker_script.py
│   ├── worker_visual.py
│   ├── worker_voice.py
│   ├── worker_edit.py
│   └── worker_qc.py
├── data/
│   └── queue.json
├── memory/
│   ├── best_performance.json
│   └── failed_cases.json
├── output/
└── main.py
```

## Setup

```bash
pip install requests edge-tts python-dotenv
pkg install ffmpeg  # Termux
```

`.env`:
```
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

## Run

```bash
# Scan RSS + process 1 video
python main.py --scan

# Check queue
python main.py --status

# Manual headline
python main.py --push "Bitcoin hits new ATH" --tone 3

# Process next in queue
python main.py

# Cron (daily 9am)
0 9 * * * cd ~/konten && source ~/.env && python main.py --scan
```
EOF

echo "Done"
