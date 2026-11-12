"""Tabelas do módulo de cadastros (prefixo `cadastros_`)."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


class ClienteModel(Base):
    """Identificadores do cliente. É a primeira fonte do detector de anonimização."""

    __tablename__ = "cadastros_cliente"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sigla: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(200))
    outros_nomes: Mapped[list[str]] = mapped_column(ARRAY(String(200)), default=list)
    # 14 caracteres, sem pontuação (aceita o CNPJ alfanumérico).
    cnpj: Mapped[str | None] = mapped_column(String(14), unique=True)
    dominios: Mapped[list[str]] = mapped_column(ARRAY(String(253)), default=list)
    # Termos marcados à mão na prévia de anonimização (sprint 6) também entram aqui.
    apelidos: Mapped[list[str]] = mapped_column(ARRAY(String(200)), default=list)
    # "on_premise" ou "hosting"; sugerido na abertura da requisição.
    modelo_implantacao_padrao: Mapped[str | None] = mapped_column(String(16))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EquipeModel(Base):
    __tablename__ = "cadastros_equipe"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(120), unique=True)
    # Assuntos que a equipe responde. Dado interno: o agente lê para rotear perguntas.
    escopo: Mapped[str] = mapped_column(Text, default="")
    email: Mapped[str | None] = mapped_column(String(254))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MembroModel(Base):
    __tablename__ = "cadastros_membro"
    __table_args__ = (UniqueConstraint("equipe_id", "usuario_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    equipe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cadastros_equipe.id", ondelete="CASCADE"), index=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("identidade_usuario.id", ondelete="CASCADE"), index=True
    )
    # Responsável recebe os escalonamentos da equipe.
    responsavel: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RegraEscalonamentoModel(Base):
    __tablename__ = "cadastros_regra_escalonamento"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Nulo: regra padrão, vale para as equipes que não têm regra própria.
    equipe_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cadastros_equipe.id", ondelete="CASCADE"), index=True
    )
    nome: Mapped[str] = mapped_column(String(120))
    # Dias úteis em relação ao prazo interno: negativo é antes, zero é no dia, positivo é depois.
    dias_do_prazo: Mapped[int] = mapped_column(Integer)
    destinatario: Mapped[str] = mapped_column(String(32))
    canais: Mapped[list[str]] = mapped_column(ARRAY(String(16)), default=list)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
