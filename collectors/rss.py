#!/usr/bin/env python3
"""
rss.py — Chineur RSS
Collecte les flux définis dans nb_config.py → nb_rss_output.json
"""

import json
import feedparser
from datetime import datetime, timezone
from core.config import FLUX_RSS, RSS_OUTPUT

# ───────────────────────────────────────────────
def fetch_rss() -> list[dict]:
    articles = []
    for url in FLUX_RSS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                articles.append({
                    "titre":  entry.get("title", "").strip(),
                    "lien":   entry.get("link", "").strip(),
                    "date":   entry.get("published", ""),
                    "source": feed.feed.get("title", url),
                    "via":    "rss",
                })
        except Exception as e:
            print(f"⚠️  {url} — {e}")

    return articles

# ───────────────────────────────────────────────
if __name__ == "__main__":
    print(f"📡 Collecte RSS ({len(FLUX_RSS)} flux)...")
    articles = fetch_rss()
    RSS_OUTPUT.write_text(json.dumps(articles, ensure_ascii=False, indent=2))
    print(f"✅ {len(articles)} articles → {RSS_OUTPUT.name}")
