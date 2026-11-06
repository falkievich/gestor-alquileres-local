"""
Smoke test de los 9 errores detectados en la revisión de temporalidad y meses
arrastrados (ver Documentación/errores detectados y parches.md).

Corre siempre contra una SQLite temporal propia (nunca la base real) y con
fechas relativas al mes actual, así pasa en cualquier fecha.
Ejecutar desde backend/: .venv\\Scripts\\python.exe test\\smoke_test_iter9_errores_detectados.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, create_engine, select  # noqa: E402

import app.db as db  # noqa: E402

db.engine = create_engine(
    f"sqlite:///{os.path.join(tempfile.mkdtemp(), 'errores.sqlite')}",
    connect_args={"check_same_thread": False},
)
import app.main  # noqa: E402,F401  (registra los modelos en la metadata)
db.create_db_and_tables()

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
import app.service.mes_service as mes_service  # noqa: E402
from app.crud import registros as crud_registros  # noqa: E402
from app.model.models import Contrato, HistorialAumento, RegistroMensual  # noqa: E402

engine = db.engine
client = TestClient(app, raise_server_exceptions=True)
errores = []


def check(nombre, cond, detalle=""):
    estado = "OK " if cond else "FAIL"
    print(f"[{estado}] {nombre} {detalle}")
    if not cond:
        errores.append(nombre)


def periodo(n):
    """(anio, mes) ubicado n meses después del actual (n < 0: antes)."""
    anio, mes = mes_service.get_mes_actual()
    total = anio * 12 + (mes - 1) + n
    return total // 12, total % 12 + 1


def fecha_mes(n):
    anio, mes = periodo(n)
    return f"{anio}-{mes:02d}-01"


r = client.post("/inquilinos/", json={"nombre_apellido": "TEST ERRORES", "es_actual": True})
ID_INQ = r.json()["id_inquilinos"]
_deps = iter(range(1, 100))


def crear_contrato(**kw):
    r = client.post("/departamentos/", json={"piso": "Piso 1", "codigo": f"E9{next(_deps):02d}"})
    assert r.status_code == 201, r.text
    base = {
        "id_departamentos": r.json()["id_departamentos"], "id_inquilinos": ID_INQ,
        "fecha_inicio": fecha_mes(-6), "fecha_fin": fecha_mes(12),
        "alquiler_base_actual": 100000, "tipo_aumento": "MANUAL",
        "porcentaje_aumento": 10.0, "periodicidad_aumento_meses": 12,
        # Último aumento hace un mes: no corresponde aumento en el mes actual.
        "fecha_ultimo_aumento": fecha_mes(-1),
    }
    base.update(kw)
    r = client.post("/contratos/", json=base)
    assert r.status_code == 201, r.text
    return r.json()["id_contratos"]


def insertar_registro(id_c, n, alquiler, **kw):
    anio, mes = periodo(n)
    with Session(engine) as s:
        reg = RegistroMensual(id_contratos=id_c, anio=anio, mes=mes,
                              alquiler_calculado=alquiler, total=alquiler, **kw)
        s.add(reg)
        s.commit()
        s.refresh(reg)
        return reg.id_registros_mensuales


def insertar_pendiente(id_c, n, anterior, aplicado):
    anio, mes = periodo(n)
    with Session(engine) as s:
        h = HistorialAumento(
            id_contratos=id_c, anio=anio, mes=mes, estado="PENDIENTE",
            tipo_aumento="MANUAL", alquiler_anterior=anterior,
            alquiler_propuesto=aplicado, alquiler_aplicado=aplicado,
            porcentaje_alquiler_propuesto=10.0, porcentaje_alquiler_aplicado=10.0)
        s.add(h)
        s.commit()
        s.refresh(h)
        return h.id_historial_aumentos


def registro(id_c, n):
    with Session(engine) as s:
        return crud_registros.get_registro(s, id_c, *periodo(n))


def registros(id_c):
    with Session(engine) as s:
        return sorted(crud_registros.get_registros_by_contrato(s, id_c),
                      key=lambda r: (r.anio, r.mes))


def historial(id_h):
    with Session(engine) as s:
        return s.get(HistorialAumento, id_h)


def historial_periodo(id_c, n):
    with Session(engine) as s:
        anio, mes = periodo(n)
        return s.exec(select(HistorialAumento).where(
            HistorialAumento.id_contratos == id_c,
            HistorialAumento.anio == anio, HistorialAumento.mes == mes)).first()


def contrato(id_c):
    with Session(engine) as s:
        return s.get(Contrato, id_c)


def filas(url, id_c):
    return [i for i in client.get(url).json() if i["contrato"]["id_contratos"] == id_c]


def dashboard(id_c):
    return filas("/dashboard/mes-actual", id_c)


def pagar(id_reg):
    return client.post(f"/dashboard/registros/{id_reg}/pagado").status_code


def ajustar(id_reg, **params):
    r = client.post(f"/dashboard/registros/{id_reg}/override", params=params)
    assert r.status_code == 200, r.text


# ══ Error 1: contratos que todavía no empezaron ══════════════════════
print("\n--- Error 1: Servicios no genera cobros de contratos que no empezaron ---")
id_futuro = crear_contrato(fecha_inicio=fecha_mes(1), fecha_fin=fecha_mes(13),
                           fecha_ultimo_aumento=None, cobra_agua=True)
check("Servicios no lista el contrato futuro", filas("/servicios/pendientes", id_futuro) == [])
check("Dashboard no lista el contrato futuro", dashboard(id_futuro) == [])
check("no se creó ningún registro del contrato futuro", registros(id_futuro) == [])

# Registro fantasma de antes del inicio (creado por la versión anterior).
id_inicia_hoy = crear_contrato(fecha_inicio=fecha_mes(0), fecha_ultimo_aumento=None,
                               cobra_luz=True)
id_fantasma = insertar_registro(id_inicia_hoy, -1, 100000)
filas_d = dashboard(id_inicia_hoy)
check("el registro fantasma no aparece como atrasado",
      [(f["anio"], f["mes"]) for f in filas_d] == [periodo(0)], str([(f["anio"], f["mes"]) for f in filas_d]))
check("Servicios tampoco lo lista",
      all(f["registro"]["id_registros_mensuales"] != id_fantasma
          for f in filas("/servicios/pendientes", id_inicia_hoy)))
check("no se puede cobrar un mes anterior al inicio", pagar(id_fantasma) == 409)

# ══ Error 2: aumento aplicado después de crear el registro del mes ═══
print("\n--- Error 2: aumento aplicado tarde ---")
# 2a) Se corrige la configuración del aumento a mitad de mes.
id_e2 = crear_contrato()
dashboard(id_e2)
reg = registro(id_e2, 0)
ajustar(reg.id_registros_mensuales, alquiler_override=105000, nota_override="ajuste")
r = client.put(f"/contratos/{id_e2}", json={"fecha_ultimo_aumento": fecha_mes(-12)})
check("editar la fecha del último aumento", r.status_code == 200, r.text[:120])
fila = dashboard(id_e2)[0]
reg = registro(id_e2, 0)
check("el mes en curso pasa a cobrar el monto aumentado",
      reg.alquiler_calculado == 110000 and fila["total"] == 115000,
      f"({reg.alquiler_calculado}, total {fila['total']})")
check("el ajuste manual conserva su +5.000", reg.alquiler_override == 115000, str(reg.alquiler_override))
check("se guarda el porcentaje usado", reg.porcentaje_aumento_usado == 10.0)
check("el aumento queda PENDIENTE", historial_periodo(id_e2, 0).estado == "PENDIENTE")

# 2b) ICL: el BCRA no responde al crear el registro y publica después.
fetch_original = mes_service._fetch_icl_bcra
mes_service._fetch_icl_bcra = lambda desde, hasta: (None, "BCRA caído")
try:
    id_icl = crear_contrato(tipo_aumento="ICL", porcentaje_aumento=0,
                            fecha_ultimo_aumento=fecha_mes(-12))
    dashboard(id_icl)
    check("sin datos ICL se cobra el monto vigente",
          registro(id_icl, 0).alquiler_calculado == 100000
          and historial_periodo(id_icl, 0) is None)
    mes_service._fetch_icl_bcra = lambda desde, hasta: ([
        {"fecha": desde.isoformat(), "valor": 100.0},
        {"fecha": hasta.isoformat(), "valor": 120.0},
    ], None)
    dashboard(id_icl)
    reg = registro(id_icl, 0)
    check("al publicarse el ICL el registro existente cobra el aumento",
          reg.alquiler_calculado == 120000 and reg.total == 120000, str(reg.alquiler_calculado))
finally:
    mes_service._fetch_icl_bcra = fetch_original

# 2c) El mes ya se cobró cuando el aumento pudo aplicarse.
id_e2c = crear_contrato()
dashboard(id_e2c)
check("cobrar el mes sin aumento", pagar(registro(id_e2c, 0).id_registros_mensuales) == 200)
client.put(f"/contratos/{id_e2c}", json={"fecha_ultimo_aumento": fecha_mes(-12)})
dashboard(id_e2c)
reg = registro(id_e2c, 0)
h = historial_periodo(id_e2c, 0)
check("el mes cobrado no se modifica", reg.pagado and reg.alquiler_calculado == 100000)
check("el aumento se consolida (no queda PENDIENTE para siempre)",
      h is not None and h.estado == "CONSOLIDADO", str(h and h.estado))
check("el contrato queda aumentado para los meses siguientes",
      contrato(id_e2c).alquiler_base_actual == 110000)

# ══ Error 3: meses en los que no se abrió la app ═════════════════════
print("\n--- Error 3: meses faltantes se generan como atrasados ---")
id_e3 = crear_contrato(periodicidad_aumento_meses=3, fecha_ultimo_aumento=fecha_mes(-5))
insertar_registro(id_e3, -4, 100000, pagado=True)
filas_d = dashboard(id_e3)
check("aparecen los meses faltantes como atrasados",
      [(f["anio"], f["mes"]) for f in filas_d if f["atrasado"]] == [periodo(-3), periodo(-2), periodo(-1)],
      str([(f["anio"], f["mes"]) for f in filas_d if f["atrasado"]]))
check("cada mes con su monto (el aumento cae en su mes)",
      [r.alquiler_calculado for r in registros(id_e3)] == [100000, 100000, 110000, 110000, 110000],
      str([r.alquiler_calculado for r in registros(id_e3)]))
check("el aumento queda registrado en su mes", historial_periodo(id_e3, -2) is not None
      and historial_periodo(id_e3, -2).estado == "PENDIENTE")
check("el ciclo sigue desde el mes del aumento (no hay otro aumento hoy)",
      historial_periodo(id_e3, 0) is None)

# Sin fecha de último aumento (regla por múltiplos desde el inicio): el
# aumento del mes -1 ya no se pierde.
id_e3b = crear_contrato(fecha_inicio=fecha_mes(-4), fecha_ultimo_aumento=None,
                        periodicidad_aumento_meses=3)
insertar_registro(id_e3b, -3, 100000, pagado=True)
dashboard(id_e3b)
check("el primer aumento por múltiplos no se pierde",
      historial_periodo(id_e3b, -1) is not None and registro(id_e3b, 0).alquiler_calculado == 110000,
      str(registro(id_e3b, 0).alquiler_calculado))

# Contrato cargado hoy sin registros: no se inventa deuda hacia atrás.
id_e3c = crear_contrato(fecha_inicio=fecha_mes(-6))
dashboard(id_e3c)
check("contrato sin registros previos no genera meses atrás",
      [(r.anio, r.mes) for r in registros(id_e3c)] == [periodo(0)])
n_antes = len(registros(id_e3))
dashboard(id_e3)
check("volver a abrir el Dashboard no duplica meses", len(registros(id_e3)) == n_antes)

# ══ Error 4: eliminar departamento / inquilino con contratos ════════
print("\n--- Error 4: eliminar con contratos asociados ---")
id_e4 = crear_contrato()
dashboard(id_e4)
c4 = contrato(id_e4)
r = client.delete(f"/departamentos/{c4.id_departamentos}")
check("no se puede eliminar un departamento con contratos",
      r.status_code == 409 and "contratos asociados" in r.json()["detail"], str(r.status_code))
r = client.delete(f"/inquilinos/{ID_INQ}")
check("no se puede eliminar un inquilino con contratos", r.status_code == 409, str(r.status_code))
check("el contrato sigue intacto", contrato(id_e4) is not None)
id_h4 = insertar_pendiente(id_e4, -1, 90000, 100000)
check("borrar el contrato", client.delete(f"/contratos/{id_e4}").status_code == 204)
check("borrar el contrato elimina sus registros e historial",
      registros(id_e4) == [] and historial(id_h4) is None)
check("ahora sí se puede eliminar el departamento",
      client.delete(f"/departamentos/{c4.id_departamentos}").status_code == 204)

# ══ Error 5: cerrar un contrato con meses sin cobrar ═════════════════
print("\n--- Error 5: la deuda de un contrato cerrado sigue visible ---")
id_e5 = crear_contrato(cobra_luz=True)
id_reg5_a1 = insertar_registro(id_e5, -1, 100000)
id_h5 = insertar_pendiente(id_e5, -1, 90000, 100000)
dashboard(id_e5)
r = client.get(f"/contratos/{id_e5}/meses-sin-cobrar")
check("el modal de cierre recibe los meses sin cobrar",
      r.status_code == 200
      and [(m["anio"], m["mes"]) for m in r.json()] == [periodo(-1), periodo(0)]
      and all(m["total"] == 100000 for m in r.json()), str(r.json()))
check("cerrar el contrato", client.post(f"/contratos/{id_e5}/cerrar").status_code == 200)
filas_d = dashboard(id_e5)
check("Dashboard sigue mostrando el atrasado y el mes en curso",
      [(f["anio"], f["mes"], f["atrasado"]) for f in filas_d]
      == [(*periodo(-1), True), (*periodo(0), False)], str([(f["anio"], f["mes"], f["atrasado"]) for f in filas_d]))
check("las filas indican contrato finalizado", all(f["contrato"]["estado"] == "finalizado" for f in filas_d))
check("Servicios también los lista", len(filas("/servicios/pendientes", id_e5)) == 2)
check("su aumento PENDIENTE sigue visible en Aumentos",
      any(i["historial"]["id_historial_aumentos"] == id_h5
          for i in client.get("/aumentos/historial", params={"estado": "PENDIENTE"}).json()))
n_antes = len(registros(id_e5))
for reg5 in registros(id_e5):
    client.post("/servicios/guardar", params={"id_registro": reg5.id_registros_mensuales, "luz": 1000})
    check(f"cobrar {reg5.mes}/{reg5.anio} del contrato cerrado", pagar(reg5.id_registros_mensuales) == 200)
check("al cobrarse el aumento se consolida", historial(id_h5).estado == "CONSOLIDADO")
check("cobrado todo, el contrato cerrado sale del Dashboard", dashboard(id_e5) == [])
check("un contrato cerrado no genera meses nuevos", len(registros(id_e5)) == n_antes)

# ══ Error 6: acortar fecha_fin ═══════════════════════════════════════
print("\n--- Error 6: meses posteriores al nuevo vencimiento ---")
id_e6 = crear_contrato()
id_reg6 = insertar_registro(id_e6, -1, 100000)
id_h6 = insertar_pendiente(id_e6, -1, 90000, 100000)
dashboard(id_e6)
r = client.put(f"/contratos/{id_e6}", json={"fecha_fin": fecha_mes(-2)})
check("acortar el vencimiento", r.status_code == 200, r.text[:120])
check("el Dashboard ya no muestra meses que no se pueden cobrar", dashboard(id_e6) == [])
check("Aumentos no muestra el PENDIENTE fuera de la vigencia",
      all(i["historial"]["id_historial_aumentos"] != id_h6
          for i in client.get("/aumentos/historial", params={"estado": "PENDIENTE"}).json()))
check("el modal de cierre no los cuenta como deuda",
      client.get(f"/contratos/{id_e6}/meses-sin-cobrar").json() == [])
check("cobrarlo sigue bloqueado", pagar(id_reg6) == 409)
client.put(f"/contratos/{id_e6}", json={"fecha_fin": fecha_mes(12)})
filas_d = [(f["anio"], f["mes"]) for f in dashboard(id_e6)]
check("si se vuelve a extender, los meses reaparecen sin perder datos",
      sorted(filas_d) == [periodo(-1), periodo(0)], str(filas_d))

# ══ Error 7: ajuste masivo ═══════════════════════════════════════════
print("\n--- Error 7: ajuste masivo suma y conserva expensa/nota ---")
# Reproduce el pedido que arma guardarAjusteMasivo (Dashboard.tsx).
id_e7 = crear_contrato(cobra_expensa=True, expensa_base_actual=20000)
dashboard(id_e7)
reg = registro(id_e7, 0)
ajustar(reg.id_registros_mensuales, alquiler_override=105000,
        expensa_override=18000, nota_override="nota previa")
reg = registro(id_e7, 0)
params = {"alquiler_override": (reg.alquiler_override if reg.alquiler_override is not None
                                else reg.alquiler_calculado) + 1000}
if reg.expensa_override is not None:
    params["expensa_override"] = reg.expensa_override
params["nota_override"] = "" or reg.nota_override
ajustar(reg.id_registros_mensuales, **params)
reg = registro(id_e7, 0)
check("el ajuste masivo se suma al ajuste existente", reg.alquiler_override == 106000, str(reg.alquiler_override))
check("se conserva el ajuste de expensa", reg.expensa_override == 18000)
check("se conserva la nota", reg.nota_override == "nota previa")
check("total correcto (106000 + 18000)", reg.total == 124000, str(reg.total))

# ══ Error 8: el ajuste conserva su diferencia ════════════════════════
print("\n--- Error 8: ajustes manuales siguen al monto base ---")
id_e8 = crear_contrato(cobra_expensa=True, expensa_base_actual=20000)
dashboard(id_e8)
reg = registro(id_e8, 0)
ajustar(reg.id_registros_mensuales, alquiler_override=105000,
        expensa_override=18000, nota_override="ajuste")
client.put(f"/contratos/{id_e8}", json={"alquiler_base_actual": 120000, "expensa_base_actual": 25000})
reg = registro(id_e8, 0)
check("alquiler: +5.000 sigue siendo +5.000", (reg.alquiler_calculado, reg.alquiler_override) == (120000, 125000),
      str((reg.alquiler_calculado, reg.alquiler_override)))
check("expensa: -2.000 sigue siendo -2.000", (reg.expensa_calculada, reg.expensa_override) == (25000, 23000),
      str((reg.expensa_calculada, reg.expensa_override)))
check("total con los ajustes desplazados", reg.total == 148000, str(reg.total))
id_e8b = crear_contrato()
dashboard(id_e8b)
ajustar(registro(id_e8b, 0).id_registros_mensuales, alquiler_override=0, nota_override="bonificado")
client.put(f"/contratos/{id_e8b}", json={"alquiler_base_actual": 130000})
reg = registro(id_e8b, 0)
check("un mes bonificado (ajuste en 0) sigue en 0", reg.alquiler_override == 0 and reg.total == 0)

# ══ Error 9: modificar un aumento atrasado no pisa correcciones ═════
print("\n--- Error 9: modificar aumento atrasado respeta la corrección del contrato ---")
id_e9 = crear_contrato(alquiler_base_actual=110000)
insertar_registro(id_e9, -1, 110000)
id_h9 = insertar_pendiente(id_e9, -1, 100000, 110000)
dashboard(id_e9)
client.put(f"/contratos/{id_e9}", json={"alquiler_base_actual": 115000})
check("la corrección llega al mes en curso", registro(id_e9, 0).alquiler_calculado == 115000)
r = client.patch(f"/aumentos/historial/{id_h9}", json={"alquiler_aplicado": 112000})
check("modificar el aumento atrasado", r.status_code == 200, str(r.status_code))
check("el mes del aumento toma el monto modificado", registro(id_e9, -1).alquiler_calculado == 112000)
check("la corrección del contrato no se pisa", contrato(id_e9).alquiler_base_actual == 115000)
check("el mes en curso conserva la corrección", registro(id_e9, 0).alquiler_calculado == 115000)

# Sin corrección, la modificación sigue propagándose (y el ajuste conserva su diferencia).
id_e9b = crear_contrato(alquiler_base_actual=110000)
insertar_registro(id_e9b, -1, 110000)
id_h9b = insertar_pendiente(id_e9b, -1, 100000, 110000)
dashboard(id_e9b)
ajustar(registro(id_e9b, 0).id_registros_mensuales, alquiler_override=113000)
client.patch(f"/aumentos/historial/{id_h9b}", json={"alquiler_aplicado": 112000})
reg = registro(id_e9b, 0)
check("sin corrección: contrato y mes en curso heredan el aplicado",
      contrato(id_e9b).alquiler_base_actual == 112000 and reg.alquiler_calculado == 112000)
check("y el ajuste del mes en curso conserva su +3.000", reg.alquiler_override == 115000, str(reg.alquiler_override))

# ══ Invariantes globales ═════════════════════════════════════════════
print("\n--- Invariantes ---")
with Session(engine) as s:
    todos = s.exec(select(RegistroMensual)).all()
    claves = [(r.id_contratos, r.anio, r.mes) for r in todos]
    check("no hay registros duplicados por contrato/mes", len(claves) == len(set(claves)))
    fuera = [r.id_registros_mensuales for r in todos
             if not mes_service.contrato_vigente_para_mes(s.get(Contrato, r.id_contratos), r.anio, r.mes)]
    check("los únicos registros fuera de vigencia son los insertados a mano",
          fuera == [id_fantasma], str(fuera))
    pend_cobrados = [
        h.id_historial_aumentos for h in s.exec(select(HistorialAumento).where(
            HistorialAumento.estado == "PENDIENTE")).all()
        if (reg := crud_registros.get_registro(s, h.id_contratos, h.anio, h.mes)) is not None and reg.pagado
    ]
    check("ningún aumento PENDIENTE tiene su mes cobrado", pend_cobrados == [], str(pend_cobrados))

if errores:
    print(f"\nHUBO ERRORES: {errores}")
    sys.exit(1)
print("\nTODO OK")
