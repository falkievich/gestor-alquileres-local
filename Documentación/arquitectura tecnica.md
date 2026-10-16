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
  override). "Restaurar" envía vacío y limpia los tres campos.
- Los overrides **nunca se tocan** al modificar un aumento; ni al recalcular
  por edición de contrato.

### Recalculación al editar contrato

`crud/contratos.py → update_contrato` hace, en este orden:

1. Compara el payload contra el contrato para saber si cambiaron realmente
   `alquiler_base_actual` y/o `expensa_base_actual` (no alcanza con que vengan
   en el body: el frontend los manda siempre).
2. Aplica los campos y commitea.
3. Si cambió algún monto, `rebasar_aumento_pendiente` (mes_service) re-calcula
   el aumento PENDIENTE del contrato — ver abajo.
4. `_sincronizar_registros_mensuales` propaga el `*_base_actual` final y el
   `impuesto_fijo` a los registros **no pagados, sin override, del mes actual
   (o mes de inicio) hasta el mes de fecha_fin**. Meses pagados nunca se
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
  y `total`), preservando los overrides.
- Un aumento CONSOLIDADO nunca entra: al cobrar el mes deja de ser PENDIENTE.

### Dashboard y Servicios comparten lógica

- Ambos llaman a `preparar_registro_mes`, que a su vez ejecuta
  `aplicar_aumento_si_corresponde` (aumento automático antes de congelar el
  registro) y a `get_or_create_registro`.
- `calcular_estado_servicios()` comparte: `"Pendiente"` si falta agua o luz
  para un contrato que los cobra, `"OK"` si no.

### Cobros atrasados

- El listado del mes también recupera, en una segunda consulta, los registros
  `pagado == False` con `(anio < actual) OR (anio == actual AND mes < actual)`,
  orden ascendente (antiguo → reciente).
- Solo lectura: **no crea ni prepara nada**, y el total se calcula en la
  respuesta sin escribir DB.
- Solo contratos **activos** reaparecen (los pendientes de contratos
  finalizados quedan en DB pero fuera de las vistas operativas).
- Cada item se marca con `atrasado: True`; los registros "frescos" van con
  `atrasado: False`.

---

## Vigencia y protecciones de fecha_fin

- `contrato_vigente_para_mes(contrato, anio, mes)`: `True` mientras
  `(anio, mes) <= (fecha_fin.year, fecha_fin.month)` — el **mes de vencimiento
  sigue siendo válido**; los meses posteriores no.
- Está aplicada en: preparación de registros (409 si no vigente), cobrar
  (`marcar_pagado`, 409), override (409) y servicios/guardar (409). El
  Dashboard además omite contratos con `fecha_inicio > hoy` y los no vigentes
  para el mes actual.
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
   aplicado, no del propuesto). No se tocan `*_base_inicial` ni fechas.
3. `registros_mensuales`: sobreescrita `alquiler_calculado` /
   `expensa_calculada` y `porcentaje_aumento_usado` del registro del período,
   recalcula `total` común. **Los overrides no se tocan.**

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
  - `GET /servicios/pendientes` — contratos activos con agua/luz, mes actual
    + atrasados.
  - `POST /servicios/guardar?id_registro&agua&luz` — 400 si pagado, 409 fuera
    de vigencia.
- Contratos: `GET/POST /contratos/`, `GET/PUT/DELETE /contratos/{id}`,
  `GET /contratos/{id}/tiene-pagos`, `POST /contratos/{id}/cerrar`,
  `POST/GET /contratos/{id}/archivo` (PDF/DOCX).
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
  atrasados por construcción.

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
