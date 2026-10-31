"""Acesso às tabelas de identidade. Uso interno do módulo."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.identidade.models import SessaoModel, UsuarioModel


class IdentidadeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def usuario_por_email(self, email: str) -> UsuarioModel | None:
        return self.db.scalar(select(UsuarioModel).where(UsuarioModel.email == email))

    def usuario_por_id(self, usuario_id: UUID) -> UsuarioModel | None:
        return self.db.get(UsuarioModel, usuario_id)

    def adicionar(self, obj: UsuarioModel | SessaoModel) -> None:
        self.db.add(obj)

    def sessao_valida(self, token_hash: str, agora: datetime) -> SessaoModel | None:
        return self.db.scalar(
            select(SessaoModel).where(
                SessaoModel.token_hash == token_hash,
                SessaoModel.encerrada_em.is_(None),
                SessaoModel.expira_em > agora,
            )
        )

    def encerrar_sessao(self, token_hash: str, agora: datetime) -> None:
        self.db.execute(
            update(SessaoModel)
            .where(SessaoModel.token_hash == token_hash, SessaoModel.encerrada_em.is_(None))
            .values(encerrada_em=agora)
        )
