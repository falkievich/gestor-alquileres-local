from typing import List, Optional
from sqlmodel import Session, select
from app.model.models import (
    Contrato, ContratoCreate, ContratoUpdate,
    Departamento, Inquilino, RegistroMensual
)
from fastapi import HTTPException
from app.service.mes_service import (
    get_mes_actual, rebasar_aumento_pendiente, total_efectivo_registro,
)


def get_contratos(session: Session) -> List[Contrato]:
    return session.exec(select(Contrato).order_by(Contrato.id_contratos.desc())).all()


def get_contrato(session: Session, id: int) -> Optional[Contrato]:
    return session.get(Contrato, id)


def get_contratos_activos(session: Session) -> List[Contrato]:
    return session.exec(
        select(Contrato).where(Contrato.estado == "activo")
    ).all()


def create_contrato(session: Session, data: ContratoCreate) -> Contrato:
    # Verificar no haya 2 contratos activos para mismo departamento
    existing = session.exec(
        select(Contrato).where(
            Contrato.id_departamentos == data.id_departamentos,
            Contrato.estado == "activo"
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un contrato activo para este departamento."
        )
    contrato = Contrato.model_validate(data)
    # Los montos iniciales son históricos: si no vienen informados
    # (contrato nuevo, no "en curso"), arrancan con el valor actual.
    if contrato.alquiler_base_inicial is None:
        contrato.alquiler_base_inicial = contrato.alquiler_base_actual
    if contrato.cobra_expensa and contrato.expensa_base_inicial is None:
        contrato.expensa_base_inicial = contrato.expensa_base_actual
    session.add(contrato)
    # Marcar departamento como ocupado
    dep = session.get(Departamento, data.id_departamentos)
    if dep:
        dep.esta_ocupado = True
        session.add(dep)
    session.commit()
    session.refresh(contrato)
    return contrato


def update_contrato(session: Session, id: int, data: ContratoUpdate) -> Optional[Contrato]:
    contrato = session.get(Contrato, id)
    if not contrato:
        return None
    update_data = data.model_dump(exclude_unset=True)
    # Qué montos vigentes cambió realmente el usuario: si el contrato tiene un
    # aumento PENDIENTE, el monto corregido es la nueva base de ese aumento.
    alquiler_editado = (
        "alquiler_base_actual" in update_data
        and update_data["alquiler_base_actual"] != contrato.alquiler_base_actual
    )
    expensa_editada = (
        "expensa_base_actual" in update_data
        and update_data["expensa_base_actual"] != contrato.expensa_base_actual
    )
    for key, val in update_data.items():
        setattr(contrato, key, val)
    session.add(contrato)
    session.commit()
    session.refresh(contrato)
    if alquiler_editado or expensa_editada:
        rebasar_aumento_pendiente(
            session, contrato, alquiler_editado, expensa_editada)
    _sincronizar_registros_mensuales(session, contrato)
    return contrato


def _sincronizar_registros_mensuales(session: Session, contrato: Contrato) -> None:
    """
    Si se edita el alquiler/expensa actual de un contrato, propaga el cambio
    a los registros mensuales NO pagados y sin override del mes en curso en
    adelante. Los meses históricos pagados no se modifican.

    Los conceptos que el contrato dejó de cobrar (expensa, agua, luz) se
    limpian del registro para que el total no siga sumando montos que las
    pantallas ya no muestran.
    """
    anio_actual, mes_actual = get_mes_actual()
    registros = session.exec(
        select(RegistroMensual).where(
            RegistroMensual.id_contratos == contrato.id_contratos,
            RegistroMensual.pagado == False  # noqa: E712
        )
    ).all()

    for registro in registros:
        if (registro.anio, registro.mes) < (anio_actual, mes_actual):
            continue
        # No escribir en meses posteriores al vencimiento del contrato.
        if (registro.anio, registro.mes) > (contrato.fecha_fin.year, contrato.fecha_fin.month):
            continue
        cambio = False
        if registro.alquiler_override is None and \
                registro.alquiler_calculado != contrato.alquiler_base_actual:
            registro.alquiler_calculado = contrato.alquiler_base_actual
            cambio = True
        if contrato.cobra_expensa:
            if registro.expensa_override is None and \
                    registro.expensa_calculada != contrato.expensa_base_actual:
                registro.expensa_calculada = contrato.expensa_base_actual
                cambio = True
        elif registro.expensa_calculada is not None or registro.expensa_override is not None:
            # El contrato dejó de cobrar expensa: se limpia el concepto
            # completo (incluido el ajuste manual, que ya no tiene sentido).
            registro.expensa_calculada = None
            registro.expensa_override = None
            cambio = True
        if not contrato.cobra_agua and registro.agua is not None:
            registro.agua = None
            cambio = True
        if not contrato.cobra_luz and registro.luz is not None:
            registro.luz = None
            cambio = True
        nuevo_impuesto = contrato.impuesto_fijo
        if registro.impuesto != nuevo_impuesto:
            registro.impuesto = nuevo_impuesto
            cambio = True
        if cambio:
            registro.total = total_efectivo_registro(registro)
            session.add(registro)

    session.commit()


def cerrar_contrato(session: Session, id: int) -> Optional[Contrato]:
    contrato = session.get(Contrato, id)
    if not contrato:
        return None
    contrato.estado = "finalizado"
    session.add(contrato)

    # Revisar si el departamento tiene otros contratos activos
    otros_activos_dep = session.exec(
        select(Contrato).where(
            Contrato.id_departamentos == contrato.id_departamentos,
            Contrato.estado == "activo",
            Contrato.id_contratos != id
        )
    ).first()
    if not otros_activos_dep:
        dep = session.get(Departamento, contrato.id_departamentos)
        if dep:
            dep.esta_ocupado = False
            session.add(dep)

    # Revisar si el inquilino tiene otros contratos activos
    otros_activos_inq = session.exec(
        select(Contrato).where(
            Contrato.id_inquilinos == contrato.id_inquilinos,
            Contrato.estado == "activo",
            Contrato.id_contratos != id
        )
    ).first()
    if not otros_activos_inq:
        inq = session.get(Inquilino, contrato.id_inquilinos)
        if inq:
            inq.es_actual = False
            session.add(inq)

    session.commit()
    session.refresh(contrato)
    return contrato


def update_blob(session: Session, id: int, blob: bytes, nombre: str) -> Optional[Contrato]:
    contrato = session.get(Contrato, id)
    if not contrato:
        return None
    contrato.archivo_blob = blob
    contrato.archivo_nombre = nombre
    session.add(contrato)
    session.commit()
    session.refresh(contrato)
    return contrato


def delete_contrato(session: Session, id: int) -> bool:
    contrato = session.get(Contrato, id)
    if not contrato:
        return False
    session.delete(contrato)
    session.commit()
    return True
