@echo off
schtasks /end /tn "UniversiaControl" 2>nul
schtasks /delete /tn "UniversiaControl" /f
echo Autoarranque desactivado.
pause
