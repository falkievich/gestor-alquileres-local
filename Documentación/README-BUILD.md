# Depto Manager — Guía técnica de build y despliegue portable

Guía para preparar el paquete que se entrega al cliente usando **Python
embebido** (Windows) y para actualizarlo después. El cliente no instala nada:
solo descomprime y ejecuta `start.bat`.

Cómo funciona el portable: `start.bat` ejecuta el backend con
`python\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
(trabajando dentro de `backend/`), que sirve también el build del frontend
(`frontend/dist`). Además busca el navegador **Supermium** (compatible con
Windows antiguos) en `Supermium\` de la raíz o en `Program Files`; si no está,
abre el navegador por defecto del sistema.

---

## Requisitos (máquina de desarrollo)

- Node.js + npm (para el build del frontend).
- Python instalado localmente (cualquiera) para preparar el Python embebido.

---

## 1) Preparar Python embebido (Windows)

1. Descargar de https://www.python.org/downloads/windows el "Windows
   embeddable package (64-bit)" (el proyecto usa **Python 3.13**).
2. Extraer el contenido en la carpeta `python/` de la raíz del proyecto
   (ruta final: `python\python.exe`).
3. **Habilitar pip:**
   - Editar `python\python313._pth` (el nombre exacto varía según la versión)
     y descomentar la línea `import site`.
   - Descargar `get-pip.py` desde https://bootstrap.pypa.io/get-pip.py y
     colocarlo dentro de la carpeta `python/`.
   - Ejecutar:

     ```
     "python\python.exe" "python\get-pip.py"
     ```

## 2) Instalar dependencias Python

Ejecutar `update.bat` (en la raíz). El script corre:

```
"python\python.exe" -m pip install -r "backend\requirements.txt" --quiet
```

Verificar que termine sin errores. Las versiones están fijadas en
`backend/requirements.txt` (FastAPI, Uvicorn, SQLModel, httpx, etc.).

## 3) Generar el build del frontend

Ejecutar `build-frontend.bat`. Internamente hace `npm ci` y `npm run build`
dentro de `frontend/`. Resultado esperado: `frontend/dist/` con `index.html`
y la carpeta `assets/`.

## 4) Probar el portable localmente

- Ejecutar `start.bat`: arranca el backend y abre
  `http://127.0.0.1:8000` en el navegador.
- Probar las funciones principales (cobros, ajustes, aumentos, servicios,
  backups).

> Nota: si falta `frontend\dist\index.html`, la app arranca igual pero solo
> como API (sin interfaz web); el propio `start.bat` lo avisa.

## 5) Empaquetar

- Antes de comprimir, quitar artefactos de desarrollo si existen:
  `frontend/node_modules`, entornos `.venv`, etc.
- Crear el ZIP con toda la carpeta del proyecto, conservando: `python/`,
  `backend/`, `frontend/dist/`, `base_de_datos/`, `start.bat`, `update.bat`,
  `build-frontend.bat` y `icons/`.
- Entregar el ZIP: el cliente solo descomprime y ejecuta `start.bat`.

---

## Actualizaciones después de entregar

**Antes de cualquier actualización en el cliente:** hacer backup de
`base_de_datos/alquileres.sqlite` (o pedirle al cliente que use el botón
"Backup" del Dashboard) y guardarlo fuera de la carpeta del programa.

### Caso 1 — Solo cambia el backend (`backend/app/`)

1. Reemplazar los archivos dentro de `backend/app/` con la versión nueva.
2. Si también cambió `backend/requirements.txt` (dependencias nuevas),
   ejecutar `update.bat` en la carpeta del cliente.
3. Ejecutar `start.bat` nuevamente. Las migraciones de columnas se aplican
   solas al arrancar (sin riesgo para los datos).

### Caso 2 — Solo cambia el frontend (`frontend/src/`)

1. En la máquina de desarrollo ejecutar `build-frontend.bat` (regenera
   `frontend/dist/`).
2. Copiar la carpeta `frontend/dist/` generada al paquete del cliente,
   reemplazando la anterior.
3. Reiniciar `start.bat`.

> Nunca copiar al cliente `frontend/src/` ni `node_modules/`; solo el
> `dist/` ya compilado.

### Caso 3 — Backend + frontend (funcionalidad completa)

1. Generar `frontend/dist/` con `build-frontend.bat`.
2. Backup de la base del cliente.
3. Copiar al cliente: `backend/app/` (+ `backend/requirements.txt` si cambió
   → `update.bat`), `frontend/dist/` y `start.bat` si cambió.
4. Ejecutar `start.bat` y verificar rápidamente una función de lo nuevo.

### Caso 4 — Actualización completa (ZIP nuevo)

1. Backup de `base_de_datos/alquileres.sqlite` del cliente, guardado fuera de
   la carpeta.
2. Reemplazar la carpeta completa con el ZIP nuevo.
3. Restaurar `alquileres.sqlite` del backup en `base_de_datos/`.
4. Ejecutar `start.bat`.

---

## Notas y recomendaciones

- Rutas relativas: el backend resuelve `base_de_datos/alquileres.sqlite` y
  `frontend/dist/` respecto de la raíz del proyecto. No usar rutas absolutas.
- Migraciones: si el backend agrega columnas o tablas, se aplican
  automáticamente al arrancar; no hace falta tocar la base a mano.
- Caché del navegador: si tras actualizar el frontend el cliente no ve los
  cambios, pedir modo incógnito o vaciar caché (o reiniciar la app).
- Antivirus/SmartScreen: la primera ejecución del Python embebido puede
  levantar avisos; el cliente puede aceptar o agregar la carpeta a
  excepciones.
- Certificado BCRA: el cálculo ICL consulta la API pública del BCRA
  (`api.bcra.gob.ar`); la PC del cliente necesita internet para esos cálculos.
- Validación final: probar el ZIP en una VM Windows limpia y confirmar que no
  haya que instalar nada.
