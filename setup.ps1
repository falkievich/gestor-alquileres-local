# =============================================================
#  setup.ps1 — Instalación completa del proyecto gestor-alquileres-local
#  Uso: .\setup.ps1
# =============================================================

$ROOT = $PSScriptRoot

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  gestor-alquileres-local — Setup" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Backend: crear .venv si no existe ─────────────────────
Write-Host "[1/4] Configurando entorno virtual de Python (backend)..." -ForegroundColor Yellow

$venvPath = "$ROOT\backend\.venv"

if (-Not (Test-Path $venvPath)) {
    python -m venv $venvPath
    Write-Host "      .venv creado en backend\.venv" -ForegroundColor Green
} else {
    Write-Host "      .venv ya existe, se omite la creacion." -ForegroundColor Gray
}

# ── 2. Backend: instalar dependencias Python ──────────────────
Write-Host ""
Write-Host "[2/4] Instalando dependencias de Python..." -ForegroundColor Yellow

& "$venvPath\Scripts\pip.exe" install -r "$ROOT\backend\requirements.txt" --quiet

Write-Host "      Dependencias de Python instaladas." -ForegroundColor Green

# ── 3. Frontend: instalar dependencias Node ───────────────────
Write-Host ""
Write-Host "[3/4] Instalando dependencias de Node (frontend)..." -ForegroundColor Yellow

Set-Location "$ROOT\frontend"
npm install --silent

Write-Host "      Dependencias de Node instaladas." -ForegroundColor Green
Set-Location $ROOT

# ── 4. Crear archivo .env en backend (si no existe) ──────────
Write-Host ""
Write-Host "[4/4] Creando archivo de variables de entorno (backend\.env)..." -ForegroundColor Yellow

$envFile = "$ROOT\backend\.env"

if (-Not (Test-Path $envFile)) {
    @"
# Variables de entorno — gestor-alquileres-local
# Generado automaticamente por setup.ps1

# Ruta a la base de datos SQLite (relativa al backend)
DATABASE_URL=sqlite:///../base_de_datos/alquileres.sqlite

# Puerto del servidor
PORT=8000

# Entorno (development | production)
ENVIRONMENT=development
"@ | Set-Content $envFile -Encoding UTF8
    Write-Host "      backend\.env creado." -ForegroundColor Green
} else {
    Write-Host "      backend\.env ya existe, se omite." -ForegroundColor Gray
}

# ── Resumen final ─────────────────────────────────────────────
Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  Setup completado exitosamente!" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para levantar el proyecto:" -ForegroundColor White
Write-Host ""
Write-Host "  Backend:" -ForegroundColor Yellow
Write-Host "    cd backend" -ForegroundColor Gray
Write-Host "    .venv\Scripts\uvicorn.exe app.main:app --reload --port 8000" -ForegroundColor Gray
Write-Host ""
Write-Host "  Frontend:" -ForegroundColor Yellow
Write-Host "    cd frontend" -ForegroundColor Gray
Write-Host "    npm run dev" -ForegroundColor Gray
Write-Host ""
