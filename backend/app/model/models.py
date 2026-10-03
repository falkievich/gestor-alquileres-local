from typing import Optional
from datetime import date, datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint, CheckConstraint


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
    alquiler_base_inicial: Optional[int] = Field(default=None, nullable=True)
    expensa_base_inicial: Optional[int] = Field(default=None, nullable=True)
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
    impuesto_fijo: Optional[int] = Field(default=None, nullable=True)
    tipo_aumento: str = Field(default='MANUAL', max_length=20)
    archivo_blob: Optional[bytes] = Field(default=None)
    archivo_nombre: Optional[str] = Field(default=None, max_length=255)


class ContratoCreate(SQLModel):
    id_departamentos: int
    id_inquilinos: int
    fecha_inicio: date
    fecha_fin: date
    alquiler_base_inicial: Optional[int] = None
    expensa_base_inicial: Optional[int] = None
    alquiler_base_actual: int
    expensa_base_actual: Optional[int] = None
    porcentaje_aumento: float = 0.0
    periodicidad_aumento_meses: int = 3
    cobra_expensa: bool = False
    cobra_agua: bool = False
    cobra_luz: bool = False
    impuesto_fijo: Optional[int] = None
    tipo_aumento: str = 'MANUAL'
    fecha_ultimo_aumento: Optional[date] = None


class ContratoUpdate(SQLModel):
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    alquiler_base_inicial: Optional[int] = None
    expensa_base_inicial: Optional[int] = None
    alquiler_base_actual: Optional[int] = None
    expensa_base_actual: Optional[int] = None
    porcentaje_aumento: Optional[float] = None
    periodicidad_aumento_meses: Optional[int] = None
    cobra_expensa: Optional[bool] = None
    cobra_agua: Optional[bool] = None
    cobra_luz: Optional[bool] = None
    impuesto_fijo: Optional[int] = None
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
    alquiler_base_inicial: Optional[int] = None
    expensa_base_inicial: Optional[int] = None
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
    impuesto_fijo: Optional[int] = None
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
    impuesto: Optional[int] = Field(default=None, nullable=True)
    pagado: bool = Field(default=False)
    total: int
    porcentaje_aumento_usado: Optional[float] = Field(
        default=None, nullable=True)


class HistorialAumento(SQLModel, table=True):
    """Fuente de verdad del historial de aumentos.

    Estado del evento de aumento:
      - PENDIENTE: generado por el sistema, el mes todavía no fue cobrado.
      - CONSOLIDADO: el mes fue cobrado; el aumento queda inmutable.

    Semántica de montos:
      - *_anterior: monto vigente antes del aumento.
      - *_propuesto: monto calculado originalmente por el sistema (congelado).
      - *_aplicado: monto final a cobrar; en esta etapa siempre == propuesto.
    """
    __tablename__ = "historial_aumentos"
    __table_args__ = (
        UniqueConstraint(
            "id_contratos", "anio", "mes",
            name="uq_historial_contrato_periodo"),
        CheckConstraint("mes >= 1 AND mes <= 12", name="ck_historial_mes_rango"),
    )

    id_historial_aumentos: Optional[int] = Field(default=None, primary_key=True)
    id_contratos: int = Field(foreign_key="contratos.id_contratos")
    anio: int
    mes: int
    estado: str = Field(default="PENDIENTE", max_length=20)
    tipo_aumento: str = Field(max_length=20)

    # Alquiler
    alquiler_anterior: int
    alquiler_propuesto: int
    alquiler_aplicado: int
    porcentaje_alquiler_propuesto: float
    porcentaje_alquiler_aplicado: float

    # Expensa (NULL cuando el contrato no cobra expensa)
    expensa_anterior: Optional[int] = None
    expensa_propuesta: Optional[int] = None
    expensa_aplicada: Optional[int] = None
    porcentaje_expensa_propuesto: Optional[float] = None
    porcentaje_expensa_aplicado: Optional[float] = None

    # Datos ICL (NULL cuando el aumento es MANUAL)
    coeficiente_icl: Optional[float] = None
    icl_inicial: Optional[float] = None
    icl_final: Optional[float] = None
    fecha_icl_inicial: Optional[date] = None
    fecha_icl_final: Optional[date] = None

    # Auditoría
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_actualizacion: datetime = Field(default_factory=datetime.now)
    fecha_consolidacion: Optional[datetime] = None


class HistorialAumentoRead(SQLModel):
    id_historial_aumentos: Optional[int] = None
    id_contratos: int
    anio: int
    mes: int
    estado: str
    tipo_aumento: str
    alquiler_anterior: int
    alquiler_propuesto: int
    alquiler_aplicado: int
    porcentaje_alquiler_propuesto: float
    porcentaje_alquiler_aplicado: float
    expensa_anterior: Optional[int] = None
    expensa_propuesta: Optional[int] = None
    expensa_aplicada: Optional[int] = None
    porcentaje_expensa_propuesto: Optional[float] = None
    porcentaje_expensa_aplicado: Optional[float] = None
    coeficiente_icl: Optional[float] = None
    icl_inicial: Optional[float] = None
    icl_final: Optional[float] = None
    fecha_icl_inicial: Optional[date] = None
    fecha_icl_final: Optional[date] = None
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    fecha_consolidacion: Optional[datetime] = None


class RegistroMensualCreate(SQLModel):
    id_contratos: int
    anio: int
    mes: int
    alquiler_calculado: int
    expensa_calculada: Optional[int] = None
    agua: Optional[int] = None
    luz: Optional[int] = None
    impuesto: Optional[int] = None
    total: int
    porcentaje_aumento_usado: Optional[float] = None


class RegistroMensualUpdate(SQLModel):
    alquiler_override: Optional[int] = None
    expensa_override: Optional[int] = None
    nota_override: Optional[str] = None
    agua: Optional[int] = None
    luz: Optional[int] = None
    impuesto: Optional[int] = None
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
    impuesto: Optional[int] = None
    pagado: bool = False
    total: int
    porcentaje_aumento_usado: Optional[float] = None
