#!/usr/bin/env python3
"""
pricer.py — Agent estimateur de prix HRDshift
Détecte les signaux prix dans collected.json via MOTS_PRIX
→ Injecte le prix précédent comme ancre de continuité
→ Appel OpenRouter via templates/prompt_price.txt
→ data/archives/prices/price_AAMMJJ_HHMM.json
"""

import json
import requests
from datetime import datetime, timezone
from core.config import (
    OR_API_KEY, OR_MODEL, OR_URL, OR_TIMEOUT, OR_REFERER, OR_APP_TITLE,
    COLLECTED_JSON, ARCHIVES_PRICE,
    PROMPT_PRICE_TXT, MOTS_PRIX,
)

# ═══════════════════════════════════════════════════════════════════
# DÉTECTION
# ═══════════════════════════════════════════════════════════════════

def detecter_articles_prix() -> list[dict]:
    if not COLLECTED_JSON.exists():
        raise FileNotFoundError(f"❌ {COLLECTED_JSON.name} introuvable")
    articles = json.loads(COLLECTED_JSON.read_text())
    return [a for a in articles if any(m in a.get("titre", "").lower() for m in MOTS_PRIX)]


# ═══════════════════════════════════════════════════════════════════
# PRIX PRÉCÉDENT — continuité inter-runs
# ═══════════════════════════════════════════════════════════════════

def lire_prix_precedent() -> int:
    """
    Lit le prix estimé du dernier run archivé.
    Retourne 0 si aucune archive n'existe encore.
    Le prompt informera le LLM que 0 = première estimation.
    """
    fichiers = sorted(ARCHIVES_PRICE.glob("*.json"), reverse=True)
    for f in fichiers:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            val  = data.get("prix_estime", 0)
            # Nettoyer si ancien format contenait un $
            val  = str(val).replace("$", "").replace("~", "").replace(" ", "").replace(",", ".")
            prix = int(float(val))
            if prix > 0:
                return prix
        except Exception:
            continue
    return 0


# ═══════════════════════════════════════════════════════════════════
# CONTEXTE
# ═══════════════════════════════════════════════════════════════════

def construire_contexte(articles: list[dict]) -> str:
    return "\n".join(
        f"- {a.get('titre', '')} ({a.get('source', '')})"
        for a in articles
    )


# ═══════════════════════════════════════════════════════════════════
# APPEL OPENROUTER
# ═══════════════════════════════════════════════════════════════════

def appeler_llm(prompt: str) -> dict:
    headers = {
        "Authorization": f"Bearer {OR_API_KEY}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  OR_REFERER,
        "X-Title":       OR_APP_TITLE,
    }
    payload = {
        "model":       OR_MODEL,
        "messages":    [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens":  256,
    }
    response = requests.post(OR_URL, headers=headers, json=payload, timeout=OR_TIMEOUT)
    if response.status_code != 200:
        print(f"[LLM] Erreur {response.status_code} : {response.text[:300]}")
    response.raise_for_status()
    contenu = response.json()["choices"][0]["message"]["content"].strip()

    # Nettoyer les éventuels blocs markdown ```json ... ```
    contenu = contenu.strip("` \n")
    if contenu.startswith("json"):
        contenu = contenu[4:].strip()

    try:
        return json.loads(contenu)
    except json.JSONDecodeError:
        return {"prix_estime": 0, "confiance": "faible", "note": "parsing JSON échoué"}


# ═══════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════

def exporter(resultat: dict, nb_sources: int, prix_precedent: int) -> object:
    date_str = datetime.now().strftime("%y%m%d_%H%M")

    # Normaliser prix_estime en entier propre
    val_brute = resultat.get("prix_estime", 0)
    try:
        prix_net = int(float(str(val_brute).replace("$", "").replace(" ", "").replace(",", ".")))
    except (ValueError, TypeError):
        prix_net = 0

    payload = {
        "meta": {
            "agent":          "pricer",
            "modele":         OR_MODEL,
            "timestamp":      datetime.now(timezone.utc).isoformat(),
            "nb_sources":     nb_sources,
            "prix_precedent": prix_precedent,
        },
        "prix_estime": prix_net,
        "confiance":   resultat.get("confiance", "inconnue"),
        "note":        resultat.get("note", ""),
    }
    archive = ARCHIVES_PRICE / f"nb_price_{date_str}.json"
    archive.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return archive, prix_net


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("💰 Détection signaux prix...")
    articles = detecter_articles_prix()
    print(f"   {len(articles)} articles avec signal prix détectés")

    if not articles:
        print("⏸️  Aucun signal prix — estimation reportée.")
    else:
        if not PROMPT_PRICE_TXT.exists():
            raise FileNotFoundError(f"❌ {PROMPT_PRICE_TXT.name} introuvable")

        prix_precedent = lire_prix_precedent()
        print(f"   📌 Prix précédent : {prix_precedent if prix_precedent else 'aucun (premier run)'} $")

        contexte     = construire_contexte(articles)
        prompt_brut  = PROMPT_PRICE_TXT.read_text(encoding="utf-8")
        prompt_final = (prompt_brut
                        .replace("{articles}",       contexte)
                        .replace("{prix_precedent}", str(prix_precedent) if prix_precedent else "inconnue"))

        print(f"   🔁 Envoi à {GROQ_MODEL}...")
        resultat = appeler_groq(prompt_final)

        archive, prix_net = exporter(resultat, len(articles), prix_precedent)
        print(f"   💵 Prix estimé   : {prix_net} $")
        print(f"   📊 Confiance     : {resultat.get('confiance', '?')}")
        print(f"   📝 Note          : {resultat.get('note', '')}")
        print(f"   ✅ → {archive.name}")
