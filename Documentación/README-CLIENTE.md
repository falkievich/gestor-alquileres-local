# Depto Manager — Guía de uso

## Requisitos

Ninguno. No es necesario instalar Python, Node ni ninguna dependencia.
Todo lo necesario está incluido en esta carpeta.

---

## Cómo ejecutar

1. Doble clic en **`start.bat`**
2. Se abrirá el navegador automáticamente en `http://127.0.0.1:8000`
3. Para cerrar el programa, cerrá la ventana de terminal que se abrió

---

## Estructura de la carpeta

```
DeptoManager/
├── start.bat               ← Ejecutar la aplicación
├── update.bat              ← Actualizar dependencias (solo para el desarrollador)
├── build-frontend.bat      ← Regenerar interfaz (solo para el desarrollador)
├── python/                 ← Python embebido (no tocar)
├── backend/                ← Código del servidor
│   ├── app/
│   └── requirements.txt
├── frontend/
│   └── dist/               ← Interfaz web generada (no tocar)
└── base_de_datos/
    └── alquileres.sqlite   ← Base de datos (aquí están tus datos)
```

---

## Cómo desinstalar

Simplemente **borrá esta carpeta completa**.
No queda nada instalado en el sistema (ni Python, ni librerías, ni configuraciones).

---

## Cómo actualizar (para el desarrollador)

**Antes de cualquier actualización:** si el cliente ya tiene datos cargados, hacer backup de `base_de_datos/alquileres.sqlite` (o pedirle que use el botón "Backup" del Dashboard).

---

### Caso 1: Solo cambia el código del backend (`backend/app/`)
Cuando: cambiaste archivos Python del backend pero NO tocaste el frontend ni `requirements.txt`.

1. Reemplazar los archivos dentro de `backend/app/` con la versión nueva
2. Volver a ejecutar `start.bat`

Si también cambiaste `requirements.txt` (nuevas dependencias):
1. Reemplazar los archivos de `backend/app/` y `backend/requirements.txt`
2. Ejecutar `update.bat` (instala las dependencias nuevas en el Python embebido)
3. Volver a ejecutar `start.bat`

---

### Caso 2: Solo cambia el frontend (`frontend/src/`)
Cuando: cambiaste código React pero NO el backend.

1. En la máquina de desarrollo ejecutar `build-frontend.bat` (regenera `frontend/dist/`)
2. Copiar la carpeta `frontend/dist/` generada y reemplazar la del cliente
3. Volver a ejecutar `start.bat`

⚠️ Importante: al cliente **nunca se le copia `frontend/src/` ni `node_modules/`**, solo la carpeta `dist/` ya compilada.

---

### Caso 3: Cambian el backend y el frontend (ej. nueva funcionalidad completa)
Cuando: los cambios incluyen código Python y React a la vez.

1. En la máquina de desarrollo ejecutar `build-frontend.bat`
2. Hacer backup de `base_de_datos/alquileres.sqlite` del cliente
3. Copiar al cliente:
   - `backend/app/` (y `backend/requirements.txt` si cambió → + `update.bat`)
   - `frontend/dist/` (la versión ya compilada)
   - `start.bat` si cambió
4. Ejecutar `start.bat`: si el backend agrega columnas o tablas nuevas a la base, la migración corre automáticamente al arrancar (no hay que tocar la DB a mano, los datos existentes se conservan)
5. Verificación rápida: abrir la app y probar una función de lo nuevo (ej. editar un contrato)

---

### Caso 4: Actualización completa (ZIP nuevo)
Cuando: hay muchos cambios dispersos y es más seguro reemplazar todo.

1. Hacer backup de `base_de_datos/alquileres.sqlite` del cliente y guardarlo fuera de la carpeta
2. Reemplazar la carpeta completa del proyecto con el ZIP nuevo
3. Restaurar el `alquileres.sqlite` del backup en `base_de_datos/`
4. Ejecutar `start.bat`

---

### ¿Cuándo NO hay que hacer nada extra?
- Si el backend agrega columnas a tablas existentes (migraciones livianas): se aplican solas al ejecutar `start.bat`, sin pasos manuales ni riesgo para los datos.
- Si solo cambió `start.bat`, `build-frontend.bat` u otros scripts: copiar únicamente ese archivo.

---

## Base de datos

Los datos se guardan en `base_de_datos/alquileres.sqlite`.
Si querés hacer un backup manual, copiá ese archivo a otro lugar.

El sistema también tiene backup integrado desde la interfaz (botón "Backup" en el Dashboard).

---

## Problemas frecuentes

**El navegador no se abre solo:**
→ Abrir manualmente `http://127.0.0.1:8000` en el navegador

**Puerto 8000 en uso:**
→ Cerrar otra instancia del programa o reiniciar la PC

**Error al iniciar:**
→ Verificar que la carpeta `python/` existe y contiene `python.exe`
→ Ejecutar `update.bat` para reinstalar dependencias
