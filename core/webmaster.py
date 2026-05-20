#!/usr/bin/env python3
"""
webmaster.py — Générateur multi-pages HRDshift (mode MEM)
Produit : index.html, drops.html, about.html, community.html, trajectory.html
Corrections :
- HAI lu depuis le dernier édito (hai_edito / hai_global)
- Prix lu comme entier propre
- Trajectoire & mini SVG gérés par trajectory.py
- Sidebar enrichie avec les mini SVG
- Toutes les pages secondaires assemblées avec shell.html + template central
"""

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime

from core.config import (
    BLOOM_FEED_JSON,
    HAI_INDEX_JSON,
    ARCHIVES_EDITO,
    ARCHIVES_PRICE,
    MERGE_TXT,
    SITE_DIR,
    PROJECT_ROOT,
    SHELL_HTML,
    CENTRAL_HTML,
    TEMPLATES_DIR,
    TRAJECTORY_JSON,
    HAI_MINI_SVG,
    PRICE_MINI_SVG,
)

# ════════════════════════════════════════════════════════════
# COUCHE 1 — READERS
# ════════════════════════════════════════════════════════════

def lire_bloom_block() -> str:
    chemin = SITE_DIR / "bloom_block.html"
    if chemin.exists():
        return chemin.read_text(encoding="utf-8")
    return ""


def lire_tous_editos() -> list[dict]:
    fichiers = sorted(ARCHIVES_EDITO.glob("edito_*.json"))
    if not fichiers:
        return []
    editos = []
    for f in fichiers:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        nom = f.stem
        parties = nom.split("_")
        if len(parties) >= 3:
            date_str = parties[1]
            heure_str = parties[2]
            try:
                an = int("20" + date_str[0:2])
                mois = int(date_str[2:4])
                jour = int(date_str[4:6])
                heure = int(heure_str[0:2])
                minute = int(heure_str[2:4])
                date_formatee = f"{jour:02d}/{mois:02d}/{an%100:02d} à {heure:02d}:{minute:02d}"
            except Exception:
                date_formatee = ""
        else:
            date_formatee = ""

        data["date_edito"] = date_formatee if date_formatee else data.get("date", "")
        editos.append(data)
    return editos


def lire_tous_prix() -> list[dict]:
    fichiers = sorted(ARCHIVES_PRICE.glob("nb_price_*.json"))
    if not fichiers:
        return []
    prix = []
    for f in fichiers:
        try:
            prix.append(json.loads(f.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    return prix


def lire_hai() -> dict:
    if not HAI_INDEX_JSON.exists():
        return {"hai": 0, "tendance": "→", "mise_a_jour": ""}
    try:
        return json.loads(HAI_INDEX_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"hai": 0, "tendance": "→", "mise_a_jour": ""}


def lire_hashtags(max_tags: int = 12) -> list[str]:
    if not MERGE_TXT.exists():
        return []
    texte = MERGE_TXT.read_text(encoding="utf-8").strip()
    tags = [tag for tag in texte.split() if tag.startswith("#")]
    return tags[:max_tags]


def lire_texte_fichier(chemin: Path) -> str:
    if chemin.exists():
        return chemin.read_text(encoding="utf-8").strip()
    return ""


# ════════════════════════════════════════════════════════════
# COUCHE 2 — TRANSFORMERS
# ════════════════════════════════════════════════════════════

def normaliser_edito(item: dict, index: int) -> dict:
    hai = (
        item.get("hai_edito") or
        item.get("hai_global") or
        item.get("hai", item.get("hai_score", item.get("valeur", 0)))
    )
    tendance = item.get("tendance", "→")
    texte = item.get("texte", item.get("edito", item.get("text", "")))
    date = item.get("date", item.get("mise_a_jour", ""))
    return {
        "index":      index,
        "hai":        round(float(hai), 1),
        "tendance":   tendance,
        "texte":      texte,
        "date":       date,
        "date_edito": item.get("date_edito", ""),
    }


def extraire_historique_prix(tous_prix: list[dict]) -> list[dict]:
    serie = []
    for p in tous_prix:
        valeur_brute = p.get("prix_estime") or p.get("prix") or p.get("valeur") or ""
        date = p.get("date") or p.get("mise_a_jour") or ""
        valeur_nettoyee = (str(valeur_brute)
                           .replace("~", "").replace(" ", "")
                           .replace(",", ".").replace("$", "")
                           .replace("€", "").replace("USD", ""))
        try:
            valeur = float(valeur_nettoyee)
        except ValueError:
            valeur = 0.0
        serie.append({"date": date, "valeur": valeur})
    return serie


def extraire_historique_hai(tous_editos: list[dict]) -> list[dict]:
    serie = []
    for e in reversed(tous_editos):
        hai = e.get("hai", e.get("hai_score", e.get("valeur", 0)))
        date = e.get("date", e.get("mise_a_jour", ""))
        try:
            hai = round(float(hai), 1)
        except (ValueError, TypeError):
            hai = 0
        serie.append({"date": date, "valeur": hai})
    return serie


# ════════════════════════════════════════════════════════════
# COUCHE 3 — BUILDERS HTML
# ════════════════════════════════════════════════════════════

def build_hashtags_html(tags: list[str]) -> str:
    if not tags:
        return '<span class="nav-tag" style="color:var(--text-muted)">Aucun hashtag</span>'
    return "\n".join(f'<span class="nav-tag">{tag}</span>' for tag in tags)


def build_latest_drops_html(editos: list[dict]) -> str:
    if not editos:
        return '<a class="nav-link" style="font-size:10px;color:var(--text-muted)">Aucun drop</a>'
    lignes = []
    for i, e in enumerate(editos[:5]):
        date_brute = e.get("date", e.get("mise_a_jour", ""))
        try:
            dt = datetime.fromisoformat(date_brute.replace("Z", "+00:00"))
            date_fmt = dt.strftime("%d/%m/%y")
        except Exception:
            date_fmt = date_brute[:10] if len(date_brute) >= 10 else date_brute
        hai = round(float(e.get("hai", e.get("hai_score", 0))), 1)
        tendance = e.get("tendance", "→")
        lignes.append(
            f'<a href="#" class="nav-link" '
            f'style="font-size:10px;color:var(--text-muted)" '
            f'onclick="goToEdito({i});return false;">'
            f'{date_fmt} — HAI {hai} {tendance}</a>'
        )
    return "\n".join(lignes)


def build_embedded_js(
    editos_norm: list[dict],
    prix_serie: list[dict],
    hai_serie: list[dict],
    bloom_count: int,
) -> str:
    return f"""/* ── Données embarquées HRDshift (mode MEM) ───────────── */
const BBMAR_EDITOS      = {json.dumps(editos_norm, ensure_ascii=False)};
const BBMAR_PRIX_SERIE  = {json.dumps(prix_serie,  ensure_ascii=False)};
const BBMAR_HAI_SERIE   = {json.dumps(hai_serie,   ensure_ascii=False)};
const BBMAR_BLOOM_COUNT = {bloom_count};
"""


def _charger_template(chemin: Path, nom: str) -> str | None:
    if not chemin.exists():
        print(f"  ❌ Template introuvable : {chemin}")
        return None
    return chemin.read_text(encoding="utf-8")


def _assembler_page_via_shell(nom_fichier: str, template_central: str, substitutions: dict):
    """Assemble shell.html + un template central et écrit la page dans site/."""
    shell = _charger_template(SHELL_HTML, "shell.html")
    if not shell:
        return
    central = _charger_template(TEMPLATES_DIR / template_central, template_central)
    if not central:
        return

    # Substitutions dans le central
    for key, val in substitutions.items():
        central = central.replace(key, val)

    # Substitutions communes du shell (sidebar, build, mini SVG)
    hashtags = lire_hashtags()
    editos_raw = lire_tous_editos()
    build_ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    hai_mini_svg = HAI_MINI_SVG.read_text(encoding="utf-8") if HAI_MINI_SVG.exists() else ""
    price_mini_svg = PRICE_MINI_SVG.read_text(encoding="utf-8") if PRICE_MINI_SVG.exists() else ""

    shell = shell.replace("{{ LATEST_DROPS }}", build_latest_drops_html(editos_raw))
    shell = shell.replace("{{ HASHTAGS }}", build_hashtags_html(hashtags))
    shell = shell.replace("{{ BUILD_TS }}", build_ts)
    shell = shell.replace("{{ HAI_MINI_SVG }}", hai_mini_svg)
    shell = shell.replace("{{ PRICE_MINI_SVG }}", price_mini_svg)

    page = shell.replace("{{ CENTRAL }}", central)
    (SITE_DIR / nom_fichier).write_text(page, encoding="utf-8")
    print(f"  ✅ {nom_fichier}")


# ════════════════════════════════════════════════════════════
# COUCHE 4 — GÉNÉRATEURS DE PAGES
# ════════════════════════════════════════════════════════════

def generer_index():
    print("🌐 génération index.html")

    bloom_block = lire_bloom_block()
    editos_raw = lire_tous_editos()
    prix_raw = lire_tous_prix()
    hashtags = lire_hashtags()

    bloom_count = 0
    if BLOOM_FEED_JSON.exists():
        try:
            bloom_count = len(json.loads(BLOOM_FEED_JSON.read_text(encoding="utf-8")))
        except Exception:
            pass

    editos_norm = [normaliser_edito(e, i) for i, e in enumerate(editos_raw)]
    prix_serie = extraire_historique_prix(prix_raw)
    hai_serie = extraire_historique_hai(editos_raw)

    edito_actuel = editos_norm[0] if editos_norm else {
        "hai": 0, "tendance": "→", "texte": "Aucun édito disponible.",
        "date": "", "date_edito": ""
    }
    hai_valeur = edito_actuel.get("hai", 0)
    hai_tendance = edito_actuel.get("tendance", "→")
    prix_actuel = prix_serie[-1]["valeur"] if prix_serie else 0.0
    fleche_to_class = {"↑": "up", "↓": "down", "→": "flat"}.get(hai_tendance, "flat")

    hashtags_html = build_hashtags_html(hashtags)
    latest_drops_html = build_latest_drops_html(editos_raw)
    embedded_js = build_embedded_js(editos_norm, prix_serie, hai_serie, bloom_count)
    build_ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    hai_mini_svg = HAI_MINI_SVG.read_text(encoding="utf-8") if HAI_MINI_SVG.exists() else ""
    price_mini_svg = PRICE_MINI_SVG.read_text(encoding="utf-8") if PRICE_MINI_SVG.exists() else ""

    shell_html = _charger_template(SHELL_HTML, "shell.html")
    central_html = _charger_template(CENTRAL_HTML, "central.html")
    if not shell_html or not central_html:
        return

    for key, val in {
        "{{ EDITO_TEXT }}":       edito_actuel.get("texte", ""),
        "{{ EDITO_DATE }}":       edito_actuel.get("date_edito", ""),
        "{{ HAI_VALUE }}":        str(hai_valeur),
        "{{ HAI_TREND }}":        hai_tendance,
        "{{ HAI_PERCENT }}":      str(hai_valeur),
        "{{ HAI_TREND_CLASS }}":  fleche_to_class,
        "{{ PRICE }}":            str(prix_actuel),
        "{{ BLOOM_COUNT }}":      str(bloom_count),
        "{{ BLOOM_ANIM }}":       bloom_block,
        "{{ EMBEDDED_DATA_JS }}": embedded_js,
    }.items():
        central_html = central_html.replace(key, val)

    for key, val in {
        "{{ LATEST_DROPS }}": latest_drops_html,
        "{{ HASHTAGS }}":     hashtags_html,
        "{{ BUILD_TS }}":     build_ts,
        "{{ HAI_MINI_SVG }}": hai_mini_svg,
        "{{ PRICE_MINI_SVG }}": price_mini_svg,
    }.items():
        shell_html = shell_html.replace(key, val)

    page = shell_html.replace("{{ CENTRAL }}", central_html)
    (SITE_DIR / "index.html").write_text(page, encoding="utf-8")
    print(f"  ✅ index.html — {len(editos_norm)} drops, {bloom_count} articles bloom")


def generer_drops():
    print("📜 génération drops.html")
    editos_raw = lire_tous_editos()
    if not editos_raw:
        drops_html = "<p>Aucun drop pour le moment.</p>"
    else:
        items = []
        for e in reversed(editos_raw):
            hai = e.get("hai_edito") or e.get("hai_global") or e.get("hai", 0)
            tendance = e.get("tendance", "→")
            texte = e.get("texte", e.get("edito", ""))
            date_edito = e.get("date_edito", e.get("date", ""))
            items.append(f"""
<article class="drop-card">
  <div class="drop-meta">
    <span class="drop-date">{date_edito}</span>
    <span class="drop-hai">HAI {round(float(hai), 1)} {tendance}</span>
  </div>
  <div class="drop-text">{texte}</div>
</article>""")
        drops_html = "\n".join(items)

    _assembler_page_via_shell("drops.html", "drops_template.html", {"{{ DROPS_LIST }}": drops_html})


def generer_about():
    print("📖 génération about.html")
    about_text = lire_texte_fichier(PROJECT_ROOT / "data" / "archives" / "ressources" / "about.txt")
    paragraphes = [f"<p>{p.strip()}</p>" for p in about_text.split("\n\n") if p.strip()]
    about_html = "\n".join(paragraphes) if paragraphes else "<p>À propos — contenu à venir.</p>"

    _assembler_page_via_shell("about.html", "about_template.html", {"{{ ABOUT_TEXT }}": about_html})


def generer_community():
    print("🤝 génération community.html")
    community_text = lire_texte_fichier(PROJECT_ROOT / "data" / "archives" / "ressources" / "communaute.txt")
    paragraphes = [f"<p>{p.strip()}</p>" for p in community_text.split("\n\n") if p.strip()]
    community_html = "\n".join(paragraphes) if paragraphes else "<p>Communauté — contenu à venir.</p>"

    _assembler_page_via_shell("community.html", "community_template.html", {"{{ COMMUNITY_TEXT }}": community_html})

def generer_trajectory():
    print("📈 génération trajectory.html")
    if not TRAJECTORY_JSON.exists():
        print("  ⚠ trajectory.json introuvable, exécutez d'abord processors/trajectory.py")
        return

    traj_data = json.loads(TRAJECTORY_JSON.read_text(encoding="utf-8"))
    hai_serie = traj_data.get("hai", [])
    price_serie = traj_data.get("price", [])
    edito_by_date = traj_data.get("edito_by_date", {})

    substitutions = {
        "{{ HAI_SERIE_JSON }}": json.dumps(hai_serie),
        "{{ PRICE_SERIE_JSON }}": json.dumps(price_serie),
        "{{ EDITO_BY_DATE_JSON }}": json.dumps(edito_by_date),
    }

    _assembler_page_via_shell("trajectory.html", "trajectory_template.html", substitutions)

# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

def main():
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    generer_index()
    generer_drops()
    generer_about()
    generer_community()
    generer_trajectory()
    print("🚀 Site complet généré.")


if __name__ == "__main__":
    main()
