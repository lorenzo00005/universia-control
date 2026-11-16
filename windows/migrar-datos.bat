@echo off
rem Migra las sesiones de WhatsApp y respaldos de una carpeta vieja a esta (con todo detenido).
rem Uso: migrar-datos.bat [carpeta_origen]   (por defecto D:\universia-control)
set SRC=%~1
if "%SRC%"=="" set SRC=D:\universia-control
set DST=%~dp0..
echo Origen : %SRC%
echo Destino: %DST%
if not exist "%SRC%\data\waha" (echo No encuentro %SRC%\data\waha & pause & exit /b 1)
echo.
echo 1/3 Deteniendo servicios (los datos no se borran)...
pushd "%SRC%"
docker compose -f docker-compose.yml -f docker-compose.usb.yml down 2>nul
docker compose down
popd
echo 2/3 Copiando claves (.env) y sesiones de WhatsApp...
if not exist "%DST%\.env" if exist "%SRC%\.env" copy "%SRC%\.env" "%DST%\.env" >nul
robocopy "%SRC%\data" "%DST%\data" /E /R:2 /W:2 /NFL /NDL
if exist "%SRC%\backups" robocopy "%SRC%\backups" "%DST%\backups" /E /R:2 /W:2 /NFL /NDL
echo 3/3 Iniciando desde el disco nuevo...
call "%~dp0iniciar-ahora.bat"
