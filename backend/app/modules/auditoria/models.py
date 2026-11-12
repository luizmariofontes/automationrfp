"""Tabelas do módulo de auditoria (prefixo `auditoria_`)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


class RegistroModel(Base):
    """Uma ação feita por alguém. Só é inserido; nunca é alterado nem apagado pela aplicação."""

    __tablename__ = "auditoria_registro"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ocorrido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    # Sem chave estrangeira: o registro continua existindo se o usuário for removido.
    ator_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    ator_email: Mapped[str | None] = mapped_column(String(254))
    acao: Mapped[str] = mapped_column(String(64))  # ex.: "cliente.criado"
    entidade: Mapped[str] = mapped_column(String(64), index=True)  # ex.: "cliente"
    entidade_id: Mapped[str] = mapped_column(String(64), index=True)
    # Nomes dos campos alterados. Os valores não são guardados: podem ser dados de clientes.
    campos: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list)
    request_id: Mapped[str | None] = mapped_column(String(64))
