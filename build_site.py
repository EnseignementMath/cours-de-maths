import os, sys, pathlib, shutil, re
import pandas as pd
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape

REPO_ROOT = pathlib.Path(__file__).parent.resolve()
ODS_PATH = REPO_ROOT / "cahier_de_texte.ods"
TEMPLATE_DIR = REPO_ROOT / "templates"
OUTPUT_DIR = REPO_ROOT / "classes"

def ensure_dir(p: pathlib.Path):
    p.mkdir(parents=True, exist_ok=True)

def slugify(text: str, maxlen=80) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text[:maxlen] if len(text) > maxlen else text

def parse_date(value: str) -> str:
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%Y-%m-%d")
    v = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(v, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    try:
        return datetime.fromisoformat(v).strftime("%Y-%m-%d")
    except Exception:
        raise ValueError(f"Date invalide: {value}")

def parse_pieces(cell):
    if pd.isna(cell) or str(cell).strip() == "":
        return []
    parts = [str(p).strip().replace("\\", "/") for p in str(cell).split(";")]
    return [p for p in parts if p]

def main():
    if not ODS_PATH.exists():
        print(f"ODS manquant: {ODS_PATH}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_excel(ODS_PATH, sheet_name=0, engine="odf")
    low = {c.lower().strip(): c for c in df.columns}
    def getcol(*cands):
        for c in cands:
            if c in low: return low[c]
        return None

    c_date = getcol("date")
    c_classe = getcol("classe")
    c_chap = getcol("chapitre")
    c_titre = getcol("titre","intitulé","intitule")
    c_resume = getcol("resume","résumé","description")
    c_lien = getcol("lien","lien_externe","url")
    c_pj = getcol("pieces_jointes","pièces_jointes","pj","pieces","pièces")

    for need, name in [(c_date,"date"),(c_classe,"classe"),(c_chap,"chapitre"),(c_titre,"titre")]:
        if need is None:
            raise SystemExit(f"Colonne requise manquante dans l'ODS: {name}")

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)),
                      autoescape=select_autoescape(["html","xml","md"]))
    tpl = env.get_template("seance.md.j2")

    generated = []
    for _, row in df.iterrows():
        date = parse_date(row[c_date])
        classe = str(row[c_classe]).strip()
        chapitre = str(row[c_chap]).strip()
        titre = str(row[c_titre]).strip()
        resume = "" if c_resume is None or pd.isna(row.get(c_resume, "")) else str(row[c_resume]).strip()
        lien = "" if c_lien is None or pd.isna(row.get(c_lien, "")) else str(row[c_lien]).strip()
        pieces = [] if c_pj is None else parse_pieces(row.get(c_pj, ""))

        out_dir = OUTPUT_DIR / classe
        ensure_dir(out_dir)
        slug = slugify(f"{chapitre}-{titre}")
        out_path = out_dir / f"{date}-{slug}.md"
        md = tpl.render(date=date, classe=classe, chapitre=chapitre, titre=titre,
                        resume=resume if resume else None,
                        lien_externe=lien if lien else None,
                        pieces=pieces)
        out_path.write_text(md, encoding="utf-8")
        generated.append(out_path)

    for classe_dir in OUTPUT_DIR.iterdir():
        if classe_dir.is_dir():
            files = sorted(classe_dir.glob("*.md"), reverse=True)
            lines = ["# Séances", ""]
            if not files:
                lines.append("Aucune séance.")
            for md in files:
                lines.append(f"- [{md.stem}](/classes/{classe_dir.name}/{md.name})")
            (classe_dir / "index.md").write_text("\n".join(lines)+"\n", encoding="utf-8")

    print(f"OK - séances générées: {len(generated)}")

if __name__ == "__main__":
    main()
