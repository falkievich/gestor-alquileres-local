from typing import List, Optional
from sqlmodel import Session, select
from app.model.models import RegistroMensual, RegistroMensualCreate, RegistroMensualUpdate


def get_registro(session: Session, id_contrato: int, anio: int, mes: int) -> Optional[RegistroMensual]:
    return session.exec(
        select(RegistroMensual).where(
            RegistroMensual.id_contratos == id_contrato,
            RegistroMensual.anio == anio,
            RegistroMensual.mes == mes
        )
    ).first()


def get_registros_by_contrato(session: Session, id_contrato: int) -> List[RegistroMensual]:
    return session.exec(
        select(RegistroMensual).where(RegistroMensual.id_contratos == id_contrato)
    ).all()


def get_all_registros(session: Session) -> List[RegistroMensual]:
    return session.exec(select(RegistroMensual)).all()


def create_registro(session: Session, data: RegistroMensualCreate) -> RegistroMensual:
    registro = RegistroMensual.model_validate(data)
    session.add(registro)
    session.commit()
    session.refresh(registro)
    return registro


def update_registro(session: Session, id: int, data: RegistroMensualUpdate) -> Optional[RegistroMensual]:
    registro = session.get(RegistroMensual, id)
    if not registro:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(registro, key, val)
    session.add(registro)
    session.commit()
    session.refresh(registro)
    return registro


def get_registros_by_anio_mes(session: Session, anio: int, mes: int) -> List[RegistroMensual]:
    return session.exec(
        select(RegistroMensual).where(
            RegistroMensual.anio == anio,
            RegistroMensual.mes == mes
        )
    ).all()
