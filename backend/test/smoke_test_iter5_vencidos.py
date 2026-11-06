"""
Smoke test del Punto 3b: guarda de vencimiento (fecha_fin) en Dashboard/Servicios/cobros.
Contrato vencido y estado='activo': deja de generar registros/cobros pasando el mes de
fecha_fin; el mes de vencimiento sigue siendo válido. Ejecutar desde backend/:
.venv\\Scripts\\python.exe test\\smoke_test_iter5_vencidos.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.db import engine
from sqlmodel import Session, select
import app.service.mes_service as mes_service
from app.model.models import Contrato, RegistroMensual

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


def fecha_iso(anio, mes, dia=1):
    return f"{anio:04d}-{mes:02d}-{dia:02d}"


# ── Preparación de datos ─────────────────────────────────────────────
def crear_dep(codigo):
    r = client.post("/departamentos/", json={"piso": "Piso 1", "codigo": codigo})
    assert r.status_code == 201, r.text
    return r.json()["id_departamentos"]

ids_dep = [crear_dep(f"TP5{i}") for i in range(1, 4)]
r = client.post("/inquilinos/", json={"nombre_apellido": "TEST P4", "es_actual": True})
id_inq = r.json()["id_inquilinos"]

def crear_contrato(dep, **kw):
    base = {
        "id_departamentos": dep, "id_inquilinos": id_inq,
        "fecha_inicio": fecha_iso(ANIO, MES), "fecha_fin": fecha_iso(*sumar_meses(ANIO, MES, 12)),
        "alquiler_base_actual": 100000, "tipo_aumento": "MANUAL",
        "porcentaje_aumento": 10.0, "periodicidad_aumento_meses": 0,
    }
    base.update(kw)
    r = client.post("/contratos/", json=base)
    assert r.status_code == 201, r.text
    return r.json()["id_contratos"]

# C1: vencido (fin = MES-1) pero estado = activo, SIN_AUMENTO para no interferir
anio_f, mes_f = sumar_meses(ANIO, MES, -1)
id_c1 = crear_contrato(ids_dep[0], fecha_inicio=fecha_iso(ANIO, MES),
                       fecha_fin=fecha_iso(anio_f, mes_f),
                       tipo_aumento="SIN_AUMENTO", porcentaje_aumento=0)

# C2: vigente con fin = MES+12 (control)
id_c2 = crear_contrato(ids_dep[1], cobra_luz=True)

# C3: fin = MES actual (mes de vencimiento válido), SIN_AUMENTO
id_c3 = crear_contrato(ids_dep[2], fecha_fin=fecha_iso(ANIO, MES),
                       tipo_aumento="SIN_AUMENTO", porcentaje_aumento=0)

# ── 1) Vencido activo: NO aparece en Dashboard ni Servicios ──────────
r = client.get("/dashboard/mes-actual")
check("dashboard 200", r.status_code == 200)
check("C1 vencido NO aparece en Dashboard",
      id_c1 not in [i["contrato"]["id_contratos"] for i in r.json()])
check("C2 vigente SÍ aparece en Dashboard",
      id_c2 in [i["contrato"]["id_contratos"] for i in r.json()])
check("C3 fin = mes actual SÍ aparece (mes de vencimiento válido)",
      id_c3 in [i["contrato"]["id_contratos"] for i in r.json()])

r = client.get("/servicios/pendientes")
check("servicios 200", r.status_code == 200)
check("C1 vencido NO aparece en Servicios",
      id_c1 not in [i["contrato"]["id_contratos"] for i in r.json()])

# ── 2) Guarda defensiva en preparar_registro_mes ─────────────────────
with Session(engine) as s:
    c1 = s.get(Contrato, id_c1)
    anio_out, mes_out = sumar_meses(ANIO, MES, 0)
    try:
        mes_service.preparar_registro_mes(s, c1, anio_out, mes_out)
        check("preparar mes > fin levanta 409", False, "no levantó excepción")
    except Exception as exc:
        code = getattr(exc, "status_code", None)
        check("preparar mes > fin levanta 409", code == 409, str(code))

# ── 3) Registro manual post-vencimiento: cobro/override/servicios rechazados ──
# Se crea el registro directamente en DB (ya no puede generarse por API).
with Session(engine) as s:
    reg = RegistroMensual(
        id_contratos=id_c1,
        anio=sumar_meses(ANIO, MES, 0)[0], mes=sumar_meses(ANIO, MES, 0)[1],
        alquiler_calculado=100000, total=100000,
    )
    s.add(reg)
    s.commit()
    s.refresh(reg)
    id_reg = reg.id_registros_mensuales

r = client.post(f"/dashboard/registros/{id_reg}/pagado")
check("cobrar mes > fin rechazado (409)", r.status_code == 409, str(r.status_code))
r = client.post(f"/dashboard/registros/{id_reg}/override", params={"alquiler_override": 90000})
check("override mes > fin rechazado (409)", r.status_code == 409, str(r.status_code))
r = client.post("/servicios/guardar", params={"id_registro": id_reg, "luz": 5000})
check("guardar servicios mes > fin rechazado (409)", r.status_code == 409, str(r.status_code))

with Session(engine) as s:
    reg_db = s.get(RegistroMensual, id_reg)
    check("registro post-fin sin cobro ni ajustes",
          reg_db.pagado is False and reg_db.alquiler_override is None and reg_db.luz is None)

# ── 4) Mes de vencimiento: cobrable ─────────────────────────────────
with Session(engine) as s:
    reg3 = s.exec(select(RegistroMensual).where(
        RegistroMensual.id_contratos == id_c3,
        RegistroMensual.anio == ANIO, RegistroMensual.mes == MES)).first()
    check("C3 registro del mes de vencimiento generado", reg3 is not None)
if reg3:
    r = client.post(f"/dashboard/registros/{reg3.id_registros_mensuales}/pagado")
    check("cobrar mes de vencimiento permitido", r.status_code == 200, str(r.status_code))

# ── Limpieza ─────────────────────────────────────────────────────────
from app.model.models import HistorialAumento
for cid in (id_c1, id_c2, id_c3):
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