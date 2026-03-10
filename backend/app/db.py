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


def get_session():
    with Session(engine) as session:
        yield session
