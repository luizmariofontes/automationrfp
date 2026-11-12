"""Rotas HTTP do módulo cadastros: /api/v1/cadastros.

Alterações são só para administradores. A leitura de clientes é liberada também ao
analista (ele escolhe a sigla ao abrir uma requisição) e a de equipes a qualquer usuário.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.modules.cadastros import service
from app.modules.cadastros.domain import (
    ClienteAtualizacao,
    ClienteEntrada,
    ClienteSaida,
    EquipeAtualizacao,
    EquipeEntrada,
    EquipeSaida,
    MembroEntrada,
    RegraAtualizacao,
    RegraEntrada,
    RegraSaida,
    UsuarioSaida,
)
from app.modules.identidade import service as identidade
from app.modules.identidade.service import Papel, UsuarioAutenticado, exigir_papeis, usuario_atual
from app.shared.db import get_session

router = APIRouter(prefix="/api/v1/cadastros", tags=["cadastros"])

DbDep = Annotated[Session, Depends(get_session)]
Admin = Annotated[UsuarioAutenticado, Depends(exigir_papeis(Papel.ADMIN))]
AdminOuAnalista = Annotated[UsuarioAutenticado, Depends(exigir_papeis(Papel.ANALISTA))]
Logado = Annotated[UsuarioAutenticado, Depends(usuario_atual)]

# ---------------------------------------------------------------- clientes


@router.get("/clientes", response_model=list[ClienteSaida])
def listar_clientes(db: DbDep, _: AdminOuAnalista) -> list[ClienteSaida]:
    return service.listar_clientes(db)


@router.post("/clientes", response_model=ClienteSaida, status_code=status.HTTP_201_CREATED)
def criar_cliente(entrada: ClienteEntrada, db: DbDep, ator: Admin) -> ClienteSaida:
    return service.criar_cliente(db, ator, entrada)


@router.get("/clientes/{cliente_id}", response_model=ClienteSaida)
def obter_cliente(cliente_id: UUID, db: DbDep, _: AdminOuAnalista) -> ClienteSaida:
    return service.obter_cliente(db, cliente_id)


@router.patch("/clientes/{cliente_id}", response_model=ClienteSaida)
def atualizar_cliente(
    cliente_id: UUID, entrada: ClienteAtualizacao, db: DbDep, ator: Admin
) -> ClienteSaida:
    return service.atualizar_cliente(db, ator, cliente_id, entrada)


# ---------------------------------------------------------------- equipes


@router.get("/equipes", response_model=list[EquipeSaida])
def listar_equipes(db: DbDep, _: Logado) -> list[EquipeSaida]:
    return service.listar_equipes(db)


@router.post("/equipes", response_model=EquipeSaida, status_code=status.HTTP_201_CREATED)
def criar_equipe(entrada: EquipeEntrada, db: DbDep, ator: Admin) -> EquipeSaida:
    return service.criar_equipe(db, ator, entrada)


@router.patch("/equipes/{equipe_id}", response_model=EquipeSaida)
def atualizar_equipe(
    equipe_id: UUID, entrada: EquipeAtualizacao, db: DbDep, ator: Admin
) -> EquipeSaida:
    return service.atualizar_equipe(db, ator, equipe_id, entrada)


@router.put("/equipes/{equipe_id}/membros/{usuario_id}", response_model=EquipeSaida)
def definir_membro(
    equipe_id: UUID, usuario_id: UUID, entrada: MembroEntrada, db: DbDep, ator: Admin
) -> EquipeSaida:
    return service.definir_membro(db, ator, equipe_id, usuario_id, responsavel=entrada.responsavel)


@router.delete("/equipes/{equipe_id}/membros/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_membro(equipe_id: UUID, usuario_id: UUID, db: DbDep, ator: Admin) -> None:
    service.remover_membro(db, ator, equipe_id, usuario_id)


@router.get("/usuarios", response_model=list[UsuarioSaida])
def listar_usuarios(db: DbDep, _: Admin) -> list[UsuarioSaida]:
    """Usuários ativos, para o administrador escolher os membros das equipes."""
    return [
        UsuarioSaida(id=u.id, nome=u.nome, email=u.email, papeis=sorted(u.papeis))
        for u in identidade.listar_usuarios(db)
    ]


# ---------------------------------------------------------------- escalonamento


@router.get("/regras-escalonamento", response_model=list[RegraSaida])
def listar_regras(db: DbDep, _: Admin) -> list[RegraSaida]:
    return service.listar_regras(db)


@router.post(
    "/regras-escalonamento", response_model=RegraSaida, status_code=status.HTTP_201_CREATED
)
def criar_regra(entrada: RegraEntrada, db: DbDep, ator: Admin) -> RegraSaida:
    return service.criar_regra(db, ator, entrada)


@router.patch("/regras-escalonamento/{regra_id}", response_model=RegraSaida)
def atualizar_regra(
    regra_id: UUID, entrada: RegraAtualizacao, db: DbDep, ator: Admin
) -> RegraSaida:
    return service.atualizar_regra(db, ator, regra_id, entrada)


@router.delete("/regras-escalonamento/{regra_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_regra(regra_id: UUID, db: DbDep, ator: Admin) -> None:
    service.remover_regra(db, ator, regra_id)
