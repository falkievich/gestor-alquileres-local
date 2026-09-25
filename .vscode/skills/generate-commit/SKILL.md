---
name: generate-commit
description: Genera el título y la descripción de un commit a partir de los cambios locales todavía no comiteados.
disable-model-invocation: true
---

# Generate Commit

## Objetivo

Generar únicamente en el chat un título y una descripción de commit basados en los cambios locales todavía no comiteados.

El usuario realizará el commit manualmente.

## Restricciones

- NO ejecutar `git add`, `git commit`, `git push` ni ningún comando que modifique el repositorio.
- NO modificar, crear ni eliminar archivos.
- Analizar únicamente cambios sin comitear: staged, unstaged y archivos nuevos.
- NO incluir cambios que ya estén comiteados.
- NO inventar información.
- Responder únicamente con el commit listo para copiar.

## Minimizar tokens

Aprovechar primero el contexto reciente del chat para entender qué se implementó.

Luego verificar únicamente los cambios reales del repositorio.

Priorizar:

`git status --short`

`git diff --stat`

`git diff --cached --stat`

Después revisar solo los diffs necesarios:

`git diff --unified=1`

`git diff --cached --unified=1`

Leer archivos completos únicamente cuando el diff no sea suficiente o el archivo sea nuevo.

NO recorrer ni analizar todo el proyecto.

## Título

Crear una sola línea que describa de forma general el cambio principal.

Debe ser breve, descriptivo y técnico pero entendible.

Ejemplo:

`Presupuesto de tokens por etapa: prompt real medido en vez de reserva estimada`

No usar automáticamente prefijos como `feat:`, `fix:`, `refactor:` o similares.

## Descripción

Antes de redactar la descripción del commit, analizar todos los archivos modificados y clasificarlos por el área real del proyecto a la que pertenecen.

NO usar ningún encabezado por defecto.

Los encabezados deben surgir de los cambios reales encontrados. Primero clasificar los archivos y después redactar los apartados.

Reglas obligatorias de clasificación:

- Archivos de backend, por ejemplo rutas dentro de `backend/`, APIs, routers, servicios, modelos, persistencia, lógica de negocio o tests propios del backend -> `BACKEND`.
- Archivos de frontend, por ejemplo rutas dentro de `frontend/`, componentes, páginas, estilos, hooks, estado o lógica de interfaz -> `FRONTEND`.
- Archivos de documentación, por ejemplo `README.md`, `Documentación/`, `docs/`, manuales o archivos cuya función principal sea documentar el proyecto -> `DOCUMENTACIÓN`.
- Archivos de infraestructura, despliegue, Docker, contenedores, servidores, proxy o configuración externa de ejecución -> `INFRAESTRUCTURA`.
- Workflows, pipelines o configuración específica de integración y despliegue continuo -> `CI/CD`.
- Scripts auxiliares que no pertenezcan claramente al backend ni al frontend -> `SCRIPTS`.
- Archivos específicamente dedicados a migraciones, estructura o administración de base de datos pueden usar `BASE DE DATOS` cuando constituyan un área diferenciada del cambio.
- Si aparece otra área real del proyecto, crear un encabezado descriptivo equivalente.

La clasificación debe basarse en la ruta, el propósito del archivo y el cambio realizado. No seguir una plantilla fija ni asumir un área por el orden de los archivos en el diff.

Reglas obligatorias para los apartados:

- Crear únicamente los apartados que tengan archivos modificados.
- Si solo existen cambios de frontend, usar `FRONTEND`. NO incluir `BACKEND`.
- Si solo existen cambios de backend, usar `BACKEND`. NO incluir `FRONTEND`.
- Si existen cambios de frontend y documentación, usar únicamente `FRONTEND` y `DOCUMENTACIÓN`.
- Si existen cambios de backend, frontend, infraestructura y documentación, crear esos cuatro apartados.
- Un archivo `frontend/...` debe aparecer bajo `FRONTEND`, nunca bajo `BACKEND`.
- Un archivo `backend/...` debe aparecer bajo `BACKEND`, nunca bajo `FRONTEND`.
- `README.md`, `Documentación/...`, `docs/...` y otros archivos puramente documentales deben aparecer bajo `DOCUMENTACIÓN`.
- Nunca colocar archivos de áreas diferentes bajo un mismo encabezado solo para reducir la cantidad de apartados.
- Los encabezados no están limitados a `BACKEND`, `FRONTEND` y `DOCUMENTACIÓN`; deben representar las áreas realmente modificadas.
- El primer encabezado de la descripción debe corresponder al primer grupo real de cambios. No comenzar con `BACKEND` salvo que efectivamente existan cambios de backend.

Antes de responder, realizar una verificación final:

- cada archivo modificado debe estar asignado al apartado correcto;
- no debe existir ningún encabezado sin archivos propios;
- no debe faltar un encabezado para un área que sí tenga cambios;
- ningún archivo de frontend puede quedar bajo `BACKEND`;
- ningún archivo de documentación puede quedar bajo `BACKEND` o `FRONTEND`.

Debajo de cada apartado, indicar cada archivo o grupo de archivos modificados y resumir sus cambios.

Mantener la ruta completa.

Si un archivo es nuevo, agregar `(nuevo)`.

Se pueden agrupar archivos cuando hayan recibido cambios equivalentes.

Para cada archivo o grupo usar normalmente entre 2 y 5 bullets.

Los bullets deben:

- explicar brevemente qué cambió;
- tener un nivel técnico intermedio;
- mencionar funciones, clases o variables cuando sea útil;
- priorizar cambios funcionales, arquitectura, validaciones, tests y configuración;
- evitar detalles triviales o explicaciones línea por línea.

Ejemplo 1 — solo frontend y documentación:

FRONTEND

frontend/src/pages/Dashboard.tsx
- Estandariza la alineación de columnas de importes, estados y acciones.
- Mantiene los valores monetarios sin saltos de línea.

frontend/src/pages/Contratos.tsx
- Ajusta la alineación de fechas e importes según el estándar visual de las tablas.

DOCUMENTACIÓN

README.md
- Documenta el estándar de alineación aplicado a las tablas de la aplicación.

Ejemplo 2 — solo backend:

BACKEND

backend/app/core/presupuesto.py (nuevo)
- Centraliza el cálculo del presupuesto de tokens usando el prompt real y el margen disponible.
- Incorpora `PresupuestoInsuficiente` para evitar llamadas que no entren correctamente en contexto.

backend/tests/test_presupuesto.py (nuevo)
- Cubre la fórmula central de presupuesto y sus límites.

Ejemplo 3 — backend, frontend e infraestructura:

BACKEND

backend/app/service/mes_service.py
- Centraliza la preparación de registros mensuales.

FRONTEND

frontend/src/pages/Dashboard.tsx
- Adapta la interfaz a los datos generados por el backend.

INFRAESTRUCTURA

Dockerfile
- Actualiza la configuración de construcción de la aplicación.

## Formato de salida

Responder únicamente en formato Markdown plano dentro del chat.

Reglas obligatorias:

- NO usar negritas.
- NO usar cursivas.
- NO usar `*` como bullet.
- NO usar `•` como bullet.
- NO usar tablas.
- NO usar bloques de código.
- NO agregar explicaciones antes o después.
- Cada cambio debe comenzar obligatoriamente con `- `.
- Mantener las rutas de archivos como texto normal.
- Todos los encabezados de apartados que correspondan a los cambios reales, como `BACKEND`, `FRONTEND`, `DOCUMENTACIÓN`, `INFRAESTRUCTURA` u otros, deben escribirse como texto normal.
- El título debe escribirse como texto normal.

Formato exacto esperado:

Título del commit

<APARTADO QUE CORRESPONDA A LOS CAMBIOS REALES>

ruta/del/archivo.ext
- Descripción del cambio.
- Descripción del cambio.

<OTRO APARTADO, SOLO SI EXISTEN CAMBIOS DE ESA ÁREA>

ruta/de/otro/archivo.ext
- Descripción del cambio.

No sustituir `<APARTADO QUE CORRESPONDA A LOS CAMBIOS REALES>` literalmente: debe reemplazarse por `BACKEND`, `FRONTEND`, `DOCUMENTACIÓN`, `INFRAESTRUCTURA` u otro encabezado que corresponda.

No usar `BACKEND` como encabezado predeterminado.