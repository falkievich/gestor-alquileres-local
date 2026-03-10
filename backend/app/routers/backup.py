from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.db import get_session
import shutil
import os
from datetime import datetime

router = APIRouter(prefix="/backup", tags=["backup"])

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_DIR = os.path.dirname(BACKEND_DIR)
DB_PATH = os.path.join(PROJECT_DIR, "base_de_datos", "alquileres.sqlite")
BACKUPS_DIR = os.path.join(PROJECT_DIR, "backups")


@router.post("/")
def crear_backup():
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Base de datos no encontrada")
    ahora = datetime.now()
    nombre = f"alquileres_{ahora.strftime('%Y-%m-%d_%H-%M')}.sqlite"
    destino = os.path.join(BACKUPS_DIR, nombre)
    shutil.copy2(DB_PATH, destino)
    return {"mensaje": "Backup creado correctamente", "archivo": nombre}


@router.get("/")
def listar_backups():
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    archivos = sorted(
        [f for f in os.listdir(BACKUPS_DIR) if f.endswith(".sqlite")],
        reverse=True
    )
    return {"backups": archivos}
