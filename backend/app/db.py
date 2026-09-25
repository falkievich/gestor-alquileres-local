from sqlmodel import Session, create_engine, SQLModel
import os

# backend/app/db.py -> goes up to backend/ then to project root
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(BACKEND_DIR)
DB_DIR = os.path.join(PROJECT_DIR, "base_de_datos")
DB_PATH = os.path.join(DB_DIR, "alquileres.sqlite")

os.makedirs(DB_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _migrar_columnas_contratos()


def _migrar_columnas_contratos():
    """
    Migración liviana para bases SQLite ya existentes:
    agrega columnas nuevas si todavía no existen.
    """
    from sqlalchemy import text

    with engine.begin() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(contratos)"))]
        if not cols:
            return
        if "alquiler_base_inicial" not in cols:
            conn.execute(text(
                "ALTER TABLE contratos ADD COLUMN alquiler_base_inicial INTEGER"))
        if "expensa_base_inicial" not in cols:
            conn.execute(text(
                "ALTER TABLE contratos ADD COLUMN expensa_base_inicial INTEGER"))
        if "impuesto_fijo" not in cols:
            conn.execute(text(
                "ALTER TABLE contratos ADD COLUMN impuesto_fijo INTEGER"))

        cols_reg = [row[1] for row in conn.execute(text("PRAGMA table_info(registros_mensuales)"))]
        if cols_reg and "impuesto" not in cols_reg:
            conn.execute(text(
                "ALTER TABLE registros_mensuales ADD COLUMN impuesto INTEGER"))


def get_session():
    with Session(engine) as session:
        yield session
