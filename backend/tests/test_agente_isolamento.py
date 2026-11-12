"""Isolamento do agente no banco e outbox de eventos.

Prova o "pronto quando" do sprint 2: o papel do agente não lê nenhuma tabela de cliente.
"""

from typing import ClassVar

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import ProgrammingError

from app.modules.cadastros.models import ClienteModel
from app.shared.agente import NOME_SCHEMA_AGENTE
from app.shared.config import get_settings
from app.shared.db import get_agente_sessionmaker, get_engine
from app.shared.eventos import (
    MAX_TENTATIVAS,
    Evento,
    OutboxModel,
    assinar,
    despachar_pendentes,
    limpar_assinantes,
    publicar,
)

PAPEL = get_settings().agente_db_role

# ---------------------------------------------------------------- papel do agente


def test_sessao_do_agente_usa_o_papel_restrito(banco):
    with get_agente_sessionmaker()() as agente:
        assert agente.scalar(text("SELECT current_user")) == PAPEL
        agente.rollback()
        # O papel continua valendo depois do rollback.
        assert agente.scalar(text("SELECT current_user")) == PAPEL


def test_papel_do_agente_nao_tem_permissao_em_nenhuma_tabela_fora_do_schema_agente(banco):
    consulta = text(
        """
        SELECT schemaname || '.' || tablename
        FROM pg_tables
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema', :schema)
          AND (
            has_table_privilege(:papel, format('%I.%I', schemaname, tablename), 'SELECT')
            OR has_table_privilege(:papel, format('%I.%I', schemaname, tablename), 'INSERT')
            OR has_table_privilege(:papel, format('%I.%I', schemaname, tablename), 'UPDATE')
            OR has_table_privilege(:papel, format('%I.%I', schemaname, tablename), 'DELETE')
          )
        """
    )
    with get_engine().connect() as conn:
        tabelas = conn.scalars(consulta, {"papel": PAPEL, "schema": NOME_SCHEMA_AGENTE}).all()
        total = conn.scalar(text("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'"))
    assert total and total >= 7  # garante que a consulta olhou as tabelas de verdade
    assert tabelas == []


@pytest.mark.parametrize(
    "tabela",
    [
        "cadastros_cliente",
        "cadastros_equipe",
        "cadastros_membro",
        "identidade_usuario",
        "identidade_sessao",
        "auditoria_registro",
        "shared_outbox",
    ],
)
def test_agente_nao_le_tabelas_de_clientes(db, tabela):
    db.add(ClienteModel(sigla="AUR", nome="Banco Aurora", ativo=True))
    db.commit()
    with (
        get_agente_sessionmaker()() as agente,
        pytest.raises(ProgrammingError, match=r"permission denied|permissão negada"),
    ):
        agente.execute(text(f"SELECT * FROM {tabela} LIMIT 1"))  # noqa: S608


def test_agente_le_mas_nao_escreve_no_schema_agente(banco):
    with get_engine().begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS agente._teste_isolamento"))
        conn.execute(text("CREATE TABLE agente._teste_isolamento (texto text)"))
        conn.execute(text("INSERT INTO agente._teste_isolamento VALUES ('O {{CLIENTE}} usa SSO?')"))
    try:
        with get_agente_sessionmaker()() as agente:
            lido = agente.scalar(text("SELECT texto FROM agente._teste_isolamento"))
            assert lido == "O {{CLIENTE}} usa SSO?"
            # Só o módulo privacidade escreve na memória, com o papel da aplicação.
            with pytest.raises(ProgrammingError):
                agente.execute(text("INSERT INTO agente._teste_isolamento VALUES ('x')"))
            agente.rollback()
            with pytest.raises(ProgrammingError):
                agente.execute(text("CREATE TABLE agente._outra (x int)"))
    finally:
        with get_engine().begin() as conn:
            conn.execute(text("DROP TABLE agente._teste_isolamento"))


# ---------------------------------------------------------------- outbox


class ClienteAlterado(Evento):
    tipo: ClassVar[str] = "teste.cliente_alterado"

    cliente_id: str


@pytest.fixture
def assinantes():
    limpar_assinantes()
    yield
    limpar_assinantes()


def test_evento_so_existe_se_a_transacao_for_confirmada(db, assinantes):
    publicar(db, ClienteAlterado(cliente_id="1"))
    db.rollback()
    assert db.scalar(select(OutboxModel)) is None


def test_outbox_entrega_uma_vez(db, assinantes):
    recebidos: list[dict] = []
    assinar(ClienteAlterado.tipo, lambda _db, payload: recebidos.append(payload))
    publicar(db, ClienteAlterado(cliente_id="1"))
    publicar(db, ClienteAlterado(cliente_id="2"))
    db.commit()

    assert despachar_pendentes(db) == 2
    assert despachar_pendentes(db) == 0
    assert sorted(p["cliente_id"] for p in recebidos) == ["1", "2"]


def test_outbox_tenta_de_novo_quando_o_assinante_falha(db, assinantes):
    chamadas = 0

    def instavel(_db, _payload):
        nonlocal chamadas
        chamadas += 1
        if chamadas == 1:
            raise RuntimeError("falha temporária")

    assinar(ClienteAlterado.tipo, instavel)
    publicar(db, ClienteAlterado(cliente_id="1"))
    db.commit()

    assert despachar_pendentes(db) == 0
    item = db.scalar(select(OutboxModel))
    assert item.tentativas == 1
    assert item.entregue_em is None
    assert despachar_pendentes(db) == 1

    # Depois do limite de tentativas, o evento para de ser tentado.
    publicar(db, ClienteAlterado(cliente_id="2"))
    db.commit()
    preso = db.scalar(select(OutboxModel).where(OutboxModel.entregue_em.is_(None)))
    preso.tentativas = MAX_TENTATIVAS
    db.commit()
    assert despachar_pendentes(db) == 0


def test_evento_recusa_campos_fora_do_contrato():
    with pytest.raises(ValueError, match="cliente_nome"):
        ClienteAlterado.model_validate({"cliente_id": "1", "cliente_nome": "Banco Aurora"})
