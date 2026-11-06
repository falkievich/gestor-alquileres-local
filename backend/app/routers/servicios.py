from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.db import get_session
from app.crud import contratos as crud_contratos
from app.crud import registros as crud_registros
from app.service.mes_service import (
    get_mes_actual,
    calcular_estado_servicios,
    total_efectivo_registro,
    preparar_registro_mes,
    contrato_vigente_para_mes,
    contrato_operativo_hoy,
    registros_sin_cobrar_fuera_del_ciclo,
)
from app.model.models import Contrato, ContratoRead, RegistroMensual
from typing import Optional

router = APIRouter(prefix="/servicios", tags=["servicios"])


@router.get("/pendientes")
def listar_pendientes(session: Session = Depends(get_session)):
    """
    Lista los contratos que cobren agua/luz, del mes actual y de la deuda fuera
    del ciclo del mes (meses atrasados y mes en curso de contratos finalizados):
    incluye los pendientes de cargar y los ya cargados, con un campo "estado"
    para diferenciarlos ("Pendiente" / "OK") y "atrasado" para marcar los de
    meses anteriores. Una fila sale del listado recién cuando se cobra el mes.
    """
    anio, mes = get_mes_actual()
    contratos = crud_contratos.get_contratos_activos(session)
    resultado = []

    for contrato in contratos:
        if not contrato.cobra_agua and not contrato.cobra_luz:
            continue
        if not contrato_operativo_hoy(contrato):
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

    # Deuda fuera del ciclo del mes. Igual que el mes actual, sigue listada
    # aunque ya tenga Agua/Luz cargados (para poder corregir un monto mal
    # cargado) y solo sale al cobrarse el mes.
    from app.model.models import Departamento, Inquilino
    for reg_atrasado, contrato in registros_sin_cobrar_fuera_del_ciclo(session):
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
            "atrasado": (reg_atrasado.anio, reg_atrasado.mes) < (anio, mes),
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
    # No se permiten servicios sobre meses fuera de la vigencia.
    if not contrato_vigente_para_mes(contrato, registro.anio, registro.mes):
        raise HTTPException(
            status_code=409,
            detail="No se pueden cargar servicios fuera de la vigencia del "
                   f"contrato ({contrato.fecha_inicio.isoformat()} a "
                   f"{contrato.fecha_fin.isoformat()})")

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
