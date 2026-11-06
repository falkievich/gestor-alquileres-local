# Convenciones UI — Depto Manager

Fuente única de las reglas visuales y de comportamiento de la interfaz.
Las funcionalidades están en `especificacion funcional.md`; este documento
describe CÓMO deben verse y comportarse los componentes.

---

## Tablas

Aplica a todas las tablas y grillas del sistema (incluidas las de los modales).
El encabezado usa siempre la misma alineación que el contenido de su columna:

- **Texto e identificación → izquierda:** Departamento, Inquilino / Nombre,
  Dirección, Teléfono.
- **Fechas y períodos → centro:** Inicio, Vencimiento, Mes / Año,
  Periodicidad.
- **Importes y porcentajes → izquierda:** Alquiler, Expensa, Agua, Luz,
  Impuesto, Diferencia, % aplicado. Siempre con fuente mono
  (`font-mono`) y `whitespace-nowrap` para que no se corten ni deformen.
- **Total → centro:** encabezado y contenido centrados, `font-mono` y
  destacado en negrita (en el historial de pagos, además, en verde).
- **Estados, badges y tipos → centro:** Estado, Pago, Servicios, Incluye,
  Tipo, Activo / Finalizado / Por vencer / Cargado.
- **Acciones → centro:** siempre última columna, ocultas en impresión
  (`print:hidden`).

### Estructura de tabla estándar

- Contenedor: `bg-white rounded-xl shadow-sm border border-gray-200
  overflow-x-auto` (scroll horizontal cuando la tabla excede el ancho).
- Cada tabla define un **ancho mínimo** (`min-w-*`) para no deformar columnas:
  Dashboard cobros (760px), historial de pagos (820px), Servicios (640px),
  Contratos (760px), Departamentos/Inquilinos (640px), Historial de aumentos
  (900px, grilla CSS en lugar de `<table>`).
- Cuerpo con separadores finos entre filas (`divide-y`) y resaltado de fila al
  pasar el mouse.
- `whitespace-nowrap` en columnas monetarias y de acciones.
- Encabezados de sección en mayúsculas pequeñas con espaciado tracking
  (Departamentos, historial de aumentos).

---

## Responsive y zoom

- **Tablas:** con ancho mínimo + `overflow-x-auto`, a partir de ~300 % de zoom
  aparece scroll horizontal sin cortar contenido ni apilar columnas.
- **Modales:** el scroll vive en el overlay del modal (no en el contenido
  interno), lo que permite navegar el 100 % del contenido con zoom 300 %/400 %
  (llegar hasta el tope y el pie con scroll normal).
- **Botones y agrupaciones:** los grupos de acciones usan flex con gap y
  `flex-wrap` donde corresponde (ej. acciones de Departamentos) para acomodarse
  en pantallas angostas.
- La clase `.modal-grande` (index.css) escala ligeramente la tipografía y los
  controles dentro de los modales para legibilidad.

---

## Modales

Estructura común (`ModalShell` en `lib/ui.tsx`), obligatoria para todos los
modales del sistema:

- Overlay oscuro con scroll (`fixed inset-0 bg-black/40 overflow-auto`) y
  caja blanca centrada (`rounded-xl shadow-xl`) con ancho máximo según el
  caso: `max-w-lg` (formularios y ajustes), `max-w-xl` (historiales),
  `max-w-2xl` (modificar aumento), `max-w-3xl` (contratos, pagos).
- Cierre con botón X o botones Cancelar/Confirmar.
- Los modales se ocultan en impresión.
- **Popup de campos faltantes:** si se envía un formulario con campos
  obligatorios vacíos, se muestra el popup "Faltan campos obligatorios"
  listándolos, y los campos faltantes se muestran en rojo con borde y anillo
  intensos. El error de cada campo se limpia al editarlo.
- Confirmaciones destructivas (eliminar departamento o inquilino):
  confirmación nativa del navegador.
- **Modales de confirmación con resumen** (cobro y cierre de contrato): ícono
  circular de color + título, caja gris (`bg-gray-50 rounded-lg`) con el
  resumen en filas `etiqueta / valor` (importes en `font-mono`) y dos botones
  `flex-1` al pie. El de cobro muestra el desglose del mes (alquiler, expensa,
  agua, luz, impuesto, total destacado); el de cierre de contrato muestra los
  datos del contrato más un aviso ámbar con las consecuencias del cierre.
  En el cierre el botón de confirmar va en **verde** y el de cancelar en
  **rojo**.
- **Modal en solo lectura** (detalle de un contrato finalizado): reutiliza el
  mismo formulario de edición con todos los campos `disabled`; el subtítulo
  aclara que los datos no pueden modificarse, el adjunto se ofrece como botón
  de descarga en lugar del selector de archivo y el pie deja solo el botón
  "Cerrar". El estilo de campo deshabilitado lo aporta `clasesCampo`
  (`disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed`).

---

## Feedback

- **Toasts globales** (esquina inferior derecha): cada operación exitosa
  muestra un **toast verde** con el mensaje correspondiente (guardar, editar,
  eliminar, cobrar, ajustes, backup, etc.); los errores muestran un **toast
  rojo** con el detalle (`detail` de la respuesta HTTP cuando existe).
- Desaparecen solos a los ~3 segundos; no bloquean la UI.
- Errores de validación de formularios: popup con la lista de campos + resaltado
  inline de cada campo fallado.
- Botones muestran estado de carga con deshabilitado (`Guardar...`,
  `Actualizando...`, etc.).

---

## Estados visuales

Paleta estándar de badges/estados (pill `rounded-full text-xs px-2 py-0.5
font-semibold` salvo indicación):

| Estado | Color | Dónde |
| --- | --- | --- |
| Activo / OK / Cargado / Pagado en historial / CONSOLIDADO / Libre | verde (`bg-green-100 text-green-700`) | Contratos, Servicios, Departamentos, Aumentos |
| Pendiente / Por vencer / PENDIENTE | amarillo (`bg-yellow-100 text-yellow-700`) | Servicios, Contratos/Cobros, Aumentos |
| Vencido / Ocupado | rojo (`bg-red-100 text-red-700`/`text-red-600`) | Contratos, Cobros, Departamentos, Aumentos |
| Finalizado / Anterior / No pagado | gris (`bg-gray-100 text-gray-500`) | Contratos, Inquilinos, pagos |
| Ajustado | amarillo rectangular (`bg-yellow-100 text-yellow-700`) | Dashboard (override) |
| Atrasado | ámbar (ver sección siguiente) | Dashboard, Servicios, Aumentos |

Casos particulares:

- **Pagado** en el Dashboard es texto inline azul con check (mes debajo en
  gris azulado), no pill verde.
- **Servicios** en las filas del Dashboard: texto `OK` en verde con check, o
  `Pendiente` en naranja con ícono de alerta.
- **Tipo de aumento** (Aumentos): ICL violeta, MANUAL azul, SIN AUMENTO gris.
- **Tarjetas de Aumentos:** fondo rojo y borde rojo cuando el aumento queda
  fuera del contrato ("Sin más aumentos"); caja celeste para "ICL calculado"
  con la fecha de vigencia; caja ámbar para ICL pendiente (con última fecha
  disponible del BCRA y días faltantes) y para falta de fecha de último
  aumento.

---

## Atrasados

Convención común en Dashboard, Servicios y Aumentos (pendientes de
consolidar):

- Los atrasados aparecen **arriba** del contenido del mes, ordenados del más
  antiguo al más reciente.
- Badge rectangular ámbar con ícono de reloj: **"Atrasado · Mes Año"**
  (`bg-amber-100 text-amber-800 border-amber-200`, `font-semibold`).
- Fila: fondo `amber-50` translúcido y **acento izquierdo** con borde
  izquierdo ámbar de 4px (en tarjetas de Aumentos, borde con acento
  lateral izquierdo igual).
- En Aumentos el badge de atrasado convive con el badge PENDIENTE (amarillo).
- La paleta ámbar se usa solo para atrasados y estados de aviso similar: no
  saturar la UI con más acentos de color simultáneos.
- En Dashboard los atrasados **no participan del ajuste masivo** (sin
  checkbox y sin selección, el modo selección los ignora); sí aceptan ajuste
  individual.
- En Aumentos, si el pendiente atrasado no puede modificarse (existe un
  aumento posterior), el botón "Modificar aumento" se deshabilita con
  opacidad reducida, tooltip explicativo y un texto junto al botón.
- En Servicios los atrasados son **tan editables como el mes actual**: el
  acento ámbar indica el período, no un estado de solo lectura. La fila
  mantiene su estado (Pendiente/Cargado) y su acción (Guardar/Actualizar).

---

## Impresión

Reglas visuales globales de impresión (CSS `@media print` en `index.css`):

- Se ocultan: barra lateral de navegación, botones y encabezados de acción
  (`print:hidden`), columna de checkboxes y de acciones, columna "Servicios"
  del dashboard (`.col-servicios-impresion`), overlays de modales y toasts.
- **Columnas monetarias vacías:** las columnas Expensa, Agua, Luz e Impuesto
  se ocultan al imprimir si ninguna fila del listado tiene un valor cargado.
  El Dashboard calcula esas banderas con `columnasConDatos()` y marca el `th`
  y los `td` de la columna con `.col-vacia-impresion`.
- Fondo blanco, ancho completo del contenido, márgenes de página ajustados.
- Las tablas anulan su ancho mínimo y usan el 100 % de la hoja, con
  separadores por inquilino y encabezado destacado.
- El Dashboard inyecta un encabezado visible solo en impresión:
  "Cobros — {mes actual}".
- El botón Imprimir del Dashboard dispara `window.print()`.
