"""Tabelas do módulo de identidade (prefixo `identidade_`)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


class UsuarioModel(Base):
    __tablename__ = "identidade_usuario"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(200))
    # Nulo para quem entra só por SSO.
    senha_hash: Mapped[str | None] = mapped_column(String(255))
    papeis: Mapped[list[str]] = mapped_column(ARRAY(String(32)), default=list)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    falhas_login: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_ate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ultimo_login_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SessaoModel(Base):
    __tablename__ = "identidade_sessao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("identidade_usuario.id", ondelete="CASCADE"), index=True
    )
    # Guardamos só o hash SHA-256 do token; o token em si fica apenas no cookie.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    metodo: Mapped[str] = mapped_column(String(16))  # "local" ou "oidc"
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    encerrada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
