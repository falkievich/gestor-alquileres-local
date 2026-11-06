from datetime import date, datetime
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
        "fecha_icl_inicial": fecha_desde.isoformat(),
        "fecha_icl_final": fecha_hasta.isoformat(),
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


def total_efectivo_registro(registro: RegistroMensual) -> int:
    """
    Total de un registro mensual sobre sus valores efectivos
    (override ?? calculado) más servicios e impuesto. No persiste nada.
    """
    alquiler = (
        registro.alquiler_override
        if registro.alquiler_override is not None
        else registro.alquiler_calculado
    )
    expensa = (
        registro.expensa_override
        if registro.expensa_override is not None
        else registro.expensa_calculada
    )
    return calcular_total(
        alquiler, expensa, registro.agua, registro.luz, registro.impuesto)


def _ajuste_desplazado(
    override: Optional[int], anterior: Optional[int], nuevo: int,
) -> Optional[int]:
    # Un ajuste en 0 (mes bonificado) sigue en 0 y nunca queda negativo.
    if not override or anterior is None:
        return override
    return max(0, override + nuevo - anterior)


def fijar_montos_calculados(
    registro: RegistroMensual,
    alquiler: Optional[int] = None,
    expensa: Optional[int] = None,
) -> bool:
    """
    Cambia el monto base (calculado) de alquiler y/o expensa de un registro
    (None = no tocar) y recalcula el total. El ajuste manual (override)
    conserva su diferencia con el monto base: un +5.000 sobre 100.000 pasa a
    ser +5.000 sobre 110.000. No persiste; devuelve True si hubo cambios.
    """
    cambio = False
    if alquiler is not None and alquiler != registro.alquiler_calculado:
        registro.alquiler_override = _ajuste_desplazado(
            registro.alquiler_override, registro.alquiler_calculado, alquiler)
        registro.alquiler_calculado = alquiler
        cambio = True
    if expensa is not None and expensa != registro.expensa_calculada:
        registro.expensa_override = _ajuste_desplazado(
            registro.expensa_override, registro.expensa_calculada, expensa)
        registro.expensa_calculada = expensa
        cambio = True
    if cambio:
        registro.total = total_efectivo_registro(registro)
    return cambio


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
    1. Genera, como atrasados, los meses vigentes que quedaron sin registro
       entre el último mes registrado del contrato y el mes dado (meses en
       los que no se abrió la app), cada uno con su aumento si le corresponde.
       Un contrato sin ningún registro previo no genera meses hacia atrás.
    2. Aplica el aumento del mes si corresponde (mutando el contrato).
    3. Crea (o reutiliza) el registro mensual con los valores congelados.

    Usada por el Dashboard y por la sección Servicios para que ambos
    generen el registro del mes de la misma forma.
    Retorna (registro, porcentaje_aplicado).

    Protección: no prepara meses fuera de la vigencia del contrato (el mes de
    vencimiento sigue siendo válido). Levanta HTTPException 409.
    """
    if not contrato_vigente_para_mes(contrato, anio, mes):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=409,
            detail="No se pueden generar meses fuera de la vigencia del "
                   f"contrato ({contrato.fecha_inicio.isoformat()} a "
                   f"{contrato.fecha_fin.isoformat()})",
        )
    for anio_faltante, mes_faltante in _meses_sin_registro(
            session, contrato, anio, mes):
        _preparar_mes(session, contrato, anio_faltante, mes_faltante)
    return _preparar_mes(session, contrato, anio, mes)


def _meses_sin_registro(
    session: Session, contrato: Contrato, anio: int, mes: int,
) -> List[Tuple[int, int]]:
    """Meses vigentes sin registro entre el último registrado antes de (anio, mes) y (anio, mes), en orden."""
    anteriores = [
        (r.anio, r.mes)
        for r in crud_registros.get_registros_by_contrato(
            session, contrato.id_contratos)
        if (r.anio, r.mes) < (anio, mes)
    ]
    if not anteriores:
        return []
    ultimo_anio, ultimo_mes = max(anteriores)
    faltantes = []
    for indice in range(ultimo_anio * 12 + ultimo_mes, anio * 12 + mes - 1):
        periodo = (indice // 12, indice % 12 + 1)
        if contrato_vigente_para_mes(contrato, *periodo):
            faltantes.append(periodo)
    return faltantes


def _preparar_mes(
    session: Session, contrato: Contrato, anio: int, mes: int,
) -> Tuple[RegistroMensual, Optional[float]]:
    """Aplica el aumento del mes si corresponde y crea o actualiza su registro."""
    from app.crud import historial_aumentos as crud_historial

    porcentaje_aplicado = aplicar_aumento_si_corresponde(
        session, contrato, anio, mes)
    session.refresh(contrato)
    registro = get_or_create_registro(session, contrato, anio, mes)
    if porcentaje_aplicado is None:
        return registro, None

    if registro.pagado:
        # El aumento se aplicó después de cobrar el mes (ej.: ICL del BCRA
        # publicado tarde): el mes cobrado no se modifica y el aumento se
        # consolida ya, para que no quede PENDIENTE sin un mes por cobrar. El
        # contrato queda aumentado para los meses siguientes.
        crud_historial.consolidar_pendiente(
            session, contrato.id_contratos, anio, mes)
        return registro, porcentaje_aplicado

    # Si el registro ya existía (se creó antes de que el aumento pudiera
    # aplicarse), pasa a cobrar el monto aumentado.
    fijar_montos_calculados(
        registro,
        contrato.alquiler_base_actual,
        contrato.expensa_base_actual if contrato.cobra_expensa else None,
    )
    if registro.porcentaje_aumento_usado is None:
        registro.porcentaje_aumento_usado = porcentaje_aplicado
    session.add(registro)
    session.commit()
    session.refresh(registro)
    return registro, porcentaje_aplicado


def contrato_vigente_para_mes(contrato: Contrato, anio: int, mes: int) -> bool:
    """
    Indica si el mes dado está dentro de la vigencia del contrato: desde el
    mes de fecha_inicio hasta el mes de fecha_fin, ambos incluidos.

    Fuera de ese rango no se generan registros, servicios, ajustes ni cobros
    (un mes anterior al inicio o posterior al vencimiento no se adeuda). El
    cierre manual del contrato (estado = 'finalizado') se mantiene como acción
    formal e independiente de esta guarda.
    """
    inicio, fin = contrato.fecha_inicio, contrato.fecha_fin
    return (inicio.year, inicio.month) <= (anio, mes) <= (fin.year, fin.month)


def contrato_operativo_hoy(contrato: Contrato) -> bool:
    """
    El ciclo del mes en curso (Dashboard y Servicios) lista y prepara el
    contrato solo si ya empezó (por fecha exacta) y el mes en curso está
    dentro de su vigencia.
    """
    anio, mes = get_mes_actual()
    return contrato.fecha_inicio <= date.today() \
        and contrato_vigente_para_mes(contrato, anio, mes)


def registros_sin_cobrar_fuera_del_ciclo(
    session: Session,
) -> List[Tuple[RegistroMensual, Contrato]]:
    """
    Registros sin cobrar que el ciclo del mes en curso no lista: los de meses
    anteriores (atrasados) de cualquier contrato y el del mes en curso de los
    contratos finalizados, para que la deuda de un contrato cerrado siga a la
    vista hasta cobrarse. Se excluyen los meses fuera de la vigencia del
    contrato, que no se pueden cobrar. Orden: del más antiguo al más reciente.
    """
    from sqlmodel import select

    actual = get_mes_actual()
    registros = session.exec(
        select(RegistroMensual).where(
            RegistroMensual.pagado == False,  # noqa: E712
        ).order_by(RegistroMensual.anio.asc(), RegistroMensual.mes.asc())
    ).all()
    resultado = []
    for registro in registros:
        periodo = (registro.anio, registro.mes)
        if periodo > actual:
            continue
        contrato = session.get(Contrato, registro.id_contratos)
        if not contrato:
            continue
        if periodo == actual and contrato.estado == "activo":
            continue
        if not contrato_vigente_para_mes(contrato, registro.anio, registro.mes):
            continue
        resultado.append((registro, contrato))
    return resultado


def calcular_estado_servicios(contrato: Contrato, registro: RegistroMensual) -> str:
    """Calcula si los servicios están OK o Pendiente."""
    if contrato.cobra_agua and registro.agua is None:
        return "Pendiente"
    if contrato.cobra_luz and registro.luz is None:
        return "Pendiente"
    return "OK"


def corresponde_aumento(contrato: Contrato, anio: int, mes: int) -> bool:
    """Determina si le corresponde un aumento en el mes/año dado."""
    if getattr(contrato, 'tipo_aumento', 'MANUAL') == 'SIN_AUMENTO':
        return False
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
    Aplica el aumento al contrato si corresponde y registra el evento en
    historial_aumentos con estado PENDIENTE (se consolida al cobrar el mes).

    Protecciones:
      - tipo_aumento == SIN_AUMENTO: nunca aplica ni registra nada.
      - Si el período (anio, mes) es posterior al mes de fecha_fin: no aplica.
        (Si cae en el mismo mes de vencimiento, sí puede aplicarse.)
      - Idempotencia: si ya existe historial para (contrato, anio, mes), no
        re-aplica ni modifica la propuesta congelada.
      - ICL pendiente (datos BCRA incompletos): no muta nada, no registra nada.

    Consistencia: historial + mutación del contrato se commitean juntos.
    Retorna el porcentaje aplicado (para el legacy porcentaje_aumento_usado),
    o None si no se aplicó ningún aumento.
    """
    from app.crud import historial_aumentos as crud_historial
    from app.model.models import HistorialAumento

    tipo = getattr(contrato, 'tipo_aumento', 'MANUAL')

    if tipo == 'SIN_AUMENTO':
        return None

    if not corresponde_aumento(contrato, anio, mes):
        return None

    # Protección por vencimiento: un aumento cuyo período de vigencia cae en
    # un mes posterior al mes de fecha_fin no se aplica nunca.
    fin = contrato.fecha_fin
    if (anio, mes) > (fin.year, fin.month):
        return None

    # Idempotencia: el evento ya fue generado para este contrato/período;
    # la propuesta congelada no se recalcula ni se duplica.
    if crud_historial.get_by_contrato_periodo(
            session, contrato.id_contratos, anio, mes) is not None:
        return None

    # Capturar los montos vigentes ANTES de mutar el contrato
    alquiler_anterior = contrato.alquiler_base_actual
    expensa_anterior = (
        contrato.expensa_base_actual
        if contrato.cobra_expensa and contrato.expensa_base_actual is not None
        else None
    )

    icl_info: Optional[Dict[str, Any]] = None
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

    # Propuesta (a partir de acá, congelada para siempre en el historial)
    alquiler_propuesto = round(alquiler_anterior * factor)
    expensa_propuesta = (
        round(expensa_anterior * factor) if expensa_anterior is not None
        else None
    )
    porcentaje_propuesto = (factor - 1) * 100

    # Validaciones de negocio: un aumento nunca deja montos por debajo del
    # valor anterior (bloquea, por ejemplo, variaciones ICL negativas).
    if alquiler_propuesto < alquiler_anterior:
        return None
    if expensa_propuesta is not None and expensa_anterior is not None \
            and expensa_propuesta < expensa_anterior:
        return None

    historial = HistorialAumento(
        id_contratos=contrato.id_contratos,
        anio=anio,
        mes=mes,
        estado="PENDIENTE",
        tipo_aumento=tipo,
        alquiler_anterior=alquiler_anterior,
        alquiler_propuesto=alquiler_propuesto,
        alquiler_aplicado=alquiler_propuesto,
        porcentaje_alquiler_propuesto=porcentaje_propuesto,
        porcentaje_alquiler_aplicado=porcentaje_propuesto,
        expensa_anterior=expensa_anterior,
        expensa_propuesta=expensa_propuesta,
        expensa_aplicada=expensa_propuesta,
        porcentaje_expensa_propuesto=(
            porcentaje_propuesto if expensa_propuesta is not None else None),
        porcentaje_expensa_aplicado=(
            porcentaje_propuesto if expensa_propuesta is not None else None),
        coeficiente_icl=(
            icl_info["icl_coeficiente"] if icl_info else None),
        icl_inicial=(icl_info["icl_inicial"] if icl_info else None),
        icl_final=(icl_info["icl_final"] if icl_info else None),
        fecha_icl_inicial=(
            date.fromisoformat(icl_info["fecha_icl_inicial"]) if icl_info else None),
        fecha_icl_final=(
            date.fromisoformat(icl_info["fecha_icl_final"]) if icl_info else None),
    )

    # Mutación del contrato + historial en un único commit
    contrato.alquiler_base_actual = alquiler_propuesto
    if expensa_propuesta is not None:
        contrato.expensa_base_actual = expensa_propuesta
    contrato.ultimo_aumento_anio = anio
    contrato.ultimo_aumento_mes = mes
    # Actualizar tambien la fecha de ultimo aumento: queda como base del
    # proximo periodo y evita que el mismo aumento se vuelva a aplicar
    # cada vez que se abre el Dashboard en el mes de vigencia.
    contrato.fecha_ultimo_aumento = date(anio, mes, 1)
    session.add(historial)
    session.add(contrato)
    session.commit()
    session.refresh(contrato)

    # Nota: el porcentaje_aumento_usado (legacy) se guarda en el registro
    # mensual DESPUÉS de que este se crea (en el caller, ej. dashboard).
    return porcentaje_usado


def rebasar_aumento_pendiente(
    session: Session,
    contrato: Contrato,
    alquiler_editado: bool,
    expensa_editada: bool,
) -> Optional["HistorialAumento"]:  # noqa: F821
    """
    Re-calcula el aumento PENDIENTE del contrato cuando el usuario corrige los
    montos vigentes editando el contrato.

    El aumento ya aplicado dejó el contrato con el monto aumentado, así que el
    monto que el usuario carga al editar se interpreta como el monto *anterior*
    al aumento: pasa a ser `*_anterior` y la propuesta se recalcula con el
    porcentaje congelado del evento (no con la configuración actual del
    contrato, que puede haber cambiado). El contrato queda con el monto
    resultante y el registro mensual del período se sincroniza.

    Solo se re-basa el concepto efectivamente editado, solo el PENDIENTE más
    reciente (los viejos, con un aumento posterior ya generado, no se tocan:
    misma regla que `modificar_aumento_pendiente`) y solo si su período es el
    mes en curso o posterior.

    Devuelve el historial actualizado, o None si no hay nada que re-basar.
    """
    from app.crud import historial_aumentos as crud_historial

    historial = crud_historial.get_ultimo_pendiente(
        session, contrato.id_contratos)
    if not historial:
        return None

    # Los meses anteriores quedan congelados con sus montos históricos: solo
    # se re-calcula el aumento del mes en curso (o posterior), igual que la
    # sincronización de registros mensuales.
    if (historial.anio, historial.mes) < get_mes_actual():
        return None

    # El registro del período debe existir y estar sin cobrar: un mes cobrado
    # es histórico (y su aumento ya estaría CONSOLIDADO).
    registro = crud_registros.get_registro(
        session, historial.id_contratos, historial.anio, historial.mes)
    if not registro or registro.pagado:
        return None

    cambio = False

    if alquiler_editado:
        factor = 1 + (historial.porcentaje_alquiler_propuesto / 100)
        historial.alquiler_anterior = contrato.alquiler_base_actual
        historial.alquiler_propuesto = round(
            contrato.alquiler_base_actual * factor)
        historial.alquiler_aplicado = historial.alquiler_propuesto
        historial.porcentaje_alquiler_aplicado = historial.porcentaje_alquiler_propuesto
        contrato.alquiler_base_actual = historial.alquiler_propuesto
        fijar_montos_calculados(registro, alquiler=historial.alquiler_aplicado)
        registro.porcentaje_aumento_usado = historial.porcentaje_alquiler_aplicado
        cambio = True

    if expensa_editada and historial.expensa_anterior is not None \
            and contrato.cobra_expensa and contrato.expensa_base_actual is not None:
        porcentaje = historial.porcentaje_expensa_propuesto or 0.0
        factor = 1 + (porcentaje / 100)
        historial.expensa_anterior = contrato.expensa_base_actual
        historial.expensa_propuesta = round(
            contrato.expensa_base_actual * factor)
        historial.expensa_aplicada = historial.expensa_propuesta
        historial.porcentaje_expensa_aplicado = historial.porcentaje_expensa_propuesto
        contrato.expensa_base_actual = historial.expensa_propuesta
        fijar_montos_calculados(registro, expensa=historial.expensa_aplicada)
        cambio = True

    if not cambio:
        return None

    historial.fecha_actualizacion = datetime.now()
    session.add(historial)
    session.add(contrato)
    session.add(registro)
    session.commit()
    session.refresh(historial)
    session.refresh(contrato)
    return historial


def modificar_aumento_pendiente(session: Session, id_historial_aumentos: int, data) -> RegistroMensual:
    """
    Modifica los montos aplicados de un aumento en estado PENDIENTE.

    El usuario edita directamente los montos (no los porcentajes): los
    porcentajes aplicados se recalculan siempre en el backend como
    ((aplicado - anterior) / anterior) * 100.

    Reglas:
      - Solo PENDIENTE es editable; CONSOLIDADO se rechaza (inmutable).
      - monto_aplicado >= monto_anterior (puede ser <, = o > que el propuesto).
      - *_anterior, *_propuesto y porcentajes propuestos quedan congelados.
      - Sincroniza contrato (base_actual) y registro mensual del período
        (calculado + total; los ajustes manuales conservan su diferencia) en
        un único commit.
      - Los registros posteriores sin cobrar (atrasados o del mes en curso)
        se generaron con el monto anterior del contrato y heredan el aplicado;
        los ya cobrados no se tocan.
      - Si el usuario corrigió el monto del contrato después del aumento
        (editando el contrato), esa corrección no se pisa: ni la base del
        contrato ni los registros que ya no tienen el monto del aumento.
      - Si no existe el registro mensual del período (inconsistencia), aborta
        sin cambios parciales.

    `data` es un HistorialAumentoUpdate: solo los campos con valor distinto de
    None se aplican, permitiendo modificar alquiler y/o expensa de forma
    independiente.
    """
    from fastapi import HTTPException
    from app.crud import historial_aumentos as crud_historial
    from app.model.models import HistorialAumento, HistorialAumentoUpdate

    historial = session.get(HistorialAumento, id_historial_aumentos)
    if not historial:
        raise HTTPException(status_code=404, detail="Aumento no encontrado")

    # Protección real en backend: un aumento CONSOLIDADO es histórico e
    # inmutable, sin importar lo que muestre el frontend.
    if historial.estado != "PENDIENTE":
        raise HTTPException(
            status_code=409,
            detail="El aumento está CONSOLIDADO y no puede modificarse",
        )

    # Protección de la cadena histórica: si ya existe un aumento posterior
    # para este contrato, el PENDIENTE viejo solo puede cobrarse/consolidarse,
    # no modificarse (modificarlo rompería la continuidad de los montos).
    if crud_historial.existe_posterior(
            session, historial.id_contratos, historial.anio, historial.mes):
        raise HTTPException(
            status_code=409,
            detail="No se puede modificar un aumento de un mes anterior al "
                   "último aumento generado del contrato",
        )

    if data.alquiler_aplicado is None and data.expensa_aplicada is None:
        raise HTTPException(
            status_code=400,
            detail="Debe indicar al menos un monto a aplicar",
        )

    # Validación de negocio: nunca por debajo del monto anterior.
    if data.alquiler_aplicado is not None \
            and data.alquiler_aplicado < historial.alquiler_anterior:
        raise HTTPException(
            status_code=400,
            detail="El nuevo monto de alquiler no puede ser inferior al monto anterior",
        )
    if data.expensa_aplicada is not None \
            and historial.expensa_anterior is not None \
            and data.expensa_aplicada < historial.expensa_anterior:
        raise HTTPException(
            status_code=400,
            detail="El nuevo monto de expensa no puede ser inferior al monto anterior",
        )

    # El registro mensual del período debe existir (se creó al generar el
    # aumento). Si falta es una inconsistencia: abortar sin cambios parciales.
    registro = crud_registros.get_registro(
        session, historial.id_contratos, historial.anio, historial.mes)
    if not registro:
        raise HTTPException(
            status_code=409,
            detail="No existe el registro mensual del período del aumento; "
                   "no se puede modificar",
        )
    if registro.pagado:
        raise HTTPException(
            status_code=409,
            detail="El registro mensual del período ya está pagado; "
                   "no se puede modificar el aumento",
        )

    def _porcentaje(monto_anterior: int, monto_aplicado: int) -> float:
        if not monto_anterior:
            return 0.0
        return round(((monto_aplicado - monto_anterior) / monto_anterior) * 100, 2)

    # Montos que el aumento dejaba aplicados antes de esta modificación: lo que
    # todavía los tenga derivó del aumento; lo que no, fue corregido después
    # por el usuario (editando el contrato) y no se pisa.
    alquiler_previo = historial.alquiler_aplicado
    expensa_previa = historial.expensa_aplicada

    # 1) Historial: actualizar aplicados + porcentajes recalculados.
    if data.alquiler_aplicado is not None:
        historial.alquiler_aplicado = data.alquiler_aplicado
        historial.porcentaje_alquiler_aplicado = _porcentaje(
            historial.alquiler_anterior, data.alquiler_aplicado)
    if data.expensa_aplicada is not None:
        if historial.expensa_anterior is not None:
            historial.expensa_aplicada = data.expensa_aplicada
            historial.porcentaje_expensa_aplicado = _porcentaje(
                historial.expensa_anterior, data.expensa_aplicada)
        else:
            raise HTTPException(
                status_code=400,
                detail="El aumento no tiene expensa",
            )
    historial.fecha_actualizacion = datetime.now()
    session.add(historial)

    def _heredado(actual: Optional[int], previo: Optional[int], nuevo: Optional[int]) -> Optional[int]:
        """Nuevo monto si `actual` todavía es el que dejaba el aumento; si no, None (no tocar)."""
        return nuevo if previo is not None and actual == previo else None

    # 2) Contrato: la base de futuros aumentos pasa a ser el monto realmente
    #    aplicado (no se toca *_base_inicial, ni fechas de último aumento).
    contrato = session.get(Contrato, historial.id_contratos)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    alquiler_base = _heredado(
        contrato.alquiler_base_actual, alquiler_previo, historial.alquiler_aplicado)
    if alquiler_base is not None:
        contrato.alquiler_base_actual = alquiler_base
    expensa_base = _heredado(
        contrato.expensa_base_actual, expensa_previa, historial.expensa_aplicada)
    if expensa_base is not None:
        contrato.expensa_base_actual = expensa_base
    session.add(contrato)

    # 3) Registro mensual: congelar los montos aplicados y recalcular el total
    #    con la lógica común (override ?? calculado); los ajustes manuales
    #    conservan su diferencia. Se actualiza también el
    #    porcentaje_aumento_usado (legacy).
    fijar_montos_calculados(
        registro, historial.alquiler_aplicado, historial.expensa_aplicada)
    registro.porcentaje_aumento_usado = historial.porcentaje_alquiler_aplicado
    session.add(registro)

    # 4) Registros posteriores sin cobrar: como no hay aumentos posteriores
    #    (existe_posterior), los que siguen con el monto anterior del aumento
    #    derivan de él y cobran el aplicado.
    for posterior in crud_registros.get_registros_by_contrato(
            session, historial.id_contratos):
        if posterior.pagado or \
                (posterior.anio, posterior.mes) <= (historial.anio, historial.mes):
            continue
        if fijar_montos_calculados(
            posterior,
            _heredado(posterior.alquiler_calculado,
                      alquiler_previo, historial.alquiler_aplicado),
            _heredado(posterior.expensa_calculada,
                      expensa_previa, historial.expensa_aplicada),
        ):
            session.add(posterior)

    # Commit único: historial + contrato + registros quedan consistentes o no
    # se aplica ningún cambio.
    session.commit()
    session.refresh(historial)
    session.refresh(registro)
    return registro


def calcular_proximo_aumento(contrato: Contrato) -> Dict[str, Any]:
    """
    Calcula el próximo aumento para un contrato activo.

    Para contratos MANUAL: misma lógica anterior.
    Para contratos ICL: consulta la API del BCRA y devuelve el estado
    correspondiente (calculado o pendiente de datos).
    """
    tipo = getattr(contrato, 'tipo_aumento', 'MANUAL')

    if tipo == 'SIN_AUMENTO':
        return {
            "proximo_anio": None, "proximo_mes": None,
            "alquiler_actual": contrato.alquiler_base_actual, "alquiler_nuevo": None,
            "requires_fecha_ultimo": False,
            "tipo_aumento": tipo,
            "aumento_fuera_de_contrato": False,
        }

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
