# Depto Manager — Guía para preparar el paquete portable (Python embebido)

Breve: estos pasos preparan la carpeta que se entregará al cliente usando Python Embedded (Windows). El cliente no instala nada: solo descomprime y ejecuta `start.bat`.

Requisitos (en la máquina de desarrollo)
- Node.js + npm (para build del frontend)
- Python (cualquier) para preparar el entorno y generar `requirements.txt` si hace falta

Pasos para preparar el paquete

1) Descargar Python embebido (Windows)
- Ir a https://www.python.org/downloads/windows
- Descargar el paquete "Windows embeddable package (64-bit)" para la versión que uses (ej. 3.12)
- Extraer el contenido en la carpeta `python/` dentro de la raíz del proyecto (ruta final: `.../python/python.exe`)

2) Habilitar pip en el Python embebido
- Abrir `python/python312._pth` (el nombre puede variar según la versión) y descomentar la línea que contiene `import site` (quitar el `#`).
- Descargá `get-pip.py` desde https://bootstrap.pypa.io/get-pip.py y colocalo en la raíz `python/`.
- Desde la línea de comando (PowerShell o CMD) ejecutar:

  "python\python.exe" "python\get-pip.py"

  Esto instalará pip dentro del Python embebido.

3) Instalar dependencias de Python (usar `update.bat`)
- Ejecutar `update.bat` (incluido en el repo). Esto ejecuta:

  "python\python.exe" -m pip install -r "backend\requirements.txt"

  Verificar que la instalación termine sin errores.

4) Generar build del frontend
- Ejecutar `build-frontend.bat`. Internamente hace `npm ci` y `npm run build` dentro de `frontend/`.
- Resultado esperado: `frontend/dist/` con los archivos estáticos listos.

5) Probar localmente
- Ejecutar `start.bat` desde la raíz del proyecto. Esto lanzará el backend usando `python\python.exe` y abrirá `http://127.0.0.1:8000` en el navegador.
- Probar funcionalidades, backups, etc.

6) Empaquetar para el cliente
- Antes de comprimir, limpiar elementos de desarrollo innecesarios (opcional):
  - Eliminar `frontend/node_modules` si existe
  - No incluir carpetas de desarrollo (.venv) si están presentes
- Crear ZIP con toda la carpeta del proyecto (mantener `python/`, `backend/`, `frontend/dist/`, `base_de_datos/`, `start.bat`, etc.).
- Entregar el ZIP. El cliente solo debe descomprimir y ejecutar `start.bat`.

Cómo actualizar después de entregar

- Cambios en backend (solo código):
  1. Reemplazar archivos dentro de `backend/app/` con los nuevos.
  2. Si agregaste nuevas dependencias, actualizar `backend/requirements.txt` y ejecutar `update.bat` en la carpeta del cliente (o entregar ZIP nuevo).
  3. Reiniciar la aplicación (pedir al cliente cerrar y volver a ejecutar `start.bat`).

- Cambios en frontend:
  1. En la máquina de desarrollo ejecutar `build-frontend.bat`.
  2. Copiar la carpeta generada `frontend/dist/` al paquete desplegado, reemplazando la anterior.
  3. Reiniciar la aplicación en el cliente.

- Cambio completo / release nueva:
  - Preparar una nueva versión del ZIP y entregar al cliente.
  - Antes de reemplazar, instruir al cliente a hacer backup de `base_de_datos/alquileres.sqlite` si quiere conservar datos.

Notas y recomendaciones
- Rutas: el backend está configurado para usar rutas relativas (`base_de_datos/alquileres.sqlite`, `frontend/dist/`). No usar rutas absolutas.
- Caché del navegador: si se actualiza frontend y el cliente no ve cambios, pedir abrir en modo incógnito o limpiar caché (o cerrar la app y reiniciar).
- Seguridad: avisar al cliente que puede rechazar permisos de antivirus la primera vez que ejecute un Python embebido.
- Comprobación final: probar el ZIP en una VM Windows limpia para verificar que no haga falta instalar nada.

Si querés, genero un script PowerShell que automatice la descarga/descompresión del Python embebido y la instalación de pip en una carpeta `python/`.
