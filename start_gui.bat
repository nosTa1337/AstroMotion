@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto start
call "%~dp0setup.bat"
if errorlevel 1 exit /b 1
:start
if "%~1"=="" goto interactive
set "AM_FIRST=%~1"
if "%AM_FIRST:~0,2%"=="--" goto cli
".venv\Scripts\python.exe" gui.py --input "%~1"
goto done
:cli
".venv\Scripts\python.exe" gui.py %*
goto done
:interactive
".venv\Scripts\python.exe" gui.py
:done
if not errorlevel 1 exit /b 0
pause
exit /b 1
