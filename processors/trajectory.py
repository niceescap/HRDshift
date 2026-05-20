#!/usr/bin/env python3
"""
trajectory.py — Générateur de trajectoire HAI & Prix pour HRDshift
============================================================================
Lit les archives editos/ et prices/ pour extraire les séries journalières,
puis produit :
  • trajectory.json  → { hai: [{date, valeur}...], price: [{date, valeur}...], edito_by_date: {date: {...}} }
  • hai_mini.svg     → courbe SVG miniature (7 derniers jours) pour la sidebar
  • price_mini.svg   → idem pour le prix

Tous les chemins sont importés de core.config (zéro valeur en dur).
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from core.config import (
    ARCHIVES_EDITO, ARCHIVES_PRICE,
    TRAJECTORY_JSON, HAI_MINI_SVG, PRICE_MINI_SVG,
)

# -------------------------------------------------------------------
# 1. PARSING DES DATES
# -------------------------------------------------------------------
def _parse_date_from_filename(stem: str, prefix: str) -> str | None:
    """
    Extrait une date normalisée (YYYY-MM-DD) à partir du nom de fichier.
    Exemples :
      edito_260512_0722.json → stem='edito_260512_0722', prefix='edito_'
      nb_price_260515_0013.json → stem='nb_price_260515_0013', prefix='nb_price_'
    Retourne '2026-05-12' ou None.
    """
    if not stem.startswith(prefix):
        return None
    reste = stem[len(prefix):]          # '260512_0722' ou '260515_0013'
    parties = reste.split("_")
    if len(parties) >= 1:
        date_part = parties[0]          # '260512'
        if len(date_part) == 6:
            try:
                an = int("20" + date_part[0:2])
                mois = int(date_part[2:4])
                jour = int(date_part[4:6])
                return f"{an}-{mois:02d}-{jour:02d}"
            except (ValueError, IndexError):
                pass
    return None


# -------------------------------------------------------------------
# 2. EXTRACTION DES SÉRIES JOURNALIÈRES
# -------------------------------------------------------------------
def extract_hai_series() -> list[dict]:
    fichiers = sorted(ARCHIVES_EDITO.glob("edito_*.json"))
    daily = defaultdict(list)

    for f in fichiers:
        # 1) Date depuis le nom du fichier (prioritaire)
        day = _parse_date_from_filename(f.stem, prefix="edito_")
        # 2) Sinon, tenter le meta.timestamp
        if not day:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                ts = data.get("meta", {}).get("timestamp")
                if ts:
                    dt = datetime.fromisoformat(ts)
                    day = dt.strftime("%Y-%m-%d")
            except Exception:
                pass
        if not day:
            continue

        # Lecture des données (si pas déjà fait)
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        val = data.get("hai_edito") or data.get("hai_global") or data.get("hai")
        if val is None:
            continue
        try:
            daily[day].append(float(val))
        except (ValueError, TypeError):
            pass

    series = []
    for day, values in sorted(daily.items()):
        if values:
            avg = round(sum(values) / len(values), 1)
            series.append({"date": day, "valeur": avg})
    return series


def extract_price_series() -> list[dict]:
    fichiers = sorted(ARCHIVES_PRICE.glob("nb_price_*.json"))
    daily = defaultdict(list)

    for f in fichiers:
        # 1) Date depuis le nom du fichier
        day = _parse_date_from_filename(f.stem, prefix="nb_price_")
        # 2) Sinon, meta.timestamp
        if not day:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                ts = data.get("meta", {}).get("timestamp")
                if ts:
                    dt = datetime.fromisoformat(ts)
                    day = dt.strftime("%Y-%m-%d")
            except Exception:
                pass
        if not day:
            continue

        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        val = data.get("prix_estime")
        if val is None:
            continue
        try:
            daily[day].append(float(val))
        except (ValueError, TypeError):
            pass

    series = []
    for day, values in sorted(daily.items()):
        if values:
            avg = round(sum(values) / len(values), 1)
            series.append({"date": day, "valeur": avg})
    return series


# -------------------------------------------------------------------
# 3. MINI SVG POUR LA SIDEBAR
# -------------------------------------------------------------------
def mini_svg_curve(points: list[float],
                   width: int = 180,
                   height: int = 36,
                   stroke_color: str = "#c8a84b") -> str:
    if not points:
        return f'<svg width="{width}" height="{height}"></svg>'

    min_val, max_val = min(points), max(points)
    if max_val == min_val:
        max_val = min_val + 1
    norm = [(p - min_val) / (max_val - min_val) for p in points]

    x_step = width / (len(points) - 1) if len(points) > 1 else width
    pts = []
    for i, v in enumerate(norm):
        x = i * x_step
        y = height - (v * height * 0.8) - height * 0.1
        pts.append((x, y))

    if len(pts) == 1:
        return (f'<svg width="{width}" height="{height}">'
                f'<circle cx="{pts[0][0]}" cy="{pts[0][1]}" r="2" '
                f'fill="{stroke_color}"/></svg>')

    path = f"M {pts[0][0]},{pts[0][1]} "
    for i in range(1, len(pts)):
        cp1_x = pts[i-1][0] + (pts[i][0] - pts[i-1][0]) * 0.4
        cp1_y = pts[i-1][1]
        cp2_x = pts[i][0] - (pts[i][0] - pts[i-1][0]) * 0.4
        cp2_y = pts[i][1]
        path += f"C {cp1_x},{cp1_y} {cp2_x},{cp2_y} {pts[i][0]},{pts[i][1]} "

    svg = (f'<svg width="{width}" height="{height}">'
           f'<path d="{path}" fill="none" stroke="{stroke_color}" '
           f'stroke-width="1.5" opacity="0.8"/></svg>')
    return svg


# -------------------------------------------------------------------
# 4. FONCTION PRINCIPALE
# -------------------------------------------------------------------
def generate():
    print("📈 trajectory.py — génération des courbes et mini SVG")

    hai_series = extract_hai_series()
    price_series = extract_price_series()

    # Construire edito_by_date (un édito par jour)
    edito_by_date = {}
    editos_files = sorted(ARCHIVES_EDITO.glob("edito_*.json"))
    for f in editos_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except:
            continue
        day = _parse_date_from_filename(f.stem, prefix="edito_")
        if not day:
            ts = data.get("meta", {}).get("timestamp")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    day = dt.strftime("%Y-%m-%d")
                except:
                    pass
        if not day:
            continue
        if day not in edito_by_date:
            edito_by_date[day] = {
                "date": day,
                "texte": data.get("texte", data.get("edito", "")),
                "hai": data.get("hai_edito") or data.get("hai_global") or data.get("hai"),
                "tendance": data.get("tendance", "→"),
                "date_edito": data.get("date_edito", "")
            }

    trajectory = {
        "hai": hai_series,
        "price": price_series,
        "edito_by_date": edito_by_date,
        "generated": datetime.now().isoformat()
    }
    TRAJECTORY_JSON.write_text(json.dumps(trajectory, indent=2), encoding="utf-8")
    print(f"  ✅ trajectory.json — {len(hai_series)} jours HAI, {len(price_series)} jours prix, {len(edito_by_date)} éditos")

    # Mini SVG pour les 7 derniers jours
    last_hai = [p["valeur"] for p in hai_series[-7:]] if hai_series else []
    last_price = [p["valeur"] for p in price_series[-7:]] if price_series else []

    hai_svg = mini_svg_curve(last_hai, width=180, height=36, stroke_color="#42b883")
    price_svg = mini_svg_curve(last_price, width=180, height=36, stroke_color="#c8a84b")

    HAI_MINI_SVG.write_text(hai_svg)
    PRICE_MINI_SVG.write_text(price_svg)
    print("  ✅ hai_mini.svg / price_mini.svg")


if __name__ == "__main__":
    generate()
