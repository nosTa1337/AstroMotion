@echo off
setlocal
cd /d "%~dp0"
echo AstroMotion - Python-Umgebung einrichten
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.11+ von python.org installieren, inklusive Python Launcher.
  pause
  exit /b 1
)
py -3 -c "import sys; assert sys.version_info.__ge__((3,11)), 'Python 3.11+ erforderlich'"
if errorlevel 1 goto failed
py -3 -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Einrichtung abgeschlossen. FFmpeg und StarNet separat installieren, siehe README.
pause
exit /b 0
:failed
echo Einrichtung fehlgeschlagen. Fehlermeldung oben beachten.
pause
exit /b 1
