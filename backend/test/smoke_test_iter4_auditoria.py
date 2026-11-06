"""
Smoke test del Punto 3: auditoría de contratos cortos, SIN_AUMENTO, MANUAL+0% legacy
y reglas de fecha_fin (MANUAL e ICL). Ejecutar desde backend/:
.venv\\Scripts\\python.exe test\\smoke_test_iter4_auditoria.py
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


def fecha_iso(anio, mes, dia=1):
    return f"{anio:04d}-{mes:02d}-{dia:02d}"


# ── Preparación de datos ─────────────────────────────────────────────
def crear_dep(codigo):
    r = client.post("/departamentos/", json={"piso": "Piso 1", "codigo": codigo})
    assert r.status_code == 201, r.text
    return r.json()["id_departamentos"]

ids_dep = [crear_dep(f"TP4{i}") for i in range(1, 8)]
r = client.post("/inquilinos/", json={"nombre_apellido": "TEST P3", "es_actual": True})
id_inq = r.json()["id_inquilinos"]

def crear_contrato(dep, **kw):
    base = {
        "id_departamentos": dep, "id_inquilinos": id_inq,
        "fecha_inicio": fecha_iso(ANIO, MES), "fecha_fin": fecha_iso(*sumar_meses(ANIO, MES, 12)),
        "alquiler_base_actual": 100000, "tipo_aumento": "MANUAL",
        "porcentaje_aumento": 10.0, "periodicidad_aumento_meses": 3,
    }
    base.update(kw)
    r = client.post("/contratos/", json=base)
    assert r.status_code == 201, r.text
    return r.json()["id_contratos"]

# C1: corto de 4 meses (inicio MES-2, fin MES+1), proximo aumento = MES+1 = mes de vencimiento
anio_i1, mes_i1 = sumar_meses(ANIO, MES, -2)
id_c1 = crear_contrato(ids_dep[0], fecha_inicio=fecha_iso(anio_i1, mes_i1),
                       fecha_fin=fecha_iso(*sumar_meses(ANIO, MES, 1)),
                       periodicidad_aumento_meses=3)

# C2: ICL con proximo aumento en MES y fin en MES (mismo mes permitido, MES+1 bloqueado)
anio_b2, mes_b2 = sumar_meses(ANIO, MES, -3)
id_c2 = crear_contrato(ids_dep[1], tipo_aumento="ICL", porcentaje_aumento=0,
                       periodicidad_aumento_meses=3, fecha_ultimo_aumento=fecha_iso(anio_b2, mes_b2),
                       fecha_fin=fecha_iso(ANIO, MES))

# C3: MANUAL + 0% legacy (compatibilidad), periodicidad 1
id_c3 = crear_contrato(ids_dep[2], porcentaje_aumento=0, periodicidad_aumento_meses=1)

# C4: SIN_AUMENTO
id_c4 = crear_contrato(ids_dep[3], tipo_aumento="SIN_AUMENTO", porcentaje_aumento=0,
                       periodicidad_aumento_meses=0)

# C5: ICL con proximo en MES+1 pero fin en MES -> MES+1 bloqueado (fuera de fecha_fin)
anio_b5, mes_b5 = sumar_meses(ANIO, MES, -2)
id_c5 = crear_contrato(ids_dep[4], tipo_aumento="ICL", porcentaje_aumento=0,
                       periodicidad_aumento_meses=3, fecha_ultimo_aumento=fecha_iso(anio_b5, mes_b5),
                       fecha_fin=fecha_iso(ANIO, MES))

# C6: MANUAL corto de 3 meses (inicio MES-2, fin MES): el aumento corresponde en
# inicio+3 = MES+1, posterior a fecha_fin -> nunca recibe aumento (comportamiento
# correcto y bloqueado por backend).
id_c6 = crear_contrato(ids_dep[5], fecha_inicio=fecha_iso(anio_i1, mes_i1),
                       fecha_fin=fecha_iso(ANIO, MES), periodicidad_aumento_meses=3)

# ── Monkeypatch BCRA ─────────────────────────────────────────────────
def fake_fetch_ok(fecha_desde, fecha_hasta):
    detalle = [
        {"fecha": fecha_desde.isoformat(), "valor": 25.0},
        {"fecha": fecha_hasta.isoformat(), "valor": 28.75},
    ]
    return detalle, None
mes_service._fetch_icl_bcra = fake_fetch_ok

# ── C1: corto 4 meses MANUAL ─────────────────────────────────────────
with Session(engine) as s:
    c1 = s.get(Contrato, id_c1)
    res = mes_service.aplicar_aumento_si_corresponde(s, c1, ANIO, MES)
check("C1 corto: no aumenta antes de periodicidad", res is None)
    # proximo = MES+1 (mes de vencimiento): permitido
with Session(engine) as s:
    c1 = s.get(Contrato, id_c1)
    res = mes_service.aplicar_aumento_si_corresponde(s, c1, *sumar_meses(ANIO, MES, 1))
check("C1 corto: aumento en mes de vencimiento permitido", res == 10.0, str(res))
with Session(engine) as s:
    check("C1 corto: historial creado", historial_de(s, id_c1, *sumar_meses(ANIO, MES, 1)) is not None)
    c1 = s.get(Contrato, id_c1)
    res = mes_service.aplicar_aumento_si_corresponde(s, c1, *sumar_meses(ANIO, MES, 2))
    check("C1 corto: mes posterior a fecha_fin bloqueado", res is None)
    check("C1 corto: sin historial posterior", historial_de(s, id_c1, *sumar_meses(ANIO, MES, 2)) is None)

# ── C2: ICL mismo mes de vencimiento permitido ───────────────────────
with Session(engine) as s:
    c2 = s.get(Contrato, id_c2)
    res = mes_service.aplicar_aumento_si_corresponde(s, c2, ANIO, MES)
check("C2 ICL: aumento en mes de vencimiento permitido", res == 15.0, str(res))
with Session(engine) as s:
    h2 = historial_de(s, id_c2, ANIO, MES)
    check("C2 ICL: historial creado con ICL", h2 is not None and round(h2.coeficiente_icl or 0, 6) == 1.15)
    c2 = s.get(Contrato, id_c2)
    res = mes_service.aplicar_aumento_si_corresponde(s, c2, *sumar_meses(ANIO, MES, 1))
    check("C2 ICL: mes posterior a fecha_fin bloqueado", res is None)
    check("C2 ICL: sin historial posterior", historial_de(s, id_c2, *sumar_meses(ANIO, MES, 1)) is None)

# ── C5: ICL fuera de fecha_fin ───────────────────────────────────────
with Session(engine) as s:
    c5 = s.get(Contrato, id_c5)
    res = mes_service.aplicar_aumento_si_corresponde(s, c5, *sumar_meses(ANIO, MES, 1))
check("C5 ICL fuera de fecha_fin: bloqueado", res is None)
with Session(engine) as s:
    check("C5 ICL: sin historial", historial_de(s, id_c5, *sumar_meses(ANIO, MES, 1)) is None)
    check("C5 ICL: contrato sin mutar", s.get(Contrato, id_c5).alquiler_base_actual == 100000)

# ── C3: MANUAL + 0% legacy ───────────────────────────────────────────
with Session(engine) as s:
    c3 = s.get(Contrato, id_c3)
    res = mes_service.aplicar_aumento_si_corresponde(s, c3, ANIO, MES)
check("C3 MANUAL 0% legacy: nunca aumenta", res is None)
with Session(engine) as s:
    check("C3 MANUAL 0%: sin historial", historial_de(s, id_c3, ANIO, MES) is None)
    check("C3 MANUAL 0%: contrato sin mutar", s.get(Contrato, id_c3).alquiler_base_actual == 100000)

# ── C4: SIN_AUMENTO ──────────────────────────────────────────────────
with Session(engine) as s:
    check("C4 SIN_AUMENTO: sin historial", historial_de(s, id_c4, ANIO, MES) is None)

# ── C6: MANUAL corto 3 meses: corresponde en MES+1 (posterior a fin) -> nunca ──
with Session(engine) as s:
    c6 = s.get(Contrato, id_c6)
    res = mes_service.aplicar_aumento_si_corresponde(s, c6, ANIO, MES)
check("C6 corto 3 meses: no aumenta en MES", res is None)
with Session(engine) as s:
    c6 = s.get(Contrato, id_c6)
    res = mes_service.aplicar_aumento_si_corresponde(s, c6, *sumar_meses(ANIO, MES, 1))
    check("C6 corto: MES+1 posterior a fecha_fin bloqueado", res is None)
    check("C6 corto: sin historial", historial_de(s, id_c6, *sumar_meses(ANIO, MES, 1)) is None)

# ── C7: contrato vencido pero estado activo ──────────────────────────
# fecha_fin = MES-1 (vencido), sigue activo: el Dashboard lo sigue listando y
# genera registro/cobro. Se documenta el comportamiento (no se corrige aqui).
anio_f7, mes_f7 = sumar_meses(ANIO, MES, -1)
id_c7 = crear_contrato(ids_dep[6], fecha_inicio=fecha_iso(ANIO, MES), fecha_fin=fecha_iso(anio_f7, mes_f7),
                       periodicidad_aumento_meses=0, tipo_aumento="SIN_AUMENTO",
                       porcentaje_aumento=0)
r = client.get("/dashboard/mes-actual")
item_c7 = next((i for i in r.json() if i["contrato"]["id_contratos"] == id_c7), None)
# Guarda de vencimiento (Punto 3b): un vencido activo ya NO genera registro en Dashboard.
check("C7 vencido activo: NO genera registro en Dashboard (guarda vigencia)", item_c7 is None)

# ── Limpieza ─────────────────────────────────────────────────────────
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