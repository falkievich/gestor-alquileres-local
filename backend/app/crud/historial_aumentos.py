from datetime import datetime
from typing import List, Optional

from sqlmodel import Session, select

from app.model.models import HistorialAumento


def get_by_contrato_periodo(
    session: Session, id_contratos: int, anio: int, mes: int
) -> Optional[HistorialAumento]:
    """Devuelve el historial de aumento para un contrato y período dado."""
    return session.exec(
        select(HistorialAumento).where(
            HistorialAumento.id_contratos == id_contratos,
            HistorialAumento.anio == anio,
            HistorialAumento.mes == mes,
        )
    ).first()


def listar(session: Session) -> List[HistorialAumento]:
    """Historial completo, del más reciente al más viejo."""
    return session.exec(
        select(HistorialAumento).order_by(
            HistorialAumento.anio.desc(), HistorialAumento.mes.desc(),
            HistorialAumento.id_historial_aumentos.desc(),
        )
    ).all()


def consolidar_pendiente(
    session: Session, id_contratos: int, anio: int, mes: int
) -> Optional[HistorialAumento]:
    """
    Pasa a CONSOLIDADO el aumento PENDIENTE de un contrato/período al cobrarlo.
    Completa fecha_consolidacion. Si no existe un PENDIENTE, no hace nada.
    """
    historial = session.exec(
        select(HistorialAumento).where(
            HistorialAumento.id_contratos == id_contratos,
            HistorialAumento.anio == anio,
            HistorialAumento.mes == mes,
            HistorialAumento.estado == "PENDIENTE",
        )
    ).first()
    if not historial:
        return None
    historial.estado = "CONSOLIDADO"
    historial.fecha_consolidacion = datetime.now()
    historial.fecha_actualizacion = datetime.now()
    session.add(historial)
    session.commit()
    session.refresh(historial)
    return historial


def actualizar(session: Session, historial: HistorialAumento) -> HistorialAumento:
    """Guarda cambios sobre un historial existente actualizando el timestamp."""
    historial.fecha_actualizacion = datetime.now()
    session.add(historial)
    session.commit()
    session.refresh(historial)
    return historial
