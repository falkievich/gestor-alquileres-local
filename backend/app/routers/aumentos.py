from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.db import get_session
from app.crud import contratos as crud_contratos
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
        from app.model.models import Departamento, Inquilino
        dep = session.get(Departamento, contrato.id_departamentos)
        inq = session.get(Inquilino, contrato.id_inquilinos)
        proximo = calcular_proximo_aumento(contrato)
        vencido = contrato.fecha_fin < hoy

        # Alerta vencimiento
        meses_hasta_fin = (contrato.fecha_fin.year - hoy.year) * 12 + (contrato.fecha_fin.month - hoy.month)
        alerta = None
        if vencido:
            alerta = "Vencido"
        elif meses_hasta_fin <= 3:
            alerta = "Por vencer"

        resultado.append({
            "contrato": contrato,
            "departamento": dep,
            "inquilino": inq,
            "proximo_aumento": proximo,
            "alerta": alerta,
        })

    return resultado
