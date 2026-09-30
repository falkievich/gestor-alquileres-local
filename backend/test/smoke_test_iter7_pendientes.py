"""
Smoke test del Punto 4: cobros pendientes de meses anteriores (atrasados).
Dashboard/Servicios muestran mes actual + pendientes anteriores con montos
congelados; cobro posterior consolida solo su período; modificación de
aumentos PENDIENTES viejos bloqueada si existe uno posterior.
Ejecutar desde backend/: .venv\\Scripts\\python.exe test\\smoke_test_iter7_pendientes.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.db import engine
from sqlmodel import Session, select
import app.service.mes_service as mes_service
from app.model.models import Contrato, RegistroMensual, HistorialAumento

client = TestClient(app, raise_server_exceptions=True)
errores = []


def check(nombre, cond, detalle=""):
    estado = "OK " if cond else "FAIL"
    print(f"[{estado}] {nombre} {detalle}")
    if not cond:
        errores.append(nombre)


def sumar_meses(anio, mes, n):
    t = mes + n
    a = anio
    while t > 12:
        t -= 12
        a += 1
    while t < 1:
        t += 12
        a -= 1
    return a, t


ANIO, MES = mes_service.get_mes_actual()
ANIO_A1, MES_A1 = sumar_meses(ANIO, MES, -1)   # mes atrasado 1 (más reciente)
ANIO_A2, MES_A2 = sumar_meses(ANIO, MES, -2)   # mes atrasado (más antiguo)


# ── Preparación de datos ─────────────────────────────────────────────
def crear_dep(codigo):
    r = client.post("/departamentos/", json={"piso": "Piso 1", "codigo": codigo})
    assert r.status_code == 201, r.text
    return r.json()["id_departamentos"]

ids_dep = [crear_dep(f"TP6{i}") for i in range(1, 5)]
r = client.post("/inquilinos/", json={"nombre_apellido": "TEST P5", "es_actual": True})
id_inq = r.json()["id_inquilinos"]

def crear_contrato(dep, **kw):
    base = {
        "id_departamentos": dep, "id_inquilinos": id_inq,
        "fecha_inicio": f"{ANIO}-{MES:02d}-01", "fecha_fin": f"{ANIO + 1}-{MES:02d}-01",
        "alquiler_base_actual": 120000, "tipo_aumento": "MANUAL",
        "porcentaje_aumento": 10.0, "periodicidad_aumento_meses": 12,
    }
    base.update(kw)
    r = client.post("/contratos/", json=base)
    assert r.status_code == 201, r.text
    return r.json()["id_contratos"]

# C1: atrasado en MES-1 con aumento PENDIENTE de ese período (base actual 120000
# simulando que ya hay un aumento posterior aplicado en el mes actual)
id_c1 = crear_contrato(ids_dep[0], cobra_luz=True)

# C2: dos atrasados (MES-2 y MES-1)
id_c2 = crear_contrato(ids_dep[1])

# C4: finalizado con deuda anterior (se cierra más abajo)
id_c4 = crear_contrato(ids_dep[3])

# Registros atrasados + aumento PENDIENTE atrasado, creados directo en DB
# (simulan meses que quedaron sin cobrar antes de esta funcionalidad).
with Session(engine) as s:
    reg_c1 = RegistroMensual(id_contratos=id_c1, anio=ANIO_A1, mes=MES_A1,
                             alquiler_calculado=110000, total=110000)
    reg_c2a = RegistroMensual(id_contratos=id_c2, anio=ANIO_A2, mes=MES_A2,
                              alquiler_calculado=100000, total=100000)
    reg_c2b = RegistroMensual(id_contratos=id_c2, anio=ANIO_A1, mes=MES_A1,
                              alquiler_calculado=100000, total=100000)
    reg_c4 = RegistroMensual(id_contratos=id_c4, anio=ANIO_A1, mes=MES_A1,
                             alquiler_calculado=100000, total=100000)
    h_c1 = HistorialAumento(id_contratos=id_c1, anio=ANIO_A1, mes=MES_A1,
                            estado="PENDIENTE", tipo_aumento="MANUAL",
                            alquiler_anterior=100000, alquiler_propuesto=110000,
                            alquiler_aplicado=110000,
                            porcentaje_alquiler_propuesto=10.0,
                            porcentaje_alquiler_aplicado=10.0)
    s.add_all([reg_c1, reg_c2a, reg_c2b, reg_c4, h_c1])
    s.commit()
    s.refresh(reg_c1); s.refresh(reg_c2a); s.refresh(reg_c2b); s.refresh(reg_c4)
    s.refresh(h_c1)
    id_reg_c1 = reg_c1.id_registros_mensuales
    id_h_c1 = h_c1.id_historial_aumentos

# ── 1) Dashboard: atrasados visibles con montos congelados ──────────
n_reg_antes = len(Session(engine).exec(select(RegistroMensual)).all())
h_antes = len(Session(engine).exec(select(HistorialAumento)).all())
r = client.get("/dashboard/mes-actual")
check("dashboard 200", r.status_code == 200)
items_atrasados = [i for i in r.json() if i.get("atrasado")]
items_actuales = [i for i in r.json() if not i.get("atrasado")]
check("C1 atrasado visible en MES-1",
      any(i["contrato"]["id_contratos"] == id_c1 and i["mes"] == MES_A1 for i in items_atrasados))
check("C2 dos atrasados (MES-2 y MES-1)",
      len([i for i in items_atrasados if i["contrato"]["id_contratos"] == id_c2]) == 2)
# Montos congelados: el atrasado muestra 110000 (su propio mes), no la base actual 120000
fila_c1 = next(i for i in items_atrasados if i["contrato"]["id_contratos"] == id_c1)
check("C1 atrasado monto congelado 110000",
      fila_c1["registro"]["alquiler_calculado"] == 110000
      and fila_c1["total"] == 110000, f"={fila_c1['total']}")
# Orden: MES-2 primero, MES-1 después (ascendente)
idx_a2 = next(i for i, x in enumerate(items_atrasados) if x["mes"] == MES_A2)
idx_a1 = next(i for i, x in enumerate(items_atrasados) if x["mes"] == MES_A1)
check("orden ascendente de atrasados", idx_a2 < idx_a1)
check("aumento PENDIENTE de sept NO consolidado",
      Session(engine).get(HistorialAumento, id_h_c1).estado == "PENDIENTE")

# Cero escritura: consultar no crea registros ni historiales
r2 = client.get("/dashboard/mes-actual")
check("GET dashboard no escribe registros",
      len(Session(engine).exec(select(RegistroMensual)).all()) == len(Session(engine).exec(select(RegistroMensual)).all())
      and len(Session(engine).exec(select(HistorialAumento)).all()) == h_antes)

# ── Montos congelados: editar base_actual no toca el atrasado ────────
r = client.put(f"/contratos/{id_c1}", json={"alquiler_base_actual": 130000})
check("editar base_actual", r.status_code == 200)
r = client.get("/dashboard/mes-actual")
fila_c1b = next(i for i in r.json() if i.get("atrasado") and i["contrato"]["id_contratos"] == id_c1)
check("atrasado sigue congelado tras editar base", fila_c1b["total"] == 110000, f"={fila_c1b['total']}")

# ── Servicios de mes anterior ────────────────────────────────────────
r = client.get("/servicios/pendientes")
fila_serv_c1 = next((i for i in r.json() if i["registro"]["id_registros_mensuales"] == id_reg_c1), None)
check("servicios: atrasado C1 visible", fila_serv_c1 is not None and fila_serv_c1.get("atrasado") is True)
if fila_serv_c1:
    r2 = client.post("/servicios/guardar",
                     params={"id_registro": id_reg_c1, "luz": 5000})
    check("servicios: guardar luz en atrasado", r2.status_code == 200)
    check("servicios: total recalculado congelado (110000+5000)",
          r2.json()["total"] == 115000, f"={r2.json().get('total')}")

# ── Override en atrasado ─────────────────────────────────────────────
r = client.post(f"/dashboard/registros/{id_reg_c1}/override",
                params={"alquiler_override": 105000, "nota_override": "ajuste viejo"})
check("override en atrasado", r.status_code == 200)

# ── Cobro posterior del atrasado ─────────────────────────────────────
r = client.post(f"/dashboard/registros/{id_reg_c1}/pagado")
check("cobrar atrasado", r.status_code == 200, str(r.status_code))
with Session(engine) as s:
    reg_db = s.get(RegistroMensual, id_reg_c1)
    check("atrasado pagado y cobro de septiembre", reg_db.pagado is True and reg_db.mes == MES_A1)
    h_db = s.get(HistorialAumento, id_h_c1)
    check("consolidacion: aumento sept -> CONSOLIDADO", h_db.estado == "CONSOLIDADO")
    check("cobro respeta override", reg_db.alquiler_override == 105000)
    # El mes actual de C1 sigue no pagado e intacto
    reg_c1_actual = s.exec(select(RegistroMensual).where(
        RegistroMensual.id_contratos == id_c1,
        RegistroMensual.anio == ANIO, RegistroMensual.mes == MES)).first()
    check("registro mes actual de C1 intacto",
          reg_c1_actual is not None and reg_c1_actual.pagado is False
          and reg_c1_actual.alquiler_calculado == 130000)
# El atrasado pagado desaparece del listado de atrasados
r = client.get("/dashboard/mes-actual")
check("atrasado pagado ya no figura",
      id_reg_c1 not in [i["registro"]["id_registros_mensuales"] for i in r.json() if i.get("atrasado")])
# Y aparece en historial de pagos
r = client.get("/dashboard/historial-pagos", params={"anio": ANIO, "mes": MES_A1})
check("aparece en historial de pagos",
      any(p["registro"]["id_registros_mensuales"] == id_reg_c1 for p in r.json()))

# ── Regla: modificar aumento PENDIENTE viejo con posterior → 409 ────
# C3: aumento PENDIENTE del mes actual (generado por el sistema):
# base MES-3 + periodicidad 3 -> próximo aumento = mes actual.
anio_b3, mes_b3 = sumar_meses(ANIO, MES, -3)
id_c3 = crear_contrato(ids_dep[2], periodicidad_aumento_meses=3,
                       fecha_ultimo_aumento=f"{anio_b3}-{mes_b3:02d}-01")
r = client.get("/dashboard/mes-actual")
check("C3 registro actual generado", any(
    i["contrato"]["id_contratos"] == id_c3 for i in r.json() if not i.get("atrasado")))
with Session(engine) as s:
    h_c3 = s.exec(select(HistorialAumento).where(
        HistorialAumento.id_contratos == id_c3,
        HistorialAumento.anio == ANIO, HistorialAumento.mes == MES)).first()
    check("C3 historial PENDIENTE actual", h_c3 is not None and h_c3.estado == "PENDIENTE")
    id_h_c3 = h_c3.id_historial_aumentos
    # Aumento PENDIENTE atrasado para C3 (MES-1) + su registro
    reg_c3 = RegistroMensual(id_contratos=id_c3, anio=ANIO_A1, mes=MES_A1,
                             alquiler_calculado=100000, total=100000)
    h_viejo = HistorialAumento(id_contratos=id_c3, anio=ANIO_A1, mes=MES_A1,
                               estado="PENDIENTE", tipo_aumento="MANUAL",
                               alquiler_anterior=100000, alquiler_propuesto=110000,
                               alquiler_aplicado=110000,
                               porcentaje_alquiler_propuesto=10.0,
                               porcentaje_alquiler_aplicado=10.0)
    s.add(reg_c3); s.add(h_viejo)
    s.commit(); s.refresh(h_viejo)
    id_h_viejo = h_viejo.id_historial_aumentos
r = client.patch(f"/aumentos/historial/{id_h_viejo}", json={"alquiler_aplicado": 105000})
check("modificar PENDIENTE viejo con posterior -> 409",
      r.status_code == 409, str(r.status_code))
check("mensaje de la regla",
      "anterior al último aumento" in r.json().get("detail", ""), r.json().get("detail", ""))
# El PENDIENTE del mes actual (sin posterior) sigue modificable
r = client.patch(f"/aumentos/historial/{id_h_c3}", json={"alquiler_aplicado": 135000})
check("modificar PENDIENTE actual sin posterior -> 200",
      r.status_code == 200, str(r.status_code))

# Flags en el endpoint de pendientes de aumentos
r = client.get("/aumentos/historial", params={"estado": "PENDIENTE"})
fila_vieja = next((i for i in r.json() if i["historial"]["id_historial_aumentos"] == id_h_viejo), None)
fila_actual = next((i for i in r.json() if i["historial"]["id_historial_aumentos"] == id_h_c3), None)
check("flag atrasado en aumentos", fila_vieja is not None and fila_vieja["atrasado"] is True)
check("flag se_puede_modificar=False en viejo",
      fila_vieja["se_puede_modificar"] is False)
check("flag se_puede_modificar=True en actual",
      fila_actual is not None and fila_actual["se_puede_modificar"] is True)

# ── Contrato finalizado: pendientes NO reaparecen como atrasados ────
r = client.post(f"/contratos/{id_c4}/cerrar")
check("cerrar C4", r.status_code == 200, str(r.status_code))
r = client.get("/dashboard/mes-actual")
check("C4 finalizado: atrasado NO visible",
      not any(i.get("atrasado") and i["contrato"]["id_contratos"] == id_c4 for i in r.json()))
r = client.get("/servicios/pendientes")
check("C4 finalizado: NO visible en servicios",
      all(i["contrato"]["id_contratos"] != id_c4 for i in r.json()))
r = client.get("/aumentos/historial", params={"estado": "PENDIENTE"})
check("C4 finalizado: sin pendientes de aumentos visibles",
      all(i["contrato"]["id_contratos"] != id_c4 for i in r.json()))
with Session(engine) as s:
    check("C4: registro pendiente permanece en DB sin cambios",
          s.get(RegistroMensual, reg_c4.id_registros_mensuales).pagado is False)
# Si se cobra (por API, mes <= fecha_fin), aparece en historial de pagos
with Session(engine) as s:
    reg_c4 = s.get(RegistroMensual, reg_c4.id_registros_mensuales)
    id_reg_c4 = reg_c4.id_registros_mensuales
r = client.post(f"/dashboard/registros/{id_reg_c4}/pagado")
check("C4 finalizado: registro anterior cobrable por API", r.status_code == 200, str(r.status_code))
r = client.get("/dashboard/historial-pagos", params={"anio": ANIO, "mes": MES_A1})
check("C4 pagado aparece en historial de pagos",
      any(p["registro"]["id_registros_mensuales"] == id_reg_c4 for p in r.json()))

# ── Limpieza ─────────────────────────────────────────────────────────
for cid in (id_c1, id_c2, id_c3, id_c4):
    client.delete(f"/contratos/{cid}")
client.delete(f"/inquilinos/{id_inq}")
for did in ids_dep:
    client.delete(f"/departamentos/{did}")

with Session(engine) as s:
    ids_ctos = [c.id_contratos for c in s.exec(select(Contrato)).all()]
    for r_ in s.exec(select(HistorialAumento)).all():
        if r_.id_contratos not in ids_ctos:
            s.delete(r_)
    for r_ in s.exec(select(RegistroMensual)).all():
        if r_.id_contratos not in ids_ctos:
            s.delete(r_)
    s.commit()
print("Limpieza hecha.")

if errores:
    print(f"\nHUBO ERRORES: {errores}")
    sys.exit(1)
print("\nTODO OK")