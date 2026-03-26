from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
from app.db import get_session
from app.model.models import Inquilino, InquilinoCreate, InquilinoUpdate, ContratoRead
from app.crud import inquilinos as crud

router = APIRouter(prefix="/inquilinos", tags=["inquilinos"])


@router.get("/", response_model=List[Inquilino])
def listar_inquilinos(session: Session = Depends(get_session)):
    return crud.get_inquilinos(session)


@router.get("/{id}", response_model=Inquilino)
def obtener_inquilino(id: int, session: Session = Depends(get_session)):
    inq = crud.get_inquilino(session, id)
    if not inq:
        raise HTTPException(status_code=404, detail="Inquilino no encontrado")
    return inq


@router.post("/", response_model=Inquilino, status_code=201)
def crear_inquilino(data: InquilinoCreate, session: Session = Depends(get_session)):
    return crud.create_inquilino(session, data)


@router.put("/{id}", response_model=Inquilino)
def actualizar_inquilino(id: int, data: InquilinoUpdate, session: Session = Depends(get_session)):
    inq = crud.update_inquilino(session, id, data)
    if not inq:
        raise HTTPException(status_code=404, detail="Inquilino no encontrado")
    return inq


@router.delete("/{id}", status_code=204)
def eliminar_inquilino(id: int, session: Session = Depends(get_session)):
    ok = crud.delete_inquilino(session, id)
    if not ok:
        raise HTTPException(status_code=404, detail="Inquilino no encontrado")


@router.get("/{id}/contratos")
def contratos_inquilino(id: int, session: Session = Depends(get_session)):
    from sqlmodel import select
    from app.model.models import Contrato, Departamento
    inq = crud.get_inquilino(session, id)
    if not inq:
        raise HTTPException(status_code=404, detail="Inquilino no encontrado")
    contratos = session.exec(
        select(Contrato).where(Contrato.id_inquilinos == id)
    ).all()
    resultado = []
    for c in contratos:
        dep = session.get(Departamento, c.id_departamentos)
        resultado.append({"contrato": ContratoRead.model_validate(c), "departamento": dep})
    return resultado


@router.get("/{id}/pagos")
def pagos_inquilino(
    id: int,
    anio: int = None,
    mes: int = None,
    session: Session = Depends(get_session)
):
    from sqlmodel import select
    from app.model.models import Contrato, RegistroMensual, Departamento
    inq = crud.get_inquilino(session, id)
    if not inq:
        raise HTTPException(status_code=404, detail="Inquilino no encontrado")
    contratos = session.exec(
        select(Contrato).where(Contrato.id_inquilinos == id)
    ).all()
    resultado = []
    for c in contratos:
        dep = session.get(Departamento, c.id_departamentos)
        query = select(RegistroMensual).where(RegistroMensual.id_contratos == c.id_contratos)
        if anio:
            query = query.where(RegistroMensual.anio == anio)
        if mes:
            query = query.where(RegistroMensual.mes == mes)
        registros = session.exec(query).all()
        for r in registros:
            resultado.append({
                "registro": r,
                "departamento": dep,
                "contrato_id": c.id_contratos
            })
    return resultado
