@echo off
cd /d "%~dp0.."
docker compose -f docker-compose.yml -f docker-compose.usb.yml down
echo Servicios detenidos (los datos no se borran). Vuelven al reiniciar Windows o con iniciar-ahora.bat.
pause
