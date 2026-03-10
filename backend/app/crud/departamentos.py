from typing import List, Optional
from sqlmodel import Session, select
from app.model.models import Departamento, DepartamentoCreate, DepartamentoUpdate


def get_departamentos(session: Session) -> List[Departamento]:
    return session.exec(select(Departamento)).all()


def get_departamento(session: Session, id: int) -> Optional[Departamento]:
    return session.get(Departamento, id)


def create_departamento(session: Session, data: DepartamentoCreate) -> Departamento:
    PISOS_VALIDOS = ["Planta baja", "Piso 1", "Piso 2", "Piso 3"]
    if data.piso not in PISOS_VALIDOS:
        raise ValueError(f"Piso inválido. Opciones: {PISOS_VALIDOS}")
    dep = Departamento.model_validate(data)
    session.add(dep)
    session.commit()
    session.refresh(dep)
    return dep


def update_departamento(session: Session, id: int, data: DepartamentoUpdate) -> Optional[Departamento]:
    dep = session.get(Departamento, id)
    if not dep:
        return None
    PISOS_VALIDOS = ["Planta baja", "Piso 1", "Piso 2", "Piso 3"]
    if data.piso is not None and data.piso not in PISOS_VALIDOS:
        raise ValueError(f"Piso inválido. Opciones: {PISOS_VALIDOS}")
    update_data = data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(dep, key, val)
    session.add(dep)
    session.commit()
    session.refresh(dep)
    return dep


def delete_departamento(session: Session, id: int) -> bool:
    dep = session.get(Departamento, id)
    if not dep:
        return False
    session.delete(dep)
    session.commit()
    return True
