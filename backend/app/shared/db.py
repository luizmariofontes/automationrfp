"""Acesso ao banco: engine, sessão e base declarativa.

Cada módulo declara os próprios modelos herdando de `Base` e só grava nas próprias tabelas.
Os nomes das tabelas usam o prefixo do módulo (ex.: `cadastros_cliente`).
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, MetaData, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.shared.config import get_settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True, future=True)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição, com commit explícito no serviço."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def ping_database(timeout: float) -> None:
    with get_engine().connect() as conn:
        conn.execute(text(f"SET statement_timeout = {int(timeout * 1000)}"))
        conn.execute(text("SELECT 1"))
