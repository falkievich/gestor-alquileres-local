# Modelo de datos — Depto Manager

Fuente de verdad documental del modelo de datos actual.

El sistema corre sobre **SQLite** (archivo `base_de_datos/alquileres.sqlite`)
con ORM **SQLModel** (`backend/app/model/models.py`). Este documento describe
las tablas reales tal como las define la aplicación.

---

## Resumen de tablas

| Tabla | Representa |
| --- | --- |
| `departamentos` | unidades físicas alquilables |
| `inquilinos` | personas inquilinas |
| `contratos` | vínculo contrato entre depto + inquilino, montos y configuración de aumentos |
| `registros_mensuales` | cobro de un contrato en un año/mes concreto |
| `historial_aumentos` | cada evento de aumento aplicado (fuente de verdad del historial) |

---

## departamentos

PK: `id_departamentos` (autonumérico).

| Campo | Tipo | Significado |
| --- | --- | --- |
| `id_departamentos` | INTEGER PK | identificador |
| `piso` | VARCHAR(50) | "Planta baja", "Piso 1"… (lista fija validada en backend) |
| `codigo` | VARCHAR(50) | código dentro del piso, ej. "1A" |
| `direccion` | VARCHAR(255) | opcional |
| `esta_ocupado` | BOOLEAN | True si tiene contrato activo (se marca al crear contrato y se libera al cerrarlo) |

---

## inquilinos

PK: `id_inquilinos` (autonumérico).

| Campo | Tipo | Significado |
| --- | --- | --- |
| `id_inquilinos` | INTEGER PK | identificador |
| `nombre_apellido` | VARCHAR(150) | nombre completo |
| `telefono` | VARCHAR(50) | opcional |
| `es_actual` | BOOLEAN | True = inquilino actual; False = anterior. Se pone False automáticamente al cerrar su contrato |

---

## contratos

PK: `id_contratos` (autonumérico). FKs: `id_departamentos` → departamentos,
`id_inquilinos` → inquilinos.

### Identidad y vigencia

| Campo | Tipo | Significado |
| --- | --- | --- |
| `id_departamentos` | INTEGER FK | departamento alquilado |
| `id_inquilinos` | INTEGER FK | inquilino |
| `fecha_inicio` | DATE | inicio de vigencia |
| `fecha_fin` | DATE | vencimiento; define el último mes cobrable |
| `estado` | VARCHAR(20) | `activo` (default) / `finalizado` (cierre manual) |

### Montos

| Campo | Tipo | Significado |
| --- | --- | --- |
| `alquiler_base_inicial` | INTEGER NULL | monto con el que comenzó (histórico; legacy/agregado por migración). Se completa en alta o en "contrato ya en curso" |
| `expensa_base_inicial` | INTEGER NULL | ídem para expensa |
| `alquiler_base_actual` | INTEGER | monto que se cobra hoy; **base de los próximos aumentos** |
| `expensa_base_actual` | INTEGER NULL | expensa actual; base de próximos aumentos si cobra expensa |

### Configuración de aumentos

| Campo | Tipo | Significado |
| --- | --- | --- |
| `tipo_aumento` | VARCHAR(20) | `MANUAL` / `ICL` / `SIN_AUMENTO` (default MANUAL) |
| `porcentaje_aumento` | FLOAT | % por aumento; solo se usa con MANUAL |
| `periodicidad_aumento_meses` | INTEGER | meses entre aumentos (default 3); `0` = sin aumentos |
| `ultimo_aumento_anio` | INTEGER NULL | año del último aumento aplicado por el sistema (legacy, convive con `fecha_ultimo_aumento`) |
| `ultimo_aumento_mes` | INTEGER NULL | mes del último aumento aplicado por el sistema (legacy) |
| `fecha_ultimo_aumento` | DATE NULL | base para el próximo aumento; la indica el usuario en "contrato ya en curso" y la actualiza el sistema a `1° del mes de vigencia` tras cada aumento |

### Servicios, adjuntos y otros

| Campo | Tipo | Significado |
| --- | --- | --- |
| `cobra_expensa` | BOOLEAN | si cobra expensas |
| `cobra_agua` | BOOLEAN | si cobra agua |
| `cobra_luz` | BOOLEAN | si cobra luz |
| `impuesto_fijo` | INTEGER NULL | monto fijo mensual opcional; NO participa de aumentos |
| `archivo_blob` | BLOB NULL | contrato adjunto (PDF/DOCX) guardado en la propia DB |
| `archivo_nombre` | VARCHAR(255) NULL | nombre original del archivo |

---

## registros_mensuales

Un registro por (contrato, año, mes). Se crea la primera vez que se pide ese
mes (Dashboard o Servicios) y **congela** los montos vigentes en ese momento.

PK: `id_registros_mensuales` (autonumérico). FK: `id_contratos` → contratos.

| Campo | Tipo | Significado |
| --- | --- | --- |
| `id_contratos` | INTEGER FK | contrato del cobro |
| `anio` / `mes` | INTEGER | período (mes 1–12) |
| `alquiler_calculado` | INTEGER | alquiler congelado al crear el registro (o actualizado al aplicarse/ajustarse un aumento) |
| `expensa_calculada` | INTEGER NULL | ídem para expensa |
| `alquiler_override` | INTEGER NULL | alquiler absoluto por ajuste manual (NULL = sin ajuste) |
| `expensa_override` | INTEGER NULL | expensa absoluta por ajuste manual |
| `nota_override` | TEXT NULL | motivo del ajuste |
| `agua` / `luz` | INTEGER NULL | valores de servicios cargados |
| `impuesto` | INTEGER NULL | copia del `impuesto_fijo` del contrato al crear el registro |
| `pagado` | BOOLEAN | False por defecto; True al cobrar (sin reversa) |
| `total` | INTEGER | suma derivada: (override ?? calculado) alquiler + expensa + agua + luz + impuesto |
| `porcentaje_aumento_usado` | FLOAT NULL | legacy: porcentaje del aumento del período (se sigue escribiendo; el historial es la fuente de verdad) |

**Unicidad lógica:** un registro por `(id_contratos, anio, mes)`. La
prevención de duplicados es check-then-create en el servicio (no hay
constraint UNIQUE en SQLite para esta tabla).

---

## historial_aumentos

Fuente de verdad del historial de aumentos. PK:
`id_historial_aumentos` (autonumérico). FK: `id_contratos` → contratos.

**Constraints reales** (definidas en `__table_args__`):

- `uq_historial_contrato_periodo` — UNIQUE `(id_contratos, anio, mes)`:
  un solo aumento por contrato y período.
- `ck_historial_mes_rango` — CHECK `(mes >= 1 AND mes <= 12)`.

| Campo | Tipo | Significado |
| --- | --- | --- |
| `id_contratos` | INTEGER FK | contrato del aumento |
| `anio` / `mes` | INTEGER | período de vigencia del aumento |
| `estado` | VARCHAR(20) | `PENDIENTE` (generado, sin cobrar) / `CONSOLIDADO` (cobrado, inmutable). Default PENDIENTE |
| `tipo_aumento` | VARCHAR(20) | `MANUAL` / `ICL` / `SIN_AUMENTO` |
| `alquiler_anterior` | INTEGER | alquiler vigente antes del aumento |
| `alquiler_propuesto` | INTEGER | monto calculado por el sistema (congelado; se re-calcula solo si estando PENDIENTE y en el mes en curso se corrige el monto del contrato) |
| `alquiler_aplicado` | INTEGER | monto final efectivo a cobrar; arranca igual al propuesto pero **puede modificarse mientras esté PENDIENTE** |
| `porcentaje_alquiler_propuesto` | FLOAT | % de la propuesta |
| `porcentaje_alquiler_aplicado` | FLOAT | % efectivo del aplicado (lo recalcula el backend ante cada modificación) |
| `expensa_anterior` | INTEGER NULL | NULL si el contrato no cobra expensa |
| `expensa_propuesta` | INTEGER NULL | propuesta de expensa |
| `expensa_aplicada` | INTEGER NULL | expensa final a cobrar (editable si PENDIENTE) |
| `porcentaje_expensa_propuesto` / `porcentaje_expensa_aplicado` | FLOAT NULL | % de propuesta/aplicado de expensa |
| `coeficiente_icl` | FLOAT NULL | coeficiente ICL del período (NULL si MANUAL) |
| `icl_inicial` / `icl_final` | FLOAT NULL | valores del índice al inicio/fin del período (NULL si MANUAL) |
| `fecha_icl_inicial` / `fecha_icl_final` | DATE NULL | fechas del período consultado al BCRA |
| `fecha_creacion` | DATETIME | alta del registro |
| `fecha_actualizacion` | DATETIME | última modificación |
| `fecha_consolidacion` | DATETIME NULL | se fija al pasar a CONSOLIDADO (al cobrar el mes) |

Reglas operativas clave:

- `*_aplicado` puede diferir de `*_propuesto` (modificación de un PENDIENTE);
  al consolidarse queda inmutable.
- Mientras el aumento esté **PENDIENTE y su período sea el mes en curso**,
  corregir el alquiler o la expensa del contrato re-basa el evento:
  `*_anterior` toma el monto corregido y `*_propuesto` / `*_aplicado` se
  recalculan con el porcentaje congelado. Los aumentos de meses anteriores y
  los CONSOLIDADO no se tocan.

---

## Relaciones

```
Departamento  1 ──────── N  Contratos
Inquilino     1 ──────── N  Contratos
Contrato      1 ──────── N  RegistrosMensuales
Contrato      1 ──────── N  HistorialAumentos
```

- Un departamento solo puede tener un contrato **activo** (regla de negocio
  en backend; no hay UNIQUE en DB).
- Las relaciones se modelan como FK lógicas; SQLite tiene FK declaradas pero
  el enforcement real lo hacen las capas de servicio.

---

## Inicialización y migraciones

- Al arrancar el backend: `SQLModel.metadata.create_all(engine)` crea tablas
  en bases nuevas.
- `_migrar_columnas_contratos()` agrega por `ALTER TABLE` (con `PRAGMA
  table_info` previo) las columnas que falten: `alquiler_base_inicial`,
  `expensa_base_inicial`, `impuesto_fijo` (contratos) e `impuesto`
  (registros_mensuales). Es una migración aditiva segura.
- La carpeta y el archivo de DB se crean automáticamente
  (`base_de_datos/alquileres.sqlite`).

---

## Anexo — DDL MySQL de referencia

> **IMPORTANTE:** la aplicación NO usa MySQL. El motor real de ejecución es
> **SQLite**, accedido por SQLModel (engine `sqlite:///…/alquileres.sqlite`).
> El siguiente DDL se conserva únicamente como diseño/referencia conceptual
> (fue el diseño original previo a la implementación). Corresponde
> fielmente a los campos del modelo actual, salvo las anotaciones entre
> llaves.

```sql
-- =============================================================
-- gestor-alquileres-local — Script MySQL de referencia (NO es la DB real)
-- =============================================================

CREATE DATABASE IF NOT EXISTS gestor_alquileres
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE gestor_alquileres;

-- -------------------------------------------------------------
-- Tabla: departamentos
-- -------------------------------------------------------------
CREATE TABLE departamentos (
    id_departamentos    INT             NOT NULL AUTO_INCREMENT,
    piso                VARCHAR(50)     NOT NULL,
    codigo              VARCHAR(50)     NOT NULL,
    direccion           VARCHAR(255)        NULL,
    esta_ocupado        TINYINT(1)      NOT NULL DEFAULT 0,

    PRIMARY KEY (id_departamentos)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- Tabla: inquilinos
-- -------------------------------------------------------------
CREATE TABLE inquilinos (
    id_inquilinos       INT             NOT NULL AUTO_INCREMENT,
    nombre_apellido     VARCHAR(150)    NOT NULL,
    telefono            VARCHAR(50)         NULL,
    es_actual           TINYINT(1)      NOT NULL DEFAULT 1,

    PRIMARY KEY (id_inquilinos)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- Tabla: contratos
-- -------------------------------------------------------------
CREATE TABLE contratos (
    id_contratos                INT             NOT NULL AUTO_INCREMENT,
    id_departamentos            INT             NOT NULL,
    id_inquilinos               INT             NOT NULL,
    fecha_inicio                DATE            NOT NULL,
    fecha_fin                   DATE            NOT NULL,
    estado                      VARCHAR(20)     NOT NULL DEFAULT 'activo',
    alquiler_base_inicial       INT                 NULL, -- Monto con el que comenzó el contrato (histórico, no se modifica por aumentos)
    expensa_base_inicial        INT                 NULL, -- Expensa con la que comenzó el contrato
    alquiler_base_actual        INT             NOT NULL, -- Monto que se cobra actualmente; base de los próximos aumentos
    expensa_base_actual         INT                 NULL,
    tipo_aumento                VARCHAR(20)     NOT NULL DEFAULT 'MANUAL', -- MANUAL (porcentaje), ICL (API del BCRA) o SIN_AUMENTO
    porcentaje_aumento          DOUBLE          NOT NULL DEFAULT 0.0,
    periodicidad_aumento_meses  INT             NOT NULL DEFAULT 3,
    ultimo_aumento_anio         INT                 NULL,
    ultimo_aumento_mes          INT                 NULL,
    fecha_ultimo_aumento        DATE                NULL,
    cobra_expensa               TINYINT(1)      NOT NULL DEFAULT 0,
    cobra_agua                  TINYINT(1)      NOT NULL DEFAULT 0,
    cobra_luz                   TINYINT(1)      NOT NULL DEFAULT 0,
    impuesto_fijo               INT                 NULL, -- Monto fijo mensual opcional; NO participa de los aumentos
    archivo_blob                LONGBLOB            NULL,
    archivo_nombre              VARCHAR(255)        NULL,

    PRIMARY KEY (id_contratos),

    CONSTRAINT fk_contratos_departamentos
        FOREIGN KEY (id_departamentos)
        REFERENCES departamentos (id_departamentos)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_contratos_inquilinos
        FOREIGN KEY (id_inquilinos)
        REFERENCES inquilinos (id_inquilinos)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    INDEX idx_contratos_estado        (estado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- Tabla: registros_mensuales
-- -------------------------------------------------------------
CREATE TABLE registros_mensuales (
    id_registros_mensuales  INT     NOT NULL AUTO_INCREMENT,
    id_contratos            INT     NOT NULL,
    anio                    INT     NOT NULL,
    mes                     INT     NOT NULL,
    alquiler_calculado      INT     NOT NULL,
    expensa_calculada       INT         NULL,
    alquiler_override       INT         NULL,
    expensa_override        INT         NULL,
    nota_override           TEXT        NULL,
    agua                    INT         NULL,
    luz                     INT         NULL,
    impuesto                INT         NULL, -- Copia del impuesto_fijo al crear el registro
    pagado                  TINYINT(1)  NOT NULL DEFAULT 0,
    total                   INT         NOT NULL,
    porcentaje_aumento_usado DOUBLE NULL, -- Legacy: se sigue escribiendo; el historial de aumentos es la fuente de verdad

    PRIMARY KEY (id_registros_mensuales),

    CONSTRAINT uq_registros_contrato_anio_mes
        UNIQUE (id_contratos, anio, mes),

    CONSTRAINT fk_registros_contratos
        FOREIGN KEY (id_contratos)
        REFERENCES contratos (id_contratos)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    INDEX idx_registros_anio_mes (anio, mes)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- Tabla: historial_aumentos
-- Fuente de verdad del historial de aumentos.
-- Estados: PENDIENTE (generado, aún no cobrado, modificable)
--          / CONSOLIDADO (cobrado, inmutable).
-- *_propuesto: monto calculado originalmente por el sistema (congelado).
-- *_aplicado: monto final efectivo (puede haberse modificado mientras
--             PENDIENTE; el backend recalcula los % aplicados).
-- Campos ICL: NULL cuando el aumento es MANUAL.
-- Campos de expensa: NULL cuando el contrato no cobra expensa.
-- -------------------------------------------------------------
CREATE TABLE historial_aumentos (
    id_historial_aumentos               INT             NOT NULL AUTO_INCREMENT,
    id_contratos                        INT             NOT NULL,
    anio                                INT             NOT NULL,
    mes                                 INT             NOT NULL,
    estado                              VARCHAR(20)     NOT NULL DEFAULT 'PENDIENTE',
    tipo_aumento                        VARCHAR(20)     NOT NULL, -- MANUAL, ICL o SIN_AUMENTO
    alquiler_anterior                   INT             NOT NULL,
    alquiler_propuesto                  INT             NOT NULL,
    alquiler_aplicado                   INT             NOT NULL,
    porcentaje_alquiler_propuesto       DOUBLE          NOT NULL,
    porcentaje_alquiler_aplicado        DOUBLE          NOT NULL,
    expensa_anterior                    INT                 NULL,
    expensa_propuesta                   INT                 NULL,
    expensa_aplicada                    INT                 NULL,
    porcentaje_expensa_propuesto        DOUBLE              NULL,
    porcentaje_expensa_aplicado         DOUBLE              NULL,
    coeficiente_icl                     DOUBLE              NULL,
    icl_inicial                         DOUBLE              NULL,
    icl_final                           DOUBLE              NULL,
    fecha_icl_inicial                   DATE                NULL,
    fecha_icl_final                     DATE                NULL,
    fecha_creacion                      DATETIME        NOT NULL,
    fecha_actualizacion                 DATETIME        NOT NULL,
    fecha_consolidacion                 DATETIME            NULL,

    PRIMARY KEY (id_historial_aumentos),

    CONSTRAINT uq_historial_contrato_periodo
        UNIQUE (id_contratos, anio, mes),

    CONSTRAINT ck_historial_mes_rango
        CHECK (mes >= 1 AND mes <= 12),

    CONSTRAINT fk_historial_aumentos_contratos
        FOREIGN KEY (id_contratos)
        REFERENCES contratos (id_contratos)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    INDEX idx_historial_periodo (anio, mes)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

> Nota adicional: la tabla SQLite real, generada por SQLModel, no incluye los
> índices explícitos ni las FK con acciones ON del DDL; esas protecciones hoy
> las aplica el código de negocio. No ejecutar este DDL sobre la base de la
> aplicación (motor distinto).
