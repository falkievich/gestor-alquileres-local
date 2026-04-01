from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlmodel import Session, select
from typing import List, Optional
from datetime import date
from app.db import get_session
from app.model.models import Contrato, ContratoCreate, ContratoUpdate, ContratoRead, Departamento, Inquilino
from app.crud import contratos as crud

router = APIRouter(prefix="/contratos", tags=["contratos"])

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
}


@router.get("/", response_model=List[ContratoRead])
def listar_contratos(
    id_inquilinos: Optional[int] = None,
    id_departamentos: Optional[int] = None,
    fecha_inicio_desde: Optional[date] = None,
    fecha_inicio_hasta: Optional[date] = None,
    fecha_fin_desde: Optional[date] = None,
    fecha_fin_hasta: Optional[date] = None,
    estado: Optional[str] = None,
    session: Session = Depends(get_session)
):
    query = select(Contrato)
    if id_inquilinos:
        query = query.where(Contrato.id_inquilinos == id_inquilinos)
    if id_departamentos:
        query = query.where(Contrato.id_departamentos == id_departamentos)
    if fecha_inicio_desde:
        query = query.where(Contrato.fecha_inicio >= fecha_inicio_desde)
    if fecha_inicio_hasta:
        query = query.where(Contrato.fecha_inicio <= fecha_inicio_hasta)
    if fecha_fin_desde:
        query = query.where(Contrato.fecha_fin >= fecha_fin_desde)
    if fecha_fin_hasta:
        query = query.where(Contrato.fecha_fin <= fecha_fin_hasta)
    if estado:
        query = query.where(Contrato.estado == estado)
    return session.exec(query).all()


@router.get("/{id}", response_model=ContratoRead)
def obtener_contrato(id: int, session: Session = Depends(get_session)):
    c = crud.get_contrato(session, id)
    if not c:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    return c


@router.post("/", response_model=ContratoRead, status_code=201)
def crear_contrato(data: ContratoCreate, session: Session = Depends(get_session)):
    return crud.create_contrato(session, data)


@router.get("/{id}/tiene-pagos")
def tiene_pagos(id: int, session: Session = Depends(get_session)):
    from sqlmodel import select
    from app.model.models import RegistroMensual
    c = crud.get_contrato(session, id)
    if not c:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    pagado = session.exec(
        select(RegistroMensual).where(
            RegistroMensual.id_contratos == id,
            RegistroMensual.pagado == True
        )
    ).first()
    return {"tiene_pagos": pagado is not None}


@router.put("/{id}", response_model=ContratoRead)
def actualizar_contrato(id: int, data: ContratoUpdate, session: Session = Depends(get_session)):
    c = crud.update_contrato(session, id, data)
    if not c:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    return c


@router.post("/{id}/cerrar", response_model=ContratoRead)
def cerrar_contrato(id: int, session: Session = Depends(get_session)):
    c = crud.cerrar_contrato(session, id)
    if not c:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    return c


@router.post("/{id}/archivo")
async def subir_archivo(
    id: int,
    archivo: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    import os
    ext = os.path.splitext(archivo.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no permitido. Solo se aceptan: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    contenido = await archivo.read()
    c = crud.update_blob(session, id, contenido, archivo.filename)
    if not c:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    return {"mensaje": "Archivo subido correctamente", "nombre": archivo.filename}


@router.get("/{id}/archivo")
def descargar_archivo(id: int, session: Session = Depends(get_session)):
    import os
    c = crud.get_contrato(session, id)
    if not c:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    if not c.archivo_blob:
        raise HTTPException(
            status_code=404, detail="No hay archivo para este contrato")
    ext = os.path.splitext(c.archivo_nombre or "")[
        1].lower() if c.archivo_nombre else ".pdf"
    content_type = "application/pdf" if ext == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return Response(
        content=c.archivo_blob,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={c.archivo_nombre or 'contrato' + ext}"}
    )


@router.delete("/{id}", status_code=204)
def eliminar_contrato(id: int, session: Session = Depends(get_session)):
    ok = crud.delete_contrato(session, id)
    if not ok:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
