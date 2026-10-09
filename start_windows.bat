@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Zuerst setup_windows.bat ausfuehren.
  pause
  exit /b 1
)
if "%~1"=="" (
  echo Foto auf diese Datei ziehen: nutzt config.yaml und konfiguriertes StarNet.
  echo Oder in CMD: start_windows.bat --input foto.png --starless ohne_sterne.png --music ambient
  pause
  exit /b 1
)
rem Datei-Drag-and-Drop oder ein einzelner Bildpfad.
set "AM_FIRST=%~1"
if "%AM_FIRST:~0,2%"=="--" goto cli
".venv\Scripts\python.exe" main.py --config config.yaml --input "%~1"
goto done
:cli
".venv\Scripts\python.exe" main.py %*
:done
set "AM_EXIT=%ERRORLEVEL%"
pause
exit /b %AM_EXIT%
