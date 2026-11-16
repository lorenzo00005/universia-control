@echo off
cd /d "%~dp0.."
if exist URL-ACTUAL.txt (type URL-ACTUAL.txt) else (echo Todavia no hay link: espera 1-2 minutos despues de iniciar.)
echo.
pause
