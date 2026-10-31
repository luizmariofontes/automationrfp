"""Fixtures dos testes.

Testes que usam o banco rodam num banco separado (`<nome>_test`), criado e migrado
automaticamente. Sem Postgres acessível, esses testes são pulados — exceto quando
REQUIRE_DB=1 (CI e `make test`), em que a falta do banco é erro.
"""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LOG_JSON", "false")

_URL_ORIGINAL = make_url(
    os.environ.get("DATABASE_URL", "postgresql+psycopg://rfp:rfp@localhost:5432/rfp")
)
_URL_TESTE = _URL_ORIGINAL.set(database=f"{_URL_ORIGINAL.database}_test")
os.environ["DATABASE_URL"] = _URL_TESTE.render_as_string(hide_password=False)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402
from app.shared.config import get_settings  # noqa: E402
from app.shared.db import Base, get_sessionmaker  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def app():
    return create_app(get_settings())


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _preparar_banco_de_teste() -> None:
    admin = create_engine(_URL_ORIGINAL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        existe = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": _URL_TESTE.database}
        )
        if not existe:
            conn.execute(text(f'CREATE DATABASE "{_URL_TESTE.database}"'))
    admin.dispose()

    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def banco():
    try:
        _preparar_banco_de_teste()
    except Exception as exc:
        if os.getenv("REQUIRE_DB") == "1":
            raise
        pytest.skip(f"Postgres indisponível para testes ({type(exc).__name__}).")
    yield


@pytest.fixture
def db(banco):
    """Sessão do banco de teste; todas as tabelas são esvaziadas ao fim de cada teste."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.rollback()
        tabelas = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
        if tabelas:
            session.execute(text(f"TRUNCATE {tabelas} RESTART IDENTITY CASCADE"))
            session.commit()
        session.close()
