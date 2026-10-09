@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Zuerst setup_windows.bat ausfuehren.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\create_demo.py
if errorlevel 1 goto failed
".venv\Scripts\python.exe" main.py --input examples\deep_sky.png --starless examples\deep_sky_starless.png --config configs\immersive_loop.yaml --resolution 720p --duration 30 --output examples\demo_loop.mp4 --overwrite
if errorlevel 1 goto failed
echo Demo fertig: examples\demo_loop.mp4
pause
exit /b 0
:failed
echo Demo fehlgeschlagen. Fehlermeldung oben und README beachten.
pause
exit /b 1
