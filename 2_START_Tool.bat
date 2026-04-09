@echo off
echo ============================================
echo   SCE Uni Projekt - Content-Analyse-Tool
echo ============================================
echo.

:: Virtual Environment aktivieren
call "%~dp0venv\Scripts\activate.bat"

:: Hilfe anzeigen
echo Verfuegbare Befehle:
echo.
echo   python run.py einlesen DATEI     - Datei einlesen
echo   python run.py einlesen ORDNER -r - Ordner einlesen
echo   python run.py crawlen URL        - Website crawlen
echo   python run.py suche "BEGRIFF"    - Suchen
echo   python run.py analyse DATEI      - KI-Analyse
echo   python run.py status             - Statistiken
echo   python run.py quellen            - Alle Quellen
echo   python run.py --help             - Hilfe
echo.
echo ============================================

:: Interaktive Shell
cmd /k
