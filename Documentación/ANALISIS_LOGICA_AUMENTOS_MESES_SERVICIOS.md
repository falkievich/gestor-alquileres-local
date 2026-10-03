# Análisis técnico — Lógica de aumentos, meses, servicios e historial (estado actual)

Documento generado a partir de lectura directa del código (sin modificaciones).
Fecha del análisis: 25/09/2026. Stack: FastAPI + SQLModel/SQLite (backend), React + TS + Tailwind (frontend).

Objetivo: documentar **cómo funciona realmente hoy** Depto Manager para que otra persona
pueda diseñar sin suposiciones estas features futuras:

1. Aumentos automáticos que puedan ser corregidos manualmente.
2. Contratos sin aumentos.
3. Consulta/preparación de meses futuros desde Dashboard/Servicios.
4. Un historial de aumentos persistente y correctamente modelado.

Convención de la sección final: **[HECHO]** = verificado en el código; **[RIESGO]** =
consecuencia detectada del diseño actual; **[POSIBLE]** = alternativa futura (no elegida).

---

## 1. Modelo de datos actual

Solo existen dos tablas reales de negocio: `contratos` y `registros_mensuales`
(más `departamentos` e `inquilinos` de soporte). **No existe tabla de aumentos ni de
servicios**: los servicios viven como columnas del registro mensual y los aumentos
como mutaciones del contrato + una columna del registro.

### 1.1 Tabla `contratos` (backend/app/model/models.py, clase `Contrato`)

| Campo | Tipo | Representa | Rol |
|---|---|---|---|
| `id_contratos` | PK | identificador | — |
| `id_departamentos` | FK → departamentos | departamento alquilado | relación |
| `id_inquilinos` | FK → inquilinos | inquilino | relación |
| `fecha_inicio` / `fecha_fin` | date | vigencia contractual | configuración |
| `estado` | str (default `'activo'`) | `'activo'` / `'finalizado'` | estado actual |
| `alquiler_base_inicial` | int nullable | monto con el que comenzó el contrato | **histórico** (no se modifica por aumentos) |
| `expensa_base_inicial` | int nullable | expensa inicial | **histórico** |
| `alquiler_base_actual` | int NOT NULL | monto que se cobra hoy; **base de cálculo de aumentos** | **estado actual** (mutable) |
| `expensa_base_actual` | int nullable | expensa que se cobra hoy | **estado actual** |
| `impuesto_fijo` | int nullable | monto fijo mensual, **no** participa de aumentos | configuración |
| `tipo_aumento` | str (`'MANUAL'`/`'ICL'`, default `'MANUAL'`) | modo de cálculo del aumento | configuración |
| `porcentaje_aumento` | float (default 0.0) | % usado cuando tipo = MANUAL | configuración |
| `periodicidad_aumento_meses` | int (default 3) | meses entre aumentos | configuración |
| `fecha_ultimo_aumento` | date nullable | fecha del último aumento aplicado (la carga el usuario en contratos "en curso"; el sistema la **reescribe** tras cada aumento aplicado) | **estado actual** (base del próximo cálculo) |
| `ultimo_aumento_anio` / `ultimo_aumento_mes` | int nullable | mes del último aumento aplicado por el sistema | **histórico** (solo informativo hoy) |
| `cobra_expensa` / `cobra_agua` / `cobra_luz` | bool | qué cobra el contrato | configuración |
| `archivo_blob` / `archivo_nombre` | bytes/str | adjunto del contrato | — |

Constraints reales: FKs declaradas (`ON UPDATE CASCADE`, `ON DELETE RESTRICT` según el
script de diseño). **En la DB SQLite real las FK no se enforcean** (ver §10): se puede
borrar un contrato y quedan registros huérfanos.

### 1.2 Tabla `registros_mensuales` (clase `RegistroMensual`)

| Campo | Representa | Rol |
|---|---|---|
| `id_registros_mensuales` | PK | — |
| `id_contratos` | FK al contrato | relación (1 registro por contrato/mes) |
| `anio`, `mes` | período del cobro | clave lógica |
| `alquiler_calculado` | alquiler congelado al crear el registro | **histórico del mes** |
| `expensa_calculada` | expensa congelada (o None) | **histórico del mes** |
| `alquiler_override` / `expensa_override` | ajuste manual absoluto (delta calculado en frontend); None = sin ajuste | modificación del mes |
| `nota_override` | motivo del ajuste | — |
| `agua` / `luz` | montos de servicios cargados (None = pendiente) | dato del mes |
| `impuesto` | copia congelada de `contrato.impuesto_fijo` al crear el registro | dato del mes |
| `pagado` | bool, cobro registrado | estado actual del mes |
| `total` | suma efectiva: alquiler efectivo + expensa efectiva + agua + luz + impuesto | derivado (se recalcula en varias operaciones) |
| `porcentaje_aumento_usado` | % aplicado si en ese mes ocurrió un aumento; None si no | **única marca histórica de aumentos** |

**[HECHO] No hay constraint UNIQUE** `(id_contratos, anio, mes)` en el modelo real
(existía solo en el script de diseño MySQL). La unicidad se maneja con
check-then-create en `get_or_create_registro` (ver §3).

### 1.3 Relaciones y lectura combinada

- `Contrato 1 → N RegistroMensual` (lógica, no enforceada).
- Dashboard/Servicios/Aumentos arman filas combinando `Contrato` + `RegistroMensual` +
  `Departamento` + `Inquilino` en dicts (no hay schemas de respuesta anidados formales).

### 1.4 Migraciones automáticas

`backend/app/db.py`:
- `create_db_and_tables()` → `SQLModel.metadata.create_all(engine)` (crea tablas si no existen; **no agrega columnas a tablas existentes**) + `_migrar_columnas_contratos()`.
- `_migrar_columnas_contratos()`: `PRAGMA table_info(contratos)` y `PRAGMA table_info(registros_mensuales)` + `ALTER TABLE ADD COLUMN` si falta alguna de: `alquiler_base_inicial`, `expensa_base_inicial`, `impuesto_fijo` (contratos) e `impuesto` (registros). Corre en el `startup` de FastAPI (`app/main.py`, `on_startup`).
- No hay Alembic ni versionado de migraciones: es una lista manual de "si no existe, ALTER".

---

## 2. Flujo completo de aumentos

Archivo central: `backend/app/service/mes_service.py`.

### 2.1 ¿Cuándo corresponde un aumento? — `corresponde_aumento(contrato, anio, mes)` (líneas ~241-268)

Orden de decisión verificado:

1. `periodicidad_aumento_meses == 0` → nunca. **[HECHO]** (hoy el frontend exige ≥ 1, pero el backend acepta 0).
2. Si `tipo_aumento == 'MANUAL'` y `porcentaje_aumento == 0` → nunca (**así se representa hoy un "contrato sin aumento"**, ver §7).
3. Base temporal, por prioridad:
   a. `fecha_ultimo_aumento` (si no es None) — caso contrato "en curso" o aumento ya aplicado;
   b. si no, `ultimo_aumento_anio/mes` (aumento aplicado por el sistema sin fecha);
   c. si no, `fecha_inicio`.
   Con a o b: corresponde si `meses_desde_base >= periodicidad`.
   Con c (sin historial): corresponde si `meses_desde_inicio > 0 AND meses_desde_inicio % periodicidad == 0` (comportamiento heredado; puede NO coincidir con la regla anterior).
4. **[HECHO] `corresponde_aumento` NO evalúa `fecha_fin`**: el vencimiento no bloquea la aplicación del aumento (solo se informa en la UI, ver §2.5).

### 2.2 Aplicación — `aplicar_aumento_si_corresponde(session, contrato, anio, mes)` (~271-320)

- Si no corresponde → `None` (sin efectos).
- Factor:
  - **MANUAL**: `factor = 1 + porcentaje_aumento/100`; `porcentaje_usado = porcentaje_aumento`.
  - **ICL**: llama `_calcular_icl_aumento(contrato, base_anio, base_mes, anio, mes)` (~71-182):
    - Período consultado al BCRA (`_fetch_icl_bcra`, API `https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/40`): desde el día 1 del mes base hasta el último día del mes anterior a la vigencia.
    - `coeficiente = ICL_final / ICL_inicial` (si el BCRA aún no publicó el valor final → `icl_pendiente = True` y **no se aplica nada**, el contrato queda intacto; muestra `ultima_fecha_disponible_bcra` y `dias_faltantes`).
    - Si hay error de API → también `icl_pendiente` con el mensaje de error.
- Mutaciones (solo si el cálculo salió bien):
  - `contrato.alquiler_base_actual = round(alquiler_base_actual * factor)` ← **única forma en que se modifica el alquiler actual**.
  - Si `cobra_expensa` y `expensa_base_actual is not None`: `expensa_base_actual = round(expensa_base_actual * factor)`.
  - `ultimo_aumento_anio = anio`; `ultimo_aumento_mes = mes`.
  - **`fecha_ultimo_aumento = date(anio, mes, 1)`** ← se reescribe (fix de la iteración 1: evitaba doble aplicación al reabrir el Dashboard en el mes de vigencia).
  - Commit inmediato.
- `impuesto_fijo` **no** se multiplica nunca. `*_base_inicial` **no** se tocan nunca.
- No registra en ninguna tabla "histórico de aumentos" (ver §6).

### 2.3 Próximo aumento (solo lectura/UI) — `calcular_proximo_aumento(contrato)` (~321-435)

- Devuelve `proximo_anio/proximo_mes = base + periodicidad`, `alquiler_actual`, `alquiler_nuevo`, `expensa_actual/nueva`, `porcentaje`, `requires_fecha_ultimo` (solo informativo), `tipo_aumento`, `icl_pendiente`, y `aumento_fuera_de_contrato` = `(proximo_anio, proximo_mes) > (fecha_fin.year, fecha_fin.month)` — agregado en iteración 2, **solo informativo** (no bloquea nada).
- Casos sin aumento posible (`periodicidad == 0`, o MANUAL con 0%) → `proximo_* = None`, "Sin aumento".
- Consumido por `GET /aumentos/` (`routers/aumentos.py::vista_aumentos`) y pintado por `frontend/src/pages/Aumentos.tsx`.

### 2.4 Qué monto se usa como base

- Para **aplicar** el aumento: siempre `alquiler_base_actual` / `expensa_base_actual` **en el momento** de ejecutar `aplicar_aumento_si_corresponde` (es decir, el estado del contrato al abrir el Dashboard/Servicios ese mes).
- Para **proyectar** (Aumentos): ídem, leído en vivo.
- Si el usuario edita `alquiler_base_actual` manualmente (PUT de contrato), los cálculos futuros usan el nuevo valor. No hay registro de "a cuánto estaba antes" salvo lo que quede congelado en registros mensuales ya creados.

### 2.5 ¿Qué pasa si el aumento cae fuera de `fecha_fin`? / contratos por vencer

- **[HECHO]** `aumento_fuera_de_contrato` solo se calcula y se **muestra** en Aumentos (card roja "Sin más aumentos", badge). `aplicar_aumento_si_corresponde` / `corresponde_aumento` **no consultan `fecha_fin`**: si el contrato sigue `estado = 'activo'` (no se cerró manualmente) y se abre el Dashboard en el mes del vencimiento o después, el registro se genera igual y **el aumento igualmente se aplicaría** si `corresponde_aumento` da True.
- **[HECHO]** El Dashboard lista contratos con `estado == 'activo'` sin filtrar por `fecha_fin`: un contrato vencido (que la UI etiqueta "Vencido") **sigue generando cobros** hasta que alguien lo cierre manualmente (POST `/contratos/{id}/cerrar`).
- El estado "Por vencer" (≤ 3 meses de calendario hasta el mes de `fecha_fin`) es solo un badge, sin efecto en cálculos.

### 2.6 `porcentaje_aumento_usado` — cuándo y cómo se guarda

- Se guarda en el **registro mensual** (no en una tabla de aumentos) desde `preparar_registro_mes` (ver §3): si `aplicar_aumento_si_corresponde` devolvió un % y el registro aún no tenía `porcentaje_aumento_usado`, se escribe ahí.
- Funciones/endpoint participantes: `mes_service.aplicar_aumento_si_corresponde`, `mes_service.preparar_registro_mes`, `mes_service.corresponde_aumento`, `mes_service._calcular_icl_aumento`, `mes_service.calcular_proximo_aumento`, `routers/dashboard.py::get_dashboard`, `routers/servicios.py::listar_pendientes`, `routers/aumentos.py::vista_aumentos` y `::historial_aumentos`, `crud/contratos.py::update_contrato` (sincronización de montos, no aplica aumentos).

---

## 3. Creación y preparación de registros mensuales (`mes_service.py`)

### 3.1 Creación perezosa (lazy)

- **[HECHO]** No hay cron ni generación por lotes: el registro del mes se crea la **primera vez que alguien lo pide**:
  - abrir el **Dashboard** (`GET /dashboard/mes-actual`) → por cada contrato activo;
  - abrir **Servicios** (`GET /servicios/pendientes`) → solo para contratos que cobran agua/luz (desde la iteración 2, para que aparezcan sin pasar por el Dashboard).
- Ambos llaman a `preparar_registro_mes(session, contrato, anio, mes)` (~líneas 246-273), que:
  1. `aplicar_aumento_si_corresponde(session, contrato, anio, mes)` → **efecto secundario: puede mutar el contrato y commitear**;
  2. `session.refresh(contrato)`;
  3. `get_or_create_registro(...)`.

### 3.2 `get_or_create_registro(session, contrato, anio, mes)` (~187-217)

- Busca con `crud_registros.get_registro(session, id_contrato, anio, mes)` (query por igualdad).
- Si no existe, crea `RegistroMensual` con valores **congelados**:
  - `alquiler_calculado = contrato.alquiler_base_actual` (post-aumento si se aplicó en el paso 1);
  - `expensa_calculada = contrato.expensa_base_actual` (si `cobra_expensa`);
  - `impuesto = contrato.impuesto_fijo`;
  - `agua = None`, `luz = None` (pendientes), `pagado = False`;
  - `total = calcular_total(alquiler, expensa, None, None, impuesto)`.
- **[HECHO]** La protección contra duplicados es solo check-then-create; **no hay UNIQUE en DB** (SQLite tampoco enforcea FK). En un escenario de concurrencia podrían crearse dos registros del mismo contrato/mes (hoy la app es mono-usuario local, riesgo teórico).

### 3.3 Efectos secundarios de "preparar un mes"

Preparar (Dashboard o Servicios) puede:
1. Aplicar un aumento (muta `alquiler_base_actual`, `expensa_base_actual`, `ultimo_aumento_*`, `fecha_ultimo_aumento`) y commitear.
2. Crear el registro congelando los valores post-aumento.
3. Marcar `porcentaje_aumento_usado` en el registro (si correspondió y no estaba).

**[HECHO] Respuesta a la pregunta clave: sí — consultar/preparar un mes futuro HOY modificaría el estado actual del contrato.** `preparar_registro_mes` es agnóstico del año/mes: si se le pasa octubre 2026 con aumento pendiente para ese mes, aplicaría el aumento **antes de tiempo**, mutaría el contrato y luego el Dashboard de septiembre seguiría mostrando el registro de septiembre (que ya existe con el valor pre-aumento), generando una inconsistencia entre "próximo aumento mostrado" y contrato real.

### 3.4 Recálculo de total en cada lectura

`GET /dashboard/mes-actual` recalcula `total` con los valores efectivos y lo persiste si difiere (`dashboard.py` ~55-70). `override` y `servicios/guardar` también recalculan. `total` es derivado, no fuente de verdad.

---

## 4. Dashboard

Endpoint: `GET /dashboard/mes-actual` (`routers/dashboard.py::get_dashboard`).

- **Año/mes**: `get_mes_actual()` (`mes_service.py` ~13-15) → `date.today().year/.month`. **[HECHO] Depende de la fecha del sistema; el endpoint no acepta parámetros** (técnicamente no puede recibir otro año/mes hoy).
- Por cada contrato con `estado == 'activo'`:
  - skip si `fecha_inicio > hoy` (no muestra contratos que aún no empezaron). **No** hay filtro por `fecha_fin` (ver §2.5).
  - `preparar_registro_mes(...)` (ver §3).
  - Valores efectivos: `alq = alquiler_override ?? alquiler_calculado`; `exp = expensa_override ?? expensa_calculada`.
  - `total = calcular_total(alq, exp, registro.agua, registro.luz, registro.impuesto)`; persiste el total si cambió.
  - `estado_servicios = calcular_estado_servicios(contrato, registro)` → `"Pendiente"` si `(cobra_agua y agua is None)` o `(cobra_luz y luz is None)`; si no `"OK"`.
  - `vencido = contrato.fecha_fin < hoy` (solo badge).
- Respuesta: lista de dicts con `contrato (ContratoRead)`, `registro (RegistroMensualRead)`, `departamento`, `inquilino`, `estado_servicios`, `vencido`, `anio`, `mes`, `total`.
- **Pagado**: `POST /dashboard/registros/{id}/pagado` rechaza si `estado_servicios != "OK"` (no se puede cobrar con servicios pendientes) y setea `pagado = True`. `POST .../desmarcar-pagado` lo revierte (y el mes vuelve a aparecer en Servicios si tenía pendientes).
- **Overrides**: `POST /dashboard/registros/{id}/override` recibe **valores absolutos** (`alquiler_override`, `expensa_override`, `nota_override` como query params; el frontend convierte el delta en absoluto). `crud_registros.update_registro` usa `model_dump(exclude_unset=True)`:
  - **[HECHO] Nuance**: el frontend solo envía los campos con delta distinto de vacío; los no enviados llegan como `None` explícito y **resetean** ese override (ej.: guardar un ajuste con solo alquiler borra un override de expensa previo). "Restaurar original" envía sin params → setea los tres overrides en `None` y recalcula el total.
- Historial de pagos: `GET /dashboard/historial-pagos` (filtros `anio`, `mes`, `id_inquilinos`; solo `pagado == True`; orden descendente). Los montos que muestra usan la misma regla `override ?? calculado`.

---

## 5. Servicios

Endpoint(s) en `routers/servicios.py`:

- **Listado** `GET /servicios/pendientes`:
  - Mes: `get_mes_actual()` (hoy, inmodificable).
  - Contratos: `get_contratos_activos` (`estado == 'activo'`), filtrados a los que cobran agua y/o luz.
  - Para cada uno: `preparar_registro_mes(session, contrato, anio, mes)` → genera el registro si no existe (con los mismos efectos secundarios que el Dashboard, incluido aplicar el aumento si correspondía).
  - Excluye registros `pagado == True`.
  - Incluye tanto pendientes como **cargados**, con campo `estado`: `"Pendiente"` / `"OK"` (`calcular_estado_servicios`).
- **Guardado/edición** `POST /servicios/guardar` (query params `id_registro`, `agua`, `luz`):
  - Rechaza con 400 si `registro.pagado` (un mes cobrado no se edita).
  - Asigna solo los parámetros `is not None` (el frontend no envía campos vacíos) → **[HECHO] no se puede "vaciar" un valor ya cargado**; una vez cargado, siempre queda un número (el estado "OK" no se revierte desde la UI).
  - Recalcula `total` con overrides + agua + luz + impuesto.
- **Relación con Dashboard**: comparten la preparación vía `preparar_registro_mes`; el Dashboard solo *muestra* el estado (OK/Pendiente) y bloquea el cobro si hay pendientes.
- **Servicios de meses pagados**: desaparecen del listado y el endpoint rechaza editarlos; no hay vista para corregirlos (requiere desmarcar el cobro).
- **Si hoy intentáramos cargar servicios de un mes futuro**: no hay camino. El listado solo prepara el mes de `get_mes_actual()`; `guardar` opera sobre un `id_registro` existente — si existiera un registro futuro creado por otra vía, el guardado lo aceptaría sin validar el período (no hay chequeo de que el registro pertenezca al mes actual).

---

## 6. Historial de aumentos actual (punto clave)

**[HECHO] No existe tabla de historial de aumentos.** El historial de la UI se **reconstruye** desde `registros_mensuales`.

### Cómo funciona hoy

- Endpoint: `GET /aumentos/historial` (`routers/aumentos.py::historial_aumentos`).
- Query: `RegistroMensual` donde `porcentaje_aumento_usado IS NOT NULL` (+ filtros opcionales `anio`, `mes`, `id_inquilinos` vía join manual con contrato).
- Cómo identifica que hubo aumento: **la marca `porcentaje_aumento_usado` escrita por `preparar_registro_mes`** en el registro del mes de vigencia. No hay otra fuente.
- Por cada registro arma:
  - mes/año: del propio registro;
  - departamento/inquilino: join a través del contrato (`session.get` por `id_departamentos` / `id_inquilinos`);
  - tipo MANUAL/ICL: **`contrato.tipo_aumento` leído HOY** (estado actual del contrato);
  - % aplicado: `registro.porcentaje_aumento_usado`;
  - alquiler anterior: busca el registro del **mes inmediatamente anterior** del mismo contrato (`mes-1`, con ajuste de año) y usa `alquiler_override ?? alquiler_calculado`;
  - alquiler nuevo: `registro.alquiler_override ?? registro.alquiler_calculado` del mes del aumento;
  - diferencia: calculada en el frontend (`alquiler_nuevo - alquiler_anterior`).
- Orden: descendente por (anio, mes).

### Por qué aparecen N/D y qué se pierde

- **Alquiler anterior `N/D`**: si no existe registro del mes anterior (ej.: el contrato se cargó a mitad de vigencia, o el mes anterior nunca se abrió en el Dashboard), no hay de dónde tomarlo. El valor pre-aumento no se guarda en ningún otro lado.
- **Información que NO se guarda hoy y no puede reconstruirse después**:
  - la fecha precisa del aumento (solo se sabe año/mes);
  - la expensa anterior y la expensa nueva (no hay historial de expensas);
  - el `tipo_aumento` vigente al momento del aumento (se muestra el actual);
  - el `porcentaje_aumento` configurado vs. el usado en ICL (para ICL se guarda el % efectivo, pero no el coeficiente ni los valores ICL del período);
  - quién/cuándo se aplicó (no hay timestamp ni auditoría);
  - el valor del alquiler anterior si faltó el registro previo.
- **Limitaciones del diseño**:
  - el historial depende de que el registro del mes se haya **generado** (si un mes no se abrió nunca en Dashboard/Servicios, su aumento… no puede existir, porque la aplicación ocurre solo al preparar);
  - si un registro se borra (hoy no hay UI, pero la FK no lo impide), el aumento desaparece del historial;
  - `alquiler_anterior` puede estar contaminado por un override del mes anterior (usa `override ?? calculado`, no el valor contractual);
  - no hay distinción entre "aumento automático aplicado" y "corrección manual" (feature futura 1).

### ¿Tendría sentido una tabla específica? (solo opinión técnica, sin implementar)

Sí: el modelo actual guarda el aumento como **mutación del contrato + una marca en un registro mensual**, lo que obliga a reconstruir el historial por inferencia (mes anterior) y pierde datos (expensa, fecha exacta, tipo vigente, coeficiente ICL). Una tabla tipo `historial_aumentos` (id, id_contratos, anio, mes de vigencia, fecha de aplicación, tipo, % o coeficiente, alquiler_anterior, alquiler_nuevo, expensa_anterior, expensa_nueva, origen: automático/manual) resolvería la persistencia y permitiría correcciones manuales con trazabilidad. Los datos para poblarla retroactivamente son parciales (solo lo reconstruible hoy).

---

## 7. Contratos cortos y contratos sin aumento

### 7.1 Representación actual de "sin aumento"

- **[HECHO]** La única representación hoy es `tipo_aumento = 'MANUAL'` con `porcentaje_aumento = 0`:
  - `corresponde_aumento` → False siempre;
  - `calcular_proximo_aumento` → "Sin aumento" (`proximo_* = None`);
  - el backend lo acepta por API (el schema no exige > 0).
- **[HECHO]** Pero el **frontend** (iteración 1) exige `% Aumento > 0` cuando MANUAL y `periodicidad > 0`: con la UI actual ya **no se puede crear** un contrato que nunca reciba aumentos (ni con periodicidad 0). El backend sigue siendo tolerante; el formulario no.
- No existe un valor `tipo_aumento = 'SIN_AUMENTO'` ni validación que lo impida a nivel backend.

### 7.2 Contrato corto (ej.: 3 meses, periodicidad 3, próximo aumento después de fecha_fin)

Qué pasa hoy, verificado:

- **Aumentos (UI)**: calcula el próximo aumento igual que cualquier contrato (base + periodicidad) y, desde la iteración 2, lo marca con `aumento_fuera_de_contrato` → card roja "Sin más aumentos". No lo aplica desde esa pantalla (es solo lectura).
- **Dashboard/Servicios**: `aplicar_aumento_si_corresponde` **no consulta `fecha_fin`**. Si el contrato sigue `estado = 'activo'` y el usuario abre el Dashboard en el mes del vencimiento (o después, mientras no lo cierre), el registro se genera y, si `corresponde_aumento` da True para ese mes, **el aumento se aplica aunque el contrato esté terminando/terminado**.
  - Ejemplo concreto: vence el 31/10/2026, último aumento 01/09/2026, periodicidad 3 → próximo aumento mes 12 (diciembre). Si el contrato no se cierra y se abre el Dashboard en diciembre, se aplicaría el aumento y se generaría un cobro de diciembre. **[RIESGO]**: cobro + aumento fuera de vigencia, con la única salvaguarda de que el usuario cierre el contrato manualmente.
- **Restricciones actuales sobre la configuración de aumento**:
  - frontend: `tipo_aumento` obligatorio, `% Aumento` obligatorio (> 0) si MANUAL, `periodicidad` obligatoria (> 0);
  - backend: solo defaults, sin validaciones de coherencia (periodicidad negativa se guardaría; fecha_ultimo_aumento puede ser posterior a fecha_fin, etc.).

### 7.3 Qué partes asumen hoy que TODO contrato tiene aumento

- `ContratoCreate`/`ContratoUpdate`: sin concepto de "sin aumentos" (solo el truco 0%).
- `calcular_proximo_aumento`: rama especial para MANUAL+0% que devuelve "Sin aumento" (la única conciliada).
- UI Aumentos: siempre muestra tarjetas de "próximo aumento"; un contrato 0% aparece con "Sin aumento" (y `aumento_fuera_de_contrato` solo si la fecha cae fuera).
- Validación del modal de Contratos: no admite 0% → **inconsistencia UI/backend** a revisar para la feature "Sin aumento" (habría que decidir: valor explícito `SIN_AUMENTO`, permitir 0% otra vez, o toggle aparte) y auditar todos los `for contrato in contratos_activos` que presuman configuración (dashboard aplica, aumentos lista, historial filtra).

---

## 8. Posibilidad de meses futuros (análisis, sin diseñar)

### 8.1 Acoplamiento actual al mes del sistema

**[HECHO] El core de `mes_service` YA está parametrizado** — estas funciones reciben `anio`/`mes` explícitos:
- `corresponde_aumento(contrato, anio, mes)`
- `aplicar_aumento_si_corresponde(session, contrato, anio, mes)`
- `get_or_create_registro(session, contrato, anio, mes)`
- `preparar_registro_mes(session, contrato, anio, mes)`
- `calcular_total(...)`, `calcular_estado_servicios(...)` (no dependen de fechas)
- `crud_registros.get_registro/create_registro/update_registro`, `get_registros_by_anio_mes`

Lo que está acoplado a "hoy":
- `get_mes_actual()` → `date.today()`, usado por `routers/dashboard.py::get_dashboard` y `routers/servicios.py::listar_pendientes` (y esa es toda la cadena de Router → Service).
- `routers/dashboard.py::get_dashboard` no acepta query params de año/mes.
- Frontend: `Dashboard.tsx` no tiene selector de mes (usa lo que devuelve el endpoint); `Servicios.tsx` muestra el mes del primer registro recibido.
- Guardas parciales: `get_dashboard` salta contratos con `fecha_inicio > hoy` (asume mes actual); `listar_pendientes` asume mes actual para decidir qué preparar; `historial-pagos` sí es parametrizable (filtros anio/mes).
- `marcar_pagado` no valida contra qué mes se cobra (acepta cualquier registro por id).

### 8.2 Efectos secundarios y riesgos de consultar un mes futuro con el código actual

Si mañana se cambiara `get_mes_actual()` o se pasara un mes futuro a los endpoints existentes:
1. **Se aplicarían aumentos por adelantado** (mutación del contrato con commit), porque `preparar_registro_mes` aplica el aumento del mes consultado. El "próximo aumento" del contrato se correría hacia adelante y el Dashboard de septiembre mostraría valores viejos congelados mientras el contrato ya tiene el alquiler de octubre. **Este es el riesgo central.**
2. Se congelarían valores proyectados en registros reales (`alquiler_calculado`, `impuesto`, total), indistinguibles de meses "reales" (no hay flag de proyección).
3. Se podrían cobrar meses futuros (`marcar_pagado` no valida fecha).
4. ICL podría quedar en `icl_pendiente` para meses cuyos datos BCRA no existen → registro creado igual (con el alquiler sin aumentar del momento).
5. La sincronización de ediciones (`_sincronizar_registros_mensuales`) tocaría registros futuros no pagados (comportamiento correcto, pero hoy incluye cualquier mes ≥ actual sin distinción).

### 8.3 Distinciones a tener en cuenta (semántica actual)

Con el diseño actual **no existe** la distinción proyectar/preparar/modificar/cobrar: preparar = congelar valores reales; modificar (override) = ajuste real; cobrar = `pagado = True`. Todo comparte la misma tabla y el mismo flujo. Para meses futuros habría que introducir esa separación (el estado "proyectado" hoy no existe ni tiene representación). Además, la aplicación de aumentos está **metida dentro de la preparación del registro** (`preparar_registro_mes`), por lo que cualquier refactor de meses futuros pasa por desacoplar "calcular/afectar aumento" de "crear registro".

---

## 9. Mapa de archivos y funciones

### Backend

| Archivo | Función/clase | Responsabilidad |
|---|---|---|
| `backend/app/db.py` | `engine`, `create_db_and_tables`, `_migrar_columnas_contratos`, `get_session` | conexión SQLite, migración liviana |
| `backend/app/main.py` | `app`, `on_startup`, montaje de `frontend/dist` | arranque, routers, SPA |
| `backend/app/model/models.py` | `Contrato(+Create/Update/Read)`, `RegistroMensual(+Create/Update/Read)`, `Departamento*`, `Inquilino*` | tablas y schemas |
| `backend/app/service/mes_service.py` | `get_mes_actual` | hoy del sistema |
| | `corresponde_aumento` | ¿toca aumento? |
| | `aplicar_aumento_si_corresponde` | aplica MANUAL/ICL, muta contrato |
| | `_calcular_icl_aumento`, `_fetch_icl_bcra`, `_valor_icl_para_fecha`, `_ultima_fecha_disponible_icl` | ICL BCRA |
| | `calcular_proximo_aumento` | proyección para UI (incl. `aumento_fuera_de_contrato`) |
| | `calcular_alquiler`, `calcular_expensa`, `calcular_total` | montos (total incluye impuesto) |
| | `get_or_create_registro` | lazy + congelado |
| | `preparar_registro_mes` | aumento + registro + marca % (usado por Dashboard y Servicios) |
| | `calcular_estado_servicios` | OK/Pendiente |
| `backend/app/crud/contratos.py` | `create_contrato` (iniciales = actual si no vienen), `update_contrato`, `_sincronizar_registros_mensuales` | CRUD + propagación de ediciones a no pagados sin override |
| | `cerrar_contrato`, `update_blob`, `delete_contrato` | cierre/adjunto/baja |
| `backend/app/crud/registros.py` | `get_registro`, `create_registro`, `update_registro`, `get_registros_by_anio_mes` | persistencia de registros |
| `backend/app/routers/dashboard.py` | `get_dashboard`, `marcar_pagado`, `desmarcar_pagado`, `override_registro`, `get_historial_pagos` | cobros del mes y pagos |
| `backend/app/routers/servicios.py` | `listar_pendientes` (prepara mes), `guardar_servicios` (rechaza pagados) | servicios |
| `backend/app/routers/aumentos.py` | `vista_aumentos` (usa `calcular_proximo_aumento`), `historial_aumentos` (reconstruye desde `registros_mensuales`) | aumentos |
| `backend/app/routers/contratos.py` | listar/crear/actualizar/cerrar/archivo, `tiene-pagos` | contratos |
| `backend/app/routers/departamentos.py`, `inquilinos.py`, `backup.py` | CRUD de soporte, backup | soporte |
| `backend/test/smoke_test_iter1.py` | `check(...)` script | regresión end-to-end |

### Frontend

| Archivo | Responsabilidad |
|---|---|
| `frontend/src/lib/api.ts` | axios: `localhost:8000` en dev, mismo origen en producción |
| `frontend/src/lib/types.ts` | tipos (Contrato, RegistroMensual, DashboardItem, AumentoItem, etc.), formatters |
| `frontend/src/lib/ui.tsx` | `ModalShell`, `Label/Asterisco`, `clasesCampo`, `ErrorCamposModal`, `ToastProvider/useToast` |
| `frontend/src/pages/Dashboard.tsx` | cobros del mes, historial pagados, overrides, ajuste masivo, confirmación de cobro; llama `/dashboard/mes-actual`, `/dashboard/historial-pagos`, `/dashboard/registros/{id}/...`, `/backup/` |
| `frontend/src/pages/Servicios.tsx` | tabla pendientes/cargados; llama `/servicios/pendientes`, `/servicios/guardar` |
| `frontend/src/pages/Contratos.tsx` | alta/edición (en curso, impuesto, badges); llama `/contratos/...` |
| `frontend/src/pages/Departamentos.tsx`, `Inquilinos.tsx` | listados + modales (tabla real desde esta iteración) |
| `frontend/src/pages/Aumentos.tsx` | próximos aumentos + historial; llama `/aumentos/`, `/aumentos/historial` |

---

## 10. Problemas y decisiones pendientes

### 10.1 HECHOS verificados (limitaciones actuales)

1. **No hay tabla de aumentos**: el historial se reconstruye desde `registros_mensuales.porcentaje_aumento_usado` + registro del mes anterior; expensa, fecha exacta, tipo vigente y coeficiente ICL no se guardan.
2. **No hay UNIQUE `(id_contratos, anio, mes)`** en la DB real (solo en el doc de diseño); unicidad por check-then-create.
3. **SQLite no enforcea FKs** (sin `PRAGMA foreign_keys=ON`): borrar contrato deja registros huérfanos (verificado en pruebas reales).
4. `corresponde_aumento` / `aplicar_aumento_si_corresponde` **ignoran `fecha_fin`**: el aumento se aplica aunque el contrato esté vencido, mientras `estado = 'activo'` (cerrar contrato es manual). `aumento_fuera_de_contrato` es solo informativo (UI Aumentos).
5. Dashboard no acepta otro mes: `get_mes_actual()` = `date.today()` en Router → Service.
6. Preparar un mes **puede aplicar aumentos** (efecto secundario de `preparar_registro_mes`): consultas de meses futuros mutarían el contrato.
7. Overrides: guardar un ajuste con un campo vacío **limpia** el override de ese campo (None explícito); el total es derivado y se recalcula en varias rutas.
8. Servicios cargados no se pueden vaciar (el frontend no envía campos vacíos); los meses pagados no admiten edición de servicios.
9. "Sin aumento" = MANUAL + 0% (backend) pero el **frontend exige % > 0** → hoy no es creable por UI.
10. La aplicación de aumentos está acoplada dentro de la preparación del registro (no hay separación calcular/aplicar/generar).

### 10.2 RIESGOS detectados

- **[RIESGO]** Generar/consultar meses futuros con el código actual: aplica aumentos por adelantado, congela proyecciones como datos "reales", permite cobros futuros y puede dejar inconsistencias Dashboard/contrato.
- **[RIESGO]** Contratos vencidos sin cerrar siguen cobrando (y aumentando) indefinidamente.
- **[RIESGO]** Doble creación de registro por carrera (sin UNIQUE) en entornos multi-request.
- **[RIESGO]** El historial de aumentos depende de que el mes se haya preparado: un aumento lógico que nunca se "abrió" no figura; y si se elimina un registro, desaparece del historial.
- **[RIESGO]** `ultimo_aumento_anio/mes` y `fecha_ultimo_aumento` se mantienen por duplicado (el sistema usa primero `fecha_ultimo_aumento`); si se editan a mano de forma inconsistente, los cálculos divergen.

### 10.3 POSIBLES (alternativas a evaluar — no decididas)

- Tabla dedicada `historial_aumentos` (fuente de verdad del aumento aplicado, con origen automático/manual y datos de expensa/ICL) — la que habilitaría correcciones manuales con trazabilidad.
- Desacoplar `preparar_registro_mes` en: (a) calcular/afectar aumento, (b) crear registro, (c) proyectar sin persistir — requisito natural para meses futuros y para "aumentos corregibles".
- Representación explícita de "sin aumentos" (ej. `tipo_aumento = 'SIN_AUMENTO'` o flag) + guardas de `fecha_fin` en la aplicación de aumentos.
- Flag de estado en el registro mensual (`proyectado`/`confirmado`) para distinguir meses futuros preparados de meses reales, + `PRAGMA foreign_keys=ON` y UNIQUE real para la integridad.

### 10.4 Decisiones de negocio a confirmar (preguntas para quien define)

1. ¿El aumento debe aplicarse si el contrato vence ese mismo mes? ¿Y si ya venció pero sigue activo?
2. ¿"Sin aumento" es un tipo nuevo, o se vuelve a permitir MANUAL con 0%?
3. ¿Un aumento aplicado se puede corregir manualmente retroactivamente (y qué pasa con los meses posteriores que ya usaron el nuevo valor)?
4. ¿Los meses futuros son "proyección" (no persistente) o se preparan/congelan como los reales? ¿Se pueden cobrar por adelantado?
5. ¿Qué debe pasar con ICL cuando se consulte un mes futuro cuyos datos BCRA no existen?
6. ¿El historial de aumentos debe ser inmutable (auditoría) o editable por el usuario?

---

## ACTUALIZACIÓN — Punto 1 implementado

Este documento describe el estado PREVIO a la implementación del Punto 1. A partir de esa
implementación quedaron superadas varias limitaciones de este análisis:

- Existe la tabla historial_aumentos como fuente de verdad del historial de aumentos
  (el historial de la UI ya no se reconstruye desde egistros_mensuales).
- Existe el tipo SIN_AUMENTO explícito (ya no depende de MANUAL + 0%).
- La regla de echa_fin está protegida en backend (no solo visual).
- El ciclo de vida de un aumento es PENDIENTE → CONSOLIDADO (al cobrar), con
  propuesta congelada ante cambios de configuración posteriores.
- La función "Desmarcar pagado" fue eliminada (un cobro es definitivo).
- Los campos porcentaje_aumento_usado, ultimo_aumento_* y echa_ultimo_aumento
  se mantienen como legacy de compatibilidad.
