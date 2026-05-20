#!/usr/bin/env python3
"""
collector.py — Registre central 
Immatricule les articles RSS + GNews dans registry.db
Déduplique via MD5(titre+lien)
Exporte collected.json
"""

import json
import sqlite3
import hashlib
import random
import string
from datetime import datetime, timezone
from core.config import (
    REGISTRY_DB, COLLECTED_JSON,
    RSS_OUTPUT, GNEWS_OUTPUT,
    ID_PREFIX_FORMAT,
)

# ───────────────────────────────────────────────
def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id          TEXT PRIMARY KEY,
            titre       TEXT,
            lien        TEXT,
            date        TEXT,
            source      TEXT,
            via         TEXT,
            md5         TEXT UNIQUE,
            collecte_le TEXT,
            hai_score   REAL DEFAULT NULL
        )
    """)
    conn.commit()

# ───────────────────────────────────────────────
def md5(titre: str, lien: str) -> str:
    return hashlib.md5(f"{titre}{lien}".encode()).hexdigest()

# ───────────────────────────────────────────────
def gen_id() -> str:
    prefix  = datetime.now().strftime(ID_PREFIX_FORMAT)   # ex. 2605
    lettres = lambda n: "".join(random.choices(string.ascii_uppercase, k=n))
    chiffres = "".join(random.choices(string.digits, k=4))
    return f"{prefix}-{lettres(3)}-{chiffres}-{lettres(3)}"

# ───────────────────────────────────────────────
def charger_articles() -> list[dict]:
    articles = []
    for fichier in [RSS_OUTPUT, GNEWS_OUTPUT]:
        if fichier.exists():
            articles += json.loads(fichier.read_text())
        else:
            print(f"⚠️  {fichier.name} introuvable — ignoré")
    return articles

# ───────────────────────────────────────────────
def immatriculer(articles: list[dict]) -> tuple[int, int]:
    conn = sqlite3.connect(str(REGISTRY_DB))
    init_db(conn)

    nouveaux = 0
    doublons = 0
    maintenant = datetime.now(timezone.utc).isoformat()

    for a in articles:
        empreinte = md5(a["titre"], a["lien"])
        try:
            conn.execute(
                """INSERT INTO articles
                   (id, titre, lien, date, source, via, md5, collecte_le)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (gen_id(), a["titre"], a["lien"], a.get("date", ""),
                 a.get("source", ""), a.get("via", ""), empreinte, maintenant)
            )
            nouveaux += 1
        except sqlite3.IntegrityError:
            doublons += 1

    conn.commit()
    conn.close()
    return nouveaux, doublons

# ───────────────────────────────────────────────
def exporter_collected():
    conn = sqlite3.connect(str(REGISTRY_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM articles ORDER BY collecte_le DESC"
    ).fetchall()
    conn.close()

    data = [dict(r) for r in rows]
    COLLECTED_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return len(data)

# ───────────────────────────────────────────────
if __name__ == "__main__":
    print("📦 Collecte en cours...")
    articles = charger_articles()
    print(f"   {len(articles)} articles chargés (RSS + GNews)")

    nouveaux, doublons = immatriculer(articles)
    print(f"   ✅ {nouveaux} nouveaux  |  ⏭️  {doublons} doublons ignorés")

    total = exporter_collected()
    print(f"   📄 {total} articles au registre → {COLLECTED_JSON.name}")
