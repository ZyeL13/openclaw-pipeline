```bash
nano README.md
```

```markdown
# AI Content Generation

> Autonomous video pipeline with intent bot + Groq LLM

## 🚀 Quick Start

### 1. Set API Key
```bash
export GROQ_API_KEY="gsk_xxxxx_kamu"
```

2. Run Intent Bot

```bash
python intent_bot.py
```

3. Or Run Pipeline

```bash
python main.py              # intent bot (default)
python main.py --scan       # news scanner mode
python main.py --run-queue  # process queue
```

---

📁 Structure

```
~/konten-pipeline/
├── intent_bot.py           # Chatbot konfirmasi intent
├── main.py                 # Entry point
│
├── agents/                 # AI agents
│   ├── script_agent.py
│   ├── visual_agent.py
│   ├── voice_agent.py
│   ├── qc_agent.py
│   └── edit_agent.py
│
├── workers/                # Pipeline workers
│   ├── worker_script.py
│   ├── worker_visual.py
│   ├── worker_voice.py
│   ├── worker_qc.py
│   ├── worker_edit.py
│   └── worker_upload.py
│
├── core/                   # Core modules
│   ├── config.py
│   ├── orchestrator.py
│   └── queue.py
│
└── memory/                 # Memory & logs
    ├── best_practices.json
    └── failed_cases.json
```

---

⚙️ Config (core/config.py)

Setting Value
Duration 15 seconds
Resolution 720x1280
LLM Groq (llama-3.3-70b)
Vision Groq (llama-3.2-11b-vision)

---

🎯 Intent Bot Flow

```
User prompt → 2-3 questions → User answers → Brief confirmation → "gas" → Queue
```

---

📦 Output

· Video: output/*.mp4
· Queue: data/queue.json
· Logs: *.log

---

🧹 Clean Commands

```bash
# Remove old files (already done in refactor)
rm -f *_skill.py konten/ -rf
```

---

🔧 Dependencies

```bash
pkg install openssh python ffmpeg
pip install requests openai-whisper
```

---

📄 License

Internal use only — THE AUDITOR

