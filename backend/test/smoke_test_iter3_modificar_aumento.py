"""
Smoke test del Punto 2: modificación de aumentos PENDIENTE (montos, no porcentajes).
Ejecutar desde backend/: .venv\\Scripts\\python.exe test\\smoke_test_iter3_modificar_aumento.py
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

ids_dep = [crear_dep(f"TP3{i}") for i in range(1, 7)]
r = client.post("/inquilinos/", json={"nombre_apellido": "TEST P2", "es_actual": True})
id_inq = r.json()["id_inquilinos"]

def crear_contrato(dep, **kw):
    base = {
        "id_departamentos": dep, "id_inquilinos": id_inq,
        "fecha_inicio": "2026-03-01", "fecha_fin": "2027-03-01",
        "alquiler_base_actual": 100000, "tipo_aumento": "MANUAL",
        "porcentaje_aumento": 10.0, "periodicidad_aumento_meses": 3,
    }
    base.update(kw)
    r = client.post("/contratos/", json=base)
    assert r.status_code == 201, r.text
    return r.json()["id_contratos"]

# C1: MANUAL con expensa (caso principal)
id_c1 = crear_contrato(ids_dep[0], cobra_expensa=True, expensa_base_actual=20000)
# C2: ICL sin expensa, próximo aumento = base + 3 debe caer en (ANIO, MES)
mes_base_c2 = MES - 3
anio_base_c2 = ANIO
while mes_base_c2 < 1:
    mes_base_c2 += 12
    anio_base_c2 -= 1
id_c2 = crear_contrato(ids_dep[1], alquiler_base_actual=480000, tipo_aumento="ICL",
                       porcentaje_aumento=0, periodicidad_aumento_meses=3,
                       fecha_ultimo_aumento=f"{anio_base_c2}-{mes_base_c2:02d}-01")
# C3: SIN_AUMENTO
id_c3 = crear_contrato(ids_dep[2], tipo_aumento="SIN_AUMENTO",
                       porcentaje_aumento=0, periodicidad_aumento_meses=0)
# C4: MANUAL sin expensa con impuesto (para sync total + overrides)
id_c4 = crear_contrato(ids_dep[3], impuesto_fijo=5000,
                       periodicidad_aumento_meses=1)
# C5: MANUAL con expensa (restaurar propuesta)
id_c5 = crear_contrato(ids_dep[4], cobra_expensa=True, expensa_base_actual=48000,
                       periodicidad_aumento_meses=1)
# C6: MANUAL (siguiente proyección usa la nueva base) + luz para regresión Servicios
id_c6 = crear_contrato(ids_dep[5], periodicidad_aumento_meses=1, cobra_luz=True)

# ── Monkeypatch BCRA (sin llamadas reales) ──────────────────────────
def fake_fetch_ok(fecha_desde, fecha_hasta):
    detalle = [
        {"fecha": fecha_desde.isoformat(), "valor": 25.0},
        {"fecha": fecha_hasta.isoformat(), "valor": 28.75},
    ]
    return detalle, None
mes_service._fetch_icl_bcra = fake_fetch_ok

# ── Generar aumentos: preparar el mes vía dashboard ──────────────────
r = client.get("/dashboard/mes-actual")
check("dashboard 200", r.status_code == 200, str(r.status_code))

def reg_de(items, id_cto):
    return next((i for i in items if i["contrato"]["id_contratos"] == id_cto), None)

reg1 = reg_de(r.json(), id_c1)
reg4 = reg_de(r.json(), id_c4)
reg6 = reg_de(r.json(), id_c6)
check("C1 registro creado con aumento", reg1 is not None and reg1["registro"]["alquiler_calculado"] == 110000,
      f"={reg1['registro']['alquiler_calculado'] if reg1 else None}")
check("C4 registro creado con aumento", reg4 is not None and reg4["registro"]["alquiler_calculado"] == 110000)

with Session(engine) as s:
    h1 = historial_de(s, id_c1, ANIO, MES)
    h2 = historial_de(s, id_c2, ANIO, MES)
    h4 = historial_de(s, id_c4, ANIO, MES)
    h5 = historial_de(s, id_c5, ANIO, MES)
    h6 = historial_de(s, id_c6, ANIO, MES)
check("C1 historial creado", h1 is not None)
check("C2 historial ICL creado", h2 is not None)
check("C4 historial creado", h4 is not None)
check("C5 historial creado", h5 is not None)
check("C6 historial creado", h6 is not None)
if not all(h is not None for h in (h1, h2, h4, h5, h6)):
    print("\nHUBO ERRORES en la preparación; abortando.")
    sys.exit(1)
id_h1 = h1.id_historial_aumentos
id_h2 = h2.id_historial_aumentos
id_h4 = h4.id_historial_aumentos
id_h5 = h5.id_historial_aumentos
id_h6 = h6.id_historial_aumentos

# C2 (ICL): base 480000, coeficiente 1.15 -> propuesto 552000 (15%)
check("C2 ICL propuesto=552000", h2.alquiler_propuesto == 552000, str(h2.alquiler_propuesto))
check("C2 ICL coeficiente=1.15", round(h2.coeficiente_icl or 0, 6) == 1.15)

# ── 19) SIN_AUMENTO: no genera historial ni pendiente editable ──────
with Session(engine) as s:
    check("C3 sin historial (SIN_AUMENTO)", historial_de(s, id_c3, ANIO, MES) is None)

# ── 1) Obtener aumentos PENDIENTES ──────────────────────────────────
r = client.get("/aumentos/historial", params={"estado": "PENDIENTE"})
check("pendientes endpoint 200", r.status_code == 200)
pend_ids = [i["historial"]["id_historial_aumentos"] for i in r.json()]
check("pendientes incluye C1", id_h1 in pend_ids)
check("pendientes incluye C2 (ICL)", id_h2 in pend_ids)
check("pendientes NO incluye C3", id_c3 not in [i["historial"]["id_contratos"] for i in r.json()])
fila = next(i for i in r.json() if i["historial"]["id_historial_aumentos"] == id_h1)
check("pendiente: departamento", fila["departamento"]["codigo"] == "TP31")
check("pendiente: inquilino", fila["inquilino"]["nombre_apellido"] == "TEST P2")
check("pendiente: anio/mes", (fila["historial"]["anio"], fila["historial"]["mes"]) == (ANIO, MES))
check("pendiente: estado", fila["historial"]["estado"] == "PENDIENTE")
check("pendiente: tipo", fila["historial"]["tipo_aumento"] == "MANUAL")
check("pendiente: anterior", fila["historial"]["alquiler_anterior"] == 100000)
check("pendiente: propuesto", fila["historial"]["alquiler_propuesto"] == 110000)
check("pendiente: aplicado inicial=propuesto", fila["historial"]["alquiler_aplicado"] == 110000)
check("pendiente: expensa presente", fila["historial"]["expensa_anterior"] == 20000)
r = client.get("/aumentos/historial", params={"estado": "CONSOLIDADO"})
check("historial CONSOLIDADO no trae pendientes del test",
      {id_h1, id_h2, id_h4, id_h5, id_h6}.isdisjoint(
          {i["historial"]["id_historial_aumentos"] for i in r.json()}))

# ── 2) Modificar solo Alquiler ──────────────────────────────────────
r = client.patch(f"/aumentos/historial/{id_h1}", json={"alquiler_aplicado": 105000})
check("PATCH solo alquiler 200", r.status_code == 200, str(r.status_code))
with Session(engine) as s:
    h1b = s.get(HistorialAumento, id_h1)
    check("alquiler_aplicado=105000", h1b.alquiler_aplicado == 105000, str(h1b.alquiler_aplicado))
    check("% alquiler recalculado=5", round(h1b.porcentaje_alquiler_aplicado, 2) == 5.0,
          str(h1b.porcentaje_alquiler_aplicado))
    check("expensa intacta", h1b.expensa_aplicada == 22000, str(h1b.expensa_aplicada))
    check("% expensa intacto=10", round(h1b.porcentaje_expensa_aplicado or 0, 6) == 10.0)

# ── 3) Modificar solo Expensa ───────────────────────────────────────
r = client.patch(f"/aumentos/historial/{id_h1}", json={"expensa_aplicada": 21500})
check("PATCH solo expensa 200", r.status_code == 200)
with Session(engine) as s:
    h1c = s.get(HistorialAumento, id_h1)
    check("expensa_aplicada=21500", h1c.expensa_aplicada == 21500)
    check("% expensa recalculado=7.5", round(h1c.porcentaje_expensa_aplicado, 2) == 7.5,
          str(h1c.porcentaje_expensa_aplicado))
    check("alquiler intacto tras expensa", h1c.alquiler_aplicado == 105000)
    check("% alquiler intacto=5", round(h1c.porcentaje_alquiler_aplicado, 2) == 5.0)

# ── 4) Modificar ambos ──────────────────────────────────────────────
r = client.patch(f"/aumentos/historial/{id_h1}", json={"alquiler_aplicado": 108000, "expensa_aplicada": 21000})
check("PATCH ambos 200", r.status_code == 200)
with Session(engine) as s:
    h1d = s.get(HistorialAumento, id_h1)
    check("ambos: alquiler=108000", h1d.alquiler_aplicado == 108000)
    check("ambos: expensa=21000", h1d.expensa_aplicada == 21000)
    check("ambos: % alq=8", round(h1d.porcentaje_alquiler_aplicado, 2) == 8.0)
    check("ambos: % exp=5", round(h1d.porcentaje_expensa_aplicado, 2) == 5.0)

# ── 5) Monto menor al anterior: rechazado ───────────────────────────
r = client.patch(f"/aumentos/historial/{id_h1}", json={"alquiler_aplicado": 95000})
check("monto < anterior rechazado (400)", r.status_code == 400, str(r.status_code))
check("mensaje claro", "no puede ser inferior" in r.json().get("detail", ""), r.json().get("detail", ""))
r = client.patch(f"/aumentos/historial/{id_h1}", json={"expensa_aplicada": 19000})
check("expensa < anterior rechazada (400)", r.status_code == 400)

# ── 6) Monto igual al anterior: permitido, % = 0 ────────────────────
r = client.patch(f"/aumentos/historial/{id_h1}", json={"alquiler_aplicado": 100000})
check("monto = anterior permitido", r.status_code == 200, str(r.status_code))
with Session(engine) as s:
    h1e = s.get(HistorialAumento, id_h1)
    check("monto = anterior: % = 0", h1e.porcentaje_alquiler_aplicado == 0.0,
          str(h1e.porcentaje_alquiler_aplicado))

# ── 7) Monto superior a la propuesta: permitido ─────────────────────
r = client.patch(f"/aumentos/historial/{id_h1}", json={"alquiler_aplicado": 120000})
check("monto > propuesta permitido", r.status_code == 200)
with Session(engine) as s:
    h1f = s.get(HistorialAumento, id_h1)
    check("monto > propuesta: % = 20", round(h1f.porcentaje_alquiler_aplicado, 2) == 20.0,
          str(h1f.porcentaje_alquiler_aplicado))

# ── 8) Múltiples modificaciones mientras PENDIENTE ──────────────────
for i, monto in enumerate((112000, 106000, 111000), 1):
    r = client.patch(f"/aumentos/historial/{id_h1}", json={"alquiler_aplicado": monto})
    check(f"modificacion multiple #{i}", r.status_code == 200)
with Session(engine) as s:
    h1g = s.get(HistorialAumento, id_h1)
    check("multiples: valor final", h1g.alquiler_aplicado == 111000)
    check("multiples: % final=11", round(h1g.porcentaje_alquiler_aplicado, 2) == 11.0)
    check("multiples: fecha_actualizacion actualizada",
          h1g.fecha_actualizacion > h1g.fecha_creacion)

# ── 10) Propuesta congelada + 14) Datos que no cambian ──────────────
with Session(engine) as s:
    h1h = s.get(HistorialAumento, id_h1)
    check("propuesta congelada (monto)", h1h.alquiler_propuesto == 110000)
    check("propuesta congelada (%)", round(h1h.porcentaje_alquiler_propuesto, 6) == 10.0)
    check("anterior congelado", h1h.alquiler_anterior == 100000)
    check("tipo_aumento congelado", h1h.tipo_aumento == "MANUAL")
    c1 = s.get(Contrato, id_c1)
    check("base_inicial intacta", c1.alquiler_base_inicial == 100000)
    check("expensa_inicial intacta", c1.expensa_base_inicial == 20000)
    check("fecha_ultimo_aumento intacta", c1.fecha_ultimo_aumento == date(ANIO, MES, 1),
          str(c1.fecha_ultimo_aumento))
    check("ultimo_aumento_anio/mes intactos", (c1.ultimo_aumento_anio, c1.ultimo_aumento_mes) == (ANIO, MES))

# ── 11) ICL: modificar aplicado NO altera datos ICL ─────────────────
r = client.patch(f"/aumentos/historial/{id_h2}", json={"alquiler_aplicado": 500000})
check("ICL PATCH 200", r.status_code == 200)
with Session(engine) as s:
    h2b = s.get(HistorialAumento, id_h2)
    check("ICL: aplicado=500000", h2b.alquiler_aplicado == 500000)
    check("ICL: % aplicado≈4.17", abs(h2b.porcentaje_alquiler_aplicado - 4.17) < 0.01,
          str(h2b.porcentaje_alquiler_aplicado))
    check("ICL: coeficiente intacto tras edicion", round(h2b.coeficiente_icl or 0, 6) == 1.15)
    check("ICL: icl_inicial/final intactos", h2b.icl_inicial == 25.0 and h2b.icl_final == 28.75)
    check("ICL: fechas ICL intactas", h2b.fecha_icl_inicial is not None and h2b.fecha_icl_final is not None)
    check("ICL: propuesto intacto", h2b.alquiler_propuesto == 552000)

# ── 12) Restaurar propuesta ─────────────────────────────────────────
r = client.patch(f"/aumentos/historial/{id_h1}",
                 json={"alquiler_aplicado": 110000, "expensa_aplicada": 22000})
check("restaurar propuesta 200", r.status_code == 200)
with Session(engine) as s:
    h1i = s.get(HistorialAumento, id_h1)
    check("restaurar: aplicado=propuesto", h1i.alquiler_aplicado == h1i.alquiler_propuesto)
    check("restaurar: % aplicado=% propuesto",
          round(h1i.porcentaje_alquiler_aplicado, 6) == round(h1i.porcentaje_alquiler_propuesto, 6))
    check("restaurar expensa: aplicada=propuesta", h1i.expensa_aplicada == h1i.expensa_propuesta)
    check("restaurar expensa: % restaurado",
          round(h1i.porcentaje_expensa_aplicado, 6) == round(h1i.porcentaje_expensa_propuesto, 6))

# ── 13/14/15) Sincronización contrato + registro + total ────────────
# C4: alquiler 100000->110000 propuesto, impuesto 5000, sin expensa.
# total = alquiler efectivo + impuesto.
r = client.patch(f"/aumentos/historial/{id_h4}", json={"alquiler_aplicado": 105000})
check("PATCH C4 200", r.status_code == 200)
with Session(engine) as s:
    c4 = s.get(Contrato, id_c4)
    check("sync contrato: base_actual=105000", c4.alquiler_base_actual == 105000,
          str(c4.alquiler_base_actual))
    reg4 = s.exec(select(RegistroMensual).where(RegistroMensual.id_contratos == id_c4,
                                                RegistroMensual.anio == ANIO,
                                                RegistroMensual.mes == MES)).first()
    check("sync registro: calculado=105000", reg4.alquiler_calculado == 105000)
    check("sync registro: legacy %=5", round(reg4.porcentaje_aumento_usado or 0, 2) == 5.0,
          str(reg4.porcentaje_aumento_usado))
    check("sync registro: total recalculado", reg4.total == 110000, str(reg4.total))  # 105000+5000

# ── 16) Overrides permanecen intactos ───────────────────────────────
r = client.post(f"/dashboard/registros/{reg4.id_registros_mensuales}/override",
                params={"alquiler_override": 100000, "nota_override": "ajuste test"})
check("override cargado", r.status_code == 200, str(r.status_code))
with Session(engine) as s:
    reg4b = s.get(RegistroMensual, reg4.id_registros_mensuales)
    check("override: total con override", reg4b.total == 105000, str(reg4b.total))  # 100000+5000
r = client.patch(f"/aumentos/historial/{id_h4}", json={"alquiler_aplicado": 107000})
check("PATCH C4 con override 200", r.status_code == 200)
with Session(engine) as s:
    reg4c = s.get(RegistroMensual, reg4.id_registros_mensuales)
    check("override intacto", reg4c.alquiler_override == 100000, str(reg4c.alquiler_override))
    check("nota_override intacta", reg4c.nota_override == "ajuste test")
    check("calculado actualizado a 107000", reg4c.alquiler_calculado == 107000)
    check("total respeta override (100000+5000)", reg4c.total == 105000, str(reg4c.total))
    # contrato sync con el aplicado
    check("contrato sincronizado a 107000", s.get(Contrato, id_c4).alquiler_base_actual == 107000)

# ── 17) Próximo aumento usa la nueva base ───────────────────────────
r = client.get("/aumentos/")
item_c6 = next(i for i in r.json() if i["contrato"]["id_contratos"] == id_c6)
with Session(engine) as s:
    c6 = s.get(Contrato, id_c6)
check("C6 proximo existe", item_c6 is not None)
check("C6 proximo = base_actual del contrato",
      item_c6 and item_c6["proximo_aumento"]["alquiler_actual"] == c6.alquiler_base_actual,
      f"proximo={item_c6['proximo_aumento']['alquiler_actual'] if item_c6 else None} base={c6.alquiler_base_actual}")

# Modificar C6 y verificar que la proyección siguiente arranca del aplicado
r = client.patch(f"/aumentos/historial/{id_h6}", json={"alquiler_aplicado": 100000})
check("PATCH C6 200", r.status_code == 200)
r = client.get("/aumentos/")
item_c6 = next(i for i in r.json() if i["contrato"]["id_contratos"] == id_c6)
check("C6 siguiente proyección parte de 100000 (aplicado)",
      item_c6["proximo_aumento"]["alquiler_actual"] == 100000,
      f"={item_c6['proximo_aumento']['alquiler_actual']}")
check("C6 próximo alquiler nuevo = 110000 (10% sobre 100000)",
      item_c6["proximo_aumento"]["alquiler_nuevo"] == 110000,
      f"={item_c6['proximo_aumento']['alquiler_nuevo']}")

# ── Casos de error del endpoint ─────────────────────────────────────
r = client.patch("/aumentos/historial/999999", json={"alquiler_aplicado": 150000})
check("aumento inexistente 404", r.status_code == 404, str(r.status_code))
r = client.patch(f"/aumentos/historial/{id_h1}", json={})
check("body vacio 400", r.status_code == 400, str(r.status_code))

# ── 9) CONSOLIDADO: modificación rechazada ──────────────────────────
# Cobrar C4 -> consolida su aumento
reg_id_c4 = reg4.id_registros_mensuales
r = client.post(f"/dashboard/registros/{reg_id_c4}/pagado")
check("cobrar C4", r.status_code == 200, str(r.status_code))
with Session(engine) as s:
    h4c = s.get(HistorialAumento, id_h4)
    check("pago consolida C4", h4c.estado == "CONSOLIDADO")
r = client.patch(f"/aumentos/historial/{id_h4}", json={"alquiler_aplicado": 200000})
check("CONSOLIDADO rechazado (409)", r.status_code == 409, str(r.status_code))
check("mensaje consolidado claro", "CONSOLIDADO" in r.json().get("detail", ""), r.json().get("detail", ""))

# ── 18) Consolidación: desaparece de pendientes, queda en historial ─
r = client.get("/aumentos/historial", params={"estado": "PENDIENTE"})
check("C4 ya no está en pendientes",
      id_h4 not in [i["historial"]["id_historial_aumentos"] for i in r.json()])
r = client.get("/aumentos/historial", params={"estado": "CONSOLIDADO"})
fila_c4 = next((i for i in r.json() if i["historial"]["id_historial_aumentos"] == id_h4), None)
check("C4 aparece en historial consolidado", fila_c4 is not None)
if fila_c4:
    check("C4 consolidado conserva aplicado final", fila_c4["historial"]["alquiler_aplicado"] == 107000,
          str(fila_c4["historial"]["alquiler_aplicado"]))
    check("C4 consolidado conserva propuesto", fila_c4["historial"]["alquiler_propuesto"] == 110000)
    check("C4 consolidado registra fecha_consolidacion",
          fila_c4["historial"]["fecha_consolidacion"] is not None)

# ── 20) Regresión: Servicios / Dashboard / impuesto / historial ─────
r = client.get("/servicios/pendientes")
check("servicios 200 (regresion)", r.status_code == 200)
fila_c6 = next((i for i in r.json() if i["contrato"]["id_contratos"] == id_c6), None)
check("servicios: C6 visible (cobra luz)", fila_c6 is not None)
if fila_c6:
    r2 = client.post("/servicios/guardar",
                     params={"id_registro": fila_c6["registro"]["id_registros_mensuales"], "luz": 8000})
    check("servicios: guardar luz", r2.status_code == 200)
    # C6: aplicado 100000 + luz 8000 = 108000
    check("servicios: total C6 recalculado con alquiler aplicado", r2.json()["total"] == 108000,
          f"={r2.json().get('total')}")

r = client.get("/dashboard/mes-actual")
check("dashboard 200 (regresion)", r.status_code == 200)
reg6_item = reg_de(r.json(), id_c6)
check("dashboard: C6 alquiler_calculado = aplicado 100000",
      reg6_item["registro"]["alquiler_calculado"] == 100000,
      f"={reg6_item['registro']['alquiler_calculado'] if reg6_item else None}")

r = client.get("/aumentos/")
check("aumentos UI 200 (regresion)", r.status_code == 200)
item_c3 = next(i for i in r.json() if i["contrato"]["id_contratos"] == id_c3)
check("aumentos: C3 SIN_AUMENTO sin proximo",
      item_c3["proximo_aumento"]["tipo_aumento"] == "SIN_AUMENTO"
      and item_c3["proximo_aumento"]["proximo_anio"] is None)

r = client.get("/aumentos/historial")
check("historial sin filtro 200", r.status_code == 200)
check("historial sin filtro incluye pendientes y consolidados",
      {id_h1, id_h4}.issubset({i["historial"]["id_historial_aumentos"] for i in r.json()}))

# ── 20b) MANUAL sigue funcionando tras modificar (nuevo ciclo) ──────
# Abrir el mes siguiente no debe reaplicar el aumento (idempotencia del historial)
with Session(engine) as s:
    c1 = s.get(Contrato, id_c1)
    res = mes_service.aplicar_aumento_si_corresponde(s, c1, ANIO, MES)
check("regresion: reaplicar mismo mes = None (idempotencia)", res is None)

# ── Limpieza ────────────────────────────────────────────────────────
for cid in (id_c1, id_c2, id_c3, id_c4, id_c5, id_c6):
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