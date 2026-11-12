"""Eventos de domínio e outbox transacional.

Um módulo avisa os outros sem conhecê-los: grava o evento na tabela `shared_outbox`
na mesma transação da mudança (`publicar`) e um worker entrega depois aos assinantes
(`despachar_pendentes`). Se a transação falhar, o evento não existe; se a entrega
falhar, ela é tentada de novo. Por isso os assinantes precisam ser idempotentes.

Regra do projeto: o evento carrega só ids e códigos, nunca texto de clientes.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, ClassVar

import structlog
from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, Integer, String, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.shared.db import Base

log = structlog.get_logger("eventos")

MAX_TENTATIVAS = 10


class Evento(BaseModel):
    """Base dos eventos. Cada subclasse define `tipo` como `modulo.fato_no_passado`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tipo: ClassVar[str]


class OutboxModel(Base):
    __tablename__ = "shared_outbox"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tipo: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    entregue_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    tentativas: Mapped[int] = mapped_column(Integer, default=0)


Assinante = Callable[[Session, dict[str, Any]], None]

_assinantes: dict[str, list[Assinante]] = {}


def assinar(tipo: str, assinante: Assinante) -> None:
    """Registra um assinante. Chamado na raiz de composição, na subida da aplicação."""
    _assinantes.setdefault(tipo, []).append(assinante)


def limpar_assinantes() -> None:
    _assinantes.clear()


def publicar(db: Session, evento: Evento) -> None:
    """Grava o evento na transação atual. Quem chama faz o commit."""
    db.add(OutboxModel(tipo=evento.tipo, payload=evento.model_dump(mode="json"), tentativas=0))


def despachar_pendentes(db: Session, limite: int = 100) -> int:
    """Entrega os eventos pendentes aos assinantes. Devolve quantos foram entregues."""
    pendentes = db.scalars(
        select(OutboxModel)
        .where(OutboxModel.entregue_em.is_(None), OutboxModel.tentativas < MAX_TENTATIVAS)
        .order_by(OutboxModel.criado_em)
        .limit(limite)
        .with_for_update(skip_locked=True)
    ).all()
    entregues = 0
    for item in pendentes:
        try:
            # Savepoint: se um assinante falhar, o que ele fez neste evento é desfeito.
            with db.begin_nested():
                for assinante in _assinantes.get(item.tipo, []):
                    assinante(db, item.payload)
            item.entregue_em = datetime.now(UTC)
            entregues += 1
        except Exception as exc:
            item.tentativas += 1
            log.warning(
                "evento_falhou",
                evento_id=str(item.id),
                tipo=item.tipo,
                tentativas=item.tentativas,
                exc_type=type(exc).__name__,
            )
    db.commit()
    return entregues
