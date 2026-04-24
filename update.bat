@echo off
TITLE Depto Manager — Actualizar dependencias
SET ROOT=%~dp0

echo.
echo  ========================================
echo   Depto Manager — Actualizando librerias
echo  ========================================
echo.

IF NOT EXIST "%ROOT%python\python.exe" (
    echo  [ERROR] No se encontro python\python.exe
    pause
    exit /b 1
)

echo  Instalando/actualizando dependencias de Python...
"%ROOT%python\python.exe" -m pip install -r "%ROOT%backend\requirements.txt" --quiet
echo  Listo.

echo.
echo  Actualizacion completada.
pause
