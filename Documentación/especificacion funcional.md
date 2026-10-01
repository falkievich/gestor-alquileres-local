# Especificación funcional — Depto Manager

Este documento describe QUÉ hace el sistema y sus reglas de negocio.
El CÓMO está implementado corresponde a `arquitectura tecnica.md`, el modelo de
datos a `modelo de datos.md` y las reglas visuales a `convenciones ui.md`.

---

## Módulos del sistema

La aplicación se organiza en seis secciones (pestañas de navegación):

- **Dashboard** — cobros del mes e historial de pagos
- **Departamentos** — abm de departamentos y sus historiales
- **Inquilinos** — alta/edición de inquilinos y sus historiales
- **Contratos** — alta, edición, cierre y adjuntos de contratos
- **Servicios** — carga de valores de agua y luz por mes
- **Aumentos** — próximos aumentos, pendientes de consolidar e historial

Además: **backups** de la base de datos e **impresión** del listado de cobros.

---

## Dashboard

Pantalla principal. Muestra los cobros pendientes del mes en curso, uno por fila
por contrato activo, con el detalle de lo que debe abonar ese inquilino.

**Composición de cada fila:**

- Departamento (piso + código) e inquilino.
- **Alquiler:** monto calculado (o el ajuste manual si hay), con indicador
  "Ajustado" si tiene override aplicado.
- **Expensa** (si el contrato cobra expensa), **agua**, **luz** e **impuesto**
  (si corresponden; si no, se muestra "—").
- **Total del mes:** alquiler + expensa + agua + luz + impuesto, siempre sobre
  los valores efectivos (override si existe, si no el calculado).
- **Estado de servicios:** `OK` o `Pendiente` (ver Servicios).
- **Estado de pago:** pendiente, o pagado con el mes consignado.
- **Estado del contrato:** Vencido (badge rojo) cuando `fecha_fin` ya pasó.

### Acciones generales

- **Mostrar / Ocultar pagados:** alterna entre la vista de cobros del mes y el
  historial de pagos con filtros.
- **Ajuste masivo:** activa el modo de selección múltiple y aplica el mismo
  delta de alquiler a varios registros a la vez.
- **Backup:** crea una copia de la base de datos en la carpeta `backups/`.
- **Imprimir:** abre el diálogo de impresión del navegador con el listado del mes.
- **Actualizar:** vuelve a consultar el mes (útil tras cargar servicios).

### Ajuste individual (override)

El modal de ajuste permite modificar alquiler y/o expensa de un registro
mensual puntual sin afectar el contrato:

- Se ingresan **deltas** ($ que se suman o restan; pueden ser negativos) con
  vista previa del monto resultante.
- La modificación es **acumulativa**: el delta se aplica sobre el valor
  efectivo actual (override + calculado).
- **Nota** opcional para registrar el motivo; se muestra en la fila y en el
  historial de pagos.
- **Restaurar:** devuelve los montos a los valores calculados originalmente
  (limpia los overrides). Puede usarse todas las veces que se quiera mientras
  el mes no esté cobrado.
- No se permite ajustar meses posteriores a la fecha de vencimiento del
  contrato (rechazo del backend).

### Ajuste masivo

- Se activa el modo selección con checkboxes, uno por fila.
- Regla: **la selección masiva solo incluye registros del mes en curso**.
  Los registros atrasados no tienen checkbox y quedan automáticamente
  excluidos.
- Permite elegir varios registros y aplicar el mismo delta de alquiler a todos,
  con nota única; se aplican en paralelo como ajustes individuales.
- El "seleccionar todos" también opera solo sobre los cobrables del mes.

### Pago definitivo

- Un cobro se marca como pagado con confirmación previa (desglose de
  alquiler, expensa, agua, luz, impuesto y total).
- El pago es **definitivo: no existe "desmarcar pagado"**.
- No se puede marcar pagado si hay **servicios pendientes** de cargar.
- No se puede cobrar un mes **posterior** a la fecha de vencimiento del
  contrato (el mes de vencimiento sí es cobrable).
- Al cobrar un mes que tenía un aumento **PENDIENTE**, ese aumento pasa
  automáticamente a **CONSOLIDADO** y queda inmutable (ver Aumentos).
- Un atrasado se cobra igual que cualquier mes: con sus montos históricos
  congelados; no se regeneran ni recalculan.

### Historial de pagos (Mostrar pagados)

- Lista todos los registros **pagados** con filtros combinables: **año**,
  **mes** e **inquilino**; ordenado del mes más reciente al más viejo.
- Cada fila muestra: mes/año, departamento, inquilino, montos efectivos de
  alquiler/expensa/agua/luz/impuesto y total.
- Las filas con ajuste manual muestran un indicador **"Ajustado"** y el botón
  **Ver ajuste**, que abre el detalle comparando valor original vs. valor
  cobrado (con el delta) y la nota del ajuste.

### Cobros atrasados (meses anteriores sin cobrar)

- El Dashboard también lista los registros de meses anteriores que siguen sin
  pagar, con sus **montos históricos congelados** (no se regeneran ni
  recalculan; los ajustes manuales previos se conservan).
- Se muestran **arriba** del mes en curso, ordenados del más antiguo al más
  reciente, identificados con el badge **"Atrasado · Mes Año"** (ver
  convenciones ui).
- Solo aparecen pendientes de **contratos activos**; los pendientes de
  contratos cerrados quedan en la base de datos pero no reaparecen en las
  vistas operativas.
- Un atrasado se cobra normalmente (con las mismas guardas: servicios OK,
  vigencia); su **pago consolida el aumento PENDIENTE de su propio período**,
  no el del mes en curso.
- Los atrasados quedan **fuera del ajuste masivo** (sin checkbox de selección);
  sí aceptan ajuste individual.

---

## Servicios

Pantalla para cargar los valores de **agua y luz** por departamento.

**Qué se muestra:**

- Filas por contrato activo que cobra agua y/o luz (`cobra_agua` / `cobra_luz`),
  cuyo registro del mes no esté cobrado.
- Columnas Agua ($) y Luz ($): campos numéricos editables si el contrato cobra
  el servicio; si no, muestra **"No cobra"**.
- **Estado** por fila: **Pendiente** o **Cargado**.
- Acción por fila: **Guardar** (o **Actualizar** si ya tenía valores).

**Reglas:**

- El registro mensual del mes se crea automáticamente al abrir la pantalla
  (misma mecánica que el Dashboard) y congela el alquiler/expensa del momento.
- Los servicios ya cargados permanecen visibles y **se pueden editar**
  hasta que el cobro del mes sea registrado como pagado; al quedar pagado el
  registro ya no aparece (y no se puede volver a editar).
- No se puede editar el servicio de un mes ya cobrado (rechazo del backend).
- No se pueden cargar servicios de meses posteriores al vencimiento del
  contrato (el mes de vencimiento sí es válido).

**Servicios atrasados:**

- También se listan los registros de meses anteriores sin cobrar, que todavía
  requieren cargar agua/luz, ordenados del más antiguo al más reciente y con el
  badge **Atrasado · Mes Año** (solo lectura de montos, misma convención ámbar).
- El encabezado de la pantalla siempre indica el **mes actual** (no se confunde
  con el primer atrasado del listado).
- Los servicios atrasados son de contratos activos; el mes de vencimiento sí es
  cargable, los posteriores no.

---

## Departamentos

Listado de departamentos en tabla con métricas (totales / ocupados / libres),
estado **Ocupado / Libre** (según tenga o no contrato activo) y acciones:

- **Crear / editar:** piso (Planta baja o Piso 1–3), código (ej. "1A") y
  dirección opcional.
- **Eliminar:** rechazado si el departamento tiene contratos asociados.
- **Historial de contratos:** modal con todos los contratos del departamento
  (inquilino, fechas, estado), ordenado de más reciente a más viejo.
- **Ver pagos:** modal con los registros mensuales cobrados del departamento,
  con filtros por año y mes.

Un departamento **libre** es requisito para crear un contrato: no puede existir
más de un contrato activo por departamento.

---

## Inquilinos

Listado con buscador por nombre (ignora mayósculas y acentos), estado
**Actual / Anterior** (`es_actual`) y acciones:

- **Crear / editar:** nombre y apellido (obligatorio), teléfono (opcional) y
  estado actual/anterior.
- **Ver contratos:** historial de contratos del inquilino, ordenado descendente.
- **Ver pagos:** historial de cobros del inquilino con filtros por año y mes.
- **Eliminar:** rechazado si el inquilino tiene contratos asociados.

En el alta de contratos solo pueden seleccionarse inquilinos **actuales**
que no tengan otro contrato activo vigente.

---

## Contratos

Listado dividido en pestañas **Activos** y **Finalizados**, con filtros por
inquilino y departamento.

**Estado visible por contrato** (calculado en la interfaz comparando la fecha
de vencimiento con la fecha de hoy, contando **meses de calendario**):

- **Vencido:** el contrato sigue activo pero `fecha_fin` ya pasó.
- **Por vencer:** quedan **3 meses o menos** hasta el mes de vencimiento.
  Se aplica igual en Contratos y en Aumentos.
- **Activo:** vigente con vencimiento futuro.
- **Finalizado:** cerrado manualmente por el usuario.

Cada fila muestra también los servicios que incluye el contrato (Expensa,
Impuesto, Agua, Luz).

### Creación de contrato

Campos:

- **Departamento:** solo los **libres**.
- **Inquilino:** solo inquilinos actuales sin contrato activo vigente.
- **Fecha de inicio** y **fecha de vencimiento** (obligatorias).
- **Tipo de aumento** (obligatorio): MANUAL, ICL o SIN_AUMENTO (ver Aumentos).
- **Alquiler base** (monto vigente con el que comienza a cobrarse).
- **Expensa base** (si el contrato cobra expensas).
- **Impuesto fijo** (opcional): monto fijo mensual; **no participa de los
  aumentos** y no se recalcula.
- **Cobra expensas / agua / luz:** toggles según los servicios que incluye.
- **Porcentaje de aumento:** obligatorio y mayor a 0 solo con MANUAL.
- **Periodicidad de aumento (meses):** obligatoria y mayor a 0 salvo con
  SIN_AUMENTO (cuántos meses entre aumentos: 1, 3, 4, 6, 12, etc.).
- **Archivo adjunto:** PDF o DOCX (opcional).

Al crear el contrato el departamento queda marcado ocupado y, si el usuario
no cargó montos históricos iniciales, el sistema iguala "inicial" al monto
actual registrado.

### Contrato ya en curso

Si el contrato comenzó antes de usar el sistema, el checkbox **"¿Este contrato
ya lleva un tiempo en curso?"** abre los campos obligatorios:

- **Alquiler inicial del contrato** y, si cobra expensas, **expensa inicial**:
  montos con los que comenzó (históricos, no se usan para calcular aumentos).
- **Alquiler actual (último cobro)** y **expensa actual**: los montos que se
  cobran hoy; son la base de los próximos aumentos.
- **Fecha del último aumento:** el sistema calcula el próximo aumento a partir
  de esta fecha + la periodicidad, tomando como base el alquiler actual.

Si un contrato no tiene fecha de último aumento (ni registro de aumentos
previos), Aumentos lo señala para que se complete la fecha editando el
contrato.

### Edición de contrato

- Departamento e inquilino **no son modificables** una vez creado.
- **Fecha de inicio bloqueada** cuando el contrato ya tiene meses cobrados
  (cambiarla alteraría el calendario de aumentos).
- Al editar el alquiler/expensa actual o el impuesto fijo, los registros
  mensuales **no pagados, sin ajuste manual y del mes en curso en adelante**
  (hasta el mes de vencimiento) se recalculan automáticamente; los meses ya
  cobrados no se tocan.
- Se pueden subir o reemplazar el archivo adjunto en cualquier momento.

### Cierre de contrato

- **Cerrar contrato:** lo marca como finalizado (con confirmación).
  Libera el departamento si no hay otros contratos activos en él, y el
  inquilino queda como "Anterior" si ya no tiene contratos activos.
- El cierre manual es independiente de la fecha de vencimiento: un contrato
  puede cerrarse aunque su `fecha_fin` sea futura, y un contrato cuya
  `fecha_fin` ya pasó aparece "Vencido" mientras no se cierre.

### Adjuntos

- Solo se aceptan archivos **.pdf** y **.docx**.
- Se guardan dentro de la base de datos (no como archivos sueltos).
- **Descargar archivo:** descarga el PDF/DOCX adjunto del contrato.

---

## Aumentos

### Tipos de aumento

- **MANUAL:** aumento por porcentaje fijo (`porcentaje_aumento`) cada
  `periodicidad_aumento_meses`.
- **ICL:** aumento calculado con el índice del BCRA (reglas más abajo).
- **SIN_AUMENTO:** el contrato no recibe aumentos automáticos: no se calcula
  próximo aumento, no se aplica ninguno y no se genera historial.
  El porcentaje y la periodicidad no intervienen en ninguna decisión.

### Próximo aumento (proyección)

La vista **Aumentos → Próximos aumentos** muestra, por contrato activo, una
tarjeta con:

- Departamento, inquilino, dirección y alerta de estado (Vencido / Por vencer).
- Tipo y periodicidad (ej. "10 % cada 3 meses").
- Fecha del próximo aumento y montos proyectados: alquiler actual → nuevo (con
  la diferencia en $ y el porcentaje), y expensa actual → nueva si cobra expensa.
- Estados: "Sin aumentos" (SIN_AUMENTO o periodicidad 0), "ICL pendiente" / "ICL
  calculado", "Próximo aumento planificado" o alerta de últimos 3 meses.
- Alerta especial si al contrato "ya en curso" le falta la fecha del último
  aumento: hay que editar el contrato para que el cálculo sea correcto.
- Si el próximo aumento cae en un mes **posterior al mes de vencimiento**, la
  tarjeta queda marcada en rojo con "Sin más aumentos" (nunca se aplicará).

La proyección es **solo lectura**: un próximo aumento todavía no puede
modificarse anticipadamente.

### Ciclo de vida: PENDIENTE → CONSOLIDADO

- Cuando llega la vigencia de un aumento (y el contrato sigue activo), el
  sistema calcula la propuesta, **aplica el aumento** a los montos vigentes del
  contrato y registra el evento en la tabla `historial_aumentos` (fuente de
  verdad del historial) con estado **PENDIENTE**.
- Mientras está PENDIENTE, los montos aplicados son corregibles (ver más abajo).
- Cuando el usuario **cobra el mes**, el aumento PENDIENTE de ese
  contrato/período pasa automáticamente a **CONSOLIDADO**: queda inmutable como
  histórico, con fecha de consolidación.
- Cada registro del historial es único por contrato y período (año/mes): no
  pueden existir dos aumentos para el mismo período.
- La **propuesta ya generada no cambia** si luego se edita la configuración del
  contrato (ej. 10 % → 15 %): el nuevo valor se usa recién para el próximo
  aumento que aún no se haya generado. La regla vale para MANUAL e ICL y está
  protegida en backend.
- Un aumento **no se aplica nunca** si su período de vigencia cae en un mes
  posterior al mes de `fecha_fin`; si cae **en el mismo mes de vencimiento,
  sí** puede aplicarse.
- El aumento nunca deja montos por debajo del valor anterior (bloquea ICL
  negativos).

### Modificación de un aumento PENDIENTE

Los aumentos ya generados cuyo mes todavía **no fue cobrado** aparecen en el
bloque **"Aumentos pendientes de consolidar"** (encima del listado de
próximos), con el botón **"Modificar aumento"**:

- Se editan los **montos a aplicar** de alquiler y/o expensa de forma
  independiente. Los porcentajes aplicados **no son editables**: se recalculan
  siempre respecto del monto anterior y se muestran solo como referencia.
- Regla de validación: `monto aplicado >= monto anterior`. Puede ser menor,
  igual o mayor que la propuesta (igual al anterior → 0 %).
- **Restaurar propuesta:** devuelve los montos a aplicar a los valores
  propuestos originales (hay que Guardar para confirmar).
- Puede modificarse **todas las veces que se quiera** mientras esté PENDIENTE.
  La propuesta original (montos, porcentajes, datos ICL, tipo, período) queda
  congelada para auditoría.
- **Bloqueo de pendientes viejos:** si para el mismo contrato ya existe un
  aumento generado posterior (mes mayor), el PENDIENTE anterior **solo puede
  cobrarse, no modificarse** (modificarlo rompería la continuidad de los
  montos). La interfaz deshabilita el botón y el backend rechaza la operación.
- La modificación recalcula el registro mensual del período: al cobrar el mes,
  el aumento consolidado refleja el monto aplicado final.

### Pestaña Historial de aumentos

- Muestra los aumentos **CONSOLIDADO** (los ya cobrados), con filtros por
  inquilino, año y mes.
- Cada fila se expande con el detalle completo: propuesto vs. aplicado
  (alquiler y expensa por separado), los datos ICL del período consultado
  (coeficiente, valores inicial/final y fechas) y la fecha de consolidación.
- Si el monto aplicado difiere del propuesto, el detalle lo indica
  ("corregido manualmente").

---

## Reglas de negocio del ICL

**Qué representa:** el ICL (Índice para Contratos de Locación) es el índice
publicado por el BCRA que sirve para actualizar el valor de los alquileres.

**Período a consultar:** la duración es igual a la periodicidad del contrato.
El período **finaliza el último día del mes inmediatamente anterior** al mes en
que entra en vigencia el nuevo valor, y comienza tantos meses antes como indique
la periodicidad (desde la base del último aumento: la fecha del último aumento
indicada, el último aumento aplicado por el sistema o la fecha de inicio del
contrato).

Ejemplo con periodicidad 4 meses:

|                          | Fecha                     |
| ------------------------ | ------------------------- |
| Inicio del período       | 01/03/2026                |
| Fin del período          | 30/06/2026                |
| Vigencia del nuevo valor | 01/07/2026 al 31/10/2026  |

**Valores tomados del índice:**

- **ICL Inicial:** valor publicado para la fecha de inicio del período.
- **ICL Final:** valor publicado para la fecha de fin del período.

**Fórmula:**

```
Coeficiente    = ICL Final / ICL Inicial
Nuevo Alquiler = Alquiler Actual × Coeficiente
```

La expensa se ajusta con el mismo coeficiente si el contrato cobra expensas.

**Ejemplo numérico:**

```
Alquiler Actual:          $500.000

ICL Inicial (01/03/2026):   25,00
ICL Final   (30/06/2026):   28,50

Coeficiente = 28,50 / 25,00 = 1,14

Nuevo Alquiler = $500.000 × 1,14 = $570.000
```

Variación ICL: 14 % → Vigencia 01/07/2026 al 31/10/2026.

**Actualización de la serie publicada por el BCRA:** la serie se actualiza con
atraso; en la práctica los datos de un mes quedan disponibles alrededor del día
17 del mes siguiente y la serie llega hasta el día 16. El sistema no usa fechas
fijas: consulta la serie y evalúa si ya existe el valor para la fecha de fin
del período.

**¿Qué pasa si el BCRA todavía no publicó el valor para la fecha final?**

- El cálculo no puede realizarse: en la vista Aumentos se muestra el estado
  **"ICL pendiente de cálculo"**, con la última fecha disponible publicada y
  los días aproximados que faltan para completar el período.
- No se muestran montos ni porcentajes estimados hasta tanto el dato esté
  disponible; el contrato y el registro del mes quedan sin cambios.
- Cuando el BCRA publica el valor faltante, el próximo cálculo ya lo toma y el
  estado pasa a "ICL calculado"; el aumento se aplica cuando el mes entra en
  vigencia (al abrir el Dashboard).
- Si el aumento quedó pendiente y el valor llega más tarde, se aplica en ese
  momento sin intervención manual.

---

## Backups

- Crea una copia del archivo de base de datos en la carpeta `backups/`
  con nombre `alquileres_AAAA-MM-DD_HH-MM.sqlite`.
- Accesible desde el botón Backup del Dashboard.
- La lista de backups existentes puede consultarse desde la API.
- Es un respaldo preventivo: copia el archivo completo, incluye todos los
  datos del sistema.

---

## Impresión

- El botón Impresión del Dashboard abre el diálogo del navegador.
- Se imprime el listado de cobros del mes (pendientes y pagados visibles).
- La hoja impresa no incluye la barra lateral de navegación, los botones, la
  columna de selección ni la columna de acciones; los modales y los avisos
  emergentes también se ocultan (ver reglas visuales en convenciones ui.md).

---

## Requerimientos no funcionales del sistema

- **Portabilidad:** la distribución portable funciona en Windows sin instalar
  Python, Node ni dependencias; se inicia con doble clic en `start.bat`.
- **Panel local único:** toda la aplicación corre en la PC (backend + frontend
  servidos en `http://127.0.0.1:8000`).
- **Persistencia local:** todos los datos en un archivo SQLite dentro de la
  carpeta del sistema; no requiere servidor externo.
- **Conectividad:** todo funciona sin conexión a internet, **excepto** la
  consulta del índice ICL a la API del BCRA (ver regla ICL), que requiere
  internet al momento de calcular/proyectar contratos ICL.
- **Interfaz responsiva:** funcional en navegadores modernos; tablas con scroll
  horizontal a partir de ancho mínimo y compatibilidad con zoom elevado del
  navegador (ver convenciones ui.md).
- **Feedback unificado:** cada operación exitosa (guardar, editar, eliminar,
  cobrar, ajustes, backup, etc.) muestra un aviso global en verde con el
  mensaje correspondiente; los errores van en aviso rojo con el detalle del
  problema. El aviso desaparece solo unos segundos.
- **Robustez:** migraciones automáticas al arrancar que agregan columnas nuevas
  sin perder datos; validaciones en frontend y backend con mensajes claros.
- **Impresión:** el dashboard debe poder imprimirse desde el navegador con
  formato limpio de hoja.
