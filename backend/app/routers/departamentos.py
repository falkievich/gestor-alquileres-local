from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
from app.db import get_session
from app.model.models import Departamento, DepartamentoCreate, DepartamentoUpdate
from app.crud import departamentos as crud
from app.crud import contratos as crud_contratos
from app.crud import registros as crud_registros

router = APIRouter(prefix="/departamentos", tags=["departamentos"])


@router.get("/", response_model=List[Departamento])
def listar_departamentos(session: Session = Depends(get_session)):
    return crud.get_departamentos(session)


@router.get("/{id}", response_model=Departamento)
def obtener_departamento(id: int, session: Session = Depends(get_session)):
    dep = crud.get_departamento(session, id)
    if not dep:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return dep


@router.post("/", response_model=Departamento, status_code=201)
def crear_departamento(data: DepartamentoCreate, session: Session = Depends(get_session)):
    try:
        return crud.create_departamento(session, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}", response_model=Departamento)
def actualizar_departamento(id: int, data: DepartamentoUpdate, session: Session = Depends(get_session)):
    try:
        dep = crud.update_departamento(session, id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not dep:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return dep


@router.delete("/{id}", status_code=204)
def eliminar_departamento(id: int, session: Session = Depends(get_session)):
    ok = crud.delete_departamento(session, id)
    if not ok:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")


@router.get("/{id}/historial")
def historial_departamento(id: int, session: Session = Depends(get_session)):
    from sqlmodel import select
    from app.model.models import Contrato, Inquilino
    dep = crud.get_departamento(session, id)
    if not dep:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    contratos = session.exec(
        select(Contrato).where(Contrato.id_departamentos == id)
    ).all()
    resultado = []
    for c in contratos:
        inq = session.get(Inquilino, c.id_inquilinos)
        resultado.append({
            "contrato": c,
            "inquilino": inq
        })
    return resultado


@router.get("/{id}/pagos")
def pagos_departamento(
    id: int,
    anio: int = None,
    mes: int = None,
    id_inquilinos: int = None,
    session: Session = Depends(get_session)
):
    from sqlmodel import select
    from app.model.models import Contrato, RegistroMensual, Inquilino
    dep = crud.get_departamento(session, id)
    if not dep:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")

    contratos = session.exec(
        select(Contrato).where(Contrato.id_departamentos == id)
    ).all()

    resultado = []
    for c in contratos:
        if id_inquilinos and c.id_inquilinos != id_inquilinos:
            continue
        inq = session.get(Inquilino, c.id_inquilinos)
        query = select(RegistroMensual).where(RegistroMensual.id_contratos == c.id_contratos)
        if anio:
            query = query.where(RegistroMensual.anio == anio)
        if mes:
            query = query.where(RegistroMensual.mes == mes)
        registros = session.exec(query).all()
        for r in registros:
            resultado.append({
                "registro": r,
                "inquilino": inq,
                "contrato_id": c.id_contratos
            })
    return resultado
