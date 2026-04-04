"""
scanner.py — News scanner for openclaw pipeline.
Fetches RSS feeds, scores headlines, pushes to queue.

Run: python scanner.py              # scan + push to queue
     python scanner.py --dry-run    # preview only, don't push
     python scanner.py --max 10     # fetch up to 10 headlines
"""

import os
import sys
import json
import hashlib
import logging
import argparse
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv
load_dotenv()

# ── PATH SETUP ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from core import queue as Q
from core.config import GROQ_API_KEY, GROQ_URL, GROQ_MODEL

# ── CONFIG ────────────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent
SEEN_FILE      = BASE_DIR / "data" / "seen_headlines.json"
CANDIDATE_POOL = 15
DUPLICATE_TTL  = 6   # hours

log = logging.getLogger("scanner")

# ── RSS FEEDS ─────────────────────────────────────────────────────────────────
RSS_FEEDS = {
    "TechCrunch AI" : "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge"     : "https://www.theverge.com/rss/index.xml",
    "MIT Tech Review": "https://www.technologyreview.com/feed/",
    "CoinDesk"      : "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Decrypt"       : "https://decrypt.co/feed",
    "Cointelegraph" : "https://cointelegraph.com/rss",
}

# ── KEYWORDS ──────────────────────────────────────────────────────────────────
KEYWORDS = [
    "artificial intelligence", "machine learning", "llm", "generative ai",
    "chatgpt", "openai", "anthropic", "gemini", "ai model", "neural network",
    "automation", "autonomous", "nvidia", "semiconductor",
    "bitcoin", "ethereum", "crypto", "defi", "blockchain", "altcoin",
    "token", "stablecoin", "binance", "sec crypto", "web3",
    "startup", "venture capital", "tech layoff", "ipo",
]

# ── DEDUP ─────────────────────────────────────────────────────────────────────
def load_seen() -> dict:
    if SEEN_FILE.exists():
        try:
            data = json.loads(SEEN_FILE.read_text())
            return {k: datetime.fromisoformat(v) for k, v in data.items()}
        except Exception:
            pass
    return {}

def save_seen(seen: dict):
    data = {k: v.isoformat() for k, v in list(seen.items())[-500:]}
    SEEN_FILE.write_text(json.dumps(data))

def make_hash(title: str, link: str) -> str:
    return hashlib.md5((title + link).strip().lower().encode()).hexdigest()

def is_duplicate(h: str, seen: dict) -> bool:
    if h not in seen:
        return False
    return datetime.now() - seen[h] < timedelta(hours=DUPLICATE_TTL)

# ── SCORING ───────────────────────────────────────────────────────────────────
def relevance_score(title: str, desc: str) -> int:
    text = (title + " " + desc).lower()
    return sum(1 for kw in KEYWORDS if kw in text)

# ── RSS FETCH ─────────────────────────────────────────────────────────────────
def fetch_rss(name: str, url: str) -> list:
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        ns   = {"atom": "http://www.w3.org/2005/Atom"}
        items = []

        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            link  = item.findtext("link",  "").strip()
            desc  = item.findtext("description", "").strip()
            if title and link:
                items.append({"title": title, "link": link, "desc": desc[:300]})

        if not items:
            for entry in root.findall(".//atom:entry", ns):
                title   = entry.findtext("atom:title", "", ns).strip()
                link_el = entry.find("atom:link", ns)
                link    = link_el.get("href", "") if link_el is not None else ""
                desc    = entry.findtext("atom:summary", "", ns).strip()
                if title and link:
                    items.append({"title": title, "link": link, "desc": desc[:300]})

        log.info(f"{name}: {len(items)} items")
        return items[:8]
    except Exception as e:
        log.warning(f"{name}: fetch failed — {e}")
        return []

# ── MAIN ──────────────────────────────────────────────────────────────────────
def scan(max_items: int = 5, dry_run: bool = False) -> list:
    seen       = load_seen()
    candidates = []

    for source, url in RSS_FEEDS.items():
        if len(candidates) >= CANDIDATE_POOL:
            break

        articles = fetch_rss(source, url)
        for article in articles:
            if len(candidates) >= CANDIDATE_POOL:
                break

            h = make_hash(article["title"], article["link"])
            if is_duplicate(h, seen):
                continue

            score = relevance_score(article["title"], article["desc"])
            if score == 0:
                continue

            seen[h] = datetime.now()
            candidates.append({
                "headline"  : article["title"],
                "source"    : source,
                "link"      : article["link"],
                "relevance" : score,
                "scanned_at": datetime.now().isoformat(),
            })

    candidates.sort(key=lambda x: x["relevance"], reverse=True)
    top = candidates[:max_items]

    if dry_run:
        print(f"\n[dry-run] {len(top)} headlines found:")
        for i, h in enumerate(top, 1):
            print(f"  {i}. [{h['relevance']}★] {h['headline'][:70]}")
        print()
        return top

    added = Q.push_many(top)
    save_seen(seen)

    log.info(f"Scan done: {len(added)} new headlines pushed to queue")
    for j in added:
        log.info(f"  [{j['id']}] {j['headline'][:60]}")

    return added


if __name__ == "__main__":
    logging.basicConfig(
        level   = logging.INFO,
        format  = "%(asctime)s [%(name)s] %(message)s",
        handlers= [logging.StreamHandler()]
    )

    ap = argparse.ArgumentParser()
    ap.add_argument("--max",     type=int, default=5)
    ap.add_argument("--dry-run", action="store_true",
                    help="Preview headlines without pushing to queue")
    args = ap.parse_args()

    results = scan(max_items=args.max, dry_run=args.dry_run)
    if not args.dry_run:
        print(f"\n[OK] {len(results)} headlines added to queue")
        print("Run: python main.py")

