# Requerimientos — Depto Manager

---

## Stack Tecnológico

---

### Frontend

- **Framework:** React 18 con TypeScript
- **Build tool:** Vite
- **Estilos:** Tailwind CSS
- **Íconos:** Lucide React
- **HTTP client:** Axios

**Iniciar en desarrollo:**

```bash
cd frontend
npm run dev
```

El servidor de desarrollo queda disponible en `http://localhost:5173`.

---

### Backend

- **Lenguaje:** Python 3.13
- **Framework:** FastAPI
- **ORM / DB access:** SQLAlchemy + SQLite
- **Servidor ASGI:** Uvicorn
- **Validación:** Pydantic
- **Variables de entorno:** python-dotenv

**Iniciar en desarrollo:**

```bash
cd backend
.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

La API queda disponible en `http://localhost:8000`.
La documentación automática (Swagger) en `http://localhost:8000/docs`.

---

### Base de datos

- **Motor:** SQLite (archivo local)
- **Ubicación:** `base_de_datos/alquileres.sqlite`
- **Backups:** se generan desde la interfaz y se guardan en `backups/` con nombre `alquileres_YYYY-MM-DD_HH-mm.sqlite`

No requiere ningún servidor de base de datos. El archivo SQLite es portátil y se puede copiar, mover o respaldar directamente desde el explorador de archivos.

---

## Requerimientos Funcionales

- Gestionar departamentos (crear, editar, eliminar, ver estado ocupado/libre)
- Gestionar inquilinos (crear, editar, ver historial de contratos y pagos)
- Gestionar contratos (crear, editar, cerrar, adjuntar archivo PDF/DOCX)
- Soportar contratos que ya estaban activos antes de usar el sistema (campo "último aumento")
- Calcular automáticamente el alquiler mensual por contrato
- Registrar cobros mensuales por inquilino (alquiler + expensas + agua + luz)
- Marcar cobros como pagados (un pago es definitivo: consolida el aumento pendiente y no se puede revertir)
- Aplicar ajustes individuales o masivos al monto de un mes
- Registrar y cargar valores de agua y luz por departamento
- Calcular y mostrar el próximo aumento de cada contrato activo
- Aplicar aumentos automáticamente según porcentaje y periodicidad configurados
- Ver historial de cobros pasados con filtros por año, mes e inquilino
- Crear backups de la base de datos desde la interfaz
- Imprimir el listado de cobros del mes actual
- Descargar el archivo adjunto de un contrato

---

## Requerimientos No Funcionales

- La aplicación corre localmente sin conexión a internet
- No requiere instalación de Python ni Node en la PC del cliente
- Toda la información se almacena en una base de datos SQLite local
- El sistema se inicia con un doble clic en `start.bat`
- El navegador se abre automáticamente al iniciar
- Para desinstalar basta con borrar la carpeta del proyecto
- La interfaz es responsiva y funcional en navegadores modernos
- El sistema debe soportar impresión del dashboard desde el navegador
- Feedback unificado: cada operación exitosa (guardar, editar, eliminar, cobrar, ajustes,
  backup, etc.) muestra un toast global en verde con el mensaje correspondiente a la acción
- Los modales son compatibles con zoom del navegador: siempre puede verse y navegarse
  el contenido completo

---

## Ventanas

---

### Dashboard

Pantalla principal del sistema. Muestra el listado de cobros pendientes del mes en curso,
uno por cada contrato activo. Cada fila representa un inquilino y su departamento, con el
detalle de lo que debe abonar ese mes.

**Información visible por fila:**

- Departamento e inquilino
- Monto de alquiler calculado (con indicación si tiene ajuste manual aplicado)
- Expensa, agua, luz e impuesto (si aplican al contrato)
- Total a cobrar del mes
- Estado: pendiente de pago o pagado
- Nota de ajuste (si se ingresó una al aplicar override)

**Acciones generales (barra superior):**

- **Mostrar / Ocultar pagados:** alterna entre ver solo los pendientes o el historial de pagados del mes
- **Ajuste masivo:** permite seleccionar varios registros y aplicar un mismo delta de alquiler a todos a la vez
- **Backup:** crea una copia de seguridad de la base de datos en la carpeta `backups/`
- **Imprimir:** abre el diálogo de impresión del navegador con el listado del mes

**Acciones por fila:**

- **Marcar como pagado:** registra el pago del mes para ese inquilino (pide confirmación)
- **Ajuste individual (ícono de sliders):** abre el modal de override para modificar montos de ese mes

---

#### Modal: Ajuste individual de monto

Permite modificar el alquiler y/o expensa de un registro mensual puntual sin afectar el contrato.

**Campos:**

- **Modificación alquiler ($):** delta numérico que se suma o resta al alquiler calculado (puede ser negativo)
- **Modificación expensa ($):** delta numérico que se suma o resta a la expensa calculada
- **Nota:** texto libre para registrar el motivo del ajuste (opcional)

Botón **Restaurar** para volver a los valores calculados originalmente si ya tenía un override aplicado.

---

#### Modal: Confirmación de pago

Muestra el resumen del mes a cobrar antes de confirmar:

- Alquiler, expensa, agua, luz, impuesto y total
- Nota de ajuste si existe
- Botones: **Confirmar** / **Cancelar**

---

#### Modal: Ajuste masivo

Aparece al activar el modo de selección múltiple. Permite elegir varios registros con un checkbox
y aplicarles el mismo ajuste de alquiler.

**Campos:**

- **Modificación alquiler ($):** delta que se aplica a todos los seleccionados
- **Nota:** texto libre para todos los registros seleccionados

---

#### Panel: Historial de pagos

Se activa con el botón "Mostrar pagados". Muestra todos los registros ya cobrados con filtros:

- **Año** (selector)
- **Mes** (selector)
- **Inquilino** (selector)

Cada fila muestra: departamento, inquilino, mes/año, alquiler, expensa, agua, luz, total y nota.
Al hacer clic en una fila se abre el detalle del ajuste aplicado si lo tenía.

---

### Departamentos

Listado de todos los departamentos registrados. Se muestran como tarjetas en grilla.
Cada tarjeta indica el piso, código, dirección y si está **Ocupado** o **Libre** según si tiene
un contrato activo.

**Acciones por departamento:**

- **Editar:** abre modal para modificar los datos
- **Eliminar:** elimina el departamento (solo si no tiene contratos)
- **Ver historial de contratos:** abre modal con todos los contratos que tuvo ese departamento
- **Ver pagos:** abre modal con el historial de cobros del departamento

---

#### Modal: Crear / Editar departamento

**Campos:**

- **Piso:** selector (PB, 1°, 2°, 3°, etc.)
- **Código:** texto libre (ej: "A", "B", "101")
- **Dirección:** texto libre opcional (ej: "Av. Corrientes 1234")

---

#### Modal: Historial de contratos del departamento

Lista todos los contratos vinculados al departamento, ordenados por fecha de inicio descendente.
Muestra: inquilino, fecha de inicio, fecha de fin y estado del contrato.

---

#### Modal: Pagos del departamento

Muestra todos los registros mensuales cobrados para ese departamento.
Permite filtrar por año y mes. Muestra: mes/año, inquilino, alquiler, expensa, agua, luz y total.

---

### Inquilinos

Listado de todos los inquilinos del sistema en formato tabla.
Incluye buscador por nombre en tiempo real.

**Columnas:**

- Nombre y apellido
- Teléfono
- Estado (Activo / Inactivo)
- Acciones

**Acciones por inquilino:**

- **Editar:** abre modal para modificar datos
- **Eliminar:** elimina el inquilino (solo si no tiene contratos)
- **Ver contratos:** abre modal con el historial de contratos del inquilino
- **Ver pagos:** abre modal con el historial de cobros del inquilino

---

#### Modal: Crear / Editar inquilino

**Campos:**

- **Nombre y apellido:** texto libre
- **Teléfono:** texto libre (opcional)
- **Es actual:** checkbox para indicar si es un inquilino vigente o uno anterior que ya no está

---

#### Modal: Contratos del inquilino

Lista todos los contratos del inquilino, ordenados por fecha de inicio descendente.
Muestra: departamento, fecha de inicio, fecha de fin, monto de alquiler y estado.

---

#### Modal: Pagos del inquilino

Muestra todos los registros mensuales cobrados para ese inquilino.
Permite filtrar por año y mes. Muestra: mes/año, departamento, alquiler, expensa, agua, luz y total.

---

### Contratos

Listado de contratos dividido en dos secciones: **Activos** y **Finalizados**.
Incluye filtros por inquilino, departamento y estado.

**Información visible por contrato:**

- Departamento e inquilino
- Fecha de inicio y vencimiento
- Estado: Activo, Por vencer (≤3 meses), Vencido, Finalizado
- Monto de alquiler base actual
- Expensas (si aplica)
- Porcentaje y periodicidad de aumento
- Servicios incluidos (agua, luz)
- Ícono de archivo adjunto si tiene contrato subido

**Acciones por contrato:**

- **Editar:** abre modal con todos los datos del contrato
- **Cerrar contrato:** marca el contrato como finalizado (pide confirmación)
- **Descargar archivo:** descarga el PDF/DOCX adjunto (si existe)

---

#### Modal: Crear contrato

**Campos:**

- **Departamento:** selector (solo muestra los disponibles / libres)
- **Inquilino:** selector (solo muestra inquilinos activos sin contrato vigente)
- **Fecha de inicio**
- **Fecha de vencimiento**
- **Alquiler base actual ($)**
- **Impuesto ($):** campo opcional. Monto fijo mensual, NO participa de los aumentos.
- **Expensas base ($):** campo opcional, se habilita con el toggle "Cobra expensas"
- **Cobra expensas / agua / luz:** toggles para indicar qué servicios incluye el contrato
- **Porcentaje de aumento (%):** obligatorio cuando el tipo de aumento es MANUAL (no se pide con ICL ni SIN_AUMENTO)
- **Periodicidad (meses):** cuántos meses entre cada aumento (ej: 3, 6, 12); no se pide con SIN_AUMENTO
- **¿Contrato ya en curso?:** checkbox. Si se activa, aparecen los campos obligatorios:
  - **Alquiler inicial del contrato:** monto con el que comenzó (histórico, no se usa para calcular aumentos)
  - **Alquiler actual (último cobro):** monto que se cobra actualmente; es la base de los próximos aumentos
  - **Fecha del último aumento:** para que el sistema calcule correctamente el próximo aumento
  - Si además cobra expensas: **Expensa inicial del contrato** y **Expensa actual (último cobro)**
- **Archivo adjunto:** selector de archivo PDF o DOCX (opcional)

Los campos con asterisco (\*) son obligatorios: se muestran en **rojo** y, si se envía el
formulario sin completarlos, el campo se resalta con un borde rojo intenso y aparece un
popup listando los campos faltantes.

Al editar el alquiler/expensa actual de un contrato, los registros mensuales del mes
en curso y futuros (no pagados y sin ajuste manual) se recalculan automáticamente
para reflejar el nuevo valor; los meses ya pagados no se modifican.

---

#### Modal: Editar contrato

Mismos campos que crear, con las siguientes diferencias:

- El departamento e inquilino no son modificables
- Si el contrato ya tiene registros pagados, la fecha de inicio queda bloqueada
- Se puede subir o reemplazar el archivo adjunto

---

### Servicios

Pantalla para cargar los valores de agua y luz del mes en curso.
Solo muestra los departamentos cuyos contratos tienen habilitado el cobro de agua y/o luz,
cuyo registro del mes no esté cobrado, y cuyo valor esté pendiente **o ya cargado**.

**Columnas de la tabla:**

- Departamento
- Inquilino
- Agua ($): campo numérico editable (solo si el contrato cobra agua; si no, muestra "No cobra")
- Luz ($): campo numérico editable (solo si el contrato cobra luz; si no, muestra "No cobra")
- Estado: badge **Pendiente** (amarillo) o **Cargado** (verde)
- Acción: botón **Guardar** (o **Actualizar** si ya estaba cargado) por fila

Los servicios ya cargados permanecen visibles y **se pueden editar** hasta que el cobro
del mes sea registrado como pagado en el Dashboard; en ese momento desaparecen del listado.

---

### Aumentos

Vista de todos los contratos activos con el detalle del próximo aumento calculado.
Cada contrato se muestra como una tarjeta con la información completa.

**Información por tarjeta:**

- Departamento e inquilino
- Dirección del departamento (si tiene)
- Porcentaje de aumento configurado y periodicidad (ej: "10% cada 3 meses")
- Fecha del próximo aumento (mes y año)
- Alerta de estado: **Vencido** (en rojo) o **Por vencer** (en amarillo)

**Cuadros de montos proyectados** (si el sistema puede calcularlos):

- Alquiler actual
- Alquiler nuevo tras el aumento (con el incremento en $)
- Expensa actual y expensa nueva (si el contrato cobra expensas)

**Alerta especial:**
Si el contrato fue cargado como "ya en curso" pero no tiene la fecha del último aumento completada,
se muestra un aviso indicando que hay que editar el contrato para que el cálculo sea correcto.

---

#### Regla de negocio obligatoria — Cálculo de ajuste por ICL

Cuando un contrato tiene tipo de aumento **ICL**, el sistema determina el nuevo alquiler
consultando el Índice para Contratos de Locación publicado por el BCRA para el período
completo que termina el día anterior al inicio de la nueva vigencia.

**¿Cómo se construye el período a consultar?**

La duración del período es igual a la periodicidad de aumento del contrato.
El período finaliza el último día del mes inmediatamente anterior al mes en que entra en vigencia
el nuevo valor. El período comienza tantos meses antes como indique la periodicidad.

Ejemplo con periodicidad 4 meses:

|                          | Fecha                    |
| ------------------------ | ------------------------ |
| Inicio del período       | 01/03/2026               |
| Fin del período          | 30/06/2026               |
| Vigencia del nuevo valor | 01/07/2026 al 31/10/2026 |

**¿Qué valores se toman de la API del BCRA?**

La API devuelve un registro diario por cada día hábil del período. El sistema toma únicamente
dos valores:

- **ICL Inicial:** el valor publicado para la fecha de inicio del período.
- **ICL Final:** el valor publicado para la fecha de fin del período.

**Fórmula:**

```
Coeficiente = ICL Final / ICL Inicial

Nuevo Alquiler = Alquiler Actual × Coeficiente
```

**Ejemplo numérico:**

```
Alquiler Actual:           $500.000

ICL Inicial (01/03/2026):    25,00
ICL Final   (30/06/2026):    28,50

Coeficiente = 28,50 / 25,00 = 1,14

Nuevo Alquiler = $500.000 × 1,14 = $570.000
```

**Resultado:**

- Variación ICL: 14 %
- Nuevo Alquiler: $570.000
- Vigencia: 01/07/2026 al 31/10/2026

**¿Qué pasa si el BCRA todavía no publicó el valor para la fecha final?**

El cálculo no puede realizarse. El sistema muestra el estado **"ICL pendiente de cálculo"**,
informa la última fecha disponible publicada por el BCRA y estima cuántos días faltan para
que el período esté completo. No se muestran montos ni porcentajes estimados hasta tanto
el dato esté disponible.

---

## Sistema de aumentos — Estados e historial (Punto 1)

---

### Tipos de aumento

- **MANUAL:** aumento por porcentaje fijo (porcentaje_aumento) cada periodicidad_aumento_meses.
- **ICL:** aumento calculado con el índice del BCRA (ver regla más arriba).
- **SIN_AUMENTO:** el contrato no recibe aumentos automáticos. No se calcula próximo aumento,
  no se aplica ninguno y no se genera historial. 	ipo_aumento es la fuente de verdad;
  el porcentaje y la periodicidad no intervienen en ninguna decisión.

---

### Ciclo de vida de un aumento: PENDIENTE → CONSOLIDADO

- Cuando corresponde un aumento (y el contrato sigue vigente), el sistema calcula la propuesta,
  crea una fila en historial_aumentos con estado **PENDIENTE** y aplica el aumento al contrato.
- Mientras está PENDIENTE, el monto queda preparado para futuras correcciones manuales (Punto 2).
- Cuando el usuario marca el mes como **cobrado** desde el Dashboard, el aumento PENDIENTE de ese
  contrato/período pasa automáticamente a **CONSOLIDADO** y queda inmutable (historia).
- Un pago es definitivo: no existe "desmarcar pagado".
- Si el mes no tenía aumento, cobrar no consolida nada (no hay error).

---

### Propuesta vs. aplicado

- **Propuesto:** monto y porcentaje calculados originalmente por el sistema; quedan congelados.
- **Aplicado:** monto y porcentaje que efectivamente corresponden cobrar. En esta etapa
  aplicado == propuesto; en la próxima iteración el usuario podrá corregir el aplicado
  (y los porcentajes de Alquiler y Expensa quedan almacenados de manera independiente).
- **Una propuesta ya generada NO cambia** si luego se edita la configuración del contrato
  (ej. 10% → 15%): el nuevo porcentaje se usará recién para el próximo aumento que aún
  no haya sido generado. Esta regla está protegida en backend, no solo en la UI.

---

### Historial de aumentos (historial_aumentos)

- Tabla nueva, fuente de verdad del historial. PK: id_historial_aumentos.
- UNIQUE (id_contratos, anio, mes): no pueden existir dos aumentos para el mismo contrato y período.
- Guarda montos y porcentajes de Alquiler y Expensa por separado, y la auditoría ICL completa
  (coeficiente, ICL inicial/final y fechas del período consultado al BCRA).
- La vista "Historial de aumentos" lee directamente de esta tabla: muestra el detalle
  (propuesto vs. aplicado, expensa, ICL) expandiendo la fila.
- El historial antiguo (reconstruido desde egistros_mensuales) **NO se migra**:
  la tabla empieza a funcionar desde esta implementación.
- porcentaje_aumento_usado (en registros mensuales) queda temporalmente como campo legacy
  de compatibilidad; ya no es la fuente de verdad del historial.

---

### Regla de vencimiento (fecha_fin)

Si el mes en que correspondería el aumento es **posterior al mes de echa_fin**, el aumento
no se aplica: no se modifica el contrato ni se crea historial. Si el aumento cae en el mismo
mes de vencimiento, sí puede aplicarse. La protección existe en backend, no solo visualmente.
