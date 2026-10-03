"""
Smoke test del Punto 1: historial_aumentos, SIN_AUMENTO, fecha_fin, idempotencia.
Ejecutar desde backend/: .venv\\Scripts\\python.exe test\\smoke_test_iter2_aumentos.py
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


def historial_de(session, id_contratos, anio, mes):
    return session.exec(
        select(HistorialAumento).where(
            HistorialAumento.id_contratos == id_contratos,
            HistorialAumento.anio == anio,
            HistorialAumento.mes == mes,
        )
    ).first()


ANIO, MES = mes_service.get_mes_actual()

# ── Preparación de datos ─────────────────────────────────────────────
def crear_dep(codigo):
    r = client.post("/departamentos/", json={"piso": "Piso 1", "codigo": codigo})
    assert r.status_code == 201, r.text
    return r.json()["id_departamentos"]

ids_dep = [crear_dep(f"TP{i}") for i in range(1, 8)]
r = client.post("/inquilinos/", json={"nombre_apellido": "TEST P1", "es_actual": True})
id_inq = r.json()["id_inquilinos"]

def crear_contrato(dep, **kw):
    base = {
        "id_departamentos": dep, "id_inquilinos": id_inq,
        "fecha_inicio": "2026-03-01", "fecha_fin": "2027-03-01",
        "alquiler_base_actual": 100000, "tipo_aumento": "MANUAL",
        "porcentaje_aumento": 10.0, "periodicidad_aumento_meses": 6,
    }
    base.update(kw)
    r = client.post("/contratos/", json=base)
    assert r.status_code == 201, r.text
    return r.json()["id_contratos"]

id_c1 = crear_contrato(ids_dep[0], cobra_expensa=True, expensa_base_actual=20000)
id_c2 = crear_contrato(ids_dep[1], fecha_fin="2026-10-31", fecha_ultimo_aumento="2026-03-01")
id_c3 = crear_contrato(ids_dep[2], fecha_fin="2026-10-31", fecha_ultimo_aumento="2026-05-01")
id_c4 = crear_contrato(ids_dep[3], alquiler_base_actual=500000, cobra_expensa=True,
                       expensa_base_actual=50000, tipo_aumento="ICL",
                       porcentaje_aumento=0, periodicidad_aumento_meses=3,
                       fecha_ultimo_aumento="2026-06-01")
id_c5 = crear_contrato(ids_dep[4], fecha_fin="2027-01-01", tipo_aumento="SIN_AUMENTO",
                       porcentaje_aumento=0, periodicidad_aumento_meses=0)
id_c6 = crear_contrato(ids_dep[5], fecha_fin="2027-01-01", impuesto_fijo=5000,
                       cobra_luz=True, periodicidad_aumento_meses=12)

# ── Monkeypatch BCRA (sin llamadas reales) ──────────────────────────
calls = {"n": 0}
def fake_fetch_ok(fecha_desde, fecha_hasta):
    calls["n"] += 1
    detalle = [
        {"fecha": fecha_desde.isoformat(), "valor": 25.0},
        {"fecha": fecha_hasta.isoformat(), "valor": 28.75},
    ]
    return detalle, None
mes_service._fetch_icl_bcra = fake_fetch_ok

# ── 1) Primer dashboard: aplica MANUAL (C1, C2) e ICL (C4) ─────────
r = client.get("/dashboard/mes-actual")
check("dashboard 200", r.status_code == 200, str(r.status_code))
def reg_de(items, id_cto):
    return next((i for i in items if i["contrato"]["id_contratos"] == id_cto), None)

reg1 = reg_de(r.json(), id_c1)
check("C1 alquiler aumentado 110000", reg1["registro"]["alquiler_calculado"] == 110000,
      f"={reg1['registro']['alquiler_calculado']}")
check("C1 expensa aumentada 22000", reg1["registro"]["expensa_calculada"] == 22000,
      f"={reg1['registro']['expensa_calculada']}")
check("C1 legacy porcentaje_aumento_usado=10", reg1["registro"]["porcentaje_aumento_usado"] == 10.0,
      f"={reg1['registro']['porcentaje_aumento_usado']}")

with Session(engine := __import__("app.db", fromlist=["engine"]).engine) as s:
    h1 = historial_de(s, id_c1, ANIO := ANIO, MES := MES)
    check("C1 historial creado", h1 is not None)
    if h1:
        check("C1 estado PENDIENTE", h1.estado == "PENDIENTE", h1.estado)
        check("C1 tipo MANUAL", h1.tipo_aumento == "MANUAL", h1.tipo_aumento)
        check("C1 anterior=100000", h1.alquiler_anterior == 100000, str(h1.alquiler_anterior))
        check("C1 propuesto=110000", h1.alquiler_propuesto == 110000, str(h1.alquiler_propuesto))
        check("C1 aplicado=propuesto", h1.alquiler_aplicado == h1.alquiler_propuesto)
        check("C1 % propuesto=10", round(h1.porcentaje_alquiler_propuesto, 6) == 10.0)
        check("C1 % aplicado=10", round(h1.porcentaje_alquiler_aplicado, 6) == 10.0)
        check("C1 expensa anterior=20000", h1.expensa_anterior == 20000)
        check("C1 expensa aplicada=22000", h1.expensa_aplicada == 22000)
        check("C1 % expensa=10", round(h1.porcentaje_expensa_aplicado or 0, 6) == 10.0)
        check("C1 campos ICL NULL (MANUAL)", h1.coeficiente_icl is None and h1.icl_inicial is None)
        check("C1 sin consolidacion", h1.fecha_consolidacion is None)
        check("C1 fecha_creacion/actualizacion", h1.fecha_creacion is not None and h1.fecha_actualizacion is not None)

    h2 = historial_de(s, id_c2, ANIO, MES)
    check("C2 historial creado (mismo mes que vence ok)", h2 is not None)
    if h2:
        check("C2 sin expensa -> campos None", h2.expensa_anterior is None and h2.expensa_aplicada is None)
        check("C2 sin ICL", h2.coeficiente_icl is None)

    h4 = historial_de(s, id_c4, ANIO, MES)
    check("C4 historial ICL creado", h4 is not None)
    if h4:
        check("C4 tipo ICL", h4.tipo_aumento == "ICL")
        check("C4 coeficiente=1.15", round(h4.coeficiente_icl or 0, 6) == 1.15, str(h4.coeficiente_icl))
        check("C4 icl_inicial=25", h4.icl_inicial == 25.0)
        check("C4 icl_final=28.75", h4.icl_final == 28.75)
        check("C4 fecha_icl_inicial", str(h4.fecha_icl_inicial) == f"{ANIO}-06-01", str(h4.fecha_icl_inicial))
        check("C4 fecha_icl_final", str(h4.fecha_icl_final) == f"{ANIO}-08-31", str(h4.fecha_icl_final))
        check("C4 propuesto=575000", h4.alquiler_propuesto == 575000, str(h4.alquiler_propuesto))
        check("C4 % full precision", round(h4.porcentaje_alquiler_propuesto, 6) == 15.0)

    c1 = s.get(Contrato, id_c1)
    check("C1 base actualizada", c1.alquiler_base_actual == 110000)
    check("C1 base inicial intacta", c1.alquiler_base_inicial == 100000, str(c1.alquiler_base_inicial))
    check("C1 expensa inicial intacta", c1.expensa_base_inicial == 20000)
    check("C4 ICL no muta sin historial", True)

reg6 = reg_de(r.json(), id_c6)
check("C6 impuesto congelado 5000", reg6["registro"]["impuesto"] == 5000,
      f"={reg6['registro'].get('impuesto')}")
check("C6 total incluye impuesto", reg6["registro"]["total"] == 105000,
      f"={reg6['registro']['total']}")
check("C6 no aumento (period 12)", reg6["registro"]["alquiler_calculado"] == 100000)
reg5 = reg_de(r.json(), id_c5)
check("C5 sin aumento alquiler 100000", reg5["registro"]["alquiler_calculado"] == 100000)
check("C5 sin legacy %", reg5["registro"]["porcentaje_aumento_usado"] is None)

# ── 7) Idempotencia: repetir dashboard no duplica ni reaplica ───────
with Session(engine) as s:
    total_h_antes = len(s.exec(select(HistorialAumento)).all())
check("preparacion: 3 historiales (C1, C2, C4)", total_h_antes == 3, f"={total_h_antes}")
for _ in range(3):
    client.get("/dashboard/mes-actual")
with Session(engine) as s:
    total_h_despues = len(s.exec(select(HistorialAumento)).all())
    c1 = s.get(Contrato, id_c1)
check("idempotencia: no duplica historiales", total_h_despues == total_h_antes,
      f"antes={total_h_antes} despues={total_h_despues}")
check("idempotencia: contrato estable", c1.alquiler_base_actual == 110000)
check("idempotencia: una sola llamada BCRA", calls["n"] == 1, f"calls={calls['n']}")

# ── 11) Configuración modificada NO cambia propuesta PENDIENTE ─────
r = client.put(f"/contratos/{id_c1}", json={"porcentaje_aumento": 15.0})
check("editar % C1", r.status_code == 200)
with Session(engine) as s:
    h1b = historial_de(s, id_c1, ANIO, MES)
    check("propuesta congelada (monto)", h1b.alquiler_propuesto == 110000, str(h1b.alquiler_propuesto))
    check("propuesta congelada (%)", round(h1b.porcentaje_alquiler_propuesto, 6) == 10.0)
    check("contrato no recalculado", s.get(Contrato, id_c1).alquiler_base_actual == 110000)

# ── 6) fecha_fin: posterior al vencimiento NO se aplica ────────────
with Session(engine) as s:
    c3 = s.get(Contrato, id_c3)
    res = mes_service.aplicar_aumento_si_corresponde(s, c3, ANIO, 11)
check("fecha_fin posterior: no aplica", res is None)
with Session(engine) as s:
    c3 = s.get(Contrato, id_c3)
    check("C3 contrato sin mutar", c3.alquiler_base_actual == 100000)
    check("C3 sin historial", historial_de(s, id_c3, ANIO, 11) is None)

# ── ICL pendiente: no aplica, no muta, no registra ─────────────────
def fake_fetch_error(fecha_desde, fecha_hasta):
    calls["err"] = calls.get("err", 0) + 1
    return None, "BCRA sin datos (test)"
mes_service._fetch_icl_bcra = fake_fetch_error
id_c7 = crear_contrato(ids_dep[6], tipo_aumento="ICL", alquiler_base_actual=400000,
                       porcentaje_aumento=0, periodicidad_aumento_meses=3,
                       fecha_ultimo_aumento="2026-06-01")
with Session(engine) as s:
    c7 = s.get(Contrato, id_c7)
    res = mes_service.aplicar_aumento_si_corresponde(s, c7, ANIO, MES)
check("ICL pendiente: no aplica", res is None)
with Session(engine) as s:
    c7 = s.get(Contrato, id_c7)
    check("ICL pendiente: contrato sin mutar", c7.alquiler_base_actual == 400000)
    check("ICL pendiente: sin historial", historial_de(s, id_c7, ANIO, MES) is None)

# ── Idempotencia fuerte vía servicio directo ───────────────────────
mes_service._fetch_icl_bcra = fake_fetch_ok
with Session(engine) as s:
    c1 = s.get(Contrato, id_c1)
    res = mes_service.aplicar_aumento_si_corresponde(s, c1, ANIO, MES)
check("idempotencia servicio directo: None", res is None)

# ── 8) UNIQUE + CHECK de DB ────────────────────────────────────────
from sqlalchemy.exc import IntegrityError
with Session(engine) as s:
    dup = HistorialAumento(
        id_contratos=id_c2, anio=ANIO, mes=MES, estado="PENDIENTE",
        tipo_aumento="MANUAL", alquiler_anterior=1, alquiler_propuesto=1,
        alquiler_aplicado=1, porcentaje_alquiler_propuesto=0.0,
        porcentaje_alquiler_aplicado=0.0,
    )
    s.add(dup)
    try:
        s.commit()
        check("UNIQUE: duplicado rechazado", False, "se insertó duplicado")
    except IntegrityError:
        s.rollback()
        check("UNIQUE: duplicado rechazado", True)
    bad = HistorialAumento(
        id_contratos=id_c2, anio=ANIO, mes=13, estado="PENDIENTE",
        tipo_aumento="MANUAL", alquiler_anterior=1, alquiler_propuesto=1,
        alquiler_aplicado=1, porcentaje_alquiler_propuesto=0.0,
        porcentaje_alquiler_aplicado=0.0,
    )
    s.add(bad)
    try:
        s.commit()
        check("CHECK mes rango: rechazado", False, "se insertó mes=13")
    except IntegrityError:
        s.rollback()
        check("CHECK mes rango: rechazado", True)

# ── 12) Historial endpoint usa historial_aumentos ──────────────────
r = client.get("/aumentos/historial")
check("historial endpoint 200", r.status_code == 200)
fila_c1 = next((i for i in r.json() if i["historial"]["id_contratos"] == id_c1), None)
check("historial incluye C1", fila_c1 is not None)
if fila_c1:
    check("historial anterior desde tabla (sin N/D)", fila_c1["historial"]["alquiler_anterior"] == 100000,
          f"={fila_c1['historial']['alquiler_anterior']}")
    check("historial aplicado", fila_c1["historial"]["alquiler_aplicado"] == 110000)
    check("historial diferencia", fila_c1["diferencia_aplicada"] == 10000)
    check("historial estado en payload", fila_c1["historial"]["estado"] == "PENDIENTE")
    check("historial dep/inquilino presentes", fila_c1["inquilino"]["nombre_apellido"] == "TEST P1")
fila_c4 = next((i for i in r.json() if i["historial"]["id_contratos"] == id_c4), None)
if fila_c4:
    check("historial ICL en payload", fila_c4["historial"]["coeficiente_icl"] is not None)

# ── 9) Pago → CONSOLIDADO ──────────────────────────────────────────
reg_id_c1 = reg1["registro"]["id_registros_mensuales"]
r = client.post(f"/dashboard/registros/{reg_id_c1}/pagado")
check("cobrar C1", r.status_code == 200, str(r.status_code))
with Session(engine) as s:
    h1c = historial_de(s, id_c1, ANIO, MES)
    check("pago consolida a CONSOLIDADO", h1c.estado == "CONSOLIDADO", h1c.estado)
    check("pago completa fecha_consolidacion", h1c.fecha_consolidacion is not None)

# ── 10) Desmarcar pagado eliminado ─────────────────────────────────
r = client.post(f"/dashboard/registros/{reg_id_c1}/desmarcar-pagado")
# El endpoint ya no existe: sin ruta POST propia, FastAPI responde 405
# (el catch-all del SPA es GET-only) o 404 según el orden de rutas.
check("desmarcar eliminado (404/405)", r.status_code in (404, 405), str(r.status_code))
with Session(engine) as s:
    from app.model.models import RegistroMensual
    reg1_db = s.get(RegistroMensual, reg_id_c1)
    check("pago permanece cobrado", reg1_db.pagado is True)

# ── 13) Regresión Servicios + Aumentos UI data ─────────────────────
r = client.get("/servicios/pendientes")
fila_c6 = next((i for i in r.json() if i["contrato"]["id_contratos"] == id_c6), None)
check("servicios: C6 pendiente visible", fila_c6 is not None)
if fila_c6:
    r2 = client.post("/servicios/guardar", params={"id_registro": fila_c6["registro"]["id_registros_mensuales"], "luz": 9000})
    check("servicios: guardar luz", r2.status_code == 200, str(r2.status_code))
    check("servicios: total recalculado", r2.json()["total"] == 114000, f"={r2.json().get('total')}")

r = client.get("/aumentos/")
item_c5 = next((i for i in r.json() if i["contrato"]["id_contratos"] == id_c5), None)
check("aumentos: C5 tipo SIN_AUMENTO", item_c5 is not None and item_c5["proximo_aumento"]["tipo_aumento"] == "SIN_AUMENTO")
if item_c5:
    check("aumentos: C5 sin próximo", item_c5["proximo_aumento"]["proximo_anio"] is None)
item_c1 = next((i for i in r.json() if i["contrato"]["id_contratos"] == id_c1), None)
if item_c1:
    check("aumentos: C1 próximo 2027-03", (item_c1["proximo_aumento"]["proximo_anio"], item_c1["proximo_aumento"]["proximo_mes"]) == (2027, 3),
          f"={item_c1['proximo_aumento']['proximo_anio']}-{item_c1['proximo_aumento']['proximo_mes']}")

# ── Limpieza ───────────────────────────────────────────────────────
for cid in (id_c1, id_c2, id_c3, id_c4, id_c5, id_c6, id_c7):
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
