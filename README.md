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

## Base de datos

Todos los datos se guardan en la carpeta `base_de_datos/alquileres.sqlite`.

- El motor es SQLite (archivo local) — no requiere servidor externo.
- La aplicación incluye un mecanismo para crear backups desde el Dashboard; los
  archivos se guardan en la carpeta `backups/` con nombre `alquileres_YYYY-MM-DD_HH-mm.sqlite`.

---

## Desarrollo y pruebas

- Revisá los endpoints en `backend/app/routers/` y las páginas en `frontend/src/pages/`.
- Para ejecutar tests (si se agregan), crear un entorno virtual en `backend/.venv` y usar pytest.

---

Si necesitás que incluya secciones adicionales (ej. guía de empaquetado paso a paso, lista de comandos de mantenimiento o ejemplos de API), decímelo y lo agrego.
