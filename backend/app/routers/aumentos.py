from fastapi import APIRouter, Depends
from sqlmodel import Session
from typing import Optional
from app.db import get_session
from app.crud import contratos as crud_contratos
from app.crud import historial_aumentos as crud_historial
from app.model.models import (
    Contrato, ContratoRead, Departamento, Inquilino, HistorialAumentoRead,
)
from app.service.mes_service import calcular_proximo_aumento, get_mes_actual
from datetime import date

router = APIRouter(prefix="/aumentos", tags=["aumentos"])


@router.get("/")
def vista_aumentos(session: Session = Depends(get_session)):
    """Lista próximos aumentos por contrato activo."""
    contratos = crud_contratos.get_contratos_activos(session)
    hoy = date.today()
    resultado = []

    for contrato in contratos:
        dep = session.get(Departamento, contrato.id_departamentos)
        inq = session.get(Inquilino, contrato.id_inquilinos)
        proximo = calcular_proximo_aumento(contrato)
        vencido = contrato.fecha_fin < hoy

        meses_hasta_fin = (contrato.fecha_fin.year - hoy.year) * \
            12 + (contrato.fecha_fin.month - hoy.month)
        alerta = None
        if vencido:
            alerta = "Vencido"
        elif meses_hasta_fin <= 3:
            alerta = "Por vencer"

        resultado.append({
            "contrato": ContratoRead.model_validate(contrato),
            "departamento": dep,
            "inquilino": inq,
            "proximo_aumento": proximo,
            "alerta": alerta,
        })

    return resultado


@router.get("/historial")
def historial_aumentos(
    id_inquilinos: Optional[int] = None,
    anio: Optional[int] = None,
    mes: Optional[int] = None,
    session: Session = Depends(get_session),
):
    """
    Historial de aumentos leído directamente de la tabla `historial_aumentos`
    (fuente de verdad). Cada fila es un evento de aumento real con su estado
    (PENDIENTE / CONSOLIDADO), montos propuestos/aplicados y datos ICL.
    """
    historiales = crud_historial.listar(session)
    hoy = date.today()
    resultado = []

    for h in historiales:
        if anio and h.anio != anio:
            continue
        if mes and h.mes != mes:
            continue
        contrato = session.get(Contrato, h.id_contratos)
        if not contrato:
            continue
        if id_inquilinos and contrato.id_inquilinos != id_inquilinos:
            continue
        dep = session.get(Departamento, contrato.id_departamentos)
        inq = session.get(Inquilino, contrato.id_inquilinos)

        resultado.append({
            "historial": HistorialAumentoRead.model_validate(h),
            "contrato": ContratoRead.model_validate(contrato),
            "departamento": dep,
            "inquilino": inq,
            "diferencia_aplicada": h.alquiler_aplicado - h.alquiler_anterior,
            "diferencia_expensa_aplicada": (
                h.expensa_aplicada - h.expensa_anterior
                if h.expensa_aplicada is not None and h.expensa_anterior is not None
                else None
            ),
            "hoy": hoy.isoformat(),
        })

    return resultado
