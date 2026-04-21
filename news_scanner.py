"""
news_scanner.py — RSS Scanner & Pipeline Feeder.
Scan berita relevan -> Push ke queue video pipeline.
Run: python main.py --scan
"""
import os
import time
import json
import logging
import hashlib
import requests
from pathlib import Path
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

# Import Pipeline Queue
try:
    from core import job_queue as core_queue
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from core import job_queue as core_queue

# ─── CONFIG ───────────────────────────────────────────────────────────
GROQ_API_KEY       = os.environ.get("GROQ_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

BASE_DIR   = Path(__file__).parent
SEEN_FILE  = BASE_DIR / "news_seen.json"
LOG_FILE   = BASE_DIR / "news.log"

MAX_POSTS      = 5
CANDIDATE_POOL = 12

# ─── LOGGING ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# ─── KEYWORD FILTER ───────────────────────────────────────────────────
KEYWORDS = [
    "artificial intelligence", "machine learning", "deep learning",
    "llm", "large language model", "generative ai", "chatgpt", "openai",
    "anthropic", "gemini", "mistral", "ai model", "neural network",
    "automation", "robot", "autonomous", "computer vision",
    "tech layoff", "semiconductor", "chip", "nvidia", "data center",    "cloud computing", "startup", "venture capital",
    "teknologi", "kecerdasan buatan", "otomatisasi", "digitalisasi",
    "ekonomi digital", "startup indonesia", "ai indonesia",
    "bitcoin", "ethereum", "crypto", "defi", "web3", "blockchain",
    "token", "altcoin", "stablecoin", "sec crypto", "binance",
]

def relevance_score(title, desc):
    text = (title + " " + desc).lower()
    return sum(1 for kw in KEYWORDS if kw in text)

def is_relevant(title, desc):
    return relevance_score(title, desc) > 0

# ─── RSS SOURCES ──────────────────────────────────────────────────────
RSS_FEEDS = {
    "TechCrunch AI"  : "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge"      : "https://www.theverge.com/rss/index.xml",
    "MIT Tech Review": "https://www.technologyreview.com/feed/",
    "BBC Tech"       : "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "CoinDesk"       : "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Decrypt"        : "https://decrypt.co/feed",
    "Cointelegraph"  : "https://cointelegraph.com/rss",
}

# ─── DEDUP ────────────────────────────────────────────────────────────
DUPLICATE_TTL_HOURS = 6

def load_seen():
    if SEEN_FILE.exists():
        try:
            with open(SEEN_FILE, "r") as f:
                data = json.load(f)
            return {k: datetime.fromisoformat(v) for k, v in data.items()}
        except Exception as e:
            log.warning(f"load_seen failed: {e}")
    return {}

def save_seen(seen):
    items = list(seen.items())[-500:]
    data = {k: v.isoformat() for k, v in items}
    with open(SEEN_FILE, "w") as f:
        json.dump(data, f)

def make_hash(title, link):
    return hashlib.md5((title + link).strip().lower().encode()).hexdigest()

def should_skip(title, link, seen):
    hash_id = make_hash(title, link)
    if hash_id not in seen:        return False
    # Skip if seen recently
    return datetime.now() - seen[hash_id] <= timedelta(hours=DUPLICATE_TTL_HOURS)

# ─── RSS FETCH ────────────────────────────────────────────────────────
def fetch_rss(name, url):
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        root = ET.fromstring(response.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = []
        
        # Standard RSS
        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            link  = item.findtext("link", "").strip()
            desc  = item.findtext("description", "").strip()
            if title and link:
                items.append({"title": title, "link": link, "desc": desc[:400]})
        
        # Atom fallback
        if not items:
            for entry in root.findall(".//atom:entry", ns):
                title   = entry.findtext("atom:title", "", ns).strip()
                link_el = entry.find("atom:link", ns)
                link    = link_el.get("href", "") if link_el is not None else ""
                desc    = entry.findtext("atom:summary", "", ns).strip()
                if title and link:
                    items.append({"title": title, "link": link, "desc": desc[:400]})
        
        log.info(f"{name}: fetched {len(items)} items")
        return items[:8]
    except Exception as e:
        log.error(f"{name}: fetch failed — {e}")
        return []

# ─── PIPELINE INTEGRATION ─────────────────────────────────────────────
def run():
    """
    Scan RSS feeds -> Filter Relevan -> Push ke Video Queue.
    Fungsi ini dipanggil oleh main.py --scan.
    """
    log.info("=" * 40)
    log.info("News Scanner Started (Pipeline Mode)")
    
    seen = load_seen()
    added_count = 0

    for source, url in RSS_FEEDS.items():
        if added_count >= 5:  # Limit per run
            break
            
        articles = fetch_rss(source, url)
        for article in articles:
            if added_count >= 5:
                break
                
            if should_skip(article["title"], article["link"], seen):
                continue
            
            if not is_relevant(article["title"], article["desc"]):
                continue
            
            # Found relevant new article
            log.info(f"[+] Relevant: {article['title'][:60]}")
            
            # Push to pipeline queue
            try:
                core_queue.push(
                    headline=article["title"],
                    source=source,
                    tone=0,
                    lang="en"
                )
                added_count += 1
                
                # Mark as seen
                seen[make_hash(article["title"], article["link"])] = datetime.now()
                
            except Exception as e:
                log.error(f"Failed to push {article['title'][:50]}: {e}")

    save_seen(seen)
    
    log.info("=" * 40)
    log.info(f"Scan Done. Added {added_count} jobs to queue.")
    if added_count > 0:
        print(f"\n✅ {added_count} berita baru masuk antrian video.")
        print("   Jalankan: python main.py --run-queue")
    else:
        print("\nℹ️ Tidak ada berita relevan/baru ditemukan.")

# ─── MAIN (Legacy / Telegram Mode) ──────────────────────────────────────
def main():
    """Legacy mode: Generate posts and send to Telegram manually."""
    # Implementation omitted for brevity, use --scan for pipeline
    print("⚠️ Telegram mode deprecated. Use 'python main.py --scan' for pipeline.")

if __name__ == "__main__":    run()
