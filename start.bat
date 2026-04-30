@echo off
echo.
echo  ========================================
echo   Depto Manager - Iniciando...
echo  ========================================
echo.
echo  Iniciando servidor en http://127.0.0.1:8000
echo  El navegador se abrira automaticamente...
echo.
echo  Para cerrar el programa, cierra esta ventana.
echo.

SET ROOT=%~dp0

REM Verificar que el Python embebido existe
IF NOT EXIST "%ROOT%python\python.exe" (
    echo  [ERROR] No se encontro python\python.exe
    echo  Descarga Python embebido y extraelo en la carpeta python\
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

REM Ir a la carpeta backend para que Python encuentre el modulo "app"
cd /d "%ROOT%backend"

REM Abrir el navegador despues de 2 segundos (en segundo plano)
start "" cmd /c "timeout /t 2 >nul && start http://127.0.0.1:8000"

REM Ejecutar uvicorn con el Python embebido
"%ROOT%python\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
