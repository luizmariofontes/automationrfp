"""Acesso ao banco: engine, sessão e base declarativa.

Cada módulo declara os próprios modelos herdando de `Base` e só grava nas próprias tabelas.
Os nomes das tabelas usam o prefixo do módulo (ex.: `cadastros_cliente`).
"""

from collections.abc import Iterator
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, MetaData, create_engine, event, text
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


@lru_cache
def get_agente_engine() -> Engine:
    """Conexões do agente: papel do Postgres que só lê o schema `agente`.

    É a camada de banco do isolamento do agente. Com AGENTE_DATABASE_URL, a conexão já
    entra com um login restrito. Sem ela, usa o login da aplicação e assume o papel a
    cada conexão nova.
    """
    settings = get_settings()
    if settings.agente_database_url:
        return create_engine(settings.agente_database_url, pool_pre_ping=True, future=True)

    engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    papel = settings.agente_db_role  # validado na configuração: só letras, números e _

    @event.listens_for(engine, "connect")
    def _assumir_papel(dbapi_conn: Any, _record: Any) -> None:
        # Fora de transação, para o SET ROLE valer pela conexão inteira e sobreviver
        # ao rollback que o pool faz ao devolver a conexão.
        anterior = dbapi_conn.autocommit
        dbapi_conn.autocommit = True
        try:
            with dbapi_conn.cursor() as cursor:
                cursor.execute(f'SET ROLE "{papel}"')
        finally:
            dbapi_conn.autocommit = anterior

    return engine


@lru_cache
def get_agente_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_agente_engine(), autoflush=False, expire_on_commit=False)


def ping_database(timeout: float) -> None:
    with get_engine().connect() as conn:
        conn.execute(text(f"SET statement_timeout = {int(timeout * 1000)}"))
        conn.execute(text("SELECT 1"))
