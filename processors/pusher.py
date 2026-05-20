#!/usr/bin/env python3
"""
pusher.py — Agent de déploiement HRDshift
Pousse uniquement site/ vers GitHub.
Cloudflare détecte le push et déploie automatiquement.

Usage :
  python processors/pusher.py        # interactif
  python processors/pusher.py --yes  # non-interactif (pour cron/alias)
Alias recommandé :  alias push='python ~/hrdshift/processors/pusher.py --yes'
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).resolve().parent.parent
SITE_DIR    = PROJECT_DIR / "site"
BRANCH      = "main"   # Branche GitHub surveillée par Cloudflare


# ════════════════════════════════════════════════════════════
# VÉRIFICATIONS PRÉALABLES
# ════════════════════════════════════════════════════════════

def verifier_site(auto_oui: bool = False) -> bool:
    """Vérifie que site/ existe, contient un index.html, et est récent."""
    if not SITE_DIR.exists():
        print("  ❌ Dossier site/ introuvable.")
        return False
    index = SITE_DIR / "index.html"
    if not index.exists():
        print("  ❌ site/index.html absent — lance le pipeline d'abord.")
        return False

    age_heures = (datetime.now().timestamp() - index.stat().st_mtime) / 3600
    if age_heures > 24:
        print(f"  ⚠️  site/index.html a {age_heures:.0f}h — es-tu sûr de vouloir déployer ?")
        if not auto_oui:
            reponse = input("  Continuer quand même ? (o/n) : ").strip().lower()
            if reponse != "o":
                print("  Annulé.")
                return False
        else:
            print("  ✅ Mode --yes : déploiement forcé.")
    return True


# ════════════════════════════════════════════════════════════
# GIT
# ════════════════════════════════════════════════════════════

def git(args: list[str], label: str) -> bool | None:
    """Exécute une commande git depuis PROJECT_DIR.
    Retourne True si succès, None si rien à committer, False si erreur.
    """
    result = subprocess.run(
        ["git"] + args,
        cwd=str(PROJECT_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
            print(f"  ℹ️  {label} — rien à committer")
            return None
        print(f"  ❌ {label}")
        print(f"     {result.stderr.strip() or result.stdout.strip()}")
        return False
    if result.stdout.strip():
        print(f"  ✅ {label} — {result.stdout.strip()[:80]}")
    else:
        print(f"  ✅ {label}")
    return True


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

def main():
    # Gestion argument --yes
    auto_oui = "--yes" in sys.argv

    print(f"\n📡 HRDshift Pusher — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("─" * 48)

    # 1. Vérifier site/
    if not verifier_site(auto_oui):
        sys.exit(1)

    # 2. git add site/
    ok = git(["add", "site/"], "git add site/")
    if ok is False:
        sys.exit(1)

    # 3. Afficher les fichiers modifiés (optionnel)
    subprocess.run(["git", "diff", "--cached", "--name-only", "--", "site/"],
                   cwd=str(PROJECT_DIR))

    # 4. git commit
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = f"deploy {ts}"
    ok  = git(["commit", "-m", msg], f"git commit '{msg}'")
    if ok is False:
        sys.exit(1)
    if ok is None:
        print("  ℹ️  Aucun changement dans site/ — déploiement ignoré.")
        print("─" * 48)
        return

    # 5. git push
    ok = git(["push", "origin", BRANCH], f"git push → GitHub ({BRANCH})")
    if ok is False:
        sys.exit(1)

    print("─" * 48)
    print("  🚀 Déployé → Cloudflare compile hrdshift.pages.dev")
    print("  ⏱️  Mise en ligne dans ~60 secondes\n")


if __name__ == "__main__":
    main()
