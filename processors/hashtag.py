#!/usr/bin/env python3
"""
hashtag.py — Extracteur de hashtags depuis les titres
Lit nb_collected.json → merge.txt
Format : une ligne de hashtags par article, prêt à enrichir un prompt.
"""

import json
import re
from core.config import (
    COLLECTED_JSON, MERGE_TXT,
    ACTEURS, MOTS_ROBOT, SIGNAL_COMMERCIAL, MOTS_VIDES,
)

# ───────────────────────────────────────────────
def normaliser(mot: str) -> str:
    """Capitalize propre, retire ponctuation, prêt pour hashtag."""
    mot = re.sub(r"[^\w]", "", mot)
    return mot.capitalize() if mot else ""

def extraire_hashtags(titre: str) -> list[str]:
    hashtags = []
    t = titre.lower()

    # 1. Acteurs — détection prioritaire
    for acteur in ACTEURS:
        if acteur.lower() in t:
            for mot in acteur.split():
                tag = re.sub(r"[^\w]", "", mot)
                if tag:
                    hashtags.append(f"#{tag}")

    # 2. Mots capitalisés dans le titre original (noms propres, sigles)
    for mot in titre.split():
        propre = re.sub(r"[^\w]", "", mot)
        if (
            propre
            and propre[0].isupper()
            and propre.lower() not in MOTS_VIDES
            and f"#{propre}" not in hashtags
        ):
            hashtags.append(f"#{propre}")

    # 3. Mots-clés métier (MOTS_ROBOT + SIGNAL_COMMERCIAL)
    for mot in MOTS_ROBOT + SIGNAL_COMMERCIAL:
        if mot in t:
            tag = f"#{normaliser(mot)}"
            if tag not in hashtags:
                hashtags.append(tag)

    # Déduplication + limite 5
    vus = set()
    resultat = []
    for h in hashtags:
        if h.lower() not in vus:
            vus.add(h.lower())
            resultat.append(h)
        if len(resultat) == 5:
            break

    return resultat

# ───────────────────────────────────────────────
def fusionner() -> int:
    if not COLLECTED_JSON.exists():
        raise FileNotFoundError(
            f"❌ {COLLECTED_JSON.name} introuvable — lancer nb_collector.py d'abord"
        )

    articles = json.loads(COLLECTED_JSON.read_text())

    lignes = []
    for a in articles:
        tags = extraire_hashtags(a.get("titre", ""))
        if tags:
            lignes.append(" ".join(tags))

    contenu = "\n".join(lignes)
    MERGE_TXT.write_text(contenu)
    return len(lignes)

# ───────────────────────────────────────────────
if __name__ == "__main__":
    print("🏷️  Extraction hashtags...")
    total = fusionner()
    print(f"✅ {total} lignes → {MERGE_TXT.name}")
