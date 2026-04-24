@echo off
TITLE Depto Manager — Build Frontend
SET ROOT=%~dp0

echo.
echo  ========================================
echo   Depto Manager — Generando Frontend
echo  ========================================
echo.

IF NOT EXIST "%ROOT%frontend\package.json" (
    echo  [ERROR] No se encontro frontend\package.json
    pause
    exit /b 1
)

cd /d "%ROOT%frontend"

echo  Instalando dependencias npm...
call npm ci

echo  Generando build de produccion...
call npm run build

echo.
echo  Frontend generado en frontend\dist\
echo  Ya podes ejecutar start.bat
pause
