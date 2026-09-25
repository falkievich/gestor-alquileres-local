from typing import List, Optional
from sqlmodel import Session, select
from app.model.models import Inquilino, InquilinoCreate, InquilinoUpdate


def get_inquilinos(session: Session) -> List[Inquilino]:
    results = session.exec(
        select(Inquilino).order_by(Inquilino.id_inquilinos.desc())
    ).all()
    # Ordenar: actuales primero
    return sorted(results, key=lambda x: (not x.es_actual, x.nombre_apellido))


def get_inquilino(session: Session, id: int) -> Optional[Inquilino]:
    return session.get(Inquilino, id)


def create_inquilino(session: Session, data: InquilinoCreate) -> Inquilino:
    inq = Inquilino.model_validate(data)
    session.add(inq)
    session.commit()
    session.refresh(inq)
    return inq


def update_inquilino(session: Session, id: int, data: InquilinoUpdate) -> Optional[Inquilino]:
    inq = session.get(Inquilino, id)
    if not inq:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(inq, key, val)
    session.add(inq)
    session.commit()
    session.refresh(inq)
    return inq


def delete_inquilino(session: Session, id: int) -> bool:
    inq = session.get(Inquilino, id)
    if not inq:
        return False
    session.delete(inq)
    session.commit()
    return True
