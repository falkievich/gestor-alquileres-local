@echo off
TITLE Depto Manager
SET ROOT=%~dp0

echo.
echo  ========================================
echo   Depto Manager — Iniciando...
echo  ========================================
echo.

REM Verificar que el Python embebido existe
IF NOT EXIST "%ROOT%python\python.exe" (
    echo  [ERROR] No se encontro python\python.exe
    echo  Ejecuta setup.bat primero o descarga Python embebido.
    pause
    exit /b 1
)

REM Verificar que el frontend build existe
IF NOT EXIST "%ROOT%frontend\dist\index.html" (
    echo  [AVISO] No se encontro frontend\dist\index.html
    echo  El sistema funcionara solo como API sin interfaz web.
    echo  Para generar la interfaz ejecuta build-frontend.bat
    echo.
)

echo  Iniciando servidor en http://127.0.0.1:8000
echo  El navegador se abrira automaticamente...
echo.
echo  Para cerrar el programa, cierra esta ventana.
echo.

REM Ejecutar backend con Python embebido
cd /d "%ROOT%backend"
"%ROOT%python\python.exe" app\main.py

pause
