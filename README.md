🤖 konten-pipeline 🎬
Autonomous AI Video Production Factory — Running 100% from Android Termux.
$0/month. No Cloud GPU. No Laptop. No PC.


🚀 The Stack (Pure Free Tier)
| Step | Tool | Model / Engine | Cost |
|---|---|---|---|
| Brain | Groq API | LLaMA 3.3 70B | $0 |
| Voice | Edge TTS | Microsoft Neural (id-ID / en-US) | $0 |
| Visual | Pollinations | FLUX.1 [schnell] | $0 |
| Editor | FFmpeg | Ken Burns + Auto-Subtitle | $0 |


📦 Features
 * 📱 Mobile Native: Dioptimalkan khusus untuk lingkungan Termux.
 * 📈 Short-Form Ready: Output 9:16 (720×1280) untuk TikTok, Reels, & Shorts.
 * 🎭 10 Emotional Tones: Dari Dark Mysterious sampai Gen-Z Slang.
 * 🛡️ Smart Deduplication: Menghindari pengolahan berita yang sama berulang kali.


🛠️ Project Structure
konten/
├── main.py             # Main Entry Point
├── news_scanner.py     # Crypto & AI News Scraper
├── agents/             # Brain Logic (Script, Voice, Visual, QC)
├── core/               # Orchestrator & Configuration
├── workers/            # Async Task Runners
└── data/               # Logs, JSON Queues, & Cache


⚡ Quick Start (Termux)
# Install Dependencies
pkg update && pkg upgrade -y
pkg install python ffmpeg -y
pip install requests edge-tts gtts python-dotenv

# Setup Environment
echo "GROQ_API_KEY=your_key_here" > .env

# Run Automated Pipeline
python konten/main.py

📂 Output Preview
Setiap proses akan menghasilkan folder unik di dalam output/:
 * final_video.mp4: Hasil akhir siap upload.
 * voice.mp3: Narasi hasil Edge-TTS.
 * scenes/: Kumpulan gambar FLUX per scene.

