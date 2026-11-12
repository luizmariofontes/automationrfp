"""Serviço público do módulo auditoria.

Outros módulos usam `registrar(...)` dentro da própria transação: a ação e o registro
são gravados juntos ou não são gravados. Quem chama faz o commit.

O registro guarda quem, quando, o quê e quais campos mudaram. Não guarda valores,
porque eles podem conter dados de clientes.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.auditoria.models import RegistroModel
from app.modules.identidade.service import UsuarioAutenticado

__all__ = ["Pagina", "Registro", "listar", "registrar"]


@dataclass(frozen=True)
class Registro:
    id: UUID
    ocorrido_em: datetime
    ator_id: UUID | None
    ator_email: str | None
    acao: str
    entidade: str
    entidade_id: str
    campos: tuple[str, ...]
    request_id: str | None


@dataclass(frozen=True)
class Pagina:
    itens: list[Registro]
    total: int


def registrar(
    db: Session,
    *,
    ator: UsuarioAutenticado | None,
    acao: str,
    entidade: str,
    entidade_id: UUID | str,
    campos: Iterable[str] = (),
) -> None:
    """Acrescenta um registro à transação atual. `ator=None` indica ação do sistema."""
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    db.add(
        RegistroModel(
            ator_id=ator.id if ator else None,
            ator_email=ator.email if ator else None,
            acao=acao,
            entidade=entidade,
            entidade_id=str(entidade_id),
            campos=sorted(set(campos)),
            request_id=str(request_id) if request_id else None,
        )
    )


def listar(
    db: Session,
    *,
    entidade: str | None = None,
    entidade_id: str | None = None,
    ator_id: UUID | None = None,
    limite: int = 50,
    offset: int = 0,
) -> Pagina:
    filtros = []
    if entidade:
        filtros.append(RegistroModel.entidade == entidade)
    if entidade_id:
        filtros.append(RegistroModel.entidade_id == entidade_id)
    if ator_id:
        filtros.append(RegistroModel.ator_id == ator_id)

    total = db.scalar(select(func.count()).select_from(RegistroModel).where(*filtros)) or 0
    linhas = db.scalars(
        select(RegistroModel)
        .where(*filtros)
        .order_by(RegistroModel.ocorrido_em.desc(), RegistroModel.id)
        .limit(limite)
        .offset(offset)
    ).all()
    return Pagina(
        itens=[
            Registro(
                id=r.id,
                ocorrido_em=r.ocorrido_em,
                ator_id=r.ator_id,
                ator_email=r.ator_email,
                acao=r.acao,
                entidade=r.entidade,
                entidade_id=r.entidade_id,
                campos=tuple(r.campos),
                request_id=r.request_id,
            )
            for r in linhas
        ],
        total=total,
    )
