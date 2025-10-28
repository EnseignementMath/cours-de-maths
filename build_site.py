# -*- coding: utf-8 -*-
# Génère des pages HTML prêtes à être servies par GitHub Pages (sans Jekyll).
# Placez ce fichier dans: cours-de-maths_site/cours-de-maths/build_site.py
# Dépendances: pandas, odfpy  (pip install pandas odfpy)

import os
import re
import pathlib
from datetime import datetime

import pandas as pd

# ==============================
# CONFIG
# ==============================
REPO_ROOT = pathlib.Path(__file__).parent.resolve()

ODS_PATH = REPO_ROOT / "cahier_de_texte.ods"  # nom attendu à la racine du site
OUTPUT_DIR = REPO_ROOT / "classes"            # pages générées
TARGET_CLASSES = {"5e"}                       # ne générer que ces classes (modifier si besoin)

# Noms de colonnes tolérés (insensibles à la casse et aux accents)
CAND_DATE = {"date", "jour"}
CAND_CLASSE = {"classe", "classe "}
CAND_CHAP = {"chapitre", "chapitre "}
CAND_TITRE = {"titre", "intitulé", "intitule"}
CAND_RESUME = {"resume", "résumé", "description"}
CAND_LIEN = {"lien", "url", "lien_externe"}
CAND_PJ = {"pieces_jointes", "pièces_jointes", "pj", "pieces", "pièces"}

# ==============================
# UTILITAIRES
# ==============================
def ensure_dir(p: pathlib.Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def slugify(text: str, maxlen: int = 80) -> str:
    t = text.lower()
    t = re.sub(r"[^\w\s-]", "", t, flags=re.UNICODE)
    t = re.sub(r"\s+", "-", t).strip("-")
    return t[:maxlen] if len(t) > maxlen else t

def parse_date(value) -> str:
    # pandas peut renvoyer Timestamp
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%Y-%m-%d")
    v = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(v, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    # dernier recours ISO
    try:
        return datetime.fromisoformat(v).strftime("%Y-%m-%d")
    except Exception:
        raise ValueError(f"Date invalide: {value}")

def split_pieces(cell) -> list:
    if pd.isna(cell) or str(cell).strip() == "":
        return []
    parts = [str(p).strip().replace("\\", "/") for p in str(cell).split(";")]
    return [p for p in parts if p]

def norm_key(s: str) -> str:
    s = s.strip().lower()
    # remplace les accents courants
    table = str.maketrans("éèêàïîôûùç", "eeea iouuc")
    s = s.translate(table).replace(" ", "")
    return s

def map_columns(df: pd.DataFrame) -> dict:
    low = {norm_key(c): c for c in df.columns}
    def find(cands):
        for c in cands:
            k = norm_key(c)
            if k in low:
                return low[k]
        # aussi: si l'utilisateur a déjà mis exactement ce nom
        for kraw, orig in low.items():
            if kraw in cands:
                return orig
        return None
    cols = {}
    cols["date"] = find(CAND_DATE)
    cols["classe"] = find(CAND_CLASSE)
    cols["chapitre"] = find(CAND_CHAP)
    cols["titre"] = find(CAND_TITRE)
    cols["resume"] = find(CAND_RESUME)
    cols["lien"] = find(CAND_LIEN)
    cols["pj"] = find(CAND_PJ)
    # vérifs minimales
    for need in ("date", "classe", "chapitre", "titre"):
        if cols[need] is None:
            raise SystemExit(f"Colonne requise manquante dans l'ODS: {need}")
    return cols

# ==============================
# RENDER HTML
# ==============================
PAGE_STYLE = """
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Arial;
     margin:24px; color:#0d1b2a; background:#f7f7fb;}
a{color:#1d4ed8; text-decoration:none} a:hover{text-decoration:underline}
.container{max-width:920px;margin:0 auto}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:18px}
h1{font-size:28px;margin:0 0 10px} h2{font-size:20px;margin:20px 0 10px}
ul{padding-left:20px}
.tag{display:inline-block;background:#eef2ff;color:#1e3a8a;border-radius:10px;padding:2px 8px;margin-left:8px;font-size:12px}
.meta{color:#475569;font-size:14px}
.footer{margin-top:28px;color:#64748b;font-size:14px}
.list>li{margin:6px 0}
</style>
"""

INDEX_CLASS_TEMPLATE = """<!doctype html>
<html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Séances — {classe}</title>
{style}
<body><div class="container">
  <h1>Séances — {classe}</h1>
  <div class="card">
    <p class="meta">Liste des séances publiées pour la classe de {classe}.</p>
    <ul class="list">
      {items}
    </ul>
  </div>
  <p class="footer"><a href="/cours-de-maths/">Retour à l’accueil</a></p>
</div></body></html>
"""

SESSION_TEMPLATE = """<!doctype html>
<html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{chapitre} — {titre} ({date})</title>
{style}
<body><div class="container">
  <h1>{chapitre} — {titre} <span class="tag">{date}</span></h1>
  <p class="meta">Classe : {classe}</p>
  {bloc_resume}
  {bloc_lien}
  <h2>Pièces jointes</h2>
  {bloc_pieces}
  <p class="footer"><a href="/cours-de-maths/classes/{classe}/">← Retour à {classe}</a></p>
</div></body></html>
"""

def render_resume(resume: str) -> str:
    if not resume:
        return ""
    return f'<div class="card"><p>{resume}</p></div>'

def render_lien(url: str) -> str:
    if not url:
        return ""
    return f'<h2>Lien utile</h2><div class="card"><a href="{url}" target="_blank" rel="noopener">{url}</a></div>'

def render_pieces(pieces: list) -> str:
    if not pieces:
        return '<div class="card"><p>Aucune pièce jointe.</p></div>'
    lis = []
    for p in pieces:
        label = p.replace("assets/", "")
        lis.append(f'<li><a href="/cours-de-maths/{p}" target="_blank" rel="noopener">{label}</a></li>')
    return '<div class="card"><ul class="list">' + "\n".join(lis) + "</ul></div>"

# ==============================
# MAIN
# ==============================
def main() -> int:
    if not ODS_PATH.exists():
        print(f"[ERREUR] ODS introuvable: {ODS_PATH}")
        return 1

    # lecture de la première feuille
    df = pd.read_excel(ODS_PATH, sheet_name=0, engine="odf")
    cols = map_columns(df)

    # filtrage classes
    df = df.copy()
    df["__classe__"] = df[cols["classe"]].astype(str).str.strip()
    if TARGET_CLASSES:
        df = df[df["__classe__"].isin(TARGET_CLASSES)]

    if df.empty:
        print("[INFO] Aucune ligne à générer pour les classes ciblées.")
        return 0

    generated = []
    # regrouper par classe
    for classe, sub in df.groupby("__classe__"):
        out_dir = OUTPUT_DIR / classe
        ensure_dir(out_dir)

        items_li = []

        for _, row in sub.iterrows():
            try:
                date = parse_date(row[cols["date"]])
            except Exception as e:
                raise SystemExit(f"Date invalide sur une ligne ({e})")

            chapitre = str(row[cols["chapitre"]]).strip()
            titre = str(row[cols["titre"]]).strip()

            resume = ""
            if cols["resume"] and pd.notna(row.get(cols["resume"], "")):
                resume = str(row[cols["resume"]]).strip()

            lien = ""
            if cols["lien"] and pd.notna(row.get(cols["lien"], "")):
                lien = str(row[cols["lien"]]).strip()

            pieces = []
            if cols["pj"]:
                pieces = split_pieces(row.get(cols["pj"], ""))

            slug = slugify(f"{chapitre}-{titre}")
            page_name = f"{date}-{slug}.html"
            page_path = out_dir / page_name

            html = SESSION_TEMPLATE.format(
                style=PAGE_STYLE,
                chapitre=chapitre,
                titre=titre,
                date=date,
                classe=classe,
                bloc_resume=render_resume(resume),
                bloc_lien=render_lien(lien),
                bloc_pieces=render_pieces(pieces),
            )
            page_path.write_text(html, encoding="utf-8")
            generated.append(page_path)

            items_li.append(
                f'<li><a href="/cours-de-maths/classes/{classe}/{page_name}">{date} — {chapitre} : {titre}</a></li>'
            )

        # index.html de la classe
        index_html = INDEX_CLASS_TEMPLATE.format(
            style=PAGE_STYLE,
            classe=classe,
            items="\n".join(sorted(items_li, reverse=True)),
        )
        (out_dir / "index.html").write_text(index_html, encoding="utf-8")

    print(f"[OK] Fichiers générés: {len(generated)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
