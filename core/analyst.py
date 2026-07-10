#!/usr/bin/env python3
"""
analyst.py — Agent d'analyse (fusion édito + HAI)
Pioche ARTICLES_PAR_ANALYSE articles non consommés dans le stock
Si stock suffisant → appel Gemini (SDK) → edito + HAI + tendance
Archive → archives/editos/edito_AAMMJJ.json
"""

import json
import sqlite3
from datetime import datetime, timezone
from google import genai
from google.genai import types

from core.config import (
    GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE,
    PROMPT_EDITO_TXT, ARCHIVES_EDITO,
    REGISTRY_DB, HAI_INDEX_JSON, LAST_ANALYSIS_JSON,
    ARTICLES_PAR_ANALYSE, SEUIL_ANALYSE,
)

# ═══════════════════════════════════════════════════════════════════
# CURSEUR — lecture et écriture
# ═══════════════════════════════════════════════════════════════════

def lire_curseur() -> int:
    """Retourne l'offset (nb d'articles déjà consommés par les analyses)."""
    if not LAST_ANALYSIS_JSON.exists():
        return 0
    data = json.loads(LAST_ANALYSIS_JSON.read_text())
    return data.get("offset", 0)

def ecrire_curseur(offset: int, hai: float, articles_count: int):
    data = {}
    if LAST_ANALYSIS_JSON.exists():
        data = json.loads(LAST_ANALYSIS_JSON.read_text())
    
    data["last_analysis"]      = datetime.now(timezone.utc).isoformat()
    data["offset"]            = offset
    data["hai_courant"]       = hai
    data["articles_consommes"] = articles_count
    
    LAST_ANALYSIS_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2))

# ═══════════════════════════════════════════════════════════════════
# STOCK — lecture des articles à consommer
# ═══════════════════════════════════════════════════════════════════

def lire_stock(offset: int) -> list[dict]:
    """Retourne ARTICLES_PAR_ANALYSE articles scorés depuis l'offset."""
    conn = sqlite3.connect(str(REGISTRY_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT titre, source, via, date, hai_score, fleche, signal
           FROM articles
           WHERE hai_score IS NOT NULL
           ORDER BY collecte_le ASC
           LIMIT ? OFFSET ?""",
        (ARTICLES_PAR_ANALYSE, offset)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def compter_stock_disponible(offset: int) -> int:
    """Nombre d'articles scorés restants depuis l'offset."""
    conn = sqlite3.connect(str(REGISTRY_DB))
    count = conn.execute(
        """SELECT COUNT(*) FROM articles
           WHERE hai_score IS NOT NULL""",
    ).fetchone()[0]
    conn.close()
    return max(0, count - offset)

# ═══════════════════════════════════════════════════════════════════
# HAI GLOBAL — moyenne pondérée de toute la DB
# ═══════════════════════════════════════════════════════════════════

def calculer_hai_global() -> float:
    conn = sqlite3.connect(str(REGISTRY_DB))
    row = conn.execute(
        "SELECT AVG(hai_score) FROM articles WHERE hai_score IS NOT NULL"
    ).fetchone()
    conn.close()
    return round(row[0] or 0, 1)

# ═══════════════════════════════════════════════════════════════════
# CONSTRUCTION DU CONTEXTE INJECTÉ DANS LE PROMPT
# ═══════════════════════════════════════════════════════════════════

def construire_contexte(articles: list[dict]) -> str:
    lignes = []
    for a in articles:
        fleche  = a.get("fleche", "→")
        score   = int(a.get("hai_score") or 0)
        titre   = a.get("titre", "")
        source  = a.get("source", "")
        signal  = a.get("signal", "")
        lignes.append(f"{fleche} [{score}] {titre} — {source} | {signal}")
    return "\n".join(lignes)

# ═══════════════════════════════════════════════════════════════════
# APPEL GEMINI VIA SDK OFFICIEL
# ═══════════════════════════════════════════════════════════════════
def appeler_gemini(prompt: str) -> dict:
    # On force le SDK à utiliser la version stable au lieu de 'v1beta'
    client = genai.Client(api_key=GOOGLE_API_KEY)
    
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=GEMINI_TEMPERATURE,
        )
    )
    
    contenu = response.text.strip()
    # ... le reste du nettoyage JSON reste identique ...
    


    # Nettoyage Markdown JSON classique
    if contenu.startswith("```json"):
        contenu = contenu.split("```json")[1].split("```")[0].strip()
    elif contenu.startswith("```"):
        contenu = contenu.split("```")[1].split("```")[0].strip()

    # Tentative de parsing JSON strict
    try:
        return json.loads(contenu)
    except json.JSONDecodeError:
        return {"hai": None, "tendance": "→", "edito": contenu}

# ═══════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════

def exporter(resultat: dict, hai_global: float, articles: list[dict]):
    date_str = datetime.now().strftime("%y%m%d_%H%M")
    fichier  = ARCHIVES_EDITO / f"edito_{date_str}.json"
    payload  = {
        "meta": {
            "agent":     "nb_analyst",
            "modele":    GEMINI_MODEL,
            "timestamp": datetime.now().isoformat(),
            "nb_articles": len(articles),
        },
        "hai_global":  hai_global,
        "hai_edito":   resultat.get("hai"),
        "tendance":    resultat.get("tendance", "→"),
        "edito":       resultat.get("edito", ""),
    }
    fichier.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    # Mise à jour hai.json
    HAI_INDEX_JSON.write_text(json.dumps({
        "hai":      hai_global,
        "tendance": resultat.get("tendance", "→"),
        "mise_a_jour": datetime.now().isoformat(),
    }, ensure_ascii=False, indent=2))

    return fichier

def afficher(resultat: dict, hai_global: float):
    sep = "═" * 60
    print(f"\n{sep}")
    print(f"  ÉDITO — {datetime.now().strftime('%d/%m/%y')}")
    print(f"  HAI global : {hai_global}/100  {resultat.get('tendance', '→')}")
    print(f"{sep}\n")
    print(resultat.get("edito", ""))
    print(f"\n{sep}\n")

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    offset    = lire_curseur()
    disponible = compter_stock_disponible(offset)

    print(f"📊 Stock disponible : {disponible} articles (offset : {offset})")

    if disponible < SEUIL_ANALYSE:
        print(f"⏸️  Seuil non atteint ({SEUIL_ANALYSE} requis) — analyse reportée.")
    else:
        articles = lire_stock(offset)
        print(f"🧠 Analyse de {len(articles)} articles en cours...\n")

        contexte    = construire_contexte(articles)
        hai_global  = calculer_hai_global()

        if not PROMPT_EDITO_TXT.exists():
            raise FileNotFoundError(f"❌ {PROMPT_EDITO_TXT.name} introuvable")
        prompt_brut  = PROMPT_EDITO_TXT.read_text(encoding="utf-8")
        prompt_final = prompt_brut.replace("{articles}", contexte)\
                                  .replace("{hai_global}", str(hai_global))

        print(f"  🔁 Envoi à {GEMINI_MODEL}...")
        resultat = appeler_gemini(prompt_final)

        fichier = exporter(resultat, hai_global, articles)
        afficher(resultat, hai_global)

        nouvel_offset = offset + len(articles)
        ecrire_curseur(nouvel_offset, hai_global, nouvel_offset)
        print(f"  💾 Sauvegardé → {fichier.name}")
        print(f"  📍 Curseur avancé → offset {nouvel_offset}\n")
