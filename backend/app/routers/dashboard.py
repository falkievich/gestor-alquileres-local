from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List, Optional
from datetime import date
from app.db import get_session
from app.model.models import Contrato, RegistroMensual
from app.crud import contratos as crud_contratos
from app.crud import registros as crud_registros
from app.model.models import ContratoRead, DepartamentoRead, InquilinoRead, RegistroMensualRead
from app.service.mes_service import (
    get_mes_actual,
    preparar_registro_mes,
    calcular_estado_servicios,
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
        # No mostrar contratos cuya fecha de inicio aún no llegó
        if contrato.fecha_inicio > hoy:
            continue

        # Aplica el aumento si corresponde y crea (o reutiliza) el registro
        # mensual con los valores congelados (misma lógica que Servicios).
        registro, porcentaje_aplicado = preparar_registro_mes(
            session, contrato, anio, mes)

        alq_efectivo = registro.alquiler_override if registro.alquiler_override is not None else registro.alquiler_calculado
        exp_efectiva = registro.expensa_override if registro.expensa_override is not None else registro.expensa_calculada

        total_calculado = calcular_total(
            alq_efectivo,
            exp_efectiva,
            registro.agua,
            registro.luz,
            registro.impuesto
        )

        # Actualizar total en DB
        if registro.total != total_calculado:
            from app.crud.registros import RegistroMensualUpdate
            crud_registros.update_registro(
                session, registro.id_registros_mensuales, RegistroMensualUpdate(total=total_calculado))
            registro.total = total_calculado

        estado_servicios = calcular_estado_servicios(contrato, registro)

        vencido = contrato.fecha_fin < hoy

        from app.model.models import Departamento, Inquilino
        dep = session.get(Departamento, contrato.id_departamentos)
        inq = session.get(Inquilino, contrato.id_inquilinos)

        resultado.append({
            "contrato": ContratoRead.model_validate(contrato),
            "registro": RegistroMensualRead.model_validate(registro),
            "departamento": DepartamentoRead.model_validate(dep) if dep else None,
            "inquilino": InquilinoRead.model_validate(inq) if inq else None,
            "estado_servicios": estado_servicios,
            "vencido": vencido,
            "anio": anio,
            "mes": mes,
            "total": total_calculado,
        })

    return resultado


@router.get("/historial-pagos")
def get_historial_pagos(
    anio: Optional[int] = None,
    mes: Optional[int] = None,
    id_inquilinos: Optional[int] = None,
    session: Session = Depends(get_session)
):
    from sqlmodel import select
    from app.model.models import Departamento, Inquilino, Contrato

    query = select(RegistroMensual).where(RegistroMensual.pagado == True)
    if anio:
        query = query.where(RegistroMensual.anio == anio)
    if mes:
        query = query.where(RegistroMensual.mes == mes)

    registros = session.exec(query).all()

    resultado = []
    for reg in registros:
        contrato = session.get(Contrato, reg.id_contratos)
        if not contrato:
            continue
        if id_inquilinos and contrato.id_inquilinos != id_inquilinos:
            continue
        dep = session.get(Departamento, contrato.id_departamentos)
        inq = session.get(Inquilino, contrato.id_inquilinos)
        resultado.append({
            "registro": RegistroMensualRead.model_validate(reg),
            "contrato": ContratoRead.model_validate(contrato),
            "departamento": DepartamentoRead.model_validate(dep) if dep else None,
            "inquilino": InquilinoRead.model_validate(inq) if inq else None,
            "anio": reg.anio,
            "mes": reg.mes,
            "total": reg.total,
        })

    # Orden: más nuevo al más viejo
    resultado.sort(key=lambda x: (x["anio"], x["mes"]), reverse=True)
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
        raise HTTPException(
            status_code=400, detail="No se puede marcar pagado: servicios pendientes")
    from app.crud.registros import RegistroMensualUpdate
    actualizado = crud_registros.update_registro(
        session, id_registro, RegistroMensualUpdate(pagado=True))

    # Consolidar el aumento PENDIENTE de este contrato/período, si existe:
    # a partir de aquí el aumento queda inmutable como histórico.
    from app.crud import historial_aumentos as crud_historial
    crud_historial.consolidar_pendiente(
        session, registro.id_contratos, registro.anio, registro.mes)

    return actualizado


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
    registro = crud_registros.update_registro(
        session, id_registro, update_data)

    alq_efectivo = registro.alquiler_override if registro.alquiler_override is not None else registro.alquiler_calculado
    exp_efectiva = registro.expensa_override if registro.expensa_override is not None else registro.expensa_calculada
    total_calculado = calcular_total(
        alq_efectivo, exp_efectiva, registro.agua, registro.luz, registro.impuesto)
    return crud_registros.update_registro(session, id_registro, RegistroMensualUpdate(total=total_calculado))
