# -*- coding: utf-8 -*-
"""
Surveille plusieurs fichiers ODS et publie silencieusement sur GitHub Pages.
A lancer avec pythonw.exe pour éviter toute fenêtre.
"""

import os, time, shutil, subprocess, traceback
from datetime import datetime

# ========= CONFIGURATION =========
PYTHON = os.path.join(os.environ.get("LOCALAPPDATA", r"C:\Users\Utilisateur\AppData\Local"),
                      r"Programs\Python\Python313\python.exe")  # adapte si besoin
REPO = r"C:\Users\Utilisateur\Desktop\cours-de-maths"
EXPORT_SCRIPT = os.path.join(REPO, "export_progression_public.py")
CHECK_INTERVAL = 5  # secondes
LOGFILE = os.path.join(REPO, "autom_update.log")
CREATE_NO_WINDOW = 0x08000000

# Fichiers surveillés
CLASSES = {
    "2nde_7": {
        "source": r"C:\Users\Utilisateur\Desktop\Lycee_Felix_Faure\Seconde\2nde_7\2nde_7_Progression.ods",
        "dest": os.path.join(REPO, "2nde_7_Progression.ods"),
        "html": os.path.join(REPO, r"docs\progressions\Seconde\2nde_7.html")
    },
    "302": {
        "source": r"C:\Users\Utilisateur\Mon Drive\Enseignement\College Montherlant 2025-2026\302\302_Progression.ods",
        "dest": os.path.join(REPO, "302_Progression.ods"),
        "html": os.path.join(REPO, r"docs\progressions\College\302.html")
    },
    "407": {
        "source": r"C:\Users\Utilisateur\Mon Drive\Enseignement\College Montherlant 2025-2026\407\407_Progression.ods",
        "dest": os.path.join(REPO, "407_Progression.ods"),
        "html": os.path.join(REPO, r"docs\progressions\College\407.html")
    }
}
# =================================


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def run_silent(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, creationflags=CREATE_NO_WINDOW)


def copy_if_new(src, dst):
    """Copie le fichier src vers dst si plus récent"""
    if not os.path.exists(src):
        log(f"[WARN] Fichier source introuvable : {src}")
        return False
    if not os.path.exists(dst):
        shutil.copy2(src, dst)
        log(f"[INFO] Copie initiale : {os.path.basename(src)}")
        return True
    if os.path.getmtime(src) > os.path.getmtime(dst):
        shutil.copy2(src, dst)
        log(f"[INFO] Nouvelle version détectée : {os.path.basename(src)}")
        return True
    return False


def export_html(classe):
    """Lance le script d'export ODS→HTML"""
    try:
        if os.path.exists(PYTHON):
            proc = run_silent([PYTHON, EXPORT_SCRIPT], cwd=REPO)
        else:
            proc = run_silent(["python", EXPORT_SCRIPT], cwd=REPO)
        log(f"[INFO] Export HTML terminé pour {classe} (code={proc.returncode})")
    except Exception as e:
        log(f"[ERREUR] Export {classe}: {e}")


def git_publish():
    """Effectue add/commit/push silencieux si des changements existent"""
    run_silent(["git", "add", "docs/progressions"], cwd=REPO)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                            creationflags=CREATE_NO_WINDOW,
                            capture_output=True, text=True)
    if status.stdout.strip():
        msg = f"MAJ auto ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        run_silent(["git", "commit", "-m", msg], cwd=REPO)
        run_silent(["git", "push"], cwd=REPO)
        log("[INFO] Git push effectué.")
    else:
        log("[INFO] Aucun changement à publier.")


def main():
    log("=== Démarrage surveillance multi-classes ===")
    while True:
        try:
            maj_effectuee = False
            for classe, paths in CLASSES.items():
                if copy_if_new(paths["source"], paths["dest"]):
                    export_html(classe)
                    if os.path.exists(paths["html"]):
                        os.utime(paths["html"], None)
                    maj_effectuee = True
            if maj_effectuee:
                git_publish()
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            log(f"[ERREUR] {repr(e)}")
            log(traceback.format_exc())
            time.sleep(10)


if __name__ == "__main__":
    main()
