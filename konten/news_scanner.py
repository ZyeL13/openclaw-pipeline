import requests
import json
import hashlib
import os
import time
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

# ─── CONFIG ───────────────────────────────────────────────────────────
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID  = os.environ.get("TELEGRAM_CHAT_ID", "")

BASE_DIR       = "/data/data/com.termux/files/home"
SEEN_FILE      = f"{BASE_DIR}/news_seen.json"
LOG_FILE       = f"{BASE_DIR}/news.log"

MAX_POSTS      = 5
CANDIDATE_POOL = 12
ENABLE_THREAD  = False

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
    "tech layoff", "semiconductor", "chip", "nvidia", "data center",
    "cloud computing", "startup", "venture capital",
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
    "TechCrunch AI" : "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge"     : "https://www.theverge.com/rss/index.xml",
    "MIT Tech Review": "https://www.technologyreview.com/feed/",
    "BBC Tech"      : "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "CoinDesk"      : "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Decrypt"       : "https://decrypt.co/feed",
    "Cointelegraph" : "https://cointelegraph.com/rss",
}

# ─── DEDUP ────────────────────────────────────────────────────────────
DUPLICATE_TTL_HOURS = 6

def load_seen():
    if os.path.exists(SEEN_FILE):
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

def is_duplicate(hash_id, seen):
    if hash_id not in seen:
        return False
    return datetime.now() - seen[hash_id] <= timedelta(hours=DUPLICATE_TTL_HOURS)

def should_skip(title, link, seen):
    hash_id = make_hash(title, link)
    if is_duplicate(hash_id, seen):
        return True
    seen[hash_id] = datetime.now()
    return False

# ─── RSS FETCH ────────────────────────────────────────────────────────
def fetch_rss(name, url):
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        root = ET.fromstring(response.content)
        ns   = {"atom": "http://www.w3.org/2005/Atom"}
        items = []

        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            link  = item.findtext("link",  "").strip()
            desc  = item.findtext("description", "").strip()
            if title and link:
                items.append({"title": title, "link": link, "desc": desc[:400]})

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

# ─── GROQ GENERATE ────────────────────────────────────────────────────
def groq_generate(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 350,
        "temperature": 0.88,
    }
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers, json=body, timeout=30,
        )
        result = response.json()
        if "choices" not in result:
            log.error(f"Groq error: {json.dumps(result)}")
            return None
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.error(f"Groq request failed: {e}")
        return None

# ─── GENERATE POST ────────────────────────────────────────────────────
def generate_post(article, source):
    prompt = f"""kamu adalah "kultivator" — pemikir independen yang menulis di x dalam bahasa indonesia.

[persona]
tenang, observasional, tidak menggurui.
lebih banyak mengamati daripada menyimpulkan secara keras.
menghindari opini generik dan klise internet.

[input]
sumber: {source}
judul: {article['title']}
ringkasan: {article['desc']}

[guidelines]
- gunakan hanya informasi dari ringkasan. jangan menambah fakta baru.
- jika informasi tidak cukup, tetap buat refleksi tanpa mengarang detail spesifik.
- hindari klaim absolut.
- hindari kalimat klise seperti: "kita harus lebih waspada", "kita tidak bisa percaya", "ini sangat ironis"

[format]
- semua huruf lowercase
- tanpa hashtag
- tanpa emoji
- maksimal 180 kata
- bahasa indonesia natural (tidak kaku)
- istilah teknis boleh english lowercase

[struktur output]
baris 1-2: fragment pendek, menangkap esensi atau kontras
baris 3-6: refleksi utama + minimal 1 insight baru
baris 7: penutup reflektif (bukan pertanyaan, bukan ajakan)
baris 8: {article['link']}

[ritme]
variasikan panjang kalimat. boleh ada satu kalimat sangat pendek untuk penekanan.

output:"""
    return groq_generate(prompt)

# ─── QUALITY & SCORING ────────────────────────────────────────────────
def is_good_post(text):
    if not text:
        return False
    lines = text.strip().split("\n")
    if len(lines) < 6:
        return False
    bad_phrases = ["kita harus", "kita perlu", "ini sangat penting"]
    return not any(p in text for p in bad_phrases)

def virality_score(text):
    score = 0
    words = text.split()
    if 60 <= len(words) <= 140:
        score += 2
    lines = text.split("\n")
    if lines and len(lines[0].split()) <= 5:
        score += 2
    for t in ["tapi", "sementara", "justru", "yang menarik"]:
        if t in text:
            score += 1
    if any(g in text for g in ["kita harus", "kita perlu"]):
        score -= 2
    return score

def score_post(item):
    return item["relevance"] + virality_score(item["content"])

def generate_with_retry(article, source, retries=2):
    for attempt in range(retries):
        content = generate_post(article, source)
        if is_good_post(content):
            return content
        log.warning(f"Retry {attempt+1}: post not good enough for '{article['title'][:50]}'")
        time.sleep(1)
    return None

# ─── SEND TO TELEGRAM ─────────────────────────────────────────────────
def send_telegram(text, source, title):
    header = (
        f"📰 *{source}*\n"
        f"_{title[:80]}{'...' if len(title) > 80 else ''}_\n\n"
        f"─────────────────\n\n"
    )
    url     = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": header + text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    for attempt in range(2):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                log.info(f"Telegram sent: {title[:60]}")
                return True
            log.warning(f"Telegram error {response.status_code}: {response.text[:100]}")
        except Exception as e:
            log.warning(f"Telegram attempt {attempt+1} failed: {e}")
            if attempt < 1:
                time.sleep(3)
    log.error(f"Failed to send to Telegram: {title[:60]}")
    return False

# ─── EXPORT MODE (untuk pipeline integrasi) ───────────────────────────
def scan_to_queue(max_items: int = 5, output_file: str = "headline_queue.json") -> list:
    """
    Mode headless: scan RSS → score → simpan top headlines ke JSON.
    Tidak generate post, tidak kirim Telegram.
    """
    seen       = load_seen()
    candidates = []

    for source, url in RSS_FEEDS.items():
        if len(candidates) >= CANDIDATE_POOL:
            break
        articles = fetch_rss(source, url)
        for article in articles:
            if len(candidates) >= CANDIDATE_POOL:
                break
            if should_skip(article["title"], article["link"], seen):
                continue
            rel_score = relevance_score(article["title"], article["desc"])
            if rel_score == 0:
                continue
            candidates.append({
                "headline"  : article["title"],
                "source"    : source,
                "link"      : article["link"],
                "desc"      : article["desc"],
                "relevance" : rel_score,
                "scanned_at": datetime.now().isoformat(),
                "used"      : False,
            })

    candidates.sort(key=lambda x: x["relevance"], reverse=True)
    queue = candidates[:max_items]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    log.info(f"[scan_to_queue] {len(queue)} headlines → {output_file}")
    save_seen(seen)
    return queue

# ─── MAIN (mode telegram) ─────────────────────────────────────────────
def main():
    log.info("=" * 50)
    log.info("News Scanner Started")

    seen         = load_seen()
    candidates   = []
    skipped_dup  = 0
    skipped_irrel = 0

    for source, url in RSS_FEEDS.items():
        if len(candidates) >= CANDIDATE_POOL:
            break
        log.info(f"Fetching: {source}")
        articles = fetch_rss(source, url)

        for article in articles:
            if len(candidates) >= CANDIDATE_POOL:
                break
            if should_skip(article["title"], article["link"], seen):
                skipped_dup += 1
                continue
            rel_score = relevance_score(article["title"], article["desc"])
            if rel_score == 0:
                skipped_irrel += 1
                log.info(f"Not relevant: {article['title'][:60]}")
                continue
            log.info(f"Generating: {article['title'][:70]}")
            content = generate_with_retry(article, source)
            if not content:
                log.error(f"Generation failed: {article['title'][:60]}")
                continue
            candidates.append({
                "title"    : article["title"],
                "content"  : content,
                "relevance": rel_score,
                "source"   : source,
                "article"  : article,
            })
            time.sleep(1)

    candidates.sort(key=score_post, reverse=True)
    top_posts = candidates[:MAX_POSTS]

    new_count = 0
    for item in top_posts:
        sent = send_telegram(item["content"], item["source"], item["title"])
        if sent:
            new_count += 1
            time.sleep(2)

    save_seen(seen)
    log.info(f"""
SUMMARY:
- candidates: {len(candidates)}
- selected  : {len(top_posts)}
- sent      : {new_count}
- skip dup  : {skipped_dup}
- skip irrel: {skipped_irrel}
""")
    log.info("=" * 50)

# ─── ENTRYPOINT ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="telegram",
                    choices=["telegram", "queue"],
                    help="telegram = kirim ke TG | queue = export ke JSON")
    ap.add_argument("--max", default=5, type=int,
                    help="Jumlah headline (default: 5)")
    args = ap.parse_args()

    if args.mode == "queue":
        results = scan_to_queue(max_items=args.max)
        print(f"\n[OK] {len(results)} headlines in queue:")
        for i, r in enumerate(results, 1):
            print(f"  {i}. [{r['relevance']}★] {r['headline'][:70]}")
    else:
        main()

