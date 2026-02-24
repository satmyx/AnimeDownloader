@echo off
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   VoirAnime Downloader V2 — Launcher     ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Setup des dependances
echo  [1/2] Installation des dependances...
py setup.py
if %errorlevel% neq 0 (
    echo.
    echo  ERREUR : Le setup a echoue. Verifie que Python est bien installe.
    pause
    exit /b 1
)

echo.
echo  [2/2] Lancement du downloader...
echo.
py voiranime_dl_v2.py

echo.
pause
