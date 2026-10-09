@echo off
setlocal
cd /d "%~dp0"
echo AstroMotion - Python-Umgebung einrichten

rem Eine vorhandene Projektumgebung unveraendert weiterverwenden.
if exist ".venv\Scripts\python.exe" goto install
if exist ".venv" goto broken_venv

rem Python Launcher bevorzugen, alternativ Python aus dem PATH verwenden.
where py >nul 2>nul
if errorlevel 1 goto create_with_python
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 goto create_with_python
py -3 -m venv .venv
if errorlevel 1 goto venv_failed
goto install

:create_with_python
where python >nul 2>nul
if errorlevel 1 goto python_missing
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 goto python_missing
python -m venv .venv
if errorlevel 1 goto venv_failed

:install
rem Genau diesen Interpreter nutzt auch start_windows.bat fuer main.py.
".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 goto unsupported_venv
if not exist "requirements.txt" goto requirements_missing
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto install_failed
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto install_failed
".venv\Scripts\python.exe" -c "import numpy, cv2, PIL, yaml, tifffile"
if errorlevel 1 goto import_failed

echo.
echo Einrichtung abgeschlossen. Alle Python-Abhaengigkeiten sind verfuegbar.
echo AstroMotion mit start_windows.bat oder .venv\Scripts\python.exe starten.
echo FFmpeg und StarNet2 separat installieren, siehe README.
pause
exit /b 0

:python_missing
echo FEHLER: Python 3.11+ fehlt. Python installieren und PATH oder Launcher aktivieren.
goto failed
:broken_venv
echo FEHLER: .venv existiert, aber .venv\Scripts\python.exe fehlt.
echo Die vorhandene Umgebung reparieren oder umbenennen und setup.bat erneut starten.
goto failed
:unsupported_venv
echo FEHLER: Die vorhandene .venv benoetigt einen funktionsfaehigen Python 3.11+ Interpreter.
echo Die Umgebung mit Python 3.11+ neu erstellen und setup.bat erneut starten.
goto failed
:venv_failed
echo FEHLER: Die virtuelle Umgebung .venv konnte nicht erstellt werden.
echo Python-Installation und Schreibrechte pruefen; Details stehen oben.
goto failed
:requirements_missing
echo FEHLER: requirements.txt fehlt. Das Repository vollstaendig entpacken.
goto failed
:install_failed
echo FEHLER: Die Abhaengigkeiten aus requirements.txt konnten nicht vollstaendig installiert werden.
echo Internetverbindung und die pip-Fehlermeldung oben pruefen. setup.bat erneut starten.
echo Manuell: .venv\Scripts\python.exe -m pip install -r requirements.txt
goto failed
:import_failed
echo FEHLER: Ein installiertes Python-Paket konnte nicht importiert werden.
echo Fehlermeldung oben pruefen. AstroMotion wird mit dieser Umgebung noch nicht gestartet.
:failed
pause
exit /b 1
