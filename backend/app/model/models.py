from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import date


class Departamento(SQLModel, table=True):
    __tablename__ = "departamentos"

    id_departamentos: Optional[int] = Field(default=None, primary_key=True)
    piso: str = Field(max_length=50)
    codigo: str = Field(max_length=50)
    direccion: Optional[str] = Field(default=None, max_length=255)
    esta_ocupado: bool = Field(default=False)


class DepartamentoCreate(SQLModel):
    piso: str
    codigo: str
    direccion: Optional[str] = None


class DepartamentoUpdate(SQLModel):
    piso: Optional[str] = None
    codigo: Optional[str] = None
    direccion: Optional[str] = None
    esta_ocupado: Optional[bool] = None


class DepartamentoRead(SQLModel):
    id_departamentos: Optional[int] = None
    piso: str
    codigo: str
    direccion: Optional[str] = None
    esta_ocupado: bool = False


class Inquilino(SQLModel, table=True):
    __tablename__ = "inquilinos"

    id_inquilinos: Optional[int] = Field(default=None, primary_key=True)
    nombre_apellido: str = Field(max_length=150)
    telefono: Optional[str] = Field(default=None, max_length=50)
    es_actual: bool = Field(default=True)


class InquilinoCreate(SQLModel):
    nombre_apellido: str
    telefono: Optional[str] = None
    es_actual: bool = True


class InquilinoUpdate(SQLModel):
    nombre_apellido: Optional[str] = None
    telefono: Optional[str] = None
    es_actual: Optional[bool] = None


class InquilinoRead(SQLModel):
    id_inquilinos: Optional[int] = None
    nombre_apellido: str
    telefono: Optional[str] = None
    es_actual: bool = True


class Contrato(SQLModel, table=True):
    __tablename__ = "contratos"

    id_contratos: Optional[int] = Field(default=None, primary_key=True)
    id_departamentos: int = Field(foreign_key="departamentos.id_departamentos")
    id_inquilinos: int = Field(foreign_key="inquilinos.id_inquilinos")
    fecha_inicio: date
    fecha_fin: date
    estado: str = Field(default="activo", max_length=20)
    alquiler_base_actual: int
    expensa_base_actual: Optional[int] = None
    porcentaje_aumento: float = Field(default=0.0)
    periodicidad_aumento_meses: int = Field(default=3)
    ultimo_aumento_anio: Optional[int] = None
    ultimo_aumento_mes: Optional[int] = None
    fecha_ultimo_aumento: Optional[date] = Field(default=None, nullable=True)
    cobra_expensa: bool = Field(default=False)
    cobra_agua: bool = Field(default=False)
    cobra_luz: bool = Field(default=False)
    tipo_aumento: str = Field(default='MANUAL', max_length=20)
    archivo_blob: Optional[bytes] = Field(default=None)
    archivo_nombre: Optional[str] = Field(default=None, max_length=255)


class ContratoCreate(SQLModel):
    id_departamentos: int
    id_inquilinos: int
    fecha_inicio: date
    fecha_fin: date
    alquiler_base_actual: int
    expensa_base_actual: Optional[int] = None
    porcentaje_aumento: float = 0.0
    periodicidad_aumento_meses: int = 3
    cobra_expensa: bool = False
    cobra_agua: bool = False
    cobra_luz: bool = False
    tipo_aumento: str = 'MANUAL'
    fecha_ultimo_aumento: Optional[date] = None


class ContratoUpdate(SQLModel):
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    alquiler_base_actual: Optional[int] = None
    expensa_base_actual: Optional[int] = None
    porcentaje_aumento: Optional[float] = None
    periodicidad_aumento_meses: Optional[int] = None
    cobra_expensa: Optional[bool] = None
    cobra_agua: Optional[bool] = None
    cobra_luz: Optional[bool] = None
    tipo_aumento: Optional[str] = None
    fecha_ultimo_aumento: Optional[date] = None


class ContratoRead(SQLModel):
    """Modelo de respuesta: igual que Contrato pero SIN archivo_blob."""
    id_contratos: Optional[int] = None
    id_departamentos: int
    id_inquilinos: int
    fecha_inicio: date
    fecha_fin: date
    estado: str
    alquiler_base_actual: int
    expensa_base_actual: Optional[int] = None
    porcentaje_aumento: float
    periodicidad_aumento_meses: int
    ultimo_aumento_anio: Optional[int] = None
    ultimo_aumento_mes: Optional[int] = None
    fecha_ultimo_aumento: Optional[date] = None
    cobra_expensa: bool
    cobra_agua: bool
    cobra_luz: bool
    tipo_aumento: str = 'MANUAL'
    archivo_nombre: Optional[str] = None


class RegistroMensual(SQLModel, table=True):
    __tablename__ = "registros_mensuales"

    id_registros_mensuales: Optional[int] = Field(
        default=None, primary_key=True)
    id_contratos: int = Field(foreign_key="contratos.id_contratos")
    anio: int
    mes: int
    alquiler_calculado: int
    expensa_calculada: Optional[int] = None
    alquiler_override: Optional[int] = None
    expensa_override: Optional[int] = None
    nota_override: Optional[str] = None
    agua: Optional[int] = None
    luz: Optional[int] = None
    pagado: bool = Field(default=False)
    total: int
    porcentaje_aumento_usado: Optional[float] = Field(
        default=None, nullable=True)


class RegistroMensualCreate(SQLModel):
    id_contratos: int
    anio: int
    mes: int
    alquiler_calculado: int
    expensa_calculada: Optional[int] = None
    agua: Optional[int] = None
    luz: Optional[int] = None
    total: int
    porcentaje_aumento_usado: Optional[float] = None


class RegistroMensualUpdate(SQLModel):
    alquiler_override: Optional[int] = None
    expensa_override: Optional[int] = None
    nota_override: Optional[str] = None
    agua: Optional[int] = None
    luz: Optional[int] = None
    pagado: Optional[bool] = None
    total: Optional[int] = None
    porcentaje_aumento_usado: Optional[float] = None


class RegistroMensualRead(SQLModel):
    id_registros_mensuales: Optional[int] = None
    id_contratos: int
    anio: int
    mes: int
    alquiler_calculado: int
    expensa_calculada: Optional[int] = None
    alquiler_override: Optional[int] = None
    expensa_override: Optional[int] = None
    nota_override: Optional[str] = None
    agua: Optional[int] = None
    luz: Optional[int] = None
    pagado: bool = False
    total: int
    porcentaje_aumento_usado: Optional[float] = None
