from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List, Optional
from datetime import date
from app.db import get_session
from app.model.models import Contrato, RegistroMensual
from app.crud import contratos as crud_contratos
from app.crud import registros as crud_registros
from app.service.mes_service import (
    get_mes_actual,
    get_or_create_registro,
    calcular_estado_servicios,
    aplicar_aumento_si_corresponde,
    calcular_proximo_aumento,
    calcular_alquiler,
    calcular_expensa,
    calcular_total,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/mes-actual")
def get_dashboard(session: Session = Depends(get_session)):
    anio, mes = get_mes_actual()
    contratos = crud_contratos.get_contratos_activos(session)
    hoy = date.today()
    resultado = []

    for contrato in contratos:
        # Aplicar aumento si corresponde antes de crear el registro
        aplicar_aumento_si_corresponde(session, contrato, anio, mes)
        # Refrescar contrato con posibles cambios
        session.refresh(contrato)

        registro = get_or_create_registro(session, contrato, anio, mes)

        alq_efectivo = registro.alquiler_override if registro.alquiler_override is not None else registro.alquiler_calculado
        exp_efectiva = registro.expensa_override if registro.expensa_override is not None else registro.expensa_calculada

        total_calculado = calcular_total(
            alq_efectivo,
            exp_efectiva,
            registro.agua,
            registro.luz
        )

        # Actualizar total en DB
        if registro.total != total_calculado:
            from app.crud.registros import RegistroMensualUpdate
            crud_registros.update_registro(session, registro.id_registros_mensuales, RegistroMensualUpdate(total=total_calculado))
            registro.total = total_calculado

        estado_servicios = calcular_estado_servicios(contrato, registro)

        vencido = contrato.fecha_fin < hoy

        from app.model.models import Departamento, Inquilino
        dep = session.get(Departamento, contrato.id_departamentos)
        inq = session.get(Inquilino, contrato.id_inquilinos)

        resultado.append({
            "contrato": contrato,
            "registro": registro,
            "departamento": dep,
            "inquilino": inq,
            "estado_servicios": estado_servicios,
            "vencido": vencido,
            "anio": anio,
            "mes": mes,
            "total": total_calculado,
        })

    return resultado


@router.post("/registros/{id_registro}/pagado")
def marcar_pagado(id_registro: int, session: Session = Depends(get_session)):
    registro = session.get(RegistroMensual, id_registro)
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    contrato = session.get(Contrato, registro.id_contratos)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    estado_servicios = calcular_estado_servicios(contrato, registro)
    if estado_servicios != "OK":
        raise HTTPException(status_code=400, detail="No se puede marcar pagado: servicios pendientes")
    from app.crud.registros import RegistroMensualUpdate
    return crud_registros.update_registro(session, id_registro, RegistroMensualUpdate(pagado=True))


@router.post("/registros/{id_registro}/desmarcar-pagado")
def desmarcar_pagado(id_registro: int, session: Session = Depends(get_session)):
    registro = session.get(RegistroMensual, id_registro)
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    from app.crud.registros import RegistroMensualUpdate
    return crud_registros.update_registro(session, id_registro, RegistroMensualUpdate(pagado=False))


@router.post("/registros/{id_registro}/override")
def override_registro(
    id_registro: int,
    alquiler_override: Optional[int] = None,
    expensa_override: Optional[int] = None,
    nota_override: Optional[str] = None,
    session: Session = Depends(get_session)
):
    registro = session.get(RegistroMensual, id_registro)
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    contrato = session.get(Contrato, registro.id_contratos)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")

    from app.crud.registros import RegistroMensualUpdate
    update_data = RegistroMensualUpdate(
        alquiler_override=alquiler_override,
        expensa_override=expensa_override,
        nota_override=nota_override,
    )
    registro = crud_registros.update_registro(session, id_registro, update_data)

    alq_efectivo = registro.alquiler_override if registro.alquiler_override is not None else registro.alquiler_calculado
    exp_efectiva = registro.expensa_override if registro.expensa_override is not None else registro.expensa_calculada
    total_calculado = calcular_total(alq_efectivo, exp_efectiva, registro.agua, registro.luz)
    return crud_registros.update_registro(session, id_registro, RegistroMensualUpdate(total=total_calculado))
