# Gestor de Alquileres — Local

Aplicación de gestión de alquileres 100% local. Sin login, se abre en Chrome.

## Stack
- **Backend**: Python + FastAPI + SQLModel + SQLite
- **Frontend**: React + Vite + TypeScript + Tailwind CSS

---

## Cómo ejecutar

### Backend
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Abrir
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs

---

## Estructura
```
gestor-alquileres-local/
├── backend/
│   ├── app/
│   │   ├── main.py          # App FastAPI
│   │   ├── db.py            # Configuración SQLite
│   │   ├── model/           # Modelos SQLModel
│   │   ├── crud/            # Operaciones DB
│   │   ├── service/         # Lógica de negocio
│   │   └── routers/         # Endpoints
│   └── requirements.txt
├── frontend/                # Vite + React + TS
├── base_de_datos/
│   └── alquileres.sqlite    # Base de datos
└── backups/                 # Copias de la DB
```

---

## Endpoints principales

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | /health | Estado del backend |
| GET/POST | /departamentos/ | ABM departamentos |
| GET/POST | /inquilinos/ | ABM inquilinos |
| GET/POST | /contratos/ | ABM contratos |
| POST | /contratos/{id}/cerrar | Cerrar contrato |
| POST | /contratos/{id}/archivo | Subir PDF/DOCX |
| GET | /contratos/{id}/archivo | Descargar archivo |
| GET | /dashboard/mes-actual | Dashboard del mes |
| POST | /dashboard/registros/{id}/pagado | Marcar pagado |
| POST | /dashboard/registros/{id}/override | Ajuste del mes |
| GET | /servicios/pendientes | Pendientes agua/luz |
| POST | /servicios/guardar | Guardar servicios |
| GET | /aumentos/ | Vista de aumentos |
| POST | /backup/ | Crear backup |

---

## Pantallas

1. **Dashboard** — Cobros del mes actual, estados servicios/pago, backup
2. **Departamentos** — ABM con historial e inquilinos
3. **Inquilinos** — ABM con contratos y pagos
4. **Contratos** — CRUD con upload PDF/DOCX, cerrar, alertas vencimiento
5. **Servicios** — Carga de agua/luz del mes
6. **Aumentos** — Próximos aumentos y alertas
