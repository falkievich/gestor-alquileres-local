"""
Smoke test de la sincronización al editar un contrato:
re-cálculo del aumento PENDIENTE, limpieza de conceptos que el contrato dejó
de cobrar y propagación al registro mensual.

Corre sobre una base SQLite temporal (no toca base_de_datos/alquileres.sqlite).
Ejecutar desde backend/:
  .venv\\Scripts\\python.exe test\\smoke_test_iter8_sincronizacion_contrato.py
"""
import sys, os, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Base temporal: se redirige el engine ANTES de importar la app.
import app.db as db
from sqlmodel import create_engine, Session, select

DB_TMP = os.path.join(tempfile.mkdtemp(), "smoke_iter8.sqlite")
db.engine = create_engine(
    f"sqlite:///{DB_TMP}", echo=False,
    connect_args={"check_same_thread": False},
)

from fastapi.testclient import TestClient
from app.main import app
import app.service.mes_service as mes_service
from app.model.models import Contrato, RegistroMensual, HistorialAumento

db.create_db_and_tables()
client = TestClient(app, raise_server_exceptions=True)
errores = []

ANIO, MES = mes_service.get_mes_actual()


def check(nombre, cond, detalle=""):
    print(f"[{'OK ' if cond else 'FAIL'}] {nombre} {detalle}")
    if not cond:
        errores.append(nombre)


def mes_desplazado(meses):
    total = MES - meses
    anio = ANIO
    while total < 1:
        total += 12
        anio -= 1
    return anio, total


def crear_contrato(codigo, **kw):
    r = client.post("/departamentos/", json={"piso": "Piso 1", "codigo": codigo})
    assert r.status_code == 201, r.text
    id_dep = r.json()["id_departamentos"]
    r = client.post("/inquilinos/", json={"nombre_apellido": f"TEST {codigo}", "es_actual": True})
    id_inq = r.json()["id_inquilinos"]
    anio_base, mes_base = mes_desplazado(3)
    base = {
        "id_departamentos": id_dep, "id_inquilinos": id_inq,
        "fecha_inicio": f"{anio_base}-{mes_base:02d}-01",
        "fecha_fin": f"{ANIO + 2}-12-31",
        "alquiler_base_actual": 100000,
        "tipo_aumento": "MANUAL", "porcentaje_aumento": 10.0,
        "periodicidad_aumento_meses": 3,
        # El aumento de este mes ya corresponde (base + periodicidad = hoy).
        "fecha_ultimo_aumento": f"{anio_base}-{mes_base:02d}-01",
    }
    base.update(kw)
    r = client.post("/contratos/", json=base)
    assert r.status_code == 201, r.text
    return r.json()["id_contratos"]


def leer(id_contrato, anio=ANIO, mes=MES):
    with Session(db.engine) as s:
        contrato = s.get(Contrato, id_contrato)
        registro = s.exec(select(RegistroMensual).where(
            RegistroMensual.id_contratos == id_contrato,
            RegistroMensual.anio == anio, RegistroMensual.mes == mes)).first()
        historial = s.exec(select(HistorialAumento).where(
            HistorialAumento.id_contratos == id_contrato,
            HistorialAumento.anio == anio, HistorialAumento.mes == mes)).first()
        return contrato, registro, historial


def editar(id_contrato, **campos):
    r = client.put(f"/contratos/{id_contrato}", json=campos)
    assert r.status_code == 200, r.text
    return r.json()


print("\n--- 1) Corregir el alquiler re-calcula el aumento PENDIENTE ---")
id_c1 = crear_contrato("T81", cobra_expensa=True, expensa_base_actual=20000)
assert client.get("/dashboard/mes-actual").status_code == 200
c, reg, h = leer(id_c1)
check("aumento generado 100.000 -> 110.000",
      h is not None and (h.alquiler_anterior, h.alquiler_propuesto, h.alquiler_aplicado) == (100000, 110000, 110000),
      f"({h.alquiler_anterior} -> {h.alquiler_aplicado})" if h else "sin historial")
check("contrato y registro quedaron en 110.000",
      c.alquiler_base_actual == 110000 and reg.alquiler_calculado == 110000)

# El usuario se da cuenta de que el alquiler era 200.000, no 100.000.
editar(id_c1, alquiler_base_actual=200000, expensa_base_actual=20000, cobra_expensa=True)
c, reg, h = leer(id_c1)
check("el aumento re-basa a 200.000 -> 220.000",
      (h.alquiler_anterior, h.alquiler_propuesto, h.alquiler_aplicado) == (200000, 220000, 220000),
      f"({h.alquiler_anterior} -> {h.alquiler_aplicado})")
check("el porcentaje congelado no cambia", round(h.porcentaje_alquiler_aplicado, 2) == 10.0,
      f"({h.porcentaje_alquiler_aplicado}%)")
check("el contrato queda con el monto aumentado", c.alquiler_base_actual == 220000,
      f"({c.alquiler_base_actual})")
check("el registro del mes cobra 220.000 + expensa 22.000",
      (reg.alquiler_calculado, reg.expensa_calculada, reg.total) == (220000, 22000, 242000),
      f"({reg.alquiler_calculado}, {reg.expensa_calculada}, total {reg.total})")
pend = client.get("/aumentos/historial", params={"estado": "PENDIENTE"}).json()
fila = next(p for p in pend if p["contrato"]["id_contratos"] == id_c1)
check("la vista Aumentos muestra el monto corregido",
      fila["historial"]["alquiler_aplicado"] == 220000 and fila["diferencia_aplicada"] == 20000)
prox = next(p for p in client.get("/aumentos/").json()
            if p["contrato"]["id_contratos"] == id_c1)
check("el próximo aumento parte de la nueva base",
      prox["proximo_aumento"]["alquiler_actual"] == 220000)

print("\n--- 2) Editar un campo que no es monto NO re-calcula el aumento ---")
editar(id_c1, fecha_fin=f"{ANIO + 3}-01-31")
c, reg, h = leer(id_c1)
check("montos intactos tras editar la fecha de vencimiento",
      (h.alquiler_anterior, h.alquiler_aplicado, c.alquiler_base_actual) == (200000, 220000, 220000),
      f"({h.alquiler_anterior} -> {h.alquiler_aplicado}, contrato {c.alquiler_base_actual})")

print("\n--- 3) Editar solo la expensa no toca el alquiler ---")
editar(id_c1, expensa_base_actual=50000)
c, reg, h = leer(id_c1)
check("expensa re-basada 50.000 -> 55.000",
      (h.expensa_anterior, h.expensa_aplicada, c.expensa_base_actual) == (50000, 55000, 55000),
      f"({h.expensa_anterior} -> {h.expensa_aplicada})")
check("alquiler sin cambios", (h.alquiler_aplicado, c.alquiler_base_actual) == (220000, 220000))
check("total recalculado", reg.total == 275000, f"({reg.total})")

print("\n--- 4) Dejar de cobrar expensa/agua/luz limpia el registro ---")
id_c2 = crear_contrato("T82", cobra_expensa=True, expensa_base_actual=30000,
                       cobra_agua=True, cobra_luz=True, impuesto_fijo=5000)
assert client.get("/dashboard/mes-actual").status_code == 200
_, reg, _ = leer(id_c2)
client.post("/servicios/guardar", params={
    "id_registro": reg.id_registros_mensuales, "agua": 7000, "luz": 8000})
_, reg, _ = leer(id_c2)
check("total inicial con todos los conceptos",
      reg.total == 110000 + 33000 + 7000 + 8000 + 5000, f"({reg.total})")

editar(id_c2, cobra_expensa=False, cobra_agua=False, cobra_luz=False, impuesto_fijo=None)
_, reg, _ = leer(id_c2)
check("expensa, agua, luz e impuesto quedaron limpios",
      (reg.expensa_calculada, reg.agua, reg.luz, reg.impuesto) == (None, None, None, None),
      f"({reg.expensa_calculada}, {reg.agua}, {reg.luz}, {reg.impuesto})")
check("el total ya no suma conceptos que el contrato no cobra",
      reg.total == 110000, f"({reg.total})")
item = next(i for i in client.get("/dashboard/mes-actual").json()
            if i["contrato"]["id_contratos"] == id_c2)
check("el Dashboard informa el mismo total", item["total"] == 110000, f"({item['total']})")

print("\n--- 5) El ajuste manual del alquiler se preserva ---")
id_c3 = crear_contrato("T83")
assert client.get("/dashboard/mes-actual").status_code == 200
_, reg, _ = leer(id_c3)
client.post(f"/dashboard/registros/{reg.id_registros_mensuales}/override",
            params={"alquiler_override": 150000, "nota_override": "ajuste"})
editar(id_c3, alquiler_base_actual=200000)
c, reg, h = leer(id_c3)
check("el override sobrevive a la edición del contrato",
      reg.alquiler_override == 150000 and reg.nota_override == "ajuste",
      f"({reg.alquiler_override})")
check("el calculado y el total respetan override + aumento re-basado",
      (reg.alquiler_calculado, reg.total) == (220000, 150000), f"({reg.alquiler_calculado}, {reg.total})")

print("\n--- 6) Un pendiente viejo con aumento posterior no se re-calcula ---")
id_c4 = crear_contrato("T84", periodicidad_aumento_meses=1,
                       fecha_ultimo_aumento=f"{mes_desplazado(2)[0]}-{mes_desplazado(2)[1]:02d}-01")
anio_viejo, mes_viejo = mes_desplazado(1)
with Session(db.engine) as s:
    contrato = s.get(Contrato, id_c4)
    mes_service.aplicar_aumento_si_corresponde(s, contrato, anio_viejo, mes_viejo)
    mes_service.get_or_create_registro(s, contrato, anio_viejo, mes_viejo)
assert client.get("/dashboard/mes-actual").status_code == 200
_, _, h_viejo = leer(id_c4, anio_viejo, mes_viejo)
_, _, h_nuevo = leer(id_c4)
check("existen dos pendientes", h_viejo is not None and h_nuevo is not None)
anterior_viejo = h_viejo.alquiler_anterior
editar(id_c4, alquiler_base_actual=300000)
_, _, h_viejo = leer(id_c4, anio_viejo, mes_viejo)
_, _, h_nuevo = leer(id_c4)
check("el pendiente viejo queda congelado",
      h_viejo.alquiler_anterior == anterior_viejo, f"({h_viejo.alquiler_anterior})")
check("solo se re-basa el pendiente más reciente",
      (h_nuevo.alquiler_anterior, h_nuevo.alquiler_aplicado) == (300000, 330000),
      f"({h_nuevo.alquiler_anterior} -> {h_nuevo.alquiler_aplicado})")

print("\n--- 8) Un pendiente de un mes anterior no se re-calcula ---")
id_c6 = crear_contrato("T86", periodicidad_aumento_meses=1,
                       fecha_ultimo_aumento=f"{mes_desplazado(2)[0]}-{mes_desplazado(2)[1]:02d}-01")
with Session(db.engine) as s:
    contrato = s.get(Contrato, id_c6)
    mes_service.aplicar_aumento_si_corresponde(s, contrato, anio_viejo, mes_viejo)
    mes_service.get_or_create_registro(s, contrato, anio_viejo, mes_viejo)
editar(id_c6, alquiler_base_actual=400000)
_, reg_viejo, h_viejo = leer(id_c6, anio_viejo, mes_viejo)
check("el aumento del mes anterior no cambia",
      (h_viejo.alquiler_anterior, h_viejo.alquiler_aplicado) == (100000, 110000),
      f"({h_viejo.alquiler_anterior} -> {h_viejo.alquiler_aplicado})")
check("el registro atrasado conserva su monto congelado",
      (reg_viejo.alquiler_calculado, reg_viejo.total) == (110000, 110000),
      f"({reg_viejo.alquiler_calculado}, total {reg_viejo.total})")

print("\n--- 7) Un aumento CONSOLIDADO es inmutable ---")
id_c5 = crear_contrato("T85")
assert client.get("/dashboard/mes-actual").status_code == 200
_, reg, _ = leer(id_c5)
r = client.post(f"/dashboard/registros/{reg.id_registros_mensuales}/pagado")
assert r.status_code == 200, r.text
editar(id_c5, alquiler_base_actual=500000)
c, reg, h = leer(id_c5)
check("el aumento cobrado no se re-calcula",
      h.estado == "CONSOLIDADO" and (h.alquiler_anterior, h.alquiler_aplicado) == (100000, 110000),
      f"({h.estado}, {h.alquiler_anterior} -> {h.alquiler_aplicado})")
check("el mes pagado conserva sus montos", reg.alquiler_calculado == 110000, f"({reg.alquiler_calculado})")
check("el contrato sí toma el monto corregido", c.alquiler_base_actual == 500000,
      f"({c.alquiler_base_actual})")

print("\n" + "=" * 60)
if errores:
    print(f"FALLARON {len(errores)} verificaciones:")
    for e in errores:
        print(f"  - {e}")
    sys.exit(1)
print("Todas las verificaciones pasaron.")
