# -*- coding: utf-8 -*-
"""
Surveille des fichiers ODS (signature mtime+taille) et publie automatiquement :
- Export HTML (via export_progression_public.py)
- git add/commit/push (docs/progressions + docs/assets)
A lancer avec pythonw.exe (silencieux). Log : autom_update.log
"""

import os, time, subprocess, traceback
from datetime import datetime
from pathlib import Path

# ========= CONFIG =========
PYTHON = os.path.join(os.environ.get("LOCALAPPDATA", r"C:\Users\Utilisateur\AppData\Local"),
                      r"Programs\Python\Python313\python.exe")
REPO = Path(r"C:\Users\Utilisateur\Desktop\cours-de-maths")
EXPORT_SCRIPT = REPO / "export_progression_public.py"
LOGFILE = REPO / "autom_update.log"
CREATE_NO_WINDOW = 0x08000000

# Intervalle de scan et fenêtre de stabilisation
CHECK_INTERVAL = 3          # secondes entre scans
STABILIZE_WINDOW = 2        # nb de scans CONSÉCUTIFS identiques avant déclenchement

# Fichiers surveillés : code_classe -> chemin ODS (source dans "Mon Drive")
FILES = {
    "2nde_7": Path(r"C:\Users\Utilisateur\Desktop\Lycee_Felix_Faure\Seconde\2nde_7\2nde_7_Progression.ods"),
    "302":    Path(r"C:\Users\Utilisateur\Mon Drive\Enseignement\College Montherlant 2025-2026\302\302_Progression.ods"),
    "407":    Path(r"C:\Users\Utilisateur\Mon Drive\Enseignement\College Montherlant 2025-2026\407\407_Progression.ods"),
}

# Optionnel : chemins HTML attendus (uniquement pour touch/mtime si besoin)
HTML_PATHS = {
    "2nde_7": REPO / r"docs\progressions\Seconde\2nde_7.html",
    "302":    REPO / r"docs\progressions\College\302.html",
    "407":    REPO / r"docs\progressions\College\407.html",
}
# ==========================


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def _sig(path: Path):
    try:
        st = path.stat()
        # mtime et taille ENTIER pour éviter le bruit de fractions
        return (int(st.st_mtime), int(st.st_size))
    except FileNotFoundError:
        return None


def run_export():
    cmd = [PYTHON, str(EXPORT_SCRIPT)] if Path(PYTHON).exists() else ["python", str(EXPORT_SCRIPT)]
    try:
        rc = subprocess.call(cmd, cwd=str(REPO), creationflags=CREATE_NO_WINDOW)
        log(f"[INFO] Export terminé (code={rc}).")
    except Exception:
        log("[ERREUR] Exception pendant l'export :\n" + traceback.format_exc())


def git_publish():
    try:
        # Ajoute pages ET assets (pièces jointes)
        subprocess.call(["git", "add", "docs/progressions", "docs/assets"], cwd=str(REPO), creationflags=CREATE_NO_WINDOW)

        status = subprocess.run(["git", "status", "--porcelain"], cwd=str(REPO),
                                creationflags=CREATE_NO_WINDOW, capture_output=True, text=True)
        if status.stdout.strip():
            msg = f"MAJ auto ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
            subprocess.call(["git", "commit", "-m", msg], cwd=str(REPO), creationflags=CREATE_NO_WINDOW)
            subprocess.call(["git", "push"], cwd=str(REPO), creationflags=CREATE_NO_WINDOW)
            log("[INFO] Git push effectué.")
        else:
            log("[INFO] Aucun changement à publier.")
    except Exception:
        log("[ERREUR] Git :\n" + traceback.format_exc())


def main():
    log("=== Démarrage surveillance (mtime+taille) ===")
    paths = {k: v for k, v in FILES.items()}
    last_sig = {k: _sig(p) for k, p in paths.items()}
    stable_count = {k: 0 for k in paths}

    # Log état initial
    for k, p in paths.items():
        log(f"[INIT] {k} -> {p}")
        log(f"[INIT] Signature initiale: {last_sig[k]}")

    while True:
        try:
            trigger = False
            changed_keys = []

            for k, p in paths.items():
                sig = _sig(p)

                if sig != last_sig[k]:
                    # Changement détecté (nouvelle signature)
                    log(f"[INFO] Changement détecté pour {k}: {last_sig[k]} -> {sig}")
                    last_sig[k] = sig
                    stable_count[k] = 0
                else:
                    # Signature identique à la dernière mesure
                    stable_count[k] += 1

                # Déclenchement seulement quand le fichier est stable depuis STABILIZE_WINDOW scans
                if sig is not None and stable_count[k] == STABILIZE_WINDOW:
                    changed_keys.append(k)
                    trigger = True

            if trigger:
                log(f"[INFO] Fichiers stables : {changed_keys} → lancement export")
                run_export()

                # Optionnel: "toucher" les HTML pour marquer une mtime récente (pas obligatoire)
                for k in changed_keys:
                    html = HTML_PATHS.get(k)
                    if html and html.exists():
                        os.utime(html, None)

                git_publish()

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            log(f"[ERREUR] Boucle principale : {repr(e)}")
            log(traceback.format_exc())
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
