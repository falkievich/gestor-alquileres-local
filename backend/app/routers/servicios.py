from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.db import get_session
from app.crud import contratos as crud_contratos
from app.crud import registros as crud_registros
from app.service.mes_service import (
    get_mes_actual,
    calcular_estado_servicios,
    calcular_total,
)
from app.model.models import Contrato, RegistroMensual
from typing import Optional

router = APIRouter(prefix="/servicios", tags=["servicios"])


@router.get("/pendientes")
def listar_pendientes(session: Session = Depends(get_session)):
    """Lista contratos activos que cobren agua/luz y estén Pendiente y No pagado en el mes actual."""
    anio, mes = get_mes_actual()
    contratos = crud_contratos.get_contratos_activos(session)
    resultado = []

    for contrato in contratos:
        if not contrato.cobra_agua and not contrato.cobra_luz:
            continue
        registro = crud_registros.get_registro(session, contrato.id_contratos, anio, mes)
        if not registro:
            continue
        if registro.pagado:
            continue
        estado = calcular_estado_servicios(contrato, registro)
        if estado != "Pendiente":
            continue

        from app.model.models import Departamento, Inquilino
        dep = session.get(Departamento, contrato.id_departamentos)
        inq = session.get(Inquilino, contrato.id_inquilinos)
        resultado.append({
            "contrato": contrato,
            "registro": registro,
            "departamento": dep,
            "inquilino": inq,
        })
    return resultado


@router.post("/guardar")
def guardar_servicios(
    id_registro: int,
    agua: Optional[int] = None,
    luz: Optional[int] = None,
    session: Session = Depends(get_session)
):
    """Guarda agua/luz en el registro mensual y recalcula el total."""
    registro = session.get(RegistroMensual, id_registro)
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    contrato = session.get(Contrato, registro.id_contratos)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")

    from app.crud.registros import RegistroMensualUpdate
    if agua is not None:
        registro.agua = agua
    if luz is not None:
        registro.luz = luz

    alq_efectivo = registro.alquiler_override if registro.alquiler_override is not None else registro.alquiler_calculado
    exp_efectiva = registro.expensa_override if registro.expensa_override is not None else registro.expensa_calculada
    total_calculado = calcular_total(alq_efectivo, exp_efectiva, registro.agua, registro.luz)

    update = RegistroMensualUpdate(
        agua=registro.agua,
        luz=registro.luz,
        total=total_calculado
    )
    return crud_registros.update_registro(session, id_registro, update)
