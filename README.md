# Depto Manager

Depto Manager es una aplicación de escritorio web que facilita la gestión de alquileres de departamentos en entornos locales. Está pensada para administradores, encargados o propietarios que necesiten llevar control de inquilinos, contratos, cobros mensuales, servicios y aumentos sin depender de servicios externos ni instalaciones complejas.

---

## Objetivo

Proveer una herramienta simple, portable y confiable para:
- Registrar y consultar inquilinos y departamentos.
- Registrar contratos (vigentes y finalizados) y adjuntar el archivo del contrato.
- Calcular automáticamente el cobro mensual (alquiler + expensas + agua + luz) por contrato.
- Marcar cobros como pagados y mantener un historial de pagos.
- Cargar los valores de servicios (agua/luz) por mes y aplicarlos al cobro mensual.
- Gestionar aumentos periódicos aplicando porcentajes y fechas de último aumento.
- Generar backups locales del archivo de base de datos.

La aplicación está diseñada para funcionar totalmente offline y ser distribuida como un paquete portable en Windows.

---

## Qué problemas resuelve / cómo ayuda

- Evita llevar registros en papel o planillas dispersas: centraliza contratos, pagos y servicios.
- Automatiza cálculos recurrentes: evita errores manuales al calcular aumentos y totales mensuales.
- Facilita la auditoría: el historial de pagos y los backups permiten recuperar información ante errores.
- Reduce fricción técnica para el cliente: se entrega como una carpeta portable que se ejecuta con doble clic (no requiere instalar Python/Node globalmente).

---

## Quick start (desarrollo)

Recomendado para desarrolladores que quieran ejecutar o modificar el proyecto.

- Backend (desarrollo):
  - Abrir terminal y ejecutar:

    cd backend
    .venv\Scripts\uvicorn.exe app.main:app --reload --port 8000

  - La API estará en `http://localhost:8000` y la documentación automática en `http://localhost:8000/docs`.

- Frontend (desarrollo):
  - Abrir terminal y ejecutar:

    cd frontend
    npm run dev

  - El servidor de desarrollo de Vite suele correr en `http://localhost:5173`.

- Build del frontend (producción):
  - Desde la carpeta raíz ejecutar `build-frontend.bat` (o manualmente `cd frontend && npm run build`).

- Ejecutable portable (cliente):
  - Para probar la distribución portable usar `start.bat` en la carpeta raíz. Ese script arranca el backend embebido y abre el navegador en la UI.

---

## Estructura del proyecto (resumen)

- `backend/` — código del servidor FastAPI
  - `app/main.py` — aplicación FastAPI, sirve la API y el frontend build en modo portable
  - `app/db.py` — conexión y rutas relativas a la base de datos
  - `app/routers/` — endpoints por área (contratos, inquilinos, dashboard, servicios, aumentos, backup)
  - `requirements.txt` — dependencias de Python

- `frontend/` — código cliente (React + TypeScript)
  - `src/` — código fuente React (páginas, componentes, llamadas a API en `lib/api.ts`)
  - `package.json`, `vite.config.ts` — configuración del proyecto frontend
  - `build-frontend.bat` — script para construir el `dist` listo para servirse

- `base_de_datos/` — ubicación por defecto del archivo SQLite
  - `alquileres.sqlite` — base de datos principal usada por la aplicación

- `backups/` — carpeta donde la aplicación guarda backups generados desde la UI

- Scripts de conveniencia en la raíz:
  - `start.bat` — inicia la aplicación en modo portable (usa Python embebido)
  - `update.bat` — procedimiento de actualización del paquete portable
  - `setup.ps1` — script de preparación para el empaquetado

---

## Pestañas

### 🏠 Dashboard — Cobros del mes

Es la pantalla principal. Muestra todos los contratos activos y cuánto debe cobrar
cada inquilino en el mes actual (alquiler + expensas + servicios).

Desde acá podés:
- Ver el total a cobrar por cada departamento
- Marcar un cobro como pagado una vez que el inquilino paga
- Hacer ajustes individuales o masivos si el monto cambia ese mes (descuentos, acuerdos, etc.)
- Imprimir el listado del mes
- Ver el historial de cobros anteriores
- Crear un backup de la base de datos

---

### 🏢 Departamentos

Listado de todos los departamentos que administrás.

Desde acá podés:
- Agregar nuevos departamentos (piso, código, dirección)
- Editar o eliminar departamentos existentes
- Ver si un departamento está ocupado o libre

---

### 👤 Inquilinos

Listado de todos los inquilinos registrados.

Desde acá podés:
- Agregar nuevos inquilinos (nombre y teléfono)
- Editar sus datos
- Ver sus contratos activos e historial de contratos anteriores
- Ver el historial de pagos de cada inquilino

---

### 📄 Contratos

Listado de contratos activos y finalizados.

Desde acá podés:
- Crear un contrato nuevo vinculando un inquilino a un departamento
- Definir fechas, monto de alquiler, expensas, porcentaje y periodicidad de aumentos
- Adjuntar el archivo del contrato (PDF o DOCX)
- Editar o cerrar un contrato cuando el inquilino se va
- Si el contrato ya estaba en curso antes de empezar a usar el sistema, podés indicar
  cuándo fue el último aumento para que los cálculos futuros sean correctos

---

### 💧 Servicios

Pantalla para cargar los valores de agua y luz del mes actual para los inquilinos
que tienen esos servicios incluidos en el contrato.

Desde acá podés:
- Ver qué departamentos tienen servicios pendientes de cargar
- Ingresar los montos de agua y/o luz de cada uno
- Guardarlos para que se sumen al total del mes en el Dashboard

---

### 📈 Aumentos

Resumen de todos los contratos activos con información sobre los aumentos configurados.

Desde acá podés:
- Ver cuándo le corresponde el próximo aumento a cada inquilino
- Ver cuánto pasará a cobrar cuando se aplique el aumento
- Detectar contratos que tienen un aumento próximo o que ya vencieron
- Identificar contratos que necesitan que se complete la fecha del último aumento

---

## Funcionamiento interno

Explicaciones sobre el comportamiento de la app que no son visibles a simple vista.

---

### Orden de los listados

- **Dashboard:** los cobros del mes se listan por orden de id de contrato. El historial de pagos se ordena del mes más reciente al más viejo.
- **Departamentos:** del más nuevo cargado al más viejo (id descendente).
- **Inquilinos:** del más nuevo cargado al más viejo (id descendente).
- **Contratos:** del más nuevo cargado al más viejo (id descendente), en las pestañas de activos y finalizados.
- **Servicios:** por orden de contrato activo (id descendente).
- **Aumentos:** tarjetas por orden de contrato; el historial de aumentos del más reciente al más viejo.

---

### Estados de un contrato (Activo / Por vencer / Vencido)

El estado se calcula comparando la **fecha de vencimiento** del contrato contra la fecha
de hoy, contando **meses de calendario** (no se tiene en cuenta el día del mes: un
contrato que vence el 1° o el 31 de octubre "vence en octubre" de la misma forma).

- **Vencido:** la fecha de vencimiento ya pasó (`fecha_fin < hoy`).
- **Por vencer:** quedan **3 meses o menos** desde hoy hasta el mes de vencimiento.
  La regla se aplica igual en la sección Contratos (badge del listado) y en la
  sección Aumentos (badge de la tarjeta).
- **Activo:** cualquier otro caso (con fecha de vencimiento futura).

---

### Cómo funciona el cobro mensual (conteo de meses)

- El sistema **no genera los cobros con un cronjob**: el registro mensual de un contrato
  se crea la **primera vez que se pide el mes**, es decir al abrir el **Dashboard** o la
  sección **Servicios** (si el contrato cobra agua/luz). A partir de ahí el valor queda
  **congelado** en la base de datos para ese mes.
- Al crear el registro se toma el **alquiler/expensa/impuesto vigentes** del contrato en
  ese momento. Si después se edita el contrato, solo se recalculan los registros
  **no pagados y sin ajuste manual** del mes en adelante.
- El **total** del mes es: alquiler + expensa + agua + luz + impuesto (impuesto es fijo,
  no participa de los aumentos). Los ajustes manuales (overrides) suman o restan sobre
  esos valores sin tocar el contrato.
- Los **aumentos** se aplican automáticamente cuando se abre el Dashboard en el **mes de
  vigencia** del próximo aumento (último aumento + periodicidad). El nuevo valor entra
  en el registro de ese mes y los siguientes; el mes anterior queda con el valor viejo.
- Cada aumento queda registrado en la tabla **`historial_aumentos`** (fuente de verdad del
  historial) con estado **PENDIENTE**; al cobrar el mes pasa a **CONSOLIDADO** (inmutable).
  Cada evento guarda montos y porcentajes de Alquiler y Expensa por separado (propuesto vs.
  aplicado) y la auditoría ICL completa cuando corresponde. `porcentaje_aumento_usado`
  queda temporalmente como campo legacy de compatibilidad.
- Una **propuesta ya generada no cambia** si después se edita la configuración del contrato
  (ej. 10% → 15%): el nuevo porcentaje se usa recién para el próximo aumento aún no generado.
- Los tipos de aumento son **MANUAL**, **ICL** y **SIN_AUMENTO** (contrato que nunca
  recibe aumentos automáticos).
- Para los contratos cargados como **"ya en curso"**, la base temporal del próximo aumento
  es la **fecha del último aumento** indicada por el usuario (y, después de cada aumento
  aplicado, el sistema actualiza esa fecha a la del nuevo aumento).
- Un **aumento no se aplica** si el contrato finaliza antes de que llegue el mes de
  vigencia (protección real en backend): la sección Aumentos lo marca con la tarjeta en
  rojo ("sin más aumentos"). Si cae en el mismo mes de vencimiento, sí puede aplicarse.
- Un **cobro es definitivo**: al marcar como pagado consolida el aumento pendiente y
  no existe la función de desmarcar.

---

## Estándar de alineamiento de tablas

Todas las tablas y grillas de la aplicación (incluidas las de los modales) siguen este
criterio de alineamiento. El encabezado siempre usa la misma alineación que el contenido
de su columna.

- **Texto e identificación → izquierda:** Departamento, Inquilino / Nombre, Dirección, Teléfono.
- **Fechas y períodos → centro:** Inicio, Vencimiento, Mes / Año, Periodicidad.
- **Importes y porcentajes → izquierda** (con `whitespace-nowrap` para que no se corten): Alquiler, Expensa, Agua, Luz, Impuesto, Diferencia, % aplicado.
- **Total → centro:** encabezado y contenido centrados.
- **Estados, badges y tipos → centro:** Estado, Pago, Servicios, Incluye, Tipo, Activo / Finalizado / Por vencer / Cargado.
- **Acciones → centro:** siempre como última columna, botones e íconos centrados en la celda.

---

## Base de datos

Todos los datos se guardan en la carpeta `base_de_datos/alquileres.sqlite`.

- El motor es SQLite (archivo local) — no requiere servidor externo.
- La aplicación incluye un mecanismo para crear backups desde el Dashboard; los
  archivos se guardan en la carpeta `backups/` con nombre `alquileres_YYYY-MM-DD_HH-mm.sqlite`.

---
