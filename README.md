# Depto Manager

Depto Manager es una aplicación de escritorio web para la gestión de alquileres
de departamentos. Corre 100 % local (backend + frontend en la misma PC) y se
distribuye como paquete portable para Windows: el cliente no instala nada.

Único requisito de conectividad: los cálculos de aumentos **ICL** consultan en
vivo la API pública del BCRA y necesitan internet; todo el resto funciona sin
conexión.

---

## Objetivo

Proveer una herramienta simple, portable y confiable para:

- Registrar departamentos, inquilinos y contratos (con adjunto PDF/DOCX).
- Calcular automáticamente el cobro mensual por contrato
  (alquiler + expensas + agua + luz + impuesto).
- Registrar cobros, ajustes manuales y pagos, con historial completo.
- Aplicar aumentos automáticos por porcentaje fijo (MANUAL) o por el índice
  ICL del BCRA, con historial auditable y corrección de propuestas pendientes.
- Mantener backups de la base de datos.

---

## Problemas que resuelve

- Centraliza contratos, cobros, servicios y aumentos en un solo lugar
  (reemplaza planillas dispersas).
- Automatiza cálculos recurrentes: cobro mensual, aumentos por periodicidad e
  ICL, totales con servicios.
- Deja trazabilidad: cada aumento con propuesta, monto aplicado y datos del
  índice; historial de pagos con filtros; backups del archivo de datos.
- Cero fricción técnica: carpeta portable que se ejecuta con doble clic.

---

## Funcionalidades principales

- **Dashboard:** cobros del mes por contrato, ajustes individuales o masivos,
  pago definitivo, cobros atrasados de meses anteriores e impresión del
  listado.
- **Departamentos e Inquilinos:** altas, ediciones, estados (ocupado/libre,
  actual/anterior) e historiales.
- **Contratos:** creación, edición (con protecciones sobre fechas y montos),
  cierre, montos "ya en curso" y tipos de aumento MANUAL / ICL / SIN_AUMENTO.
- **Servicios:** carga de agua y luz por mes, con edición hasta el cobro.
- **Aumentos:** proyección del próximo aumento, modificaciones de aumentos
  pendientes de consolidar e historial completo (incluida la auditoría ICL).
- **Backups e historial de pagos** con filtros por año, mes e inquilino.

El detalle completo está en `Documentación/especificacion funcional.md`.

---

## Quick start (desarrollo)

Backend:

```bash
cd backend
.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

API en `http://localhost:8000` (documentación automática en `/docs`).

Frontend:

```bash
cd frontend
npm run dev
```

Dev server de Vite en `http://localhost:5173`.

Para preparar el entorno desde cero (venv Python + dependencias + npm):
ejecutar `setup.ps1`.

---

## Ejecución portable (cliente final)

En la carpeta portable, doble clic en **`start.bat`**: levanta el servidor en
`http://127.0.0.1:8000` y abre el navegador automáticamente. Para cerrar,
se cierra la ventana de consola.

Instrucciones para el cliente: `Documentación/README-CLIENTE.md`.

---

## Estructura del proyecto

```
backend/                 # API FastAPI (app/main.py, routers/, service/, crud/, model/)
frontend/                # React + TypeScript + Vite (src/pages, src/lib)
frontend/dist/           # build de producción servido por FastAPI
base_de_datos/           # alquileres.sqlite (datos de la aplicación)
backups/                 # backups generados desde la interfaz
python/                  # Python embebido del paquete portable (no tocar)
start.bat                # inicia la aplicación portable
update.bat               # reinstala dependencias Python en el portable
build-frontend.bat       # genera el build del frontend en frontend/dist
setup.ps1                # preparación del entorno de desarrollo
```

---

## Documentación

| Documento | Contenido |
| --- | --- |
| `Documentación/especificacion funcional.md` | QUÉ hace el sistema: funcionalidades y reglas de negocio |
| `Documentación/arquitectura tecnica.md` | CÓMO está implementado: stack, flujos internos, endpoints |
| `Documentación/modelo de datos.md` | tablas SQLite, campos, constraints y relaciones |
| `Documentación/convenciones ui.md` | estándares visuales: tablas, modales, estados, impresión |
| `Documentación/README-BUILD.md` | cómo construir, empaquetar y actualizar la distribución portable |
| `Documentación/README-CLIENTE.md` | guía de uso para el cliente final |
