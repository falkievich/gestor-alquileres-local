# Depto Manager

Depto Manager es una aplicación de escritorio para gestionar alquileres de departamentos.
Permite llevar el control de inquilinos, contratos, cobros mensuales, servicios y aumentos
desde una interfaz sencilla que se abre directamente en el navegador.

No requiere internet ni instalación de programas adicionales.
Todo se guarda localmente en la computadora.

---

## Pestañas

### 🏠 Dashboard — Cobros del mes

Es la pantalla principal. Muestra todos los contratos activos y cuánto debe cobrar
cada inquilino en el mes actual (alquiler + expensas + servicios).

Desde acá podés:
- Ver el total a cobrar por cada departamento
- Marcar un cobro como pagado una vez que el inquilino paga
- Hacer ajustes individuales o masivos si el monto cambia ese mes (descuentos, acuerdos, etc.)
- Imprimir el listado del mes
- Ver el historial de cobros anteriores
- Crear un backup de la base de datos

---

### 🏢 Departamentos

Listado de todos los departamentos que administrás.

Desde acá podés:
- Agregar nuevos departamentos (piso, código, dirección)
- Editar o eliminar departamentos existentes
- Ver si un departamento está ocupado o libre

---

### 👤 Inquilinos

Listado de todos los inquilinos registrados.

Desde acá podés:
- Agregar nuevos inquilinos (nombre y teléfono)
- Editar sus datos
- Ver sus contratos activos e historial de contratos anteriores
- Ver el historial de pagos de cada inquilino

---

### 📄 Contratos

Listado de contratos activos y finalizados.

Desde acá podés:
- Crear un contrato nuevo vinculando un inquilino a un departamento
- Definir fechas, monto de alquiler, expensas, porcentaje y periodicidad de aumentos
- Adjuntar el archivo del contrato (PDF o DOCX)
- Editar o cerrar un contrato cuando el inquilino se va
- Si el contrato ya estaba en curso antes de empezar a usar el sistema, podés indicar
  cuándo fue el último aumento para que los cálculos futuros sean correctos

---

### 💧 Servicios

Pantalla para cargar los valores de agua y luz del mes actual para los inquilinos
que tienen esos servicios incluidos en el contrato.

Desde acá podés:
- Ver qué departamentos tienen servicios pendientes de cargar
- Ingresar los montos de agua y/o luz de cada uno
- Guardarlos para que se sumen al total del mes en el Dashboard

---

### 📈 Aumentos

Resumen de todos los contratos activos con información sobre los aumentos configurados.

Desde acá podés:
- Ver cuándo le corresponde el próximo aumento a cada inquilino
- Ver cuánto pasará a cobrar cuando se aplique el aumento
- Detectar contratos que tienen un aumento próximo o que ya vencieron
- Identificar contratos que necesitan que se complete la fecha del último aumento

---

## Base de datos

Todos los datos se guardan en la carpeta `base_de_datos/alquileres.sqlite`.
Para hacer un backup manual, copiá ese archivo a otro lugar.
El sistema también incluye un botón de Backup en el Dashboard para hacerlo desde la interfaz.
