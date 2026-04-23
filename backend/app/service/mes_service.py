from datetime import date
from typing import Optional, Dict, Any
from sqlmodel import Session
from app.model.models import Contrato, RegistroMensual
from app.crud import registros as crud_registros


def get_mes_actual():
    hoy = date.today()
    return hoy.year, hoy.month


def calcular_alquiler(contrato: Contrato, anio: int, mes: int) -> int:
    """Calcula el alquiler base del contrato aplicando aumentos si corresponde."""
    return contrato.alquiler_base_actual


def calcular_expensa(contrato: Contrato) -> Optional[int]:
    if contrato.cobra_expensa:
        return contrato.expensa_base_actual
    return None


def calcular_total(
    alquiler: int,
    expensa: Optional[int],
    agua: Optional[int],
    luz: Optional[int]
) -> int:
    total = alquiler
    if expensa is not None:
        total += expensa
    if agua is not None:
        total += agua
    if luz is not None:
        total += luz
    return total


def get_or_create_registro(session: Session, contrato: Contrato, anio: int, mes: int) -> RegistroMensual:
    registro = crud_registros.get_registro(session, contrato.id_contratos, anio, mes)
    if not registro:
        alquiler = calcular_alquiler(contrato, anio, mes)
        expensa = calcular_expensa(contrato)
        total = calcular_total(alquiler, expensa, None, None)
        from app.model.models import RegistroMensualCreate
        data = RegistroMensualCreate(
            id_contratos=contrato.id_contratos,
            anio=anio,
            mes=mes,
            alquiler_calculado=alquiler,
            expensa_calculada=expensa,
            total=total
        )
        registro = crud_registros.create_registro(session, data)
    return registro


def calcular_estado_servicios(contrato: Contrato, registro: RegistroMensual) -> str:
    """Calcula si los servicios están OK o Pendiente."""
    if contrato.cobra_agua and registro.agua is None:
        return "Pendiente"
    if contrato.cobra_luz and registro.luz is None:
        return "Pendiente"
    return "OK"


def corresponde_aumento(contrato: Contrato, anio: int, mes: int) -> bool:
    """Determina si le corresponde un aumento en el mes/año dado."""
    if contrato.porcentaje_aumento == 0:
        return False
    if contrato.periodicidad_aumento_meses == 0:
        return False

    # Si el usuario indicó fecha_ultimo_aumento (contrato en curso), usar esa como base
    if contrato.fecha_ultimo_aumento is not None:
        base_anio = contrato.fecha_ultimo_aumento.year
        base_mes = contrato.fecha_ultimo_aumento.month
        meses_desde_base = (anio - base_anio) * 12 + (mes - base_mes)
        return meses_desde_base >= contrato.periodicidad_aumento_meses

    # Si el sistema ya aplicó algún aumento, usar ese registro
    if contrato.ultimo_aumento_anio is not None and contrato.ultimo_aumento_mes is not None:
        meses_desde_ultimo = (anio - contrato.ultimo_aumento_anio) * 12 + (mes - contrato.ultimo_aumento_mes)
        return meses_desde_ultimo >= contrato.periodicidad_aumento_meses

    # Sin historial: usar fecha_inicio como base (comportamiento original).
    # Cubre tanto contratos nuevos como contratos cargados pocos días después de su inicio.
    # Si el contrato es realmente antiguo, el usuario puede indicar fecha_ultimo_aumento para corregir la base.
    inicio = contrato.fecha_inicio
    meses_desde_inicio = (anio - inicio.year) * 12 + (mes - inicio.month)
    return meses_desde_inicio > 0 and meses_desde_inicio % contrato.periodicidad_aumento_meses == 0


def aplicar_aumento_si_corresponde(session: Session, contrato: Contrato, anio: int, mes: int) -> bool:
    """Aplica el aumento al contrato si corresponde. Retorna True si se aplicó."""
    if not corresponde_aumento(contrato, anio, mes):
        return False

    factor = 1 + (contrato.porcentaje_aumento / 100)
    contrato.alquiler_base_actual = round(contrato.alquiler_base_actual * factor)
    if contrato.cobra_expensa and contrato.expensa_base_actual is not None:
        contrato.expensa_base_actual = round(contrato.expensa_base_actual * factor)
    contrato.ultimo_aumento_anio = anio
    contrato.ultimo_aumento_mes = mes
    session.add(contrato)
    session.commit()
    session.refresh(contrato)
    return True


def calcular_proximo_aumento(contrato: Contrato) -> Dict[str, Any]:
    """Calcula el próximo aumento para un contrato activo.

    Si el contrato es antiguo y no tiene ni fecha_ultimo_aumento ni historial del sistema,
    devuelve requires_fecha_ultimo=True para que el frontend pida la fecha al usuario.
    """
    if contrato.porcentaje_aumento == 0 or contrato.periodicidad_aumento_meses == 0:
        return {
            "proximo_anio": None, "proximo_mes": None,
            "alquiler_actual": contrato.alquiler_base_actual, "alquiler_nuevo": None,
            "requires_fecha_ultimo": False,
        }

    # Determinar la base para calcular el próximo aumento (mismo orden que corresponde_aumento)
    if contrato.fecha_ultimo_aumento is not None:
        base_anio = contrato.fecha_ultimo_aumento.year
        base_mes = contrato.fecha_ultimo_aumento.month
    elif contrato.ultimo_aumento_anio is not None and contrato.ultimo_aumento_mes is not None:
        base_anio = contrato.ultimo_aumento_anio
        base_mes = contrato.ultimo_aumento_mes
    else:
        # Sin historial: usar fecha_inicio como base (igual que corresponde_aumento)
        base_anio = contrato.fecha_inicio.year
        base_mes = contrato.fecha_inicio.month

    total_meses = base_mes + contrato.periodicidad_aumento_meses
    proximo_anio = base_anio + (total_meses - 1) // 12
    proximo_mes = ((total_meses - 1) % 12) + 1

    factor = 1 + (contrato.porcentaje_aumento / 100)
    alquiler_nuevo = round(contrato.alquiler_base_actual * factor)
    expensa_nueva = round(contrato.expensa_base_actual * factor) if contrato.cobra_expensa and contrato.expensa_base_actual else None

    return {
        "proximo_anio": proximo_anio,
        "proximo_mes": proximo_mes,
        "alquiler_actual": contrato.alquiler_base_actual,
        "alquiler_nuevo": alquiler_nuevo,
        "expensa_actual": contrato.expensa_base_actual,
        "expensa_nueva": expensa_nueva,
        "porcentaje": contrato.porcentaje_aumento,
        "requires_fecha_ultimo": False,
    }
