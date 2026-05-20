#!/usr/bin/env python3
"""
main.py — Orchestrateur HRDshift
Chaîne complète : collecte → immatriculation → (si stock suffisant)
analyse → prépa site → webmaster

Humanoïd Robots Demand shift
Drop your Human Resources Direction!
"""

import sys
import json
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime, timezone

# Racine du projet = dossier de main.py = hrdshift/
PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))

from core.config import (
    SEUIL_ANALYSE,
    REGISTRY_DB,
    LAST_ANALYSIS_JSON,
)

# ═══════════════════════════════════════════════════════════════════
# OUTIL — exécuter un module du projet
# ═══════════════════════════════════════════════════════════════════

import os

def run_script(chemin_relatif: str) -> bool:
    """
    Exécute un fichier Python du projet depuis PROJECT_DIR.
    PYTHONPATH forcé à PROJECT_DIR pour que tous les imports
    from core.config, from collectors.xxx etc. fonctionnent.
    """
    script_path = PROJECT_DIR / chemin_relatif
    print(f"\n▶️  {chemin_relatif}...")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_DIR)

    try:
        subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            cwd=str(PROJECT_DIR),
            env=env,
        )
        print(f"✅ {chemin_relatif} ok")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur dans {chemin_relatif} (code {e.returncode})")
        return False

# ═══════════════════════════════════════════════════════════════════
# GESTION DE LA TRÉSORERIE DE STOCK & OFFSET
# ═══════════════════════════════════════════════════════════════════

def get_offset_cursor() -> int:
    """Récupère la valeur actuelle de l'offset dans le fichier JSON."""
    if LAST_ANALYSIS_JSON.exists():
        try:
            data = json.loads(LAST_ANALYSIS_JSON.read_text())
            return data.get("offset", 0)
        except Exception:
            pass
    return 0


def get_articles_en_stock() -> int:
    """Calcule la trésorerie de stock : Total au registre - Curseur offset."""
    if not REGISTRY_DB.exists():
        return 0
    try:
        conn = sqlite3.connect(str(REGISTRY_DB))
        total = conn.execute("SELECT COUNT(*) FROM articles;").fetchone()[0]
        conn.close()
    except Exception as e:
        print(f"❌ Erreur lecture registre : {e}")
        return 0
    return total - get_offset_cursor()


def set_last_analysis_timestamp():
    """Met à jour le timestamp sans écraser l'offset."""
    data = {}
    if LAST_ANALYSIS_JSON.exists():
        try:
            data = json.loads(LAST_ANALYSIS_JSON.read_text())
        except Exception:
            pass
    data["last_analysis"] = datetime.now(timezone.utc).isoformat()
    LAST_ANALYSIS_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2))

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    print(f"═══ HRDshift RUN — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ═══")

    # ── Couche 1 : Collecte ────────────────────────────────────────
    run_script("collectors/rss.py")
    run_script("collectors/gnews.py")

    # ── Couche 2 : Immatriculation ─────────────────────────────────
    run_script("collectors/collector.py")

    # ── Vérification du seuil ──────────────────────────────────────
    offset_actuel    = get_offset_cursor()
    stock_disponible = get_articles_en_stock()
    total_registre   = stock_disponible + offset_actuel

    print(f"\n📊 Trésorerie de Stock :")
    print(f"   • Total immatriculé  : {total_registre} articles")
    print(f"   • Déjà consommés     : {offset_actuel} articles (offset)")
    print(f"   • Disponible         : {stock_disponible} articles")
    print(f"   • Seuil requis       : {SEUIL_ANALYSE} articles")

    if stock_disponible < SEUIL_ANALYSE:
        print(f"\n⏸️  Stock insuffisant. Fin du run.")
        return

    print(f"\n🚀 Stock validé. Déclenchement de la suite...")

    # ── Couche 3 : Analyse ─────────────────────────────────────────
    run_script("core/scorer.py")
    run_script("processors/pricer.py")
    run_script("core/analyst.py")

    # ── Couche 4 : Préparation affichage + site ────────────────────
    run_script("processors/hashtag.py")
    run_script("processors/merger.py")
    run_script("processors/animator.py")
    run_script("processors/trajectory.py")      # ← ajouté
    run_script("core/webmaster.py")

    # ── Mise à jour timestamp ──────────────────────────────────────
    set_last_analysis_timestamp()
    print("\n✅ Run terminé.")
    print("═══ Fin du run HRDshift ═══")

if __name__ == "__main__":
    main()
