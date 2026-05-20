#!/usr/bin/env python3
"""
scorer.py — Scoring algorithmique des dépêches
Lit registry.db (articles sans score) → màj hai_score/fleche/signal
Exporte hai_scores.json
Zéro appel LLM. Score lisible et modifiable par critère.
"""

import json
import sqlite3
from datetime import datetime, timezone
from core.config import (
    REGISTRY_DB, HAI_SCORES_JSON,
    ACTEURS, MOTS_ROBOT, SIGNAL_COMMERCIAL,
)

# ═══════════════════════════════════════════════════════════════════
# BARÈME — modifier ici uniquement
# ═══════════════════════════════════════════════════════════════════

PTS_ACTEUR         = 40   # Un acteur surveillé mentionné dans le titre
PTS_SIGNAL_COMM    = 20   # Un mot SIGNAL_COMMERCIAL détecté (max 2)
PTS_MOT_ROBOT      = 10   # Un mot MOTS_ROBOT détecté (max 1)
PTS_VIA_RSS        = 10   # Article collecté via RSS
PTS_VIA_GNEWS      =  5   # Article collecté via Google News

SEUIL_HAUT         = 70   # ≥ 70 → ↑
SEUIL_BAS          = 40   # < 40 → ↓  |  entre les deux → →
SCORE_MAX          = 100
MAX_ARTICLES_PASSE = 30   # Articles scorés par passe

# ═══════════════════════════════════════════════════════════════════
# LECTURE DB — articles non encore scorés
# ═══════════════════════════════════════════════════════════════════

def lire_a_scorer() -> list[dict]:
    conn = sqlite3.connect(str(REGISTRY_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT * FROM articles
           WHERE hai_score IS NULL
           ORDER BY collecte_le DESC
           LIMIT ?""",
        (MAX_ARTICLES_PASSE,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ═══════════════════════════════════════════════════════════════════
# MOTEUR DE SCORING
# ═══════════════════════════════════════════════════════════════════

def scorer_article(article: dict) -> dict:
    titre  = article.get("titre", "").lower()
    via    = article.get("via", "")
    score  = 0
    signaux = []

    # ── Pertinence : acteurs ────────────────────────────────────────
    acteur_detecte = None
    for acteur in ACTEURS:
        if acteur.lower() in titre:
            score += PTS_ACTEUR
            acteur_detecte = acteur
            signaux.append(f"acteur:{acteur}")
            break  # un seul acteur compté

    # ── Pertinence : signaux commerciaux (max 2) ───────────────────
    comm_count = 0
    for mot in SIGNAL_COMMERCIAL:
        if mot in titre and comm_count < 2:
            score += PTS_SIGNAL_COMM
            comm_count += 1
            signaux.append(f"commercial:{mot}")

    # ── Pertinence : mots robot (max 1) ───────────────────────────
    for mot in MOTS_ROBOT:
        if mot in titre:
            score += PTS_MOT_ROBOT
            signaux.append(f"robot:{mot}")
            break

    # ── Fiabilité : source ─────────────────────────────────────────
    if via == "rss":
        score += PTS_VIA_RSS
        signaux.append("source:rss")
    elif via == "gnews":
        score += PTS_VIA_GNEWS
        signaux.append("source:gnews")

    # ── Plafond ────────────────────────────────────────────────────
    score = min(score, SCORE_MAX)

    # ── Flèche ─────────────────────────────────────────────────────
    if score >= SEUIL_HAUT:
        fleche = "↑"
    elif score >= SEUIL_BAS:
        fleche = "→"
    else:
        fleche = "↓"

    return {
        "id":        article.get("id", ""),
        "titre":     article.get("titre", ""),
        "source":    article.get("source", ""),
        "via":       via,
        "date":      article.get("date", ""),
        "lien":      article.get("lien", ""),
        "acteur":    acteur_detecte,
        "fiabilite": score,
        "fleche":    fleche,
        "signaux":   signaux,
        "score_le":  datetime.now(timezone.utc).isoformat(),
    }

# ═══════════════════════════════════════════════════════════════════
# MISE À JOUR DB
# ═══════════════════════════════════════════════════════════════════

def mettre_a_jour_db(scores: list[dict]):
    conn = sqlite3.connect(str(REGISTRY_DB))
    for s in scores:
        conn.execute(
            """UPDATE articles
               SET hai_score = ?, fleche = ?, signal = ?
               WHERE id = ?""",
            (s["fiabilite"], s["fleche"], ",".join(s["signaux"]), s["id"])
        )
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════════════════════════════
# EXPORT JSON
# ═══════════════════════════════════════════════════════════════════

def exporter_scores():
    """Exporte tous les articles scorés depuis la DB vers nb_hai_scores.json."""
    conn = sqlite3.connect(str(REGISTRY_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT * FROM articles
           WHERE hai_score IS NOT NULL
           ORDER BY hai_score DESC"""
    ).fetchall()
    conn.close()
    data = [dict(r) for r in rows]
    HAI_SCORES_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return len(data)

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    a_scorer = lire_a_scorer()

    if not a_scorer:
        print("✅ Tous les articles sont déjà scorés.")
    else:
        print(f"🎯 Scoring de {len(a_scorer)} articles (max {MAX_ARTICLES_PASSE} par passe)...")
        scores = [scorer_article(a) for a in a_scorer]
        mettre_a_jour_db(scores)

        hausse = sum(1 for s in scores if s["fleche"] == "↑")
        neutre = sum(1 for s in scores if s["fleche"] == "→")
        baisse = sum(1 for s in scores if s["fleche"] == "↓")
        print(f"   ↑ {hausse}  →  {neutre}  ↓ {baisse}")

    total = exporter_scores()
    print(f"✅ {total} articles scorés au total → {HAI_SCORES_JSON.name}")
