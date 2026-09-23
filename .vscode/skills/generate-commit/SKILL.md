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

Usar únicamente el encabezado:

`BACKEND`

Debajo, indicar cada archivo o grupo de archivos modificados y resumir sus cambios.

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

Ejemplo:

BACKEND

app/core/presupuesto.py (nuevo)
- Centraliza el cálculo del presupuesto de tokens usando el prompt real y el margen disponible.
- Incorpora `PresupuestoInsuficiente` para evitar llamadas que no entren correctamente en contexto.
- Agrega `DesglosePrompt` como estructura compartida entre etapas.

app/core/config.py
- Agrega nuevos límites de salida y margen de seguridad configurables.
- Retira las variables antiguas de los cálculos activos.

tests/test_presupuesto.py (nuevo)
- Cubre la fórmula central de presupuesto y sus límites.
- Verifica overrides y variables deprecadas.

README.md, .env.example
- Actualiza la configuración y documentación asociada al nuevo presupuesto de tokens.

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
- El encabezado `BACKEND` debe escribirse como texto normal.
- El título debe escribirse como texto normal.

Formato exacto esperado:

Título del commit

BACKEND

app/core/archivo.py
- Descripción del cambio.
- Descripción del cambio.
- Descripción del cambio.

app/services/otro_archivo.py
- Descripción del cambio.
- Descripción del cambio.

tests/test_archivo.py
- Descripción del cambio.
- Descripción del cambio.