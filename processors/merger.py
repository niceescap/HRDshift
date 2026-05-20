#!/usr/bin/env python3
"""
merge_link.py — Préparation du bandeau Bloomberg
Lit hai_scores.json → bloom_feed.json
Tri par défaut : fiabilité DESC
L'ordre du JSON = ordre d'affichage dans le bandeau.
"""

import json
from core.config import HAI_SCORES_JSON, BLOOM_FEED_JSON

# ═══════════════════════════════════════════════════════════════════
# TRI — modifier ici pour changer l'ordre du bandeau
# Options : "fiabilite", "date", "acteur", "fleche"
# ═══════════════════════════════════════════════════════════════════
TRI_PAR    = "fiabilite"
TRI_INVERSE = True   # True = DESC, False = ASC

# ═══════════════════════════════════════════════════════════════════
# CONSTRUCTION DU FEED
# ═══════════════════════════════════════════════════════════════════

def construire_feed() -> list[dict]:
    if not HAI_SCORES_JSON.exists():
        raise FileNotFoundError(
            f"❌ {HAI_SCORES_JSON.name} introuvable — lancer nb_scorer.py d'abord"
        )

    articles = json.loads(HAI_SCORES_JSON.read_text())

    # Tri
    articles.sort(key=lambda a: a.get(TRI_PAR, 0), reverse=TRI_INVERSE)

    feed = []
    for a in articles:
        feed.append({
            "fleche":    a.get("fleche", "→"),
            "titre":     a.get("titre", ""),
            "source":    a.get("source", ""),
            "acteur":    a.get("acteur", ""),
            "fiabilite": a.get("fiabilite", 0),
            "date":      a.get("date", ""),
            "lien":      a.get("lien", ""),
        })

    return feed

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("📰 Construction du bloom feed...")
    feed = construire_feed()
    BLOOM_FEED_JSON.write_text(json.dumps(feed, ensure_ascii=False, indent=2))
    print(f"✅ {len(feed)} items → {BLOOM_FEED_JSON.name}")
    print(f"   Tri : {TRI_PAR} {'↓' if TRI_INVERSE else '↑'}")
