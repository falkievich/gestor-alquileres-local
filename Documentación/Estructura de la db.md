```sql
-- =============================================================
-- gestor-alquileres-local — Script MySQL completo
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
    expensa_base_inicial        INT                 NULL, -- Expensa con la que comenzó el contrato (histórica, no se modifica por aumentos)
    alquiler_base_actual        INT             NOT NULL, -- Monto que se cobra actualmente; base de cálculo de los próximos aumentos
    expensa_base_actual         INT                 NULL, -- Expensa que se cobra actualmente; base de cálculo de los próximos aumentos
    tipo_aumento                VARCHAR(20)     NOT NULL DEFAULT 'MANUAL', -- Puede ser: MANUAL (utiliza porcentaje_aumento) o ICL (utiliza API del BCRA)
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

    INDEX idx_contratos_departamentos (id_departamentos),
    INDEX idx_contratos_inquilinos    (id_inquilinos),
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
    impuesto                INT         NULL, -- Copia del impuesto_fijo del contrato al crear el registro (fijo, sin aumentos)
    pagado                  TINYINT(1)  NOT NULL DEFAULT 0,
    total                   INT         NOT NULL,
    porcentaje_aumento_usado DOUBLE NULL, -- Se completa únicamente cuando realmente ocurre un aumento. Si ese mes no hubo aumento: NULL

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
-- Fuente de verdad del historial de aumentos (desde el Punto 1).
-- El historial antiguo NO se migra: la tabla empieza de cero.
-- Estados: PENDIENTE (generado, aun no cobrado) / CONSOLIDADO (cobrado, inmutable).
-- *_propuesto: monto calculado originalmente por el sistema (congelado).
-- *_aplicado: monto final a cobrar (en esta etapa siempre == propuesto).
-- Campos ICL: NULL cuando el aumento es MANUAL.
-- Campos de expensa: NULL cuando el contrato no cobra expensa.
-- -------------------------------------------------------------
CREATE TABLE historial_aumentos (
    id_historial_aumentos               INT             NOT NULL AUTO_INCREMENT,
    id_contratos                        INT             NOT NULL,
    anio                                INT             NOT NULL,
    mes                                 INT             NOT NULL,
    estado                              VARCHAR(20)     NOT NULL DEFAULT 'PENDIENTE',
    tipo_aumento                        VARCHAR(20)     NOT NULL,
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
