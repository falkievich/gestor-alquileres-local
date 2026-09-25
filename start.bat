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

REM ─────────────────────────────────────────────
REM Deteccion de Supermium (navegador compatible con Windows 8/antiguos).
REM Si no se detecta, se abre el navegador por defecto del sistema.
REM Podes fijar la ruta manualmente: SET SUPERMIUM_PATH=C:\ruta\a\chrome.exe
REM ─────────────────────────────────────────────
SET "SUPERMIUM_PATH="
IF NOT DEFINED SUPERMIUM_PATH CALL :buscar_supermium "%ROOT%Supermium"
IF NOT DEFINED SUPERMIUM_PATH CALL :buscar_supermium "%ProgramFiles%\Supermium"
IF NOT DEFINED SUPERMIUM_PATH CALL :buscar_supermium "%ProgramFiles(x86)%\Supermium"
IF NOT DEFINED SUPERMIUM_PATH CALL :buscar_supermium "%LOCALAPPDATA%\Supermium"
goto continuar

:buscar_supermium
IF DEFINED SUPERMIUM_PATH goto :eof
REM El ejecutable puede llamarse supermium.exe o chrome.exe, y estar
REM directamente en la carpeta o dentro de la subcarpeta Application
IF EXIST "%~1\supermium.exe" SET "SUPERMIUM_PATH=%~1\supermium.exe"
IF EXIST "%~1\chrome.exe" SET "SUPERMIUM_PATH=%~1\chrome.exe"
IF EXIST "%~1\Application\supermium.exe" SET "SUPERMIUM_PATH=%~1\Application\supermium.exe"
IF EXIST "%~1\Application\chrome.exe" SET "SUPERMIUM_PATH=%~1\Application\chrome.exe"
goto :eof

:continuar
IF DEFINED SUPERMIUM_PATH (
    echo  Navegador detectado: Supermium
    start "" cmd /c "timeout /t 2 >nul && "%SUPERMIUM_PATH%" --app=http://127.0.0.1:8000 --new-window"
) ELSE (
    start "" cmd /c "timeout /t 2 >nul && start http://127.0.0.1:8000"
)

REM Ejecutar uvicorn con el Python embebido
"%ROOT%python\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
