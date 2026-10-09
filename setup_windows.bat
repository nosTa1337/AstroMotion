@echo off
rem Kompatibler bisheriger Dateiname; setup.bat verwaltet dieselbe .venv.
call "%~dp0setup.bat" %*
exit /b %ERRORLEVEL%
