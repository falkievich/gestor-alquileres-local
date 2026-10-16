from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db import get_session
from app.crud import contratos as crud_contratos
from app.crud import registros as crud_registros
from app.service.mes_service import (
    get_mes_actual,
    calcular_estado_servicios,
    total_efectivo_registro,
    preparar_registro_mes,
    contrato_vigente_para_mes,
)
from app.model.models import Contrato, ContratoRead, RegistroMensual
from typing import Optional

router = APIRouter(prefix="/servicios", tags=["servicios"])


@router.get("/pendientes")
def listar_pendientes(session: Session = Depends(get_session)):
    """
    Lista contratos activos que cobren agua/luz, del mes actual y de los meses
    atrasados sin cobrar: incluye los pendientes de cargar y los ya cargados,
    con un campo "estado" para diferenciarlos ("Pendiente" / "OK") y
    "atrasado" para marcar los de meses anteriores. Una fila sale del listado
    recién cuando se cobra el mes.
    """
    anio, mes = get_mes_actual()
    contratos = crud_contratos.get_contratos_activos(session)
    resultado = []

    for contrato in contratos:
        if not contrato.cobra_agua and not contrato.cobra_luz:
            continue
        # No preparar/mostrar meses posteriores al vencimiento del contrato
        # (el mes de fecha_fin sigue siendo válido).
        if not contrato_vigente_para_mes(contrato, anio, mes):
            continue
        # Genera el registro del mes si aún no existe (igual que el Dashboard),
        # así los servicios aparecen apenas se crea el contrato.
        registro, _ = preparar_registro_mes(session, contrato, anio, mes)
        if registro.pagado:
            continue
        estado = calcular_estado_servicios(contrato, registro)

        from app.model.models import Departamento, Inquilino
        dep = session.get(Departamento, contrato.id_departamentos)
        inq = session.get(Inquilino, contrato.id_inquilinos)
        resultado.append({
            "contrato": ContratoRead.model_validate(contrato),
            "registro": registro,
            "departamento": dep,
            "inquilino": inq,
            "estado": estado,
            "atrasado": False,
        })

    # Servicios atrasados: registros de meses anteriores sin cobrar. Igual que
    # el mes actual, siguen listados aunque ya tengan Agua/Luz cargados (para
    # poder corregir un monto mal cargado) y solo salen al cobrarse el mes.
    from sqlalchemy import or_
    from app.model.models import Departamento, Inquilino
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
        if not contrato.cobra_agua and not contrato.cobra_luz:
            continue
        estado = calcular_estado_servicios(contrato, reg_atrasado)
        dep = session.get(Departamento, contrato.id_departamentos)
        inq = session.get(Inquilino, contrato.id_inquilinos)
        resultado.append({
            "contrato": ContratoRead.model_validate(contrato),
            "registro": reg_atrasado,
            "departamento": dep,
            "inquilino": inq,
            "estado": estado,
            "atrasado": True,
        })

    return resultado


@router.post("/guardar")
def guardar_servicios(
    id_registro: int,
    agua: Optional[int] = None,
    luz: Optional[int] = None,
    session: Session = Depends(get_session)
):
    """Guarda (o edita) agua/luz en el registro mensual y recalcula el total."""
    registro = session.get(RegistroMensual, id_registro)
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    if registro.pagado:
        raise HTTPException(
            status_code=400,
            detail="No se puede editar el servicio de un mes ya cobrado.")
    contrato = session.get(Contrato, registro.id_contratos)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    # No se permiten servicios sobre meses posteriores al vencimiento.
    if not contrato_vigente_para_mes(contrato, registro.anio, registro.mes):
        raise HTTPException(
            status_code=409,
            detail="No se pueden cargar servicios posteriores a la fecha de "
                   f"vencimiento ({contrato.fecha_fin.isoformat()}) del contrato")

    from app.crud.registros import RegistroMensualUpdate
    if agua is not None:
        registro.agua = agua
    if luz is not None:
        registro.luz = luz

    total_calculado = total_efectivo_registro(registro)

    update = RegistroMensualUpdate(
        agua=registro.agua,
        luz=registro.luz,
        total=total_calculado
    )
    return crud_registros.update_registro(session, id_registro, update)
