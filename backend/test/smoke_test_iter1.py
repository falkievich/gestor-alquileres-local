import sys, os
# Agrega la carpeta backend (padre de test/) al path para poder importar "app"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=True)
errores = []

def check(nombre, cond, detalle=""):
    estado = "OK " if cond else "FAIL"
    print(f"[{estado}] {nombre} {detalle}")
    if not cond:
        errores.append(nombre)

# 1. Health + migracion
r = client.get("/health")
check("health", r.status_code == 200)

# 2. Crear departamento + inquilino de prueba
r = client.post("/departamentos/", json={"piso": "Piso 1", "codigo": "TEST"})
check("crear depto", r.status_code == 201, str(r.json()))
id_dep = r.json()["id_departamentos"]
r = client.post("/inquilinos/", json={"nombre_apellido": "TEST INQ", "es_actual": True})
check("crear inquilino", r.status_code == 201)
id_inq = r.json()["id_inquilinos"]

# 3. Crear contrato EN CURSO con inicial y actual distintos
from datetime import date
r = client.post("/contratos/", json={
    "id_departamentos": id_dep, "id_inquilinos": id_inq,
    "fecha_inicio": "2024-03-01", "fecha_fin": "2027-03-01",
    "alquiler_base_inicial": 200000, "alquiler_base_actual": 650000,
    "expensa_base_inicial": 30000, "expensa_base_actual": 90000,
    "cobra_expensa": True, "tipo_aumento": "MANUAL", "porcentaje_aumento": 10.0,
    "periodicidad_aumento_meses": 6, "fecha_ultimo_aumento": "2026-03-01",
})
check("crear contrato en curso", r.status_code == 201, str(r.json()))
id_cto = r.json()["id_contratos"]
check("inicial guardado", r.json()["alquiler_base_inicial"] == 200000)
check("actual guardado", r.json()["alquiler_base_actual"] == 650000)
check("expensa inicial", r.json().get("expensa_base_inicial") == 30000)

# 4. Crear contrato NORMAL (sin en curso) -> inicial debe == actual
#    Con impuesto_fijo de 5000 y cobra_luz para probar servicios + impuesto
r = client.post("/departamentos/", json={"piso": "Piso 1", "codigo": "TEST2"})
id_dep2 = r.json()["id_departamentos"]
r = client.post("/contratos/", json={
    "id_departamentos": id_dep2, "id_inquilinos": id_inq,
    "fecha_inicio": "2026-01-01", "fecha_fin": "2026-10-31",
    "alquiler_base_actual": 100000, "impuesto_fijo": 5000,
    "cobra_luz": True, "tipo_aumento": "MANUAL",
    "porcentaje_aumento": 5.0, "periodicidad_aumento_meses": 6,
    "fecha_ultimo_aumento": "2026-09-01",
})
check("crear contrato normal", r.status_code == 201, str(r.json()))
id_cto2 = r.json()["id_contratos"]
check("normal: inicial==actual", r.json()["alquiler_base_inicial"] == 100000)
check("impuesto guardado", r.json()["impuesto_fijo"] == 5000)

# 4b. Servicios SIN pasar por el dashboard: el registro se genera al pedir servicios
r = client.get("/servicios/pendientes")
check("servicios ok", r.status_code == 200)
fila = next((i for i in r.json() if i["contrato"]["id_contratos"] == id_cto2), None)
check("servicio visible sin pasar por dashboard", fila is not None)
if fila:
    check("registro tiene impuesto", fila["registro"].get("impuesto") == 5000,
          f"={fila['registro'].get('impuesto')}")

# 4c. Aumento fuera de contrato: vence 2026-10, proximo aumento (base 2026-01 + 6) = 2027-01
r = client.get("/aumentos/")
item2 = next((i for i in r.json() if i["contrato"]["id_contratos"] == id_cto2), None)
if item2:
    check("aumento fuera de contrato", item2["proximo_aumento"]["aumento_fuera_de_contrato"] is True,
          f"={item2['proximo_aumento'].get('aumento_fuera_de_contrato')}")
else:
    check("aumentos lista contrato normal", False)

# 5. Dashboard mes actual -> genera registro; luego editar alquiler actual y verificar sync
r = client.get("/dashboard/mes-actual")
check("dashboard", r.status_code == 200)
reg_antes = next((i for i in r.json() if i["contrato"]["id_contratos"] == id_cto), None)
check("registro en dashboard", reg_antes is not None)
alq_antes = reg_antes["registro"]["alquiler_calculado"]
# El dashboard puede aplicar el aumento automaticamente (650000 * 1.1 = 715000)
check("registro usa alquiler actual (con aumento auto)", alq_antes in (650000, 715000), f"={alq_antes}")

# 6. Editar alquiler actual -> el registro no pagado del mes debe re-sincronizarse
r = client.put(f"/contratos/{id_cto}", json={"alquiler_base_actual": 700000, "expensa_base_actual": 95000})
check("editar contrato", r.status_code == 200)
r = client.get("/dashboard/mes-actual")
reg_despues = next((i for i in r.json() if i["contrato"]["id_contratos"] == id_cto), None)
check("sync alquiler", reg_despues["registro"]["alquiler_calculado"] == 700000,
      f"antes={alq_antes} despues={reg_despues['registro']['alquiler_calculado']}")
check("sync expensa", reg_despues["registro"]["expensa_calculada"] == 95000,
      f"={reg_despues['registro']['expensa_calculada']}")
check("sync total", reg_despues["registro"]["total"] == 700000 + 95000,
      f"={reg_despues['registro']['total']}")

# 7b. Reabrir el dashboard NO debe aplicar el aumento de nuevo (no doble aumento)
r = client.get("/dashboard/mes-actual")
reg_reabrir = next((i for i in r.json() if i["contrato"]["id_contratos"] == id_cto), None)
check("no doble aumento en dashboard", reg_reabrir["registro"]["alquiler_calculado"] == 700000,
      f"={reg_reabrir['registro']['alquiler_calculado']}")

# 7. Servicios pendientes (este contrato no cobra agua/luz, no debe aparecer)
r = client.get("/servicios/pendientes")
check("servicios ok", r.status_code == 200)

# 7b. Editar impuesto del contrato normal -> registro no pagado del mes se sincroniza
r = client.put(f"/contratos/{id_cto2}", json={"impuesto_fijo": 7000})
check("editar impuesto", r.status_code == 200)
r = client.get("/dashboard/mes-actual")
reg_imp = next((i for i in r.json() if i["contrato"]["id_contratos"] == id_cto2), None)
if reg_imp:
    check("sync impuesto", reg_imp["registro"]["impuesto"] == 7000,
          f"={reg_imp['registro']['impuesto']}")
else:
    check("dashboard lista contrato normal", False)

# 8. Aumentos: proximo aumento usa alquiler_base_actual (700000)
r = client.get("/aumentos/")
item = next((i for i in r.json() if i["contrato"]["id_contratos"] == id_cto), None)
if item:
    check("aumento usa actual", item["proximo_aumento"]["alquiler_actual"] == 700000,
          f"={item['proximo_aumento']['alquiler_actual']}")
else:
    check("aumento lista contrato", False)

# 9. Limpieza (SQLite no enforcea FK: borrar registros huérfanos al final)
for cid in (id_cto2, id_cto):
    client.delete(f"/contratos/{cid}")
client.delete(f"/inquilinos/{id_inq}")
for did in (id_dep2, id_dep):
    client.delete(f"/departamentos/{did}")

from sqlmodel import Session, select
from app.db import engine
from app.model.models import RegistroMensual, Contrato, HistorialAumento
with Session(engine) as s:
    ids_existentes = [c.id_contratos for c in s.exec(select(Contrato)).all()]
    orfanos = [r for r in s.exec(select(RegistroMensual)).all()
               if r.id_contratos not in ids_existentes]
    for r in orfanos:
        s.delete(r)
    orfanos_h = [h for h in s.exec(select(HistorialAumento)).all()
                 if h.id_contratos not in ids_existentes]
    for h in orfanos_h:
        s.delete(h)
    s.commit()
print("Limpieza hecha.")

if errores:
    print(f"\nHUBO ERRORES: {errores}")
    sys.exit(1)
print("\nTODO OK")
