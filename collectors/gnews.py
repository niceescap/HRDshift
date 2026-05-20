#!/usr/bin/env python3
"""
gnews.py — Chineur Google News
Collecte les requêtes définies dans nb_config.py → nb_gnews_output.json
Filtre via MOTS_ROBOT + SIGNAL_COMMERCIAL (logique AND)
"""

import json
from pygooglenews import GoogleNews
from core.config import (
    REQUETES_GNEWS, GNEWS_OUTPUT,
    MAX_ARTICLES_GNEWS,
    MOTS_ROBOT, SIGNAL_COMMERCIAL,
)

gn = GoogleNews(lang="en", country="US")

# ───────────────────────────────────────────────
def passe_filtre(titre: str) -> bool:
    t = titre.lower()
    if any(m in t for m in MOTS_ROBOT) and any(m in t for m in SIGNAL_COMMERCIAL):
        return True
    return False

# ───────────────────────────────────────────────
def fetch_gnews() -> list[dict]:
    articles = []
    vus = set()

    for requete in REQUETES_GNEWS:
        try:
            results = gn.search(requete)
            entries = results.get("entries", [])[:MAX_ARTICLES_GNEWS]
            for entry in entries:
                titre = entry.get("title", "").strip()
                lien  = entry.get("link",  "").strip()
                if not titre or lien in vus:
                    continue
                if not passe_filtre(titre):
                    continue
                vus.add(lien)
                articles.append({
                    "titre":   titre,
                    "lien":    lien,
                    "date":    entry.get("published", ""),
                    "source":  entry.get("source", {}).get("title", ""),
                    "requete": requete,
                    "via":     "gnews",
                })
        except Exception as e:
            print(f"⚠️  [{requete}] — {e}")

    return articles

# ───────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🔍 Collecte GNews ({len(REQUETES_GNEWS)} requêtes)...")
    articles = fetch_gnews()
    GNEWS_OUTPUT.write_text(json.dumps(articles, ensure_ascii=False, indent=2))
    print(f"✅ {len(articles)} articles filtrés → {GNEWS_OUTPUT.name}")
