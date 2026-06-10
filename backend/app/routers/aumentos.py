from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.db import get_session
from app.crud import contratos as crud_contratos
from app.crud import registros as crud_registros
from app.model.models import ContratoRead, Departamento, Inquilino, RegistroMensual, Contrato
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
def historial_aumentos(session: Session = Depends(get_session)):
    """
    Lista todos los registros donde se aplicó un aumento real
    (porcentaje_aumento_usado IS NOT NULL).

    Para cada entrada devuelve:
      - El registro mensual (con porcentaje_aumento_usado).
      - Los datos del contrato, departamento e inquilino.
      - alquiler_anterior: valor del registro del mes inmediatamente anterior
        del mismo contrato (None si no existe).
      - alquiler_nuevo: alquiler_calculado del registro con el aumento.
    """
    query = select(RegistroMensual).where(
        RegistroMensual.porcentaje_aumento_usado.is_not(None)  # type: ignore
    )
    registros = session.exec(query).all()

    resultado = []
    for reg in registros:
        contrato = session.get(Contrato, reg.id_contratos)
        if not contrato:
            continue
        dep = session.get(Departamento, contrato.id_departamentos)
        inq = session.get(Inquilino, contrato.id_inquilinos)

        # Buscar el registro del mes inmediatamente anterior del mismo contrato
        prev_mes = reg.mes - 1
        prev_anio = reg.anio
        if prev_mes == 0:
            prev_mes = 12
            prev_anio -= 1
        prev_reg = crud_registros.get_registro(
            session, reg.id_contratos, prev_anio, prev_mes)

        alquiler_anterior = None
        if prev_reg:
            alquiler_anterior = (
                prev_reg.alquiler_override
                if prev_reg.alquiler_override is not None
                else prev_reg.alquiler_calculado
            )

        alquiler_nuevo = (
            reg.alquiler_override
            if reg.alquiler_override is not None
            else reg.alquiler_calculado
        )

        resultado.append({
            "registro": reg,
            "contrato": ContratoRead.model_validate(contrato),
            "departamento": dep,
            "inquilino": inq,
            "alquiler_anterior": alquiler_anterior,
            "alquiler_nuevo": alquiler_nuevo,
        })

    # Más reciente primero
    resultado.sort(key=lambda x: (
        x["registro"].anio, x["registro"].mes), reverse=True)
    return resultado
