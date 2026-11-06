# Errores detectados y parches

Revisión de la temporalidad del sistema (meses arrastrados, aumentos aplicados
tarde, contratos cerrados o acortados). Se encontraron **9 errores** que podían
guardar mal la información, esconder deuda o pisar valores. Están ordenados del
más crítico al menos crítico.

Todos tienen su prueba en `backend/test/smoke_test_iter9_errores_detectados.py`.
La prueba usa siempre una **base temporal propia** (nunca toca
`base_de_datos/alquileres.sqlite`) y fechas **relativas al mes actual**, así
pasa en cualquier fecha:

```
cd backend
.venv\Scripts\python.exe test\smoke_test_iter9_errores_detectados.py
```

| # | Error | Gravedad |
| --- | --- | --- |
| 1 | Servicios generaba cobros de contratos que todavía no empezaron | Alta |
| 2 | Un aumento aplicado después de crear el cobro del mes no se cobraba | Alta |
| 3 | Los meses en que no se abría la app nunca se generaban | Alta |
| 4 | Eliminar un departamento o inquilino dejaba datos huérfanos | Alta |
| 5 | Cerrar un contrato con meses sin cobrar escondía la deuda | Media |
| 6 | Acortar el vencimiento dejaba cobros visibles que no se podían cobrar | Media |
| 7 | El ajuste masivo borraba ajustes de expensa y notas | Media |
| 8 | Los ajustes manuales no seguían los cambios del monto base | Media |
| 9 | Modificar un aumento atrasado pisaba la corrección del contrato | Media |

---

## 1. Servicios generaba cobros de contratos que todavía no empezaron

**Qué pasaba.** Al abrir Servicios, un contrato con fecha de inicio en el mes
siguiente igual generaba el cobro del mes actual. Ese cobro "fantasma" aparecía
el mes siguiente en el Dashboard como **atrasado**, como si el inquilino debiera
un mes anterior a su contrato.

**Cómo se arregló.**
- La vigencia de un contrato ahora tiene en cuenta el inicio: un mes es válido
  solo entre el mes de `fecha_inicio` y el de `fecha_fin`
  (`contrato_vigente_para_mes`).
- Dashboard y Servicios usan el mismo filtro para el mes en curso
  (`contrato_operativo_hoy`): el contrato tiene que haber empezado.
- Los cobros fantasma que ya existieran dejan de mostrarse y no se pueden
  cobrar ni ajustar.

**Test:** bloque "Error 1": contrato que empieza el mes próximo (no aparece en
Servicios ni en el Dashboard y no genera registros) y registro fantasma
anterior al inicio (oculto y con cobro rechazado).

## 2. Un aumento aplicado después de crear el cobro del mes no se cobraba

**Qué pasaba.** El cobro del mes se crea con el monto del momento. Si el aumento
se aplicaba después (por ejemplo, el BCRA todavía no había publicado el ICL, o
se corrigió la fecha del último aumento a mitad de mes), el contrato quedaba
aumentado pero **el cobro del mes seguía con el monto viejo**. Si ese mes ya se
había cobrado, el aumento quedaba **PENDIENTE para siempre**, porque nunca se
iba a volver a cobrar ese mes.

**Cómo se arregló.**
- Si el aumento se aplica cuando el cobro del mes ya existe, el cobro pasa al
  monto aumentado. Si tenía un ajuste manual, el ajuste conserva su diferencia
  (ver error 8).
- Si el mes ya estaba cobrado, el cobro no se toca (es lo que se cobró) y el
  aumento se **consolida en el acto**. El contrato queda aumentado para los
  meses siguientes y el calendario de aumentos no se corre.

**Test:** bloque "Error 2":
- se corrige la fecha del último aumento a mitad de mes, y el cobro pasa de
  $100.000 a $110.000 conservando un ajuste de +$5.000;
- ICL con el BCRA caído y que publica después;
- mes ya cobrado, donde el aumento queda CONSOLIDADO.

## 3. Los meses en que no se abría la app nunca se generaban

**Qué pasaba.** Los cobros se crean solo para el mes en curso, cuando se abre
el Dashboard o Servicios. Si un mes entero no se abría la app, ese mes no
existía: la deuda era invisible, el aumento de ese mes se aplicaba recién al
mes siguiente (corriendo el calendario) y, en contratos sin fecha de último
aumento, **el primer aumento podía perderse** del todo.

**Cómo se arregló.**
- Al preparar el mes, se generan como **atrasados** los meses que faltan entre
  el último mes registrado del contrato y el actual, en orden, cada uno con el
  aumento que le corresponde en su propio mes.
- Solo pasa en contratos que ya tenían algún mes registrado: un contrato
  recién cargado no genera deuda hacia atrás.
- Volver a abrir el Dashboard no duplica meses.

**Test:** bloque "Error 3":
- contrato con un mes cobrado hace 4 meses, que genera los 3 meses faltantes
  con el aumento en su mes;
- contrato sin fecha de último aumento, donde el aumento por múltiplos ya no
  se pierde;
- contrato sin registros, que no genera meses hacia atrás;
- reabrir el Dashboard no duplica.

## 4. Eliminar un departamento o inquilino dejaba datos huérfanos

**Qué pasaba.** Se podía eliminar un departamento o un inquilino con contratos.
Los contratos, cobros y aumentos quedaban apuntando a algo que no existía. Como
SQLite reutiliza el último id, el **próximo departamento o inquilino creado
heredaba** los contratos y pagos del eliminado. Borrar un contrato por la API
también dejaba sus cobros e historial sueltos, que heredaba el siguiente
contrato.

**Cómo se arregló.**
- Eliminar un departamento o inquilino con contratos (activos o finalizados)
  se rechaza con un mensaje claro, que la pantalla muestra como aviso de error.
  La especificación ya lo pedía.
- Borrar un contrato borra también sus cobros mensuales y su historial de
  aumentos.

**Test:** bloque "Error 4": eliminar departamento e inquilino con contrato da
409; borrar el contrato limpia sus registros e historial y después sí se puede
eliminar el departamento.

## 5. Cerrar un contrato con meses sin cobrar escondía la deuda

**Qué pasaba.** Al cerrar un contrato, sus meses sin cobrar desaparecían de
todas las pantallas (Dashboard, Servicios y Aumentos) y el modal de cierre no
avisaba nada: la deuda se "perdía".

**Cómo se arregló.**
- El modal de cierre consulta y **lista los meses sin cobrar** (mes y total),
  y avisa que van a seguir en el Dashboard hasta cobrarse. El botón de
  confirmar se habilita cuando el aviso ya está cargado.
- La deuda del contrato cerrado sigue en Dashboard, Servicios y Aumentos con
  el badge **"Contrato finalizado"**, y se cobra normalmente.
- El contrato cerrado no genera meses nuevos.

**Test:** bloque "Error 5":
- el endpoint del aviso devuelve los 2 meses;
- tras cerrar, el atrasado y el mes en curso siguen visibles en Dashboard,
  Servicios y Aumentos;
- se cobran y el aumento se consolida;
- no se generan meses nuevos.

## 6. Acortar el vencimiento dejaba cobros que no se podían cobrar

**Qué pasaba.** Si se acortaba la fecha de vencimiento, los meses ya generados
posteriores al nuevo vencimiento seguían apareciendo como atrasados, pero al
cobrarlos o ajustarlos el sistema respondía con error.

**Cómo se arregló.** Los listados de deuda (Dashboard, Servicios, aviso de
cierre) y los aumentos pendientes solo muestran meses dentro de la vigencia. No
se borra nada: si se vuelve a extender el vencimiento, los meses reaparecen con
sus datos.

**Test:** bloque "Error 6": al acortar el vencimiento desaparecen del
Dashboard, de Aumentos y del aviso de cierre, y el cobro sigue bloqueado. Al
extenderlo vuelven a aparecer.

## 7. El ajuste masivo borraba ajustes de expensa y notas

**Qué pasaba.** El ajuste masivo mandaba solo el alquiler. Como el sistema
reemplaza los tres campos del ajuste (alquiler, expensa y nota), se **borraba
el ajuste de expensa y la nota** que tuviera cada cobro. Además el monto
**reemplazaba** el ajuste de alquiler anterior en vez de sumarse, distinto del
ajuste individual.

**Cómo se arregló** (`Dashboard.tsx`, sin cambios en el backend):
- el delta se suma al alquiler efectivo (con su ajuste previo);
- se reenvía el ajuste de expensa existente;
- si no se escribe una nota nueva, se conserva la anterior.

La vista previa del modal muestra el monto efectivo y el texto lo aclara.

**Test:** bloque "Error 7": reproduce el pedido que arma ahora la pantalla y
verifica que el ajuste se suma (+$5.000 y +$1.000 dan +$6.000) y que se
conservan el ajuste de expensa y la nota. El error era solo del frontend, así
que este bloque documenta el pedido correcto; el cambio de la pantalla se
verificó con el build y revisando el código.

## 8. Los ajustes manuales no seguían los cambios del monto base

**Qué pasaba.** Los ajustes se guardan como monto absoluto. Si a un cobro de
$100.000 se le hacía +$5.000 ($105.000) y después cambiaba el monto base (se
editaba el contrato o se modificaba un aumento a $110.000), el cobro quedaba en
$105.000: el **ajuste se convertía en un descuento** sin que nadie lo pidiera.
En otros casos, al editar el contrato el cobro con ajuste directamente no se
actualizaba.

**Cómo se arregló.** Todo cambio de monto base de un cobro pasa por una sola
función (`fijar_montos_calculados`), que mueve el ajuste lo mismo que cambió el
monto: +$5.000 sigue siendo +$5.000. Se usa al editar el contrato, al aplicar
un aumento tarde, al re-basar un aumento y al modificar un aumento. Un mes
**bonificado** (ajustado a $0) sigue en $0 y un ajuste nunca queda negativo.

**Test:** bloque "Error 8": +$5.000 de alquiler y −$2.000 de expensa se
conservan al editar el contrato, y un mes bonificado sigue en $0. Además se
actualizaron las expectativas de `smoke_test_iter3`, `iter7` e `iter8`, que
suponían el comportamiento anterior (ajuste fijo).

## 9. Modificar un aumento atrasado pisaba la corrección del contrato

**Qué pasaba.** Si después de un aumento atrasado el usuario corregía el monto
del contrato (por ejemplo a $115.000) y luego modificaba ese aumento a
$112.000, el sistema **pisaba la corrección**: el contrato y el mes en curso
volvían a $112.000.

**Cómo se arregló.** Al modificar un aumento, el contrato y los meses
posteriores sin cobrar se actualizan **solo si todavía tienen el monto que dejó
el aumento**. Lo que el usuario corrigió después no se toca. Sin corrección, la
modificación se sigue propagando como antes.

**Test:** bloque "Error 9": con corrección a $115.000, el aumento modificado a
$112.000 cambia solo su mes y la corrección se mantiene. Sin corrección,
contrato y mes en curso heredan $112.000 y el ajuste del mes conserva su
diferencia.

---

## Cómo se evitó que los arreglos se pisen

Las reglas nuevas viven en funciones compartidas de `mes_service.py`, así cada
pantalla usa la misma lógica y un arreglo no puede deshacer otro:

| Función | Qué decide | La usan |
| --- | --- | --- |
| `contrato_vigente_para_mes` | si un mes está dentro de la vigencia | errores 1, 3, 5 y 6 |
| `contrato_operativo_hoy` | si el contrato entra en el mes en curso | Dashboard y Servicios (error 1) |
| `registros_sin_cobrar_fuera_del_ciclo` | qué deuda anterior o de contratos cerrados se lista | Dashboard y Servicios (errores 5 y 6) |
| `fijar_montos_calculados` | cómo cambia el monto base de un cobro | errores 2, 8 y 9 y la edición de contratos |
| `preparar_registro_mes` | cómo se genera cada mes | errores 2 y 3 |

Por ejemplo:
- un mes generado por el error 3 recibe su aumento con la misma regla del
  error 2;
- el aviso de cierre del error 5 usa la vigencia del error 6;
- los errores 2 y 9 conservan los ajustes con la regla del error 8.

## Verificación final

- Los 8 smoke tests del backend pasan en seis fechas simuladas distintas
  (enero, fin de febrero, marzo, noviembre, diciembre y un año después).
- El test nuevo se corrió contra el código anterior a los arreglos: falla en
  los errores 1 a 6, 8 y 9 (el 7 era solo de pantalla) y pasa con los arreglos.
- Al final del test se comprueba que no hay cobros duplicados, que no hay
  cobros fuera de vigencia (salvo el fantasma insertado a propósito) y que
  ningún aumento queda PENDIENTE con su mes ya cobrado.
- Frontend: TypeScript compila sin errores y el build de producción se genera.
  El lint no marca nada nuevo: las 5 observaciones que muestra (3 errores y
  2 advertencias) ya existían antes en líneas que no se tocaron.

## Decisiones tomadas

- **Meses faltantes (error 3):** se generan como atrasados solo si el contrato
  ya tenía algún mes registrado.
- **Contrato cerrado (error 5):** el modal avisa los meses sin cobrar y esa
  deuda sigue en el Dashboard hasta cobrarse.
- **Ajuste masivo (error 7):** se suma al ajuste de alquiler existente y
  conserva el de expensa y la nota.
- **Ajustes manuales (error 8):** conservan su diferencia cuando cambia el
  monto base.
- **Aumento con el mes ya cobrado (error 2):** el cobro hecho no se modifica y
  el aumento se consolida, para que rija desde el mes siguiente sin correr el
  calendario de aumentos.
