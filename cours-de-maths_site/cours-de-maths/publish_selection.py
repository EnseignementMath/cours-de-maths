import json, os, sys, pathlib, re
from datetime import datetime

REPO = pathlib.Path(__file__).parent.resolve()
TMP_JSON = pathlib.Path(os.environ.get("TEMP", "")) / "cahier_selection.json"
OUTPUT_DIR = REPO / "classes"

def ensure_dir(p: pathlib.Path):
    p.mkdir(parents=True, exist_ok=True)

def slugify(text: str, maxlen=80) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text[:maxlen] if len(text) > maxlen else text

def parse_date(v: str) -> str:
    v = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(v, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    try:
        return datetime.fromisoformat(v).strftime("%Y-%m-%d")
    except Exception:
        raise ValueError(f"Date invalide: {v}")

def split_pieces(s: str):
    if not s or not str(s).strip():
        return []
    parts = [p.strip().replace("\\","/") for p in str(s).split(";")]
    return [p for p in parts if p]

def render_md(item: dict) -> str:
    date = item["date"]
    classe = item["classe"]
    chapitre = item["chapitre"]
    titre = item["titre"]
    resume = item.get("resume", "")
    lien = item.get("lien_externe", "")
    pieces = item.get("pieces", [])

    lines = []
    lines += ["---", f'title: "{titre}"', f"date: {date}", f'classe: "{classe}"', f'chapitre: "{chapitre}"', "---", ""]
    lines += [f"# {chapitre} — {titre} ({date})", ""]
    if resume:
        lines += [resume, ""]
    if lien:
        lines += [f"Lien utile : [{lien}]({lien})", ""]
    lines += ["## Pièces jointes"]
    if pieces:
        for p in pieces:
            label = p.replace("assets/", "")
            lines.append(f"- [{label}](/{p})")
    else:
        lines.append("Aucune pièce jointe.")
    lines.append("")
    return "\n".join(lines)

def main():
    if not TMP_JSON.exists():
        print(f"JSON introuvable: {TMP_JSON}", file=sys.stderr)
        return 1

    raw = json.loads(TMP_JSON.read_text(encoding='utf-8'))
    normalized = []
    def norm_key(k):
        s = k.lower().strip()
        table = str.maketrans("éèêàïî", "eeeaii")
        s = s.translate(table)
        mapping = {
            "date":"date","classe":"classe","chapitre":"chapitre","titre":"titre",
            "resume":"resume","resumee":"resume","description":"resume",
            "lien":"lien_externe","url":"lien_externe","lien_externe":"lien_externe",
            "pieces_jointes":"pieces_jointes","pieces_jointess":"pieces_jointes","pj":"pieces_jointes","pieces":"pieces_jointes","piece":"pieces_jointes"
        }
        return mapping.get(s, s)

    for row in raw:
        r = {norm_key(k): str(v) for k,v in row.items() if v is not None}
        for req in ("date","classe","chapitre","titre"):
            if req not in r or not r[req].strip():
                raise SystemExit(f"Champ requis manquant: {req} — {row}")
        r["date"] = parse_date(r["date"])
        r["pieces"] = split_pieces(r.get("pieces_jointes",""))
        normalized.append(r)

    for it in normalized:
        out_dir = OUTPUT_DIR / it["classe"]
        ensure_dir(out_dir)
        slug = slugify(f"{it['chapitre']}-{it['titre']}")
        out = out_dir / f"{it['date']}-{slug}.md"
        out.write_text(render_md(it), encoding="utf-8")

    for classe_dir in OUTPUT_DIR.iterdir():
        if classe_dir.is_dir():
            files = sorted(classe_dir.glob('*.md'), reverse=True)
            lines = ["# Séances", ""]
            if not files:
                lines.append("Aucune séance.")
            for md in files:
                lines.append(f"- [{md.stem}](/classes/{classe_dir.name}/{md.name})")
            (classe_dir / "index.md").write_text("\n".join(lines)+"\n", encoding="utf-8")

    print("OK - publication depuis sélection.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
