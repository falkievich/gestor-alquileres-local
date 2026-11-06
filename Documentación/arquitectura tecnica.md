# Arquitectura técnica — Depto Manager

Este documento explica CÓMO está implementado internamente el sistema.
El QUÉ (reglas de negocio funcionales) está en `especificacion funcional.md`,
el modelo de datos en `modelo de datos.md` y las convenciones visuales en
`convenciones ui.md`.

---

## Stack

### Frontend

| Pieza | Versión | Uso |
| --- | --- | --- |
| React | ^19 | UI |
| React DOM | ^19 | render |
| TypeScript | ~5.9 | lenguaje |
| Vite | ^8 (beta) | build tool y dev server |
| Tailwind CSS | ^4 | estilos (plugin `@tailwindcss/vite`) |
| Axios | ^1.x | HTTP client |
| Lucide React | ^0.577 | íconos |
| react-router-dom | ^7 | navegación por pestañas |

Build de producción: `tsc -b && vite build` → salida en `frontend/dist/` (la
sirve el backend FastAPI).

### Backend

| Pieza | Versión | Uso |
| --- | --- | --- |
| Python | 3.13 (embebido en el portable) | runtime |
| FastAPI | 0.111 | framework HTTP |
| SQLModel | 0.0.19 | ORM (models + Pydantic schemas) |
| SQLAlchemy | 2.0 (dependencia de SQLModel) | motor de acceso |
| Pydantic | 2.x | validación y schemas |
| Uvicorn | 0.29 | servidor ASGI |
| httpx | 0.27 | llamada a la API del BCRA |
| python-multipart | 0.0.9 | upload de adjuntos |
| aiofiles | 23.2.1 | I/O de archivos |

### Base de datos

- **SQLite** (archivo local) en `base_de_datos/alquileres.sqlite`.
- Acceso vía SQLModel/SQLAlchemy; `check_same_thread=False`.
- Sin servidor externo; el archivo es portable y copiable.

---

## Organización del código

```
backend/
├── app/
│   ├── main.py            # app FastAPI, CORS, routers, frontend estático, arranque portable
│   ├── db.py              # engine SQLite, rutas, create_db_and_tables + migraciones aditivas
│   ├── model/models.py    # tablas SQLModel + schemas Pydantic (Create/Update/Read)
│   ├── crud/              # acceso a datos por entidad (contratos, registros, historial_aumentos, ...)
│   ├── service/mes_service.py  # motor de negocio: registros mensuales, aumentos, ICL, vigencia
│   └── routers/           # endpoints por área
└── test/                  # smoke tests (scripts Python de verificación)

frontend/
├── src/
│   ├── App.tsx            # layout + rutas (BrowserRouter, NavLink por pestaña)
│   ├── index.css          # Tailwind + estilos de impresión + clase .modal-grande
│   ├── lib/
│   │   ├── api.ts         # axios (baseURL según entorno)
│   │   ├── types.ts       # interfaces, tipos de union, constantes (MESES, PISOS), helpers de formato
│   │   └── ui.tsx         # ModalShell, ToastProvider, Label/Asterisco, ErrorCamposModal
│   └── pages/             # Dashboard, Departamentos, Inquilinos, Contratos, Servicios, Aumentos
└── dist/                  # build de producción (servido por FastAPI en modo portable)
```

Responsabilidades:

- **routers/** — endpoints HTTP, validaciones de entrada, códigos de error.
  La lógica de negocio pesada vive en `service/mes_service.py` (aumentos, ICL,
  registros, vigencia) y en `crud/contratos.py` (sincronización al editar y
  cierre).
- **crud/** — persistencia con SQLModel; usan `model_dump(exclude_unset=True)`
  para updates parciales.
- **model/models.py** — cada tabla define además sus schemas `*Create`,
  `*Update` y `*Read` de Pydantic.
- **db.py** — crea la carpeta y el archivo de DB, `SQLModel.metadata.create_all`
  y migraciones aditivas de columnas al arrancar.

### Servido del frontend

- `main.py` monta `/assets` con StaticFiles y un catch-all `GET /{path}` que
  sirve los archivos de `frontend/dist` (fallback a `index.html`, SPA).
- En desarrollo, Vite corre en 5173 con CORS para `localhost:5173/3000`.
- La API expone además `GET /health` y la documentación automática en
  `http://localhost:8000/docs`.

---

## Flujo mensual de registros

### Mes actual

- `get_mes_actual()` devuelve `(hoy.year, hoy.month)` usando la fecha del
  sistema (sin zona horaria especial).

### Creación lazy de registros mensuales

- No hay cron ni generación masiva: el registro de un (contrato, año, mes) se
  crea la **primera vez que se pide ese mes**, en `GET /dashboard/mes-actual`
  o `GET /servicios/pendientes`, ambos vía `preparar_registro_mes()`.
- `get_or_create_registro()` congela al crear: `alquiler_calculado =
  contrato.alquiler_base_actual`, `expensa_calculada = expensa_base_actual`
  (si cobra expensa), `impuesto = contrato.impuesto_fijo` y `total` con agua y
  luz vacía. Queda histórico a partir de ese momento.
- **Prevención de duplicados:** check-then-create con consulta por
  (id_contratos, anio, mes). La app es mono-usuario local.

### Congelamiento y recálculo del total

- `total` es **derivado, no fuente de verdad**: se recalcula en cada operación
  y se persiste si cambió.
  Fórmula común: `total = alquiler_efectivo + expensa_efectiva + agua + luz +
  impuesto` (solo sumandos no-None), con `efectivo = override ?? calculado`.
- `total_efectivo_registro(registro)` (mes_service) es la **única** implementación
  de esa fórmula: la usan GET `dashboard/mes-actual` (frescos y atrasados),
  `override`, `servicios/guardar`, la sincronización por edición de contrato y
  las dos funciones de aumentos. Es pura: no persiste nada.

### Overrides

- `alquiler_override` / `expensa_override` son **valores absolutos**; el
  frontend trabaja con deltas (en la UI se edita el delta; en DB queda el
  absoluto: `override = calculado + delta` en el masivo), y al abrir el modal
  se reconstruye el delta (`override - calculado`).
- `RegistroMensualUpdate` usa `exclude_unset=True`; el endpoint `override`
  toma los valores por **query params** (pueden ser `None` → limpia el
  override). "Restaurar" envía vacío y limpia los tres campos. Por eso el
  ajuste masivo reenvía el `expensa_override` y la nota existentes, y suma el
  delta al alquiler efectivo (`override ?? calculado`).
- Cuando cambia el monto base de un registro (edición del contrato, aumento
  aplicado tarde, re-base o modificación de un aumento), el override
  **conserva su diferencia** con el calculado: todo pasa por
  `fijar_montos_calculados(registro, alquiler, expensa)` (mes_service), que
  desplaza el override por `nuevo - anterior` y recalcula el total. Un
  override en 0 (mes bonificado) queda en 0 y nunca queda negativo.

### Recalculación al editar contrato

`crud/contratos.py → update_contrato` hace, en este orden:

1. Compara el payload contra el contrato para saber si cambiaron realmente
   `alquiler_base_actual` y/o `expensa_base_actual` (no alcanza con que vengan
   en el body: el frontend los manda siempre).
2. Aplica los campos y commitea.
3. Si cambió algún monto, `rebasar_aumento_pendiente` (mes_service) re-calcula
   el aumento PENDIENTE del contrato — ver abajo.
4. `_sincronizar_registros_mensuales` propaga el `*_base_actual` final y el
   `impuesto_fijo` a los registros **no pagados, del mes actual en adelante y
   dentro de la vigencia** (con `fijar_montos_calculados`: los overrides
   conservan su diferencia). Meses pagados y meses anteriores nunca se
   modifican. Además limpia (`None`) `expensa_calculada` + `expensa_override`,
   `agua` y `luz` de esos registros cuando el contrato dejó de cobrar el
   concepto: es el único caso en que se toca un override, porque si no el
   `total` seguiría sumando un monto que la UI ya no muestra.

`ContratoUpdate` usa `exclude_unset=True`, así que un campo ausente del JSON no
se toca. Para poder **vaciar** los opcionales, el frontend manda `null`
explícito en `impuesto_fijo`, `expensa_base_actual` y `fecha_ultimo_aumento`
(`undefined` se omite al serializar y el valor viejo nunca se borraría).
`alquiler_base_inicial` / `expensa_base_inicial` se omiten a propósito: son
históricos y se conservan.

### `rebasar_aumento_pendiente`

Resuelve la corrección de un monto mal cargado: el aumento ya aplicado dejó el
contrato con el monto aumentado, así que el monto que el usuario carga al editar
se interpreta como el **anterior** al aumento.

- Toma el PENDIENTE más reciente (`crud_historial.get_ultimo_pendiente`) y
  aborta si su período es **anterior al mes en curso** (los meses pasados
  quedan congelados) o si su registro mensual no existe o ya está pagado.
- Re-basa **solo el concepto editado**: `*_anterior = *_base_actual` nuevo,
  `*_propuesto = anterior × factor`, `*_aplicado = *_propuesto`. El factor sale
  del porcentaje **congelado** del evento (`1 + porcentaje_*_propuesto / 100`),
  no de la configuración actual del contrato, así un cambio de 10 % → 15 % no
  retoca la propuesta ya generada (vale igual para ICL: el porcentaje congelado
  deriva del `coeficiente_icl`).
- Sincroniza en un único commit historial + contrato (`*_base_actual` =
  propuesto) + registro del período (`*_calculado`, `porcentaje_aumento_usado`
  y `total`); los overrides conservan su diferencia.
- Un aumento CONSOLIDADO nunca entra: al cobrar el mes deja de ser PENDIENTE.

### Dashboard y Servicios comparten lógica

- Ambos filtran el mes en curso con `contrato_operativo_hoy(contrato)`
  (ya empezó por fecha exacta y el mes actual está en su vigencia) y llaman a
  `preparar_registro_mes`:
  1. genera como atrasados los meses vigentes **sin registro** entre el último
     mes registrado del contrato y el mes pedido (`_meses_sin_registro`), en
     orden, cada uno con su aumento. Un contrato sin ningún registro previo no
     genera meses hacia atrás;
  2. para cada mes, `_preparar_mes` ejecuta `aplicar_aumento_si_corresponde` y
     `get_or_create_registro`. Si el aumento se aplicó y el registro ya
     existía (se creó antes, por ej. con el ICL del BCRA sin publicar), el
     registro pasa al monto aumentado con `fijar_montos_calculados`. Si ese
     mes ya estaba cobrado, el registro no se toca y el aumento se consolida
     en el acto (no queda un PENDIENTE sin mes por cobrar).
- `calcular_estado_servicios()` comparte: `"Pendiente"` si falta agua o luz
  para un contrato que los cobra, `"OK"` si no.

### Cobros atrasados

- El listado del mes agrega `registros_sin_cobrar_fuera_del_ciclo(session)`
  (mes_service, compartida por Dashboard y Servicios): registros
  `pagado == False` de meses anteriores de **cualquier** contrato y del mes en
  curso de los contratos **finalizados**, solo dentro de la vigencia del
  contrato, orden ascendente (antiguo → reciente).
- Solo lectura: **no crea ni prepara nada**, y el total se calcula en la
  respuesta sin escribir DB.
- La deuda de un contrato finalizado sigue visible hasta cobrarse (la fila
  trae `contrato.estado = 'finalizado'` y la UI la marca).
- Cada item se marca con `atrasado = (anio, mes) < actual`; los registros
  "frescos" van con `atrasado: False`.

---

## Vigencia y protecciones de fecha_fin

- `contrato_vigente_para_mes(contrato, anio, mes)`: `True` mientras
  `(inicio.year, inicio.month) <= (anio, mes) <= (fin.year, fin.month)` — el
  **mes de inicio y el de vencimiento son válidos**; los anteriores y
  posteriores no.
- Está aplicada en: preparación de registros (409 si no vigente), cobrar
  (`marcar_pagado`, 409), override (409), servicios/guardar (409), el listado
  de atrasados, `GET /contratos/{id}/meses-sin-cobrar` y los PENDIENTE de
  `GET /aumentos/historial` (un PENDIENTE fuera de la vigencia, por ejemplo
  tras acortar `fecha_fin`, no se lista). Dashboard y Servicios además omiten
  en el mes en curso los contratos con `fecha_inicio > hoy`
  (`contrato_operativo_hoy`).
- El cierre manual (`estado='finalizado'`) es independiente de la fecha: un
  contrato cerrado no genera registros aunque la fecha sea futura, y un
  contrato vencido no cerrado sigue operativo dentro del mes de vencimiento.

---

## Aumentos

### ¿Corresponde aumento?

- Técnicamente `corresponde_aumento(contrato, anio, mes)` (con las guardas
  funcionales descritas en la especificación):
  1. `SIN_AUMENTO` o `periodicidad_aumento_meses == 0` → nunca.
  2. MANUAL con `porcentaje_aumento == 0` → nunca.
  3. Base temporal en orden de prioridad: `fecha_ultimo_aumento` (indicada por
     el usuario para contratos en curso)
     → `ultimo_aumento_anio/mes` (último aumento aplicado por el sistema)
     → `fecha_inicio` del contrato.
  4. Guarda: `(anio, mes) > (fecha_fin.year, fecha_fin.month)` → nunca
     (mes de vencimiento permitido).
  5. Idempotencia: si ya existe `historial_aumentos` para (contrato, anio,
     mes), la propuesta congelada no se recalcula ni duplica.

### Aplicación del aumento

- `aplicar_aumento_si_corresponde`: factor según tipo (MANUAL: `1 + %/100`;
  ICL: coeficiente BCRA), calcula la propuesta congelada
  (`*_propuesto` + porcentajes) y crea `HistorialAumento` estado
  **PENDIENTE** con `*_aplicado == *_propuesto`.
- **Validación anti-negativa:** si la propuesta < monto anterior → no aplica
  (bloquea ICL negativos). En alquiler y expensa.
- **Mutación del contrato en la misma transacción:**
  - `alquiler_base_actual = propuesto`
  - `expensa_base_actual = expensa propuesta` (si corresponde)
  - `ultimo_aumento_anio/mes = período`
  - `fecha_ultimo_aumento = 1er día del período de vigencia`
  (evita re-aplicación al reabrir el Dashboard dentro del mes de vigencia.)
- El registro mensual recibe el `porcentaje_aumento_usado`:
  `preparar_registro_mes` guarda el porcentaje legacy solo si el registro aún
  no tenía ninguno (idempotente).

### Modificación de un PENDIENTE (`modificar_aumento_pendiente`)

Validaciones en orden:
1. 404 aumento inexistente.
2. 409 CONSOLIDADO (inmutable).
3. 409 si `existe_posterior()` → ya hay un aumento posterior del contrato
   (protege la continuidad histórica).
4. 400 sin montos, 400 `aplicado < anterior` (alquiler o expensa).
5. 409 si el registro mensual del período no existe, o 409 si ya está pagado.
6. 400 editar expensa de un aumento sin expensa.

Sincronización (commit único):
1. `historial_aumentos`: `*_aplicado` + porcentajes aplicados recalculados =
   `((aplicado - anterior) / anterior) * 100` + `fecha_actualizacion`.
2. `contratos`: `*_base_actual = *_aplicado` (el próximo aumento parte del
   aplicado, no del propuesto), **solo si el contrato todavía tiene el
   aplicado anterior**: si el usuario lo corrigió editando el contrato, la
   corrección no se pisa. No se tocan `*_base_inicial` ni fechas.
3. `registros_mensuales`: `alquiler_calculado` / `expensa_calculada` y
   `porcentaje_aumento_usado` del registro del período, con
   `fijar_montos_calculados` (los overrides conservan su diferencia).
4. `registros_mensuales` posteriores al período y **no pagados** (atrasados
   intermedios y mes en curso) que todavía tienen el aplicado anterior: se
   generaron con el monto del aumento, así que heredan el aplicado (mismo
   helper). Como `existe_posterior()` ya garantizó que no hay aumentos
   posteriores, derivan de este. Los pagados quedan como histórico y los que
   tienen otro monto (corrección del usuario) no se tocan.

### Consolidación

- `POST /dashboard/registros/{id}/pagado` → `consolidar_pendiente()`: si hay
  PENDIENTE para ese (contrato, anio, mes), setea `estado = CONSOLIDADO` +
  `fecha_consolidacion`. Sin PENDIENTE no hay error (idempotente).
- Callback desde la UI: el pago del mes cierra la vida del aumento.

---

## ICL técnico

- Endpoint del BCRA: `https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/40`
  (variable monetaria 40 = ICL). Parámetros `Desde` / `Hasta` en `YYYY-MM-DD`.
- `_fetch_icl_bcra(fecha_desde, fecha_hasta)`: GET httpx con **timeout 10 s** y
  `verify=False` (sin verificar el certificado del BCRA); parsea
  `results[0].detalle[]` con items `{fecha, valor}`.
- `_calcular_icl_aumento(contrato, base_anio, base_mes, proximo_anio,
  proximo_mes)`:
  - período: `desde` = 1° día del mes base (base del último aumento);
    `hasta` = último día del mes anterior al mes de vigencia.
  - **condiciones de `icl_pendiente`:** error de API; `fecha_hasta` posterior
    a la fecha del sistema; falta el valor publicado para `fecha_hasta`; o
    falta el inicial (con fallback: si no existe valor en la fecha exacta, se
    usa el primer valor publicado del rango).
  - resultado: `coeficiente = icl_final / icl_inicial` (redondeo a 6
    decimales), `porcentaje`, `alquiler_nuevo = round(base_actual *
    coeficiente)`, `expensa_nueva` si cobra expensa, `fecha_icl_inicial/final`,
    `ultima_fecha_disponible_bcra` y `dias_faltantes`.
- `calcular_proximo_aumento()` lo integra con los flags de UI:
  `icl_calculado = fecha_vigencia > hoy` (calculado pero no vigente todavía);
  `icl_aplicable = fecha_vigencia <= hoy`.
- **Persistencia:** al aplicarse el aumento, `historial_aumentos` congela
  `icl_inicial`, `icl_final`, `coeficiente_icl`, `fecha_icl_inicial`,
  `fecha_icl_final`. MANUAL deja esos campos NULL; expensa NULL si no cobra.
- Errores: cualquier problema (status != 200, JSON vacío, excepción) se
  transforma en "pendiente" con mensaje; el contrato y los registros quedan
  sin cambios.

---

## Endpoints principales

- Dashboard:
  - `GET /dashboard/mes-actual` — cobros del mes + atrasados (flag `atrasado`).
  - `GET /dashboard/historial-pagos?anio&mes&id_inquilinos` — pagados,
    orden descendente (más nuevo primero).
  - `POST /dashboard/registros/{id}/pagado` — cobro (400 servicios pendientes,
    409 fuera de vigencia) + consolidación.
  - `POST /dashboard/registros/{id}/override` — ajuste individual (409 fuera
    de vigencia).
- Servicios:
  - `GET /servicios/pendientes` — contratos con agua/luz, mes actual
    + atrasados (incluida la deuda de contratos finalizados).
  - `POST /servicios/guardar?id_registro&agua&luz` — 400 si pagado, 409 fuera
    de vigencia.
- Contratos: `GET/POST /contratos/`, `GET/PUT/DELETE /contratos/{id}`
  (DELETE también borra sus registros mensuales e historial de aumentos: SQLite
  reutiliza ids y un contrato nuevo los heredaría),
  `GET /contratos/{id}/tiene-pagos`, `GET /contratos/{id}/meses-sin-cobrar`
  (`[{anio, mes, total}]`, para el aviso del modal de cierre),
  `POST /contratos/{id}/cerrar`, `POST/GET /contratos/{id}/archivo` (PDF/DOCX).
- Departamentos / Inquilinos: `DELETE` responde **409** si algún contrato
  (activo o finalizado) los referencia (`crud_contratos.tiene_contratos`).
- Aumentos: `GET /aumentos/` (próximos), `GET /aumentos/historial?estado=...`
  (fuente de verdad), `PATCH /aumentos/historial/{id}` (modificar pendiente).
- Backup: `POST /backup/` y `GET /backup/` (carpeta `backups/`).

---

## Pendientes anteriores: técnica y flags

- Dashboard: la respuesta marca `atrasado: True` en los registros anteriores;
  el frontend separa `atrasados` / `actuales` y compone las filas como
  `[...atrasados, ...actuales]` (antiguos → recientes primero). También
  calcula el encabezado del mes con los registros "frescos".
- Aumentos: `GET /aumentos/historial` calcula por fila
  `atrasado = (anio, mes) < hoy` y
  `se_puede_modificar = PENDIENTE && !existe_posterior(...)`.
- Acciones por fila usan dos ids distintos por diseño:
  - `id_registros_mensuales` para operaciones de cobro/override/servicios
    (la fila es un registro mensual);
  - `id_historial_aumentos` para modificar un aumento PENDIENTE
    (la fila es un evento del historial).
- El frontend determina "cobrable" con `estado_servicios === 'OK'` +
  `pagado == False`; la selección masiva (`visiblesCobrables`) excluye
  atrasados por construcción (el mes en curso de un contrato finalizado sí
  entra, porque no es atrasado).

---

## Integridad, migraciones y compatibilidad

- `create_db_and_tables()`: `SQLModel.metadata.create_all` para bases nuevas.
- `_migrar_columnas_contratos()`: migración aditiva en el startup con
  `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` para
  `alquiler_base_inicial`, `expensa_base_inicial`, `impuesto_fijo`
  (contratos) e `impuesto` (registros_mensuales), solo si faltan. Sin pérdida
  de datos.
- Campos **legacy** mantenidos por compatibilidad:
  - `contratos.ultimo_aumento_anio/mes` (conviven con `fecha_ultimo_aumento`)
  - `registros_mensuales.porcentaje_aumento_usado` (se sigue escribiendo en
    cada aumento, pero el historial es la fuente de verdad)
- Constraints nominales en `historial_aumentos`:
  `uq_historial_contrato_periodo` (UNIQUE contrato+anio+mes) y
  `ck_historial_mes_rango` (CHECK mes 1–12).
- SQLite por defecto **no enforcea FKs**; la integridad referencial real la
  aplican las capas de servicio (checks de negocio y el orden de operación).
- CORS: `localhost:5173`, `localhost:3000`, `127.0.0.1:8000`.
