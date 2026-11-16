@echo off
set DEST=%LOCALAPPDATA%\UniversiaControl
mkdir "%DEST%" 2>nul
copy /y "%~dp0launcher.ps1" "%DEST%\launcher.ps1" >nul
schtasks /create /tn "UniversiaControl" /sc onlogon /rl limited /f /tr "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File \"%DEST%\launcher.ps1\""
schtasks /run /tn "UniversiaControl"
echo.
echo Listo. Universia Control va a arrancar solo cada vez que inicies Windows con este disco conectado.
echo El link aparece en URL-ACTUAL.txt (ver-link.bat lo abre).
pause
