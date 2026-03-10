from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import create_db_and_tables
from app.routers import departamentos, inquilinos, contratos, dashboard, servicios, aumentos, backup
# Importar modelos para que SQLModel los registre
import app.model.models  # noqa: F401

app = FastAPI(title="Gestor de Alquileres", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
