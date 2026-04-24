from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.db import create_db_and_tables
from app.routers import departamentos, inquilinos, contratos, dashboard, servicios, aumentos, backup
import app.model.models  # noqa: F401
from pathlib import Path
import sys

# ──────────────────────────────────────────────
# Ruta base del proyecto (funciona tanto en dev
# como con Python embebido en carpeta portable)
# ──────────────────────────────────────────────
def get_project_root() -> Path:
    """Retorna la raíz del proyecto independientemente de cómo se ejecute."""
    if getattr(sys, "frozen", False):
        # PyInstaller (futuro)
        return Path(sys._MEIPASS)
    # desarrollo o Python embebido: backend/app/main.py → subir 2 niveles
    return Path(__file__).resolve().parent.parent.parent

PROJECT_ROOT = get_project_root()
FRONTEND_BUILD = PROJECT_ROOT / "frontend" / "dist"

app = FastAPI(title="Gestor de Alquileres", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/health")
def health():
    return {"status": "ok", "mensaje": "Backend funcionando correctamente"}


app.include_router(departamentos.router)
app.include_router(inquilinos.router)
app.include_router(contratos.router)
app.include_router(dashboard.router)
app.include_router(servicios.router)
app.include_router(aumentos.router)
app.include_router(backup.router)

# ──────────────────────────────────────────────
# Servir frontend build (solo si existe dist/)
# Esto permite entregar el proyecto como portable
# ──────────────────────────────────────────────
if FRONTEND_BUILD.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_BUILD / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """Fallback: devuelve index.html para rutas SPA."""
        requested = FRONTEND_BUILD / full_path
        if requested.is_file():
            return FileResponse(str(requested))
        return FileResponse(str(FRONTEND_BUILD / "index.html"))


# ──────────────────────────────────────────────
# Entrypoint para Python embebido / portable
# Ejecutar: python\python.exe backend\app\main.py
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading

    url = "http://127.0.0.1:8000"

    def abrir_navegador():
        import time
        time.sleep(1.5)  # esperar que uvicorn levante
        webbrowser.open(url)

    threading.Thread(target=abrir_navegador, daemon=True).start()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")
