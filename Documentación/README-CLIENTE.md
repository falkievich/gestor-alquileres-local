# Depto Manager — Guía para el cliente

## Requisitos

Ninguno. No hay que instalar Python, Node ni ninguna dependencia:
todo está incluido en esta carpeta.

> Nota: para calcular aumentos con **ICL** la PC necesita conexión a
> internet en el momento del cálculo (consulta el índice publicado por el
> BCRA). Todo el resto del programa funciona sin internet.

---

## Cómo abrir

1. Doble clic en **`start.bat`**
2. Se abre el navegador automáticamente en `http://127.0.0.1:8000`
3. Para cerrar el programa, cierra la ventana de terminal que se abrió

---

## Estructura de la carpeta (lo mínimo que hay que saber)

```
DeptoManager/
├── start.bat               ← Ejecutar la aplicación (doble clic)
├── python/                 ← No tocar
├── backend/                ← No tocar
├── frontend/dist/          ← No tocar
├── base_de_datos/
│   └── alquileres.sqlite   ← Tus datos están acá
└── backups/                ← Copias de seguridad generadas por el sistema
```

Todo lo demás: no tocar.

---

## Dónde están tus datos

- Todos los datos se guardan en `base_de_datos/alquileres.sqlite`.
- Los archivos de contratos (PDF/DOCX) también quedan dentro de esa base.

---

## Cómo hacer backup

- Opción recomendada: botón **Backup** en el Dashboard. Guarda una copia
  automática en la carpeta `backups/` (con fecha y hora en el nombre).
- Backup manual: con el programa **cerrado**, copiar
  `base_de_datos/alquileres.sqlite` a otra carpeta (pen drive, etc.).
- Se recomienda hacer backup con frecuencia, especialmente antes de
  actualizaciones del sistema.

---

## Cómo desinstalar

Simplemente borra esta carpeta completa.
No queda nada instalado en el sistema (ni Python, ni librerías, ni
configuraciones). Si querés conservar los datos, antes copiá
`base_de_datos/alquileres.sqlite` a otro lugar.

---

## Problemas frecuentes

**El navegador no se abre solo:**
→ Abrir manualmente `http://127.0.0.1:8000` en el navegador.

**Puerto 8000 en uso:**
→ Cerrar otra instancia del programa (otra ventana de terminal abierta) o
reiniciar la PC.

**Error al iniciar / falta `python.exe`:**
→ Verificar que la carpeta `python/` existe dentro de esta carpeta.
Si falta alguna librería, contactar al soporte para reinstalarla
(el técnico puede ejecutar `update.bat`).

**La primera vez, Windows o el antivirus muestra un aviso:**
→ Es normal con programas portable. Elegir "Ejecutar igualmente" o agregar
la carpeta a las excepciones del antivirus.

**No calcula el aumento de un contrato ICL y aparece "pendiente":**
→ Es normal si el BCRA todavía no publicó los valores del período; la
pantalla indica la última fecha disponible y cuántos días faltan.
Verificar conexión a internet y volver a entrar más tarde.

**Actualicé y no veo los cambios:**
→ Cerrar el programa, volver a abrirlo; si sigue igual, abrir el navegador
en modo incógnito o vaciar la caché.
