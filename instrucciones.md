# Prompt para Copilot — gestor-alquileres-local

## Contexto
Quiero que construyas una aplicación local llamada **gestor-alquileres-local**.

- Uso: 100% local, 1 usuario, sin login, se abre en Chrome.
- Backend: Python + FastAPI + SQLModel (SQLite como motor).
- Frontend: React + Vite + TypeScript + Tailwind + shadcn/ui.
- La DB se guarda como archivo `.sqlite` y contiene todo (incluye contratos como BLOB).
- Estructura obligatoria del repo:
  - `/backend`
  - `/frontend`
  - `/database` (contiene `alquileres.sqlite`)
  - `/backups` (copias del sqlite)

Vas a trabajar por iteraciones pequeñas, verificando que compila y funciona en cada etapa.
NO avances a la siguiente etapa sin dejar la anterior funcionando.

---

## Reglas de trabajo (muy importante)
1) Siempre proponé un plan de 3 a 6 pasos máximos por iteración.
2) Implementá la iteración completa y dejá instrucciones para ejecutar y probar.
3) Después de cada iteración, indicá:
   - Qué endpoints agregaste/actualizaste
   - Qué pantallas/acciones del front quedaron listas
   - Cómo probarlo manualmente (pasos concretos)
4) Mantené el código simple y legible (no sobre-arquitectura).
5) Todo lo que sea del mes actual se calcula con la fecha local del sistema.
6) Los contratos NO se cierran automáticamente por fecha_fin; el usuario los cierra manualmente.
7) Si un contrato está vencido (fecha_fin < hoy) pero estado = activo, debe seguir apareciendo en Dashboard con etiqueta “Vencido”.

---

## Base de datos (DBML)
Esta es la base de datos final. Usala como fuente de verdad (nombres en español y formato de IDs).

Table departamentos {
  id_departamentos integer [pk, increment]
  piso varchar(50) [not null] // "Planta baja, piso 2, etc"
  codigo varchar(50) [not null] // "1A", "2B", etc.
  direccion varchar(255) // opcional
  esta_ocupado boolean [not null, default: false]
}

Table inquilinos {
  id_inquilinos integer [pk, increment]
  nombre_apellido varchar(150) [not null]
  telefono varchar(50) // opcional
  es_actual boolean [not null, default: true]
}

Table contratos {
  id_contratos integer [pk, increment]
  id_departamentos integer [not null, ref: > departamentos.id_departamentos]
  id_inquilinos integer [not null, ref: > inquilinos.id_inquilinos]
  fecha_inicio date [not null]
  fecha_fin date [not null]
  estado varchar(20) [not null, default: 'activo'] // 'activo' | 'finalizado'
  alquiler_base_actual integer [not null]
  expensa_base_actual integer // nullable si no se cobra expensa
  porcentaje_aumento real [not null, default: 0] // ej: 8.0
  periodicidad_aumento_meses integer [not null, default: 3]
  ultimo_aumento_anio integer
  ultimo_aumento_mes integer // 1..12
  cobra_expensa boolean [not null, default: false]
  cobra_agua boolean [not null, default: false]
  cobra_luz boolean [not null, default: false]
  archivo_blob blob
}

Table registros_mensuales {
  id_registros_mensuales integer [pk, increment]
  id_contratos integer [not null, ref: > contratos.id_contratos]
  anio integer [not null]
  mes integer [not null]
  alquiler_calculado integer [not null]
  expensa_calculada integer
  alquiler_override integer
  expensa_override integer
  nota_override text
  agua integer
  luz integer
  pagado boolean [not null, default: false]
  total integer [not null]
  Indexes {
    (id_contratos, anio, mes) [unique]
  }
}

Notas:
- Estado Servicios (OK/Pendiente) NO se guarda; se calcula:
  - Pendiente si cobra_agua y agua es NULL en el registro del mes actual
  - Pendiente si cobra_luz y luz es NULL en el registro del mes actual
  - Si no cobra, se considera OK automáticamente
- Estado Cobro se guarda: registros_mensuales.pagado
- Un departamento solo puede tener 1 contrato activo a la vez (implementar validación en backend)

---

## Pantallas requeridas (resumen)
1) Dashboard (mes actual):
   - Lista cobros mes actual (contratos activos)
   - Estados: Servicios OK/Pendiente (calculado), Cobro Pagado/No pagado (persistido)
   - Permite imprimir (aunque Pendiente, agua/luz en blanco y total parcial)
   - Permite marcar Pagado / Desmarcar (solo si Servicios OK)
   - Toggle “Mostrar pagados” (oculta pagados por defecto)
   - Botón “Crear backup” (copia sqlite a /backups con nombre alquileres_YYYY-MM-DD_HH-mm.sqlite)
   - Si contrato vencido pero activo: etiqueta “Vencido”

2) Carga de Servicios (mes actual):
   - Solo contratos activos que cobren agua/luz y estén Pendiente y No pagado
   - Inputs por fila: agua y/o luz
   - Guardar crea/actualiza registros_mensuales del mes actual

3) Departamentos:
   - ABM departamentos
   - Mostrar ocupado/libre
   - Historial de inquilinos/contratos del departamento
   - Historial de pagos del departamento con filtros (por inquilino y por mes/año)

3.1) Notas de UI:
- El campo `piso` se carga desde un SELECT con opciones fijas:
  - "Planta baja"
  - "Piso 1"
  - "Piso 2"
  - "Piso 3"
- No se permiten valores fuera de esa lista.

4) Inquilinos:
   - ABM inquilinos
   - Ordenar actuales primero
   - Contratos asociados
   - Historial pagos del inquilino con filtro mes/año

5) Contratos:
   - Listado: activos arriba, finalizados abajo (o secciones)
   - Filtros: inquilino, departamento, fecha_inicio (rango), fecha_fin (rango)
   - Crear/editar/cerrar contrato
   - Ver/descargar contrato (BLOB)
   - Alertas: “Por vencer (<= 3 meses)” y “Vencido” si fecha_fin < hoy pero estado activo
   - Restricción de archivos de contrato:
    - Solo se permite subir contratos en formato PDF o DOCX.
    - Backend debe validar la extensión y/o el content-type y rechazar otros formatos.
    - Frontend debe limitar el selector de archivos a: .pdf, .docx

6) Vista de aumentos:
   - Próximo aumento por contrato activo con desglose
   - Aumento se aplica automáticamente al entrar/generar el mes actual en Dashboard (si corresponde)

---

## Estructura del repositorio (obligatoria)
- backend/
  - app/
    - main.py
    - db.py
    - model/
    - crud/
    - service/
    - routers/
  - requirements.txt
  - README.md
- frontend/
  - (Vite React TS)
- base_de_datos/
  - alquileres.sqlite (se crea al iniciar si no existe)
- backups/
  - (copias)

---

## Iteración 0 — Setup base (hacer primero)
Backend:
- Crear proyecto FastAPI + SQLModel.
- Configurar SQLite en `../base_de_datos/alquileres.sqlite`.
- Crear modelos SQLModel para las 4 tablas.
- Crear script o lógica de inicialización que cree tablas si no existen.
- Habilitar CORS para el frontend local.
- Endpoint /health.

Frontend:
- Crear Vite + React + TS.
- Instalar Tailwind + shadcn/ui.
- Layout base con sidebar o navbar simple.
- Configurar cliente HTTP (fetch/axios) apuntando a http://localhost:8000.

Entregable:
- `uvicorn` levanta backend
- `npm run dev` levanta front
- Front muestra “Backend OK” consultando /health

---

## Iteración 1 — Departamentos + Inquilinos (ABM básico)
Backend:
- Endpoints CRUD departamentos
- Endpoints CRUD inquilinos
Frontend:
- Pantalla Departamentos: lista + crear + editar
- Pantalla Inquilinos: lista + crear + editar + orden es_actual primero

---

## Iteración 2 — Contratos (CRUD + reglas + BLOB)
Backend:
- CRUD contratos con validación:
  - no permitir 2 contratos activos para mismo id_departamentos
- Subir contrato (archivo) -> guardar en archivo_blob
- Descargar contrato
- Endpoint para “cerrar contrato”:
  - cambia estado a finalizado
  - actualiza departamentos.esta_ocupado = false si no quedan contratos activos
  - actualiza inquilinos.es_actual = false si no tiene otros contratos activos
- Validar upload de contrato: aceptar únicamente .pdf y .docx (rechazar el resto con error claro).

Frontend:
- Pantalla Contratos con secciones Activos/Finalizados
- Filtros básicos (inquilino/departamento/fechas)
- Crear/editar/cerrar
- Ver/descargar archivo
- Limitar el selector de archivos del formulario de contrato a: .pdf, .docx

---

## Iteración 3 — Motor del mes actual: registros_mensuales + Dashboard base
Backend:
- Servicio “obtener mes actual” (anio/mes)
- Al cargar Dashboard:
  - listar contratos activos
  - garantizar que exista (o se pueda crear on-demand) un registros_mensuales por contrato para el mes actual
  - calcular alquiler_calculado/expensa_calculada desde contrato
  - total parcial si falta agua/luz
  - estado Servicios OK/Pendiente calculado
  - estado Cobro desde registros_mensuales.pagado
- Endpoint para marcar pagado/desmarcar (solo si Servicios OK)
- Endpoint para override del mes actual (alquiler/expensa + nota_override)
Frontend:
- Dashboard con tabla y estados:
  - OK/Pendiente
  - Pagado/No pagado
  - etiqueta “Vencido” si fecha_fin < hoy y estado activo
- Toggle “Mostrar pagados”
- Botones: marcar pagado/desmarcar (según reglas)
- Botón “Ajuste solo por este mes” (modal sencillo)

---

## Iteración 4 — Carga de Servicios (agua/luz) + impresión
Backend:
- Endpoint para listar “pendientes de servicios”:
  - activos + cobra_agua|cobra_luz + pendiente + no pagado
- Endpoint para guardar agua/luz del mes actual
- Endpoint (o lógica frontend) para imprimir listado del mes actual:
  - si pendiente, agua/luz en blanco, total parcial
Frontend:
- Pantalla Carga de Servicios con inputs por fila y guardar
- Botón “Imprimir” desde Dashboard:
  - vista/plantilla imprimible con checkbox al final

---

## Iteración 5 — Aumentos + Vista de Aumentos + alertas por vencimiento
Backend:
- Función para calcular si corresponde aumento en el mes actual:
  - usando ultimo_aumento_mes/anio + periodicidad_aumento_meses
- Si corresponde, aplicar:
  - alquiler_base_actual y expensa_base_actual (si cobra_expensa)
  - actualizar ultimo_aumento_mes/anio
- Endpoint Vista de Aumentos:
  - próximo aumento (mes/año) + desglose actual->nuevo (sin agua/luz)
- Alertas contratos:
  - por vencer (<= 3 meses)
  - vencidos (fecha_fin pasada, estado activo)
Frontend:
- Pantalla Vista de Aumentos
- En Contratos, mostrar badges “Por vencer / Vencido”

---

## Iteración 6 — Backup (botón en Dashboard)
Backend:
- Endpoint POST /backup:
  - copia el archivo `../base_de_datos/alquileres.sqlite`
  - guarda en `../backups/` con nombre `alquileres_YYYY-MM-DD_HH-mm.sqlite`
  - devuelve nombre del archivo creado
Frontend:
- Botón “Crear backup” en Dashboard:
  - llama al endpoint y muestra confirmación

---

## Checklist de aceptación final
- Puedo crear departamentos, inquilinos y contratos.
- No puedo crear 2 contratos activos para el mismo departamento.
- Dashboard muestra solo mes actual:
  - servicios OK/Pendiente calculado
  - pagado persistido, oculta pagados por defecto
  - permite imprimir aunque Pendiente (agua/luz en blanco, total parcial)
  - contratos vencidos activos aparecen con etiqueta “Vencido”
- Carga de servicios solo muestra pendientes no pagados y guarda agua/luz.
- Aumentos se aplican automáticamente cuando corresponde y Vista de Aumentos muestra el próximo aumento.
- Botón backup genera copia con nombre por fecha en /backups.

---

## Instrucciones de ejecución (dejar en README)
Backend:
- cd backend
- python -m venv .venv
- activar venv
- pip install -r requirements.txt
- uvicorn app.main:app --reload --port 8000

Frontend:
- cd frontend
- npm install
- npm run dev

Abrir:
- http://localhost:5173