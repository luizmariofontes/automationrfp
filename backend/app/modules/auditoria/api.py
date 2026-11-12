"""Rotas HTTP do módulo auditoria: consulta dos registros, só para administradores."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.modules.auditoria import service
from app.modules.identidade.service import Papel, UsuarioAutenticado, exigir_papeis
from app.shared.db import get_session

router = APIRouter(prefix="/api/v1/auditoria", tags=["auditoria"])


class RegistroSaida(BaseModel):
    id: UUID
    ocorrido_em: datetime
    ator_id: UUID | None
    ator_email: str | None
    acao: str
    entidade: str
    entidade_id: str
    campos: list[str]
    request_id: str | None


class PaginaSaida(BaseModel):
    itens: list[RegistroSaida]
    total: int


@router.get("", response_model=PaginaSaida)
def listar(
    db: Annotated[Session, Depends(get_session)],
    _: Annotated[UsuarioAutenticado, Depends(exigir_papeis(Papel.ADMIN))],
    entidade: Annotated[str | None, Query(max_length=64)] = None,
    entidade_id: Annotated[str | None, Query(max_length=64)] = None,
    ator_id: UUID | None = None,
    limite: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginaSaida:
    pagina = service.listar(
        db,
        entidade=entidade,
        entidade_id=entidade_id,
        ator_id=ator_id,
        limite=limite,
        offset=offset,
    )
    return PaginaSaida(
        itens=[RegistroSaida.model_validate(r, from_attributes=True) for r in pagina.itens],
        total=pagina.total,
    )
