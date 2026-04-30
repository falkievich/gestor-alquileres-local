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

### Si solo cambia el código del backend:
1. Reemplazar los archivos dentro de `backend/app/` con la versión nueva
2. Si hay nuevas dependencias: ejecutar `update.bat`
3. Volver a ejecutar `start.bat`

### Si cambia el frontend:
1. En la máquina de desarrollo ejecutar `build-frontend.bat`
2. Copiar la carpeta `frontend/dist/` generada y reemplazar la del cliente

### Si cambia TODO (actualización completa):
1. Reemplazar la carpeta completa del proyecto con el ZIP nuevo
2. (Antes de reemplazar, hacer backup de `base_de_datos/alquileres.sqlite` si hay datos del cliente)

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
