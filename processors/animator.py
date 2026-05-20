#!/usr/bin/env python3
"""
animator.py — Bandeau Bloomberg animé
─────────────────────────────────────────────────────
Lit les articles du dernier batch d'analyse (immatriculés
depuis la dernière analyse), sélectionne jusqu'à 30 titres,
les trie du plus récent au plus ancien, génère le bloc HTML
pour le ticker (articles doublés pour boucle CSS seamless).

Sortie : site/bloom_block.html

Améliorations v4 :
  - Scrub en delta relatif pur (requestAnimationFrame)
  - touch-action:none dynamique au pointerdown (fix Android)
  - Suppression e.preventDefault() sur pointerdown (fix pointermove)
  - DOMMatrix lu une seule fois au pointerdown (stable)
  - Clic court → window.open nouvel onglet
  - Drag → reprise animation après 80ms
"""

import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from core.config import (
    REGISTRY_DB,
    LAST_ANALYSIS_JSON,
    SITE_DIR,
)

# ════════════════════════════════════════════════════════════
# PARAMÈTRES
# Toutes les valeurs configurables sont ici.
# ════════════════════════════════════════════════════════════

# Nombre max d'articles dans le ticker
TICKER_MAX_ARTICLES = 30

# Durée d'un cycle complet du ticker en secondes.
# 90s = confortable pour la lecture à vitesse normale.
# Réduire pour accélérer, augmenter pour ralentir.
TICKER_DUREE_SECONDES = 90

# Seuils flèche sur hai_score (0–100)
FLECHE_SEUIL_HAUT = 50   # > 50 → ↑ vert
FLECHE_SEUIL_BAS  = 30   # < 30 → ↓ rouge, entre les deux → → gris


# ════════════════════════════════════════════════════════════
# COUCHE 1 — RÉCUPÉRATION
# ════════════════════════════════════════════════════════════

def recuperer_articles_batch(limite: int = TICKER_MAX_ARTICLES) -> list[dict]:
    """
    Récupère les articles du dernier batch d'analyse.
    Logique : articles collectés AVANT le timestamp last_analysis
    (le pipeline enregistre last_analysis ~3s APRÈS la collecte,
    donc on prend WHERE collecte_le <= last_analysis).
    Fallback premier run : datetime(2000,1,1) → tout prendre.
    """
    if not REGISTRY_DB.exists():
        print("  ❌ Base de données introuvable.")
        return []

    # Lire le timestamp de dernière analyse
    last_ts = None
    if LAST_ANALYSIS_JSON.exists():
        try:
            data   = json.loads(LAST_ANALYSIS_JSON.read_text())
            ts_str = data.get("last_analysis")
            if ts_str:
                last_ts = datetime.fromisoformat(ts_str)
        except Exception:
            pass

    if last_ts is None:
        last_ts = datetime(2000, 1, 1, tzinfo=timezone.utc)

    conn = sqlite3.connect(str(REGISTRY_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT titre, lien, hai_score, collecte_le
        FROM articles
        WHERE collecte_le <= ?
        ORDER BY collecte_le DESC
        LIMIT ?
    """, (last_ts.isoformat(), limite)).fetchall()
    conn.close()

    articles = []
    for r in rows:
        fleche, css_class = _fleche_depuis_score(r["hai_score"])
        articles.append({
            "titre":      r["titre"] or "",
            "lien":       r["lien"]  or "#",
            "fleche":     fleche,
            "css_class":  css_class,
            "hai_score":  r["hai_score"],
            "anciennete": _anciennete(r["collecte_le"]),
        })

    return articles


# ════════════════════════════════════════════════════════════
# COUCHE 2 — TRANSFORMERS
# ════════════════════════════════════════════════════════════

def _fleche_depuis_score(score) -> tuple[str, str]:
    """
    Retourne (symbole, classe_css) depuis un hai_score brut.
    Gère les None et les valeurs non numériques sans exception.
    """
    if score is None:
        return "→", "flat"
    try:
        s = float(score)
        if s > FLECHE_SEUIL_HAUT:
            return "↑", "up"
        if s < FLECHE_SEUIL_BAS:
            return "↓", "down"
        return "→", "flat"
    except (ValueError, TypeError):
        return "→", "flat"


def _anciennete(collecte_le: str | None) -> str:
    """
    Calcule une ancienneté lisible depuis la date de collecte ISO.
    Exemples : "il y a 3 heures", "il y a 2 jours", "hier", "aujourd'hui"
    """
    if not collecte_le:
        return ""
    try:
        dt = datetime.fromisoformat(collecte_le)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now     = datetime.now(timezone.utc)
        diff    = now - dt
        minutes = int(diff.total_seconds() / 60)
        heures  = int(diff.total_seconds() / 3600)
        jours   = diff.days

        if minutes < 5:
            return "à l'instant"
        if minutes < 60:
            return f"il y a {minutes} min"
        if heures < 24:
            return f"il y a {heures} heure{'s' if heures > 1 else ''}"
        if jours == 1:
            return "hier"
        if jours < 30:
            return f"il y a {jours} jours"
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return ""


# ════════════════════════════════════════════════════════════
# COUCHE 3 — CONSTRUCTION HTML
# ════════════════════════════════════════════════════════════

def _render_item(a: dict) -> str:
    """
    Génère le HTML d'un item ticker.

    Structure visuelle :
    ┌────────────────────────────────────────┐
    │  ↑   Titre de l'article sur 2 lignes  │
    │      HAI 72.4  ·  il y a 3 heures     │
    └────────────────────────────────────────┘
    """
    # Badge score HAI
    score_html = ""
    if a["hai_score"] is not None:
        try:
            val        = round(float(a["hai_score"]), 1)
            score_html = f'<span class="bloom-score">HAI {val}</span>'
        except (ValueError, TypeError):
            pass

    # Ancienneté
    age_html = ""
    if a["anciennete"]:
        age_html = f'<span class="bloom-age">{a["anciennete"]}</span>'

    # Séparateur entre badge et ancienneté
    sep_html = ""
    if score_html and age_html:
        sep_html = '<span class="bloom-sep">·</span>'

    return (
        f'<a class="bloom-item" '
        f'href="{a["lien"]}" '
        f'target="_blank" '
        f'rel="noopener noreferrer">'
        #
        f'<span class="bloom-arrow {a["css_class"]}">{a["fleche"]}</span>'
        #
        f'<span class="bloom-content">'
        f'<span class="bloom-title">{a["titre"]}</span>'
        f'<span class="bloom-meta">{score_html}{sep_html}{age_html}</span>'
        f'</span>'
        #
        f'</a>'
    )


def _css_bloc() -> str:
    """
    CSS embarqué v3.
    - Vitesse paramétrable via TICKER_DUREE_SECONDES
    - État .paused pour gel de l'animation
    - cursor grab/grabbing pour feedback tactile desktop
    """
    return f"""<!-- bloom_block.html — nb_bloom_animator v4 -->
<style>
/* Vitesse ticker — piloté par TICKER_DUREE_SECONDES */
.bloom-inner {{
  animation-duration: {TICKER_DUREE_SECONDES}s !important;
  will-change: transform;
  cursor: grab;
}}

/* Gel de l'animation pendant interaction */
.bloom-inner.paused {{
  animation-play-state: paused !important;
  cursor: grab;
}}

.bloom-inner.dragging {{
  cursor: grabbing;
}}

/* Flèche HAI — agrandie et mise en valeur */
.bloom-arrow {{
  font-size: 20px !important;
  font-weight: 800 !important;
  line-height: 1;
  flex-shrink: 0;
  width: 26px;
  text-align: center;
  align-self: center;
  pointer-events: none;
}}

/* Contenu texte */
.bloom-content {{
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  pointer-events: none;
}}

/* Titre — 2 lignes max */
.bloom-title {{
  font-size: 11px;
  line-height: 1.45;
  color: #e3ddd5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}}

/* Ligne méta */
.bloom-meta {{
  display: flex;
  align-items: center;
  gap: 6px;
}}

/* Badge score HAI */
.bloom-score {{
  font-size: 9px;
  letter-spacing: .10em;
  color: #c8a84b;
  font-weight: 600;
  background: rgba(200,168,75,.08);
  border: 1px solid rgba(200,168,75,.18);
  padding: 1px 5px;
  white-space: nowrap;
  flex-shrink: 0;
}}

/* Séparateur · */
.bloom-sep {{
  font-size: 9px;
  color: #3c3834;
}}

/* "il y a X jours" */
.bloom-age {{
  font-size: 9px;
  color: #6e675f;
  letter-spacing: .04em;
  white-space: nowrap;
}}

/* Highlight au survol pendant pause */
.bloom-inner.paused .bloom-item:hover {{
  background: rgba(255,255,255,.03);
  outline: 1px solid rgba(200,168,75,.15);
}}
</style>
"""


def _js_bloc() -> str:
    """
    JS embarqué v5 — listeners sur document pour Android WebView.

    Problème v4 : setPointerCapture sans preventDefault ne suffit pas
    sur Android — le browser absorbe les pointermove pour le scroll page
    avant qu'ils atteignent l'élément.

    Solution v5 : pointerdown sur inner (détection du toucher),
    puis pointermove/pointerup écoutés sur DOCUMENT avec filtre pointerId.
    Le document reçoit les events avant que le browser décide de scroller.
    preventDefault() appelé UNIQUEMENT sur pointermove quand drag confirmé
    (pas sur pointerdown — sinon le long-press lien est bloqué).
    """
    return """
<script>
document.addEventListener('DOMContentLoaded', function () {
(function () {

  var SEUIL_CLIC = 8;
  var RAF_ID     = null;

  var inner = document.querySelector('.bloom-inner');
  if (!inner) return;

  // ── État interne ─────────────────────────────────────────
  var actif         = false;
  var estDrag       = false;
  var pointerId     = null;
  var xDebut        = 0;
  var xPrecedent    = 0;
  var offsetCourant = 0;

  // ── Lire la position X de l'animation CSS ───────────────
  function lireOffsetCSS() {
    try {
      return new DOMMatrix(window.getComputedStyle(inner).transform).m41;
    } catch (e) { return 0; }
  }

  // ── RAF ──────────────────────────────────────────────────
  function appliquerOffset() {
    inner.style.transform = 'translateX(' + offsetCourant + 'px)';
    RAF_ID = null;
  }

  // ── Pause ────────────────────────────────────────────────
  function pauserAnimation() {
    offsetCourant = lireOffsetCSS();
    inner.style.transform = 'translateX(' + offsetCourant + 'px)';
    inner.classList.add('paused');
    inner.classList.remove('dragging');
  }

  // ── Reprise ──────────────────────────────────────────────
  function reprendreAnimation() {
    if (RAF_ID) { cancelAnimationFrame(RAF_ID); RAF_ID = null; }
    inner.style.transform = '';
    inner.classList.remove('paused', 'dragging');
    actif     = false;
    pointerId = null;
  }

  // ── Remonter jusqu'au .bloom-item ───────────────────────
  function trouverItem(el) {
    while (el && el !== inner) {
      if (el.classList && el.classList.contains('bloom-item')) return el;
      el = el.parentElement;
    }
    return null;
  }

  // ── POINTER DOWN sur inner ────────────────────────────────
  inner.addEventListener('pointerdown', function (e) {
    if (e.button === 2) return;
    actif      = true;
    estDrag    = false;
    pointerId  = e.pointerId;
    xDebut     = e.clientX;
    xPrecedent = e.clientX;
    pauserAnimation();
  });

  // ── POINTER MOVE sur document ────────────────────────────
  // { passive: false } indispensable pour que preventDefault fonctionne
  document.addEventListener('pointermove', function (e) {
    if (!actif || e.pointerId !== pointerId) return;

    if (Math.abs(e.clientX - xDebut) > SEUIL_CLIC) {
      estDrag = true;
      inner.classList.add('dragging');
      e.preventDefault();  // bloquer scroll natif — drag confirmé seulement
    }

    offsetCourant += e.clientX - xPrecedent;
    xPrecedent     = e.clientX;

    if (!RAF_ID) {
      RAF_ID = requestAnimationFrame(appliquerOffset);
    }
  }, { passive: false });

  // ── POINTER UP sur document ──────────────────────────────
  document.addEventListener('pointerup', function (e) {
    if (!actif || e.pointerId !== pointerId) return;

    if (!estDrag) {
      var item = trouverItem(e.target);
      if (item) {
        var href = item.getAttribute('href');
        if (href && href !== '#') {
          window.open(href, '_blank', 'noopener,noreferrer');
        }
      }
      reprendreAnimation();
    } else {
      setTimeout(reprendreAnimation, 80);
    }
  });

  // ── POINTER CANCEL ───────────────────────────────────────
  document.addEventListener('pointercancel', function (e) {
    if (!actif || e.pointerId !== pointerId) return;
    reprendreAnimation();
  });

})();
});
</script>
"""


def construire_bloom_block(articles: list[dict]) -> str:
    """
    Assemble le bloc HTML complet du ticker v3 :
    CSS embarqué + items (doublés seamless) + JS interaction.
    """
    if not articles:
        fallback = (
            '<a class="bloom-item">'
            '<span class="bloom-title">Aucune dépêche récente.</span>'
            '</a>\n'
        ) * 2
        return _css_bloc() + fallback + _js_bloc()

    items_html = "\n".join(_render_item(a) for a in articles)
    # Doublement pour seamless loop CSS
    return _css_bloc() + items_html + "\n" + items_html + "\n" + _js_bloc()


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

def main():
    print("🎞️  nb_bloom_animator v4 — génération du bandeau Bloomberg")
    print("─" * 52)

    # 1. Récupération
    articles = recuperer_articles_batch(limite=TICKER_MAX_ARTICLES)
    print(f"  📥 {len(articles)} articles du dernier batch")

    if not articles:
        print("  ⚠️  Aucun article récent. Bandeau vide.")

    # 2. Construction
    bloc_html = construire_bloom_block(articles)

    # 3. Résumé
    c = {"↑": 0, "→": 0, "↓": 0}
    for a in articles:
        c[a["fleche"]] = c.get(a["fleche"], 0) + 1
    print(f"  Flèches         : ↑{c['↑']}  →{c['→']}  ↓{c['↓']}")
    print(f"  Durée animation : {TICKER_DUREE_SECONDES}s")
    print(f"  Bloc HTML       : {len(bloc_html)} caractères")

    # 4. Écriture
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = SITE_DIR / "bloom_block.html"
    output_path.write_text(bloc_html, encoding="utf-8")
    print(f"  💾 Écrit → {output_path}")
    print()


if __name__ == "__main__":
    main()
