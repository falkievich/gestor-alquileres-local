from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
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
    total_efectivo_registro,
    contrato_vigente_para_mes,
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

        # No preparar/mostrar meses posteriores al vencimiento del contrato
        # (el mes de fecha_fin sigue siendo válido).
        if not contrato_vigente_para_mes(contrato, anio, mes):
            continue

        # Aplica el aumento si corresponde y crea (o reutiliza) el registro
        # mensual con los valores congelados (misma lógica que Servicios).
        registro, porcentaje_aplicado = preparar_registro_mes(
            session, contrato, anio, mes)

        total_calculado = total_efectivo_registro(registro)

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
            "atrasado": False,
        })

    # Cobros atrasados: registros de meses anteriores sin cobrar. Se listan
    # con sus montos históricos congelados (override ?? calculado), sin
    # preparar ni crear nada. Incluye contratos finalizados mientras el
    # registro no esté pagado y su mes esté dentro de la vigencia.
    from sqlalchemy import or_
    registros_atrasados = session.exec(
        select(RegistroMensual).where(
            RegistroMensual.pagado == False,  # noqa: E712
            or_(
                RegistroMensual.anio < anio,
                (RegistroMensual.anio == anio) & (RegistroMensual.mes < mes),
            ),
        ).order_by(
            RegistroMensual.anio.asc(), RegistroMensual.mes.asc()
        )
    ).all()

    for reg_atrasado in registros_atrasados:
        contrato = session.get(Contrato, reg_atrasado.id_contratos)
        if not contrato:
            continue
        # Solo contratos activos: los pendientes de contratos cerrados
        # permanecen en DB pero no reaparecen en las vistas operativas.
        if contrato.estado != 'activo':
            continue
        from app.model.models import Departamento, Inquilino
        dep = session.get(Departamento, contrato.id_departamentos)
        inq = session.get(Inquilino, contrato.id_inquilinos)

        total_efectivo = total_efectivo_registro(reg_atrasado)

        estado_servicios = calcular_estado_servicios(contrato, reg_atrasado)

        resultado.append({
            "contrato": ContratoRead.model_validate(contrato),
            "registro": RegistroMensualRead.model_validate(reg_atrasado),
            "departamento": DepartamentoRead.model_validate(dep) if dep else None,
            "inquilino": InquilinoRead.model_validate(inq) if inq else None,
            "estado_servicios": estado_servicios,
            "vencido": contrato.fecha_fin < hoy,
            "anio": reg_atrasado.anio,
            "mes": reg_atrasado.mes,
            "total": total_efectivo,
            "atrasado": True,
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
    # Un mes posterior al vencimiento del contrato no se puede cobrar.
    if not contrato_vigente_para_mes(contrato, registro.anio, registro.mes):
        raise HTTPException(
            status_code=409,
            detail="No se puede cobrar un mes posterior a la fecha de "
                   f"vencimiento ({contrato.fecha_fin.isoformat()}) del contrato")
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
    # No se permiten ajustes sobre meses posteriores al vencimiento.
    if not contrato_vigente_para_mes(contrato, registro.anio, registro.mes):
        raise HTTPException(
            status_code=409,
            detail="No se pueden ajustar meses posteriores a la fecha de "
                   f"vencimiento ({contrato.fecha_fin.isoformat()}) del contrato")

    from app.crud.registros import RegistroMensualUpdate
    update_data = RegistroMensualUpdate(
        alquiler_override=alquiler_override,
        expensa_override=expensa_override,
        nota_override=nota_override,
    )
    registro = crud_registros.update_registro(
        session, id_registro, update_data)

    total_calculado = total_efectivo_registro(registro)
    return crud_registros.update_registro(session, id_registro, RegistroMensualUpdate(total=total_calculado))
