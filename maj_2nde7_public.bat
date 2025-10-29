@echo off
setlocal
chcp 65001 >nul

set REPO=C:\Users\Utilisateur\Desktop\cours-de-maths
set PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe

cd /d "%REPO%"
"%PY%" "%REPO%\export_progression_public.py"
if errorlevel 1 (
  echo.
  echo [ERREUR] Export en echec.
  pause
  exit /b 1
)

git add "docs\progressions\Seconde\2nde_7.html" "docs\progressions\Seconde\pieces_jointes\*"
git commit -m "MAJ progression 2nde_7 (filtre <= aujourd'hui)"
git push

echo.
echo Publication terminee.
pause
endlocal
