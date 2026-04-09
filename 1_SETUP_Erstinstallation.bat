@echo off
echo ============================================
echo   SCE Uni Projekt - Erstinstallation
echo ============================================
echo.

:: Python pruefen
python --version >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Python nicht gefunden!
    echo Bitte Python von https://python.org installieren.
    pause
    exit /b 1
)

:: Virtual Environment erstellen
echo [1/3] Virtual Environment erstellen...
if not exist "%~dp0venv" (
    python -m venv "%~dp0venv"
    echo       Erstellt.
) else (
    echo       Existiert bereits.
)

:: Dependencies installieren
echo [2/3] Dependencies installieren...
call "%~dp0venv\Scripts\activate.bat"
pip install -r "%~dp0requirements.txt" --quiet

:: .env erstellen falls nicht vorhanden
echo [3/3] Konfiguration...
if not exist "%~dp0.env" (
    copy "%~dp0.env.example" "%~dp0.env"
    echo       .env erstellt - bitte API-Key eintragen!
) else (
    echo       .env existiert bereits.
)

echo.
echo ============================================
echo   Installation abgeschlossen!
echo.
echo   Naechste Schritte:
echo   1. .env Datei oeffnen und API-Key eintragen
echo   2. 2_START_Tool.bat ausfuehren
echo ============================================
pause
