from datetime import date
from calendar import monthrange
from typing import Optional, Dict, Any, List, Tuple
from sqlmodel import Session
from app.model.models import Contrato, RegistroMensual
from app.crud import registros as crud_registros

import httpx

BCRA_ICL_URL = "https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/40"


def get_mes_actual():
    hoy = date.today()
    return hoy.year, hoy.month


def _ultimo_dia_mes(anio: int, mes: int) -> date:
    return date(anio, mes, monthrange(anio, mes)[1])


def _fetch_icl_bcra(fecha_desde: date, fecha_hasta: date) -> Tuple[Optional[List[Dict]], Optional[str]]:
    """
    Consulta el ICL (variable 40) a la API del BCRA.
    Retorna (detalle_list, error_msg).
    """
    try:
        params = {
            "Desde": fecha_desde.strftime("%Y-%m-%d"),
            "Hasta": fecha_hasta.strftime("%Y-%m-%d"),
        }
        response = httpx.get(
            BCRA_ICL_URL,
            params=params,
            timeout=10,
            verify=False,
        )
        if response.status_code != 200:
            return None, f"BCRA API devolvió status {response.status_code}"
        data = response.json()
        results = data.get("results", [])
        if not results:
            return [], None
        detalle = results[0].get("detalle", [])
        return detalle, None
    except Exception as exc:
        return None, str(exc)


def _valor_icl_para_fecha(detalle: List[Dict], target_date: date) -> Optional[float]:
    """Obtiene el valor ICL para una fecha exacta del detalle."""
    target_str = target_date.strftime("%Y-%m-%d")
    for item in detalle:
        if (item.get("fecha") or "")[:10] == target_str:
            return float(item["valor"])
    return None


def _ultima_fecha_disponible_icl(detalle: List[Dict]) -> Optional[date]:
    """Devuelve la última fecha publicada en el detalle del BCRA."""
    if not detalle:
        return None
    try:
        fechas = [date.fromisoformat(item["fecha"][:10])
                  for item in detalle if item.get("fecha")]
        return max(fechas) if fechas else None
    except Exception:
        return None


def _calcular_icl_aumento(
    contrato: Contrato,
    base_anio: int,
    base_mes: int,
    proximo_anio: int,
    proximo_mes: int,
) -> Dict[str, Any]:
    """
    Calcula el factor de aumento ICL para el período que finaliza justo antes
    de que entre en vigencia el nuevo valor.

    Regla de negocio:
    ─────────────────────────────────────────────────────────────────────
    El período a consultar en la API del BCRA es exactamente el tramo que
    transcurre desde la base del último aumento hasta el día anterior al
    inicio del nuevo período de vigencia:

      · desde  = 1º día del mes base  (ej. 01/03/2026)
      · hasta  = último día del mes anterior al nuevo período (ej. 30/06/2026)

    El ICL inicial es el valor publicado el día 'desde'.
    El ICL final   es el valor publicado el día 'hasta'.

    Fórmula:
      Coeficiente  = ICL_final / ICL_inicial
      Nuevo alquiler = Alquiler_actual × Coeficiente

    Si la API todavía no publicó el valor para 'hasta', se devuelve un
    estado pendiente indicando la última fecha disponible y los días
    aproximados que faltan para completar el período.
    ─────────────────────────────────────────────────────────────────────
    """
    # El período a consultar termina el último día del mes anterior al inicio de vigencia
    if proximo_mes == 1:
        fin_periodo_anio = proximo_anio - 1
        fin_periodo_mes = 12
    else:
        fin_periodo_anio = proximo_anio
        fin_periodo_mes = proximo_mes - 1

    fecha_desde = date(base_anio, base_mes, 1)
    fecha_hasta = _ultimo_dia_mes(fin_periodo_anio, fin_periodo_mes)

    hoy = date.today()

    # Consultar el período objetivo completo. El BCRA puede publicar
    # algunos días por adelantado respecto a la fecha del sistema.
    detalle, error = _fetch_icl_bcra(fecha_desde, fecha_hasta)

    if error or detalle is None:
        return {
            "icl_pendiente": True,
            "icl_error": error or "Sin datos del BCRA",
            "ultima_fecha_disponible_bcra": None,
            "dias_faltantes": None,
        }

    ultima_disponible = _ultima_fecha_disponible_icl(detalle)

    # Verificar si ya está disponible el valor para fecha_hasta
    if fecha_hasta > hoy or _valor_icl_para_fecha(detalle, fecha_hasta) is None:
        dias_faltantes = (fecha_hasta - (ultima_disponible or hoy)
                          ).days if ultima_disponible else None
        return {
            "icl_pendiente": True,
            "icl_error": None,
            "ultima_fecha_disponible_bcra": ultima_disponible.isoformat() if ultima_disponible else None,
            "dias_faltantes": max(dias_faltantes, 0) if dias_faltantes is not None else None,
        }

    # Valor inicial: si no tenemos exactamente fecha_desde, tomar el primer valor disponible
    icl_inicial = _valor_icl_para_fecha(detalle, fecha_desde)
    if icl_inicial is None:
        try:
            sorted_detalle = sorted(detalle, key=lambda x: x.get("fecha", ""))
            icl_inicial = float(
                sorted_detalle[0]["valor"]) if sorted_detalle else None
        except Exception:
            icl_inicial = None

    icl_final = _valor_icl_para_fecha(detalle, fecha_hasta)

    if icl_inicial is None or icl_final is None or icl_inicial == 0:
        return {
            "icl_pendiente": True,
            "icl_error": "No se encontraron valores ICL para las fechas requeridas",
            "ultima_fecha_disponible_bcra": ultima_disponible.isoformat() if ultima_disponible else None,
            "dias_faltantes": None,
        }

    coeficiente = icl_final / icl_inicial
    porcentaje = round((coeficiente - 1) * 100, 2)
    alquiler_nuevo = round(contrato.alquiler_base_actual * coeficiente)
    expensa_nueva = (
        round(contrato.expensa_base_actual * coeficiente)
        if contrato.cobra_expensa and contrato.expensa_base_actual
        else None
    )

    return {
        "icl_pendiente": False,
        "icl_error": None,
        "ultima_fecha_disponible_bcra": ultima_disponible.isoformat() if ultima_disponible else None,
        "dias_faltantes": 0,
        "icl_inicial": icl_inicial,
        "icl_final": icl_final,
        "icl_coeficiente": round(coeficiente, 6),
        "porcentaje": porcentaje,
        "alquiler_nuevo": alquiler_nuevo,
        "expensa_nueva": expensa_nueva,
        "expensa_actual": contrato.expensa_base_actual,
    }


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
    luz: Optional[int],
    impuesto: Optional[int] = None
) -> int:
    total = alquiler
    if expensa is not None:
        total += expensa
    if agua is not None:
        total += agua
    if luz is not None:
        total += luz
    if impuesto is not None:
        total += impuesto
    return total


def get_or_create_registro(session: Session, contrato: Contrato, anio: int, mes: int) -> RegistroMensual:
    registro = crud_registros.get_registro(
        session, contrato.id_contratos, anio, mes)
    if not registro:
        alquiler = calcular_alquiler(contrato, anio, mes)
        expensa = calcular_expensa(contrato)
        impuesto = contrato.impuesto_fijo
        total = calcular_total(alquiler, expensa, None, None, impuesto)
        from app.model.models import RegistroMensualCreate
        data = RegistroMensualCreate(
            id_contratos=contrato.id_contratos,
            anio=anio,
            mes=mes,
            alquiler_calculado=alquiler,
            expensa_calculada=expensa,
            impuesto=impuesto,
            total=total
        )
        registro = crud_registros.create_registro(session, data)
    return registro


def preparar_registro_mes(session: Session, contrato: Contrato, anio: int, mes: int) -> Tuple[RegistroMensual, Optional[float]]:
    """
    Prepara el registro mensual de un contrato para el mes dado:
    1. Aplica el aumento si corresponde (mutando el contrato).
    2. Crea (o reutiliza) el registro mensual con los valores congelados.

    Usada por el Dashboard y por la sección Servicios para que ambos
    generen el registro del mes de la misma forma.
    Retorna (registro, porcentaje_aplicado).
    """
    porcentaje_aplicado = aplicar_aumento_si_corresponde(
        session, contrato, anio, mes)
    session.refresh(contrato)
    registro = get_or_create_registro(session, contrato, anio, mes)

    # Guardar porcentaje_aumento_usado en el registro si se aplicó un aumento
    # y el registro todavía no tiene ese valor guardado.
    if porcentaje_aplicado is not None and registro.porcentaje_aumento_usado is None:
        from app.crud.registros import RegistroMensualUpdate
        crud_registros.update_registro(
            session, registro.id_registros_mensuales,
            RegistroMensualUpdate(porcentaje_aumento_usado=porcentaje_aplicado)
        )
        registro.porcentaje_aumento_usado = porcentaje_aplicado

    return registro, porcentaje_aplicado


def calcular_estado_servicios(contrato: Contrato, registro: RegistroMensual) -> str:
    """Calcula si los servicios están OK o Pendiente."""
    if contrato.cobra_agua and registro.agua is None:
        return "Pendiente"
    if contrato.cobra_luz and registro.luz is None:
        return "Pendiente"
    return "OK"


def corresponde_aumento(contrato: Contrato, anio: int, mes: int) -> bool:
    """Determina si le corresponde un aumento en el mes/año dado."""
    if contrato.periodicidad_aumento_meses == 0:
        return False
    # Para ICL: siempre verificar por periodicidad (no depende de porcentaje_aumento)
    tipo = getattr(contrato, 'tipo_aumento', 'MANUAL')
    if tipo == 'MANUAL' and contrato.porcentaje_aumento == 0:
        return False

    # Si el usuario indicó fecha_ultimo_aumento (contrato en curso), usar esa como base
    if contrato.fecha_ultimo_aumento is not None:
        base_anio = contrato.fecha_ultimo_aumento.year
        base_mes = contrato.fecha_ultimo_aumento.month
        meses_desde_base = (anio - base_anio) * 12 + (mes - base_mes)
        return meses_desde_base >= contrato.periodicidad_aumento_meses

    # Si el sistema ya aplicó algún aumento, usar ese registro
    if contrato.ultimo_aumento_anio is not None and contrato.ultimo_aumento_mes is not None:
        meses_desde_ultimo = (anio - contrato.ultimo_aumento_anio) * \
            12 + (mes - contrato.ultimo_aumento_mes)
        return meses_desde_ultimo >= contrato.periodicidad_aumento_meses

    # Sin historial: usar fecha_inicio como base (comportamiento original).
    # Cubre tanto contratos nuevos como contratos cargados pocos días después de su inicio.
    # Si el contrato es realmente antiguo, el usuario puede indicar fecha_ultimo_aumento para corregir la base.
    inicio = contrato.fecha_inicio
    meses_desde_inicio = (anio - inicio.year) * 12 + (mes - inicio.month)
    return meses_desde_inicio > 0 and meses_desde_inicio % contrato.periodicidad_aumento_meses == 0


def aplicar_aumento_si_corresponde(session: Session, contrato: Contrato, anio: int, mes: int) -> Optional[float]:
    """
    Aplica el aumento al contrato si corresponde.
    Retorna el porcentaje efectivamente aplicado, o None si no se aplicó ningún aumento.
    """
    if not corresponde_aumento(contrato, anio, mes):
        return None

    tipo = getattr(contrato, 'tipo_aumento', 'MANUAL')
    porcentaje_usado: Optional[float] = None

    if tipo == 'ICL':
        # Determinar base del período ICL
        if contrato.fecha_ultimo_aumento is not None:
            base_anio = contrato.fecha_ultimo_aumento.year
            base_mes = contrato.fecha_ultimo_aumento.month
        elif contrato.ultimo_aumento_anio is not None and contrato.ultimo_aumento_mes is not None:
            base_anio = contrato.ultimo_aumento_anio
            base_mes = contrato.ultimo_aumento_mes
        else:
            base_anio = contrato.fecha_inicio.year
            base_mes = contrato.fecha_inicio.month

        icl_info = _calcular_icl_aumento(
            contrato, base_anio, base_mes, anio, mes)
        if icl_info.get("icl_pendiente"):
            return None
        factor = icl_info["icl_coeficiente"]
        porcentaje_usado = icl_info["porcentaje"]
    else:
        # MANUAL
        factor = 1 + (contrato.porcentaje_aumento / 100)
        porcentaje_usado = contrato.porcentaje_aumento

    contrato.alquiler_base_actual = round(
        contrato.alquiler_base_actual * factor)
    if contrato.cobra_expensa and contrato.expensa_base_actual is not None:
        contrato.expensa_base_actual = round(
            contrato.expensa_base_actual * factor)
    contrato.ultimo_aumento_anio = anio
    contrato.ultimo_aumento_mes = mes
    # Actualizar tambien la fecha de ultimo aumento: queda como base del
    # proximo periodo y evita que el mismo aumento se vuelva a aplicar
    # cada vez que se abre el Dashboard en el mes de vigencia.
    contrato.fecha_ultimo_aumento = date(anio, mes, 1)
    session.add(contrato)
    session.commit()
    session.refresh(contrato)

    # Nota: el porcentaje_aumento_usado se guarda en el registro mensual
    # DESPUÉS de que este se crea (en el caller, ej. dashboard).
    return porcentaje_usado


def calcular_proximo_aumento(contrato: Contrato) -> Dict[str, Any]:
    """
    Calcula el próximo aumento para un contrato activo.

    Para contratos MANUAL: misma lógica anterior.
    Para contratos ICL: consulta la API del BCRA y devuelve el estado
    correspondiente (calculado o pendiente de datos).
    """
    tipo = getattr(contrato, 'tipo_aumento', 'MANUAL')

    if contrato.periodicidad_aumento_meses == 0:
        return {
            "proximo_anio": None, "proximo_mes": None,
            "alquiler_actual": contrato.alquiler_base_actual, "alquiler_nuevo": None,
            "requires_fecha_ultimo": False,
            "tipo_aumento": tipo,
            "aumento_fuera_de_contrato": False,
        }
    if tipo == 'MANUAL' and contrato.porcentaje_aumento == 0:
        return {
            "proximo_anio": None, "proximo_mes": None,
            "alquiler_actual": contrato.alquiler_base_actual, "alquiler_nuevo": None,
            "requires_fecha_ultimo": False,
            "tipo_aumento": tipo,
            "aumento_fuera_de_contrato": False,
        }

    # Determinar la base (mismo orden que corresponde_aumento)
    if contrato.fecha_ultimo_aumento is not None:
        base_anio = contrato.fecha_ultimo_aumento.year
        base_mes = contrato.fecha_ultimo_aumento.month
    elif contrato.ultimo_aumento_anio is not None and contrato.ultimo_aumento_mes is not None:
        base_anio = contrato.ultimo_aumento_anio
        base_mes = contrato.ultimo_aumento_mes
    else:
        base_anio = contrato.fecha_inicio.year
        base_mes = contrato.fecha_inicio.month

    total_meses = base_mes + contrato.periodicidad_aumento_meses
    proximo_anio = base_anio + (total_meses - 1) // 12
    proximo_mes = ((total_meses - 1) % 12) + 1
    fecha_vigencia = date(proximo_anio, proximo_mes, 1)
    hoy = date.today()

    # Si el próximo aumento cae en un mes posterior al mes de vencimiento
    # del contrato, no se aplicará nunca: el contrato termina antes.
    fin = contrato.fecha_fin
    aumento_fuera_de_contrato = (proximo_anio, proximo_mes) > (fin.year, fin.month)

    if tipo == 'ICL':
        icl_info = _calcular_icl_aumento(
            contrato, base_anio, base_mes, proximo_anio, proximo_mes)
        resultado: Dict[str, Any] = {
            "proximo_anio": proximo_anio,
            "proximo_mes": proximo_mes,
            "fecha_vigencia": fecha_vigencia.isoformat(),
            "alquiler_actual": contrato.alquiler_base_actual,
            "expensa_actual": contrato.expensa_base_actual,
            "requires_fecha_ultimo": False,
            "tipo_aumento": "ICL",
            "aumento_fuera_de_contrato": aumento_fuera_de_contrato,
        }
        resultado.update(icl_info)
        if not icl_info.get("icl_pendiente"):
            resultado["alquiler_nuevo"] = icl_info.get("alquiler_nuevo")
            resultado["expensa_nueva"] = icl_info.get("expensa_nueva")
            resultado["porcentaje"] = icl_info.get("porcentaje")
            # Estado intermedio: ya hay datos suficientes para calcular,
            # pero el nuevo valor entra en vigencia recién en fecha_vigencia.
            resultado["icl_calculado"] = fecha_vigencia > hoy
            # Mantiene compatibilidad para estado aplicado/en fecha.
            resultado["icl_aplicable"] = fecha_vigencia <= hoy
        else:
            resultado["alquiler_nuevo"] = None
            resultado["expensa_nueva"] = None
            resultado["porcentaje"] = None
            resultado["icl_calculado"] = False
            resultado["icl_aplicable"] = False
        return resultado

    # MANUAL
    factor = 1 + (contrato.porcentaje_aumento / 100)
    alquiler_nuevo = round(contrato.alquiler_base_actual * factor)
    expensa_nueva = (
        round(contrato.expensa_base_actual * factor)
        if contrato.cobra_expensa and contrato.expensa_base_actual
        else None
    )

    return {
        "proximo_anio": proximo_anio,
        "proximo_mes": proximo_mes,
        "alquiler_actual": contrato.alquiler_base_actual,
        "alquiler_nuevo": alquiler_nuevo,
        "expensa_actual": contrato.expensa_base_actual,
        "expensa_nueva": expensa_nueva,
        "porcentaje": contrato.porcentaje_aumento,
        "requires_fecha_ultimo": False,
        "tipo_aumento": "MANUAL",
        "icl_pendiente": False,
        "aumento_fuera_de_contrato": aumento_fuera_de_contrato,
    }
