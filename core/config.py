#!/usr/bin/env python3
"""
config.py — Configuration centrale du projet HRDshift
Importé par tous les modules. Zéro valeur en dur ailleurs.

Humanoïd Robots Demand shift
Drop your Human Resources Direction!
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ═══════════════════════════════════════════════════════════════════
# 1. RACINE DU PROJET & CHARGEMENT .env
# ═══════════════════════════════════════════════════════════════════
# __file__ = hrdshift/core/config.py
# .parent  = hrdshift/core/
# .parent.parent = hrdshift/          ← PROJECT_ROOT correct
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Migration de GROQ_API_KEY à GOOGLE_API_KEY
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("❌ GOOGLE_API_KEY introuvable dans .env")

# ═══════════════════════════════════════════════════════════════════
# 2. PIPELINE — FRÉQUENCE & SEUILS
# ═══════════════════════════════════════════════════════════════════
FREQUENCE_RUN        = 4     # Heures entre deux runs
SEUIL_ANALYSE        = 10    # Dépêches min pour déclencher l'analyse LLM
ARTICLES_PAR_ANALYSE = 10    # Articles injectés par analyse
MAX_ARTICLES_GNEWS   = 15
MAX_ARTICLES_RSS     = None  # Pas de limite

# ═══════════════════════════════════════════════════════════════════
# 3. MODÈLE LLM (Google Gemini - API OpenAI Compatible)
# ═══════════════════════════════════════════════════════════════════
GEMINI_MODEL       = "gemini-1.5-flash"
GEMINI_URL         = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GEMINI_TIMEOUT     = 30
GEMINI_TEMPERATURE = 0.3

# ═══════════════════════════════════════════════════════════════════
# 4. ACTEURS SURVEILLÉS
# ═══════════════════════════════════════════════════════════════════
ACTEURS = [
    "Tesla Optimus",
    "Figure AI",
    "Apptronik",
    "Agility Robotics",
    "Boston Dynamics",
    "Unitree",
    "1X Technologies",
    "UBTech Robotics",
]

# ═══════════════════════════════════════════════════════════════════
# 5. CHEMINS — DONNÉES
# Tous résolus depuis PROJECT_ROOT = hrdshift/
# ═══════════════════════════════════════════════════════════════════

# Base de données
REGISTRY_DB        = PROJECT_ROOT / "data" / "registry.db"

# Sorties collecteurs
RSS_OUTPUT         = PROJECT_ROOT / "data" / "rss_output.json"
GNEWS_OUTPUT       = PROJECT_ROOT / "data" / "gnews_output.json"

# Déduplication
SEEN_JSON          = PROJECT_ROOT / "data" / "seen.json"

# Source de vérité unifiée
COLLECTED_JSON     = PROJECT_ROOT / "data" / "collected.json"

# Scores HAI & index
HAI_SCORES_JSON    = PROJECT_ROOT / "data" / "hai_scores.json"
HAI_INDEX_JSON     = PROJECT_ROOT / "data" / "hai.json"

# Curseur d'analyse
LAST_ANALYSIS_JSON = PROJECT_ROOT / "data" / "last_analysis.json"

# Fusion LLM & bandeau
MERGE_TXT          = PROJECT_ROOT / "data" / "merge.txt"
BLOOM_FEED_JSON    = PROJECT_ROOT / "data" / "bloom_feed.json"

# ═══════════════════════════════════════════════════════════════════
# 6. CHEMINS — ARCHIVES & SITE (créés automatiquement)
# ═══════════════════════════════════════════════════════════════════
ARCHIVES_EDITO = PROJECT_ROOT / "data" / "archives" / "editos"
ARCHIVES_EDITO.mkdir(parents=True, exist_ok=True)

ARCHIVES_PRICE = PROJECT_ROOT / "data" / "archives" / "prices"
ARCHIVES_PRICE.mkdir(parents=True, exist_ok=True)

SITE_DIR = PROJECT_ROOT / "site"
SITE_DIR.mkdir(parents=True, exist_ok=True)

# ── Trajectoire ────────────────────────────────────────────
TRAJECTORY_JSON  = PROJECT_ROOT / "site" / "trajectory.json"
HAI_MINI_SVG     = PROJECT_ROOT / "site" / "hai_mini.svg"
PRICE_MINI_SVG   = PROJECT_ROOT / "site" / "price_mini.svg"

# ═══════════════════════════════════════════════════════════════════
# 7. CHEMINS — TEMPLATES & PROMPTS
# ═══════════════════════════════════════════════════════════════════
TEMPLATES_DIR    = PROJECT_ROOT / "templates"
SHELL_HTML       = PROJECT_ROOT / "templates" / "shell.html"
CENTRAL_HTML     = PROJECT_ROOT / "templates" / "central.html"

PROMPT_EDITO_TXT = PROJECT_ROOT / "templates" / "prompt_edito.txt"
PROMPT_PRICE_TXT = PROJECT_ROOT / "templates" / "prompt_price.txt"

# ═══════════════════════════════════════════════════════════════════
# 8. SOURCES RSS
# ═══════════════════════════════════════════════════════════════════
FLUX_RSS = [
    "https://roboticsandautomationnews.com/feed/",
    "https://spectrum.ieee.org/feeds/topic/robotics.rss",
    "https://www.therobotreport.com/feed/",
    "https://techcrunch.com/tag/humanoid-robots/feed/",
    "https://www.siliconrepublic.com/feed",
    "https://www.roboticsbusinessreview.com/feed/",
    "https://www.azorobotics.com/rss.ashx",
    "https://www.roboticstomorrow.com/rss/",
    "https://www.universal-robots.com/blog/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.wired.com/feed/category/science/latest",
]

# ═══════════════════════════════════════════════════════════════════
# 9. REQUÊTES GOOGLE NEWS
# ═══════════════════════════════════════════════════════════════════
REQUETES_GNEWS = [
    "humanoid robot commercial",
    "humanoid robot price",
    "humanoid robot preorder",
    "Tesla Optimus release",
    "Figure AI humanoid",
    "Apptronik humanoid",
    "Agility Robotics Digit",
    "Boston Dynamics Atlas",
    "Unitree humanoid",
    "1X Technologies humanoid",
    "UBTech Walker",
]

# ═══════════════════════════════════════════════════════════════════
# 10. FILTRAGE
# ═══════════════════════════════════════════════════════════════════
MOTS_ROBOT = [
    "humanoid", "robot", "optimus", "figure", "digit",
    "atlas", "unitree", "apptronik", "1x", "ubtech",
]

SIGNAL_COMMERCIAL = [
    "price", "preorder", "msrp", "order", "buy", "sale",
    "launch", "ship", "release", "commercial", "production",
    "factory", "reservation", "availability", "purchase",
]

MOTS_PRIX = [
    "sold at", "price", "cost", "msrp", "priced at", "costs",
]

MOTS_VIDES = [
    "the", "a", "an", "for", "of", "in", "at", "to", "and",
    "or", "but", "on", "with", "by", "from", "its", "as",
    "is", "are", "was", "be", "has", "have", "that", "this",
    "new", "says", "said", "will", "can", "how", "why", "when",
]

# ═══════════════════════════════════════════════════════════════════
# 11. FORMAT D'IMMATRICULATION
# ═══════════════════════════════════════════════════════════════════
ID_PREFIX_FORMAT = "%y%m"  # YYMM → ex. 2605-AAA-1234-BBB

# ═══════════════════════════════════════════════════════════════════
# SANITY CHECK
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("═" * 52)
    print("  config.py — HRDshift")
    print("  Humanoïd Robots Demand shift")
    print("═" * 52)
    print(f"  PROJECT_ROOT         : {PROJECT_ROOT}")
    print(f"  GOOGLE_API_KEY       : ✅ OK")
    print(f"  GEMINI_MODEL         : {GEMINI_MODEL}")
    print()
    print(f"  FREQUENCE_RUN        : toutes les {FREQUENCE_RUN}h")
    print(f"  SEUIL_ANALYSE        : {SEUIL_ANALYSE} dépêches")
    print(f"  ARTICLES_PAR_ANALYSE : {ARTICLES_PAR_ANALYSE} articles")
    print()
    print(f"  Flux RSS             : {len(FLUX_RSS)} sources")
    print(f"  Requêtes GNews       : {len(REQUETES_GNEWS)} requêtes")
    print(f"  Acteurs              : {len(ACTEURS)} robots")
    print()
    checks = [
        ("REGISTRY_DB",      REGISTRY_DB),
        ("COLLECTED_JSON",   COLLECTED_JSON),
        ("ARCHIVES_EDITO",   ARCHIVES_EDITO),
        ("SITE_DIR",         SITE_DIR),
        ("SHELL_HTML",       SHELL_HTML),
        ("CENTRAL_HTML",     CENTRAL_HTML),
        ("PROMPT_EDITO_TXT", PROMPT_EDITO_TXT),
        ("PROMPT_PRICE_TXT", PROMPT_PRICE_TXT),
    ]
    for name, path in checks:
        status = "✅" if Path(path).exists() else "⚠️  à créer"
        print(f"  {status}  {name}")
    print("═" * 52)
