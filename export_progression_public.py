# -*- coding: utf-8 -*-
r"""
Export des progressions depuis des fichiers .ods vers des pages HTML (GitHub Pages).
- Tolérant aux variantes d'en-têtes (Séance -> Date, Contenu de la séance -> Contenu)
- Gère les dates au format texte (28/10/2025, 28-10-25, 28.10.2025), vrais datetime et nombres Excel/Calc
- Filtre automatiquement les séances dont la date <= aujourd'hui
- Copie les pièces jointes dans assets/pj/<classe>/ et génère un lien "Télécharger"
"""

import os
import re
import sys
import shutil
import unicodedata
from datetime import datetime, date
from pathlib import Path

import pandas as pd

# =========================
# ========= DEBUG =========
# =========================
VERSION = "export_progression_public.py :: 2025-10-29"

def dbg(msg: str):
    print("[DEBUG]", msg)

# Active/désactive le verbosage debug (mettre False si tu n'en veux plus)
DEBUG = True

# =========================
# ===== CONFIGURATION =====
# =========================

# Racine du dépôt local
REPO = Path(r"C:\Users\Utilisateur\Desktop\cours-de-maths")

# Dossiers de sortie
PAGES_DIR = REPO / "progressions"
ASSETS_DIR = REPO / "assets" / "pj"

# Déclare ici les classes à exporter
CLASSES = {
    "407": {
        "level_subdir": "College",
        "ods": Path(r"C:\Users\Utilisateur\Mon Drive\Enseignement\College Montherlant 2025-2026\407\407_Progression.ods"),
        "sheet_name": None,  # None => première feuille
        "title": "Progression – 407",
    },
    # Ajouter d'autres classes au besoin...
}

# Nom du fichier HTML final
HTML_NAME = "{classe}.html"

# Texte du lien PJ
LINK_TEXT = "Télécharger"

# =========================
# ===== PRÉSENTATION ======
# =========================

TABLE_STYLE = """
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #eee; padding: 12px; }
th { background: #f5f589; text-align: left; }
tbody tr:nth-child(even){ background: #fbfbfb; }
"""

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans"; line-height:1.5; margin:24px; }}
h1 {{ font-size: 2rem; margin-bottom: .25rem; }}
p.lead {{ color:#444; margin-top:0; }}
{table_style}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="lead">Séances affichées automatiquement ≤ la date du jour ({today_fr}).</p>

<table>
  <thead>
    <tr>
      <th>Séance</th>
      <th>Chapitre</th>
      <th>Contenu de la séance</th>
      <th>Pièce jointe</th>
    </tr>
  </thead>
  <tbody>
    {rows_html}
  </tbody>
</table>

<p style="margin-top:16px;color:#666;">Dernière mise à jour automatique le {now_fr}.</p>
</body>
</html>
"""

# =========================
# ====== UTILITAIRES ======
# =========================

def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def ensure_dirs(*paths: Path) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)

def to_fr_date(ts: pd.Timestamp | None) -> str:
    if ts is None or pd.isna(ts):
        return ""
    return ts.strftime("%d/%m/%Y")

def normalize_filename(name: str) -> str:
    s = re.sub(r"[^\w\-.]+", "_", name, flags=re.UNICODE)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "fichier"

def _norm(s: str) -> str:
    s = str(s).strip().lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')  # retire accents
    s = re.sub(r"\s+", " ", s)
    return s

def coerce_date(v):
    """Convertit n'importe quelle valeur de date en pd.Timestamp (ou NaT)."""
    if pd.isna(v):
        return pd.NaT

    if isinstance(v, (datetime, date)):
        return pd.Timestamp(v)

    s = str(v).strip()
    if not s:
        return pd.NaT

    # Uniformiser séparateurs
    s_norm = s.replace(".", "/").replace("-", "/")

    # dd/mm/yy -> dd/mm/yyyy
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2})", s_norm)
    if m:
        d, mth, yy = map(int, m.groups())
        yy = 2000 + yy if yy < 70 else 1900 + yy
        s_norm = f"{d:02d}/{mth:02d}/{yy:04d}"

    ts = pd.to_datetime(s_norm, dayfirst=True, errors="coerce")
    if pd.notna(ts):
        return ts

    # Nombre Excel/Calc (jours depuis 1899-12-30)
    try:
        n = float(str(v))
        base = pd.Timestamp("1899-12-30")
        return base + pd.to_timedelta(int(n), unit="D")
    except Exception:
        return pd.NaT

def read_ods_as_df(path: Path, sheet_name=None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(str(path))
    df = pd.read_excel(path, engine="odf", sheet_name=sheet_name)
    if isinstance(df, dict):  # si plusieurs feuilles
        df = df[list(df.keys())[0]]
    return df

def harmonize_headers(df: pd.DataFrame, code: str) -> pd.DataFrame:
    """Renomme automatiquement les colonnes en noms canons : Date, Chapitre, Contenu, Pièce jointe."""
    present = { _norm(c): c for c in df.columns }

    wanted_norm_to_canon = {
        "date": "Date",
        "seance": "Date",                  # Séance -> Date
        "chapitre": "Chapitre",
        "contenu de la seance": "Contenu", # Contenu de la séance -> Contenu
        "contenu": "Contenu",
        "piece jointe": "Pièce jointe",
        "pièce jointe": "Pièce jointe",
    }

    rename = {}
    for norm_name, canon in wanted_norm_to_canon.items():
        if norm_name in present:
            rename[present[norm_name]] = canon

    if rename:
        df = df.rename(columns=rename)

    expected = ["Date", "Chapitre", "Contenu", "Pièce jointe"]
    missing = [c for c in expected if c not in df.columns]
    if missing and DEBUG:
        dbg(f"ATTENTION({code}) colonnes manquantes: {missing} | présentes: {list(df.columns)}")

    keep = [c for c in expected if c in df.columns]
    return df[keep].copy()

def copy_attachment_to_repo(src: str, class_code: str) -> str | None:
    """Copie la pièce jointe dans le dépôt et retourne l'URL (relative au site)."""
    if not src or str(src).strip() == "":
        return None
    src_path = Path(str(src))
    if not src_path.exists():
        return None

    target_dir = ASSETS_DIR / class_code
    ensure_dirs(target_dir)
    target_name = normalize_filename(src_path.name)
    target_path = target_dir / target_name
    shutil.copy2(src_path, target_path)

    return f"/cours-de-maths/{target_path.relative_to(REPO).as_posix()}"

def build_rows_html(df: pd.DataFrame, class_code: str) -> str:
    rows = []
    for _, row in df.iterrows():
        d = row.get("Date")
        chap = row.get("Chapitre", "")
        cont = row.get("Contenu", "")
        pj = row.get("Pièce jointe", "")

        date_txt = to_fr_date(d)
        url = None
        try:
            url = copy_attachment_to_repo(str(pj), class_code)
        except Exception:
            url = None

        link_html = f'<a href="{url}" target="_blank" rel="noopener">{LINK_TEXT}</a>' if url else ""
        rows.append(f"<tr><td>{date_txt}</td><td>{chap}</td><td>{cont}</td><td>{link_html}</td></tr>")
    return "\n".join(rows)

# =========================
# ========= EXPORT ========
# =========================

def export_one_class(code: str, spec: dict) -> Path:
    level = spec["level_subdir"]
    ods_path: Path = spec["ods"]
    sheet_name = spec.get("sheet_name")
    title = spec.get("title", f"Progression – {code}")

    log(f"Lecture ODS: {ods_path}")
    df = read_ods_as_df(ods_path, sheet_name=sheet_name)
    if DEBUG: dbg(f"Colonnes initiales: {list(df.columns)} | lignes={len(df)}")

    df = harmonize_headers(df, code)
    if DEBUG: dbg(f"Colonnes harmonisées: {list(df.columns)} | lignes={len(df)}")

    if "Date" not in df.columns:
        raise KeyError("Date")

    df["Date"] = df["Date"].apply(coerce_date)

    # Filtre <= aujourd'hui
    today = pd.Timestamp(datetime.now().date())
    df = df[df["Date"].notna() & (df["Date"] <= today)]
    if DEBUG: dbg(f"Après filtre date (<= {today.date()}): lignes={len(df)}")

    # Tri
    df = df.sort_values("Date").reset_index(drop=True)

    # Génération HTML
    rows_html = build_rows_html(df, class_code=code)
    today_fr = to_fr_date(today)
    now_fr = datetime.now().strftime("%d/%m/%Y %H:%M")

    out_dir = PAGES_DIR / level
    ensure_dirs(out_dir, ASSETS_DIR)

    out_file = out_dir / HTML_NAME.format(classe=code)
    html = PAGE_TEMPLATE.format(
        title=title,
        today_fr=today_fr,
        now_fr=now_fr,
        rows_html=rows_html,
        table_style=TABLE_STYLE,
    )
    out_file.write_text(html, encoding="utf-8")
    log(f"HTML écrit: {out_file}")

    # Dump debug (facultatif)
    if DEBUG:
        dbg_dir = REPO / "debug"
        ensure_dirs(dbg_dir)
        df.to_csv(dbg_dir / f"{code}_apres_filtre.csv", index=False, encoding="utf-8")

    return out_file

def main():
    if DEBUG: dbg(VERSION)
    ensure_dirs(PAGES_DIR, ASSETS_DIR)
    produced = []
    for code, spec in CLASSES.items():
        try:
            produced.append(export_one_class(code, spec))
        except Exception as e:
            log(f"ERREUR sur {code}: {e}")

    if produced:
        log("Export terminé.")
        return 0
    else:
        log("Aucun fichier produit.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
