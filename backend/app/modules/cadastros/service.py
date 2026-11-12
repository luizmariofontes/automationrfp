"""Serviço público do módulo cadastros.

Clientes (sigla, nomes, CNPJ, domínios e apelidos), equipes com escopo, membros e
regras de escalonamento. Toda alteração é gravada junto com um registro de auditoria.

Outros módulos usam daqui:
- `obter_cliente` e `termos_do_cliente`: identificadores para a anonimização (sprint 6);
- `listar_equipes` e `regras_da_equipe`: roteamento e cobrança.

O módulo `motor_respostas` não pode importar este pacote (import-linter): o agente não
conhece clientes.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auditoria import service as auditoria
from app.modules.cadastros.domain import (
    ClienteAtualizacao,
    ClienteEntrada,
    ClienteSaida,
    EquipeAtualizacao,
    EquipeEntrada,
    EquipeSaida,
    MembroSaida,
    RegraAtualizacao,
    RegraEntrada,
    RegraSaida,
    formatar_cnpj,
)
from app.modules.cadastros.models import (
    ClienteModel,
    EquipeModel,
    MembroModel,
    RegraEscalonamentoModel,
)
from app.modules.identidade import service as identidade
from app.modules.identidade.service import UsuarioAutenticado
from app.shared.errors import ConflictError, NotFoundError
from app.shared.logging import get_logger

__all__ = [
    "atualizar_cliente",
    "atualizar_equipe",
    "atualizar_regra",
    "criar_cliente",
    "criar_equipe",
    "criar_regra",
    "definir_membro",
    "listar_clientes",
    "listar_equipes",
    "listar_regras",
    "obter_cliente",
    "obter_equipe",
    "regras_da_equipe",
    "remover_membro",
    "remover_regra",
    "termos_do_cliente",
]

log = get_logger(__name__)

# Campos que aceitam nulo. Nos demais, um `null` enviado no PATCH é ignorado.
_NULAVEIS = {"cnpj", "modelo_implantacao_padrao", "email"}


def _aplicar(modelo: Any, dados: dict[str, Any]) -> list[str]:
    """Copia para o modelo os campos que mudaram. Devolve os nomes dos campos alterados."""
    alterados: list[str] = []
    for campo, valor in dados.items():
        if valor is None and campo not in _NULAVEIS:
            continue
        if getattr(modelo, campo) != valor:
            setattr(modelo, campo, valor)
            alterados.append(campo)
    return alterados


# ---------------------------------------------------------------- clientes


def _cliente(db: Session, cliente_id: UUID) -> ClienteModel:
    cliente = db.get(ClienteModel, cliente_id)
    if cliente is None:
        raise NotFoundError("Cliente não encontrado.")
    return cliente


def _conferir_cliente_unico(
    db: Session, *, sigla: str | None, cnpj: str | None, ignorar: UUID | None = None
) -> None:
    def existe(coluna: Any, valor: str) -> bool:
        consulta = select(ClienteModel.id).where(coluna == valor)
        if ignorar:
            consulta = consulta.where(ClienteModel.id != ignorar)
        return db.scalar(consulta) is not None

    if sigla and existe(ClienteModel.sigla, sigla):
        raise ConflictError("Já existe um cliente com esta sigla.")
    if cnpj and existe(ClienteModel.cnpj, cnpj):
        raise ConflictError("Já existe um cliente com este CNPJ.")


def listar_clientes(db: Session, *, apenas_ativos: bool = False) -> list[ClienteSaida]:
    consulta = select(ClienteModel).order_by(ClienteModel.sigla)
    if apenas_ativos:
        consulta = consulta.where(ClienteModel.ativo.is_(True))
    return [ClienteSaida.model_validate(c) for c in db.scalars(consulta)]


def obter_cliente(db: Session, cliente_id: UUID) -> ClienteSaida:
    return ClienteSaida.model_validate(_cliente(db, cliente_id))


def criar_cliente(db: Session, ator: UsuarioAutenticado, entrada: ClienteEntrada) -> ClienteSaida:
    _conferir_cliente_unico(db, sigla=entrada.sigla, cnpj=entrada.cnpj)
    dados = entrada.model_dump(mode="json")
    cliente = ClienteModel(**dados, ativo=True)
    db.add(cliente)
    db.flush()
    auditoria.registrar(
        db,
        ator=ator,
        acao="cliente.criado",
        entidade="cliente",
        entidade_id=cliente.id,
        campos=dados.keys(),
    )
    db.commit()
    log.info("cliente_criado", cliente_id=str(cliente.id))
    return ClienteSaida.model_validate(cliente)


def atualizar_cliente(
    db: Session, ator: UsuarioAutenticado, cliente_id: UUID, entrada: ClienteAtualizacao
) -> ClienteSaida:
    cliente = _cliente(db, cliente_id)
    dados = entrada.model_dump(mode="json", exclude_unset=True)
    _conferir_cliente_unico(
        db, sigla=dados.get("sigla"), cnpj=dados.get("cnpj"), ignorar=cliente.id
    )
    alterados = _aplicar(cliente, dados)
    if alterados:
        auditoria.registrar(
            db,
            ator=ator,
            acao="cliente.alterado",
            entidade="cliente",
            entidade_id=cliente.id,
            campos=alterados,
        )
        db.commit()
        db.refresh(cliente)
        log.info("cliente_alterado", cliente_id=str(cliente.id), campos=alterados)
    return ClienteSaida.model_validate(cliente)


def termos_do_cliente(db: Session, cliente_id: UUID) -> tuple[str, ...]:
    """Tudo que identifica o cliente num texto. Entrada do detector de anonimização."""
    c = _cliente(db, cliente_id)
    termos = [c.sigla, c.nome, *c.outros_nomes, *c.apelidos, *c.dominios]
    if c.cnpj:
        termos += [c.cnpj, formatar_cnpj(c.cnpj)]
    return tuple(dict.fromkeys(termos))


# ---------------------------------------------------------------- equipes


def _equipe(db: Session, equipe_id: UUID) -> EquipeModel:
    equipe = db.get(EquipeModel, equipe_id)
    if equipe is None:
        raise NotFoundError("Equipe não encontrada.")
    return equipe


def _conferir_equipe_unica(db: Session, nome: str | None, ignorar: UUID | None = None) -> None:
    if not nome:
        return
    consulta = select(EquipeModel.id).where(EquipeModel.nome == nome)
    if ignorar:
        consulta = consulta.where(EquipeModel.id != ignorar)
    if db.scalar(consulta) is not None:
        raise ConflictError("Já existe uma equipe com este nome.")


def _saida_equipes(db: Session, equipes: list[EquipeModel]) -> list[EquipeSaida]:
    membros = list(
        db.scalars(select(MembroModel).where(MembroModel.equipe_id.in_([e.id for e in equipes])))
    )
    usuarios = identidade.usuarios_por_ids(db, (m.usuario_id for m in membros))
    por_equipe: dict[UUID, list[MembroSaida]] = {e.id: [] for e in equipes}
    for m in membros:
        usuario = usuarios.get(m.usuario_id)
        if usuario:
            por_equipe[m.equipe_id].append(
                MembroSaida(
                    usuario_id=usuario.id,
                    nome=usuario.nome,
                    email=usuario.email,
                    responsavel=m.responsavel,
                )
            )
    return [
        EquipeSaida(
            id=e.id,
            nome=e.nome,
            escopo=e.escopo,
            email=e.email,
            ativo=e.ativo,
            # Responsáveis primeiro, depois por nome.
            membros=sorted(por_equipe[e.id], key=lambda m: (not m.responsavel, m.nome.casefold())),
        )
        for e in equipes
    ]


def listar_equipes(db: Session, *, apenas_ativas: bool = False) -> list[EquipeSaida]:
    consulta = select(EquipeModel).order_by(EquipeModel.nome)
    if apenas_ativas:
        consulta = consulta.where(EquipeModel.ativo.is_(True))
    return _saida_equipes(db, list(db.scalars(consulta)))


def obter_equipe(db: Session, equipe_id: UUID) -> EquipeSaida:
    return _saida_equipes(db, [_equipe(db, equipe_id)])[0]


def criar_equipe(db: Session, ator: UsuarioAutenticado, entrada: EquipeEntrada) -> EquipeSaida:
    _conferir_equipe_unica(db, entrada.nome)
    dados = entrada.model_dump(mode="json")
    equipe = EquipeModel(**dados, ativo=True)
    db.add(equipe)
    db.flush()
    auditoria.registrar(
        db,
        ator=ator,
        acao="equipe.criada",
        entidade="equipe",
        entidade_id=equipe.id,
        campos=dados.keys(),
    )
    db.commit()
    log.info("equipe_criada", equipe_id=str(equipe.id))
    return _saida_equipes(db, [equipe])[0]


def atualizar_equipe(
    db: Session, ator: UsuarioAutenticado, equipe_id: UUID, entrada: EquipeAtualizacao
) -> EquipeSaida:
    equipe = _equipe(db, equipe_id)
    dados = entrada.model_dump(mode="json", exclude_unset=True)
    _conferir_equipe_unica(db, dados.get("nome"), ignorar=equipe.id)
    alterados = _aplicar(equipe, dados)
    if alterados:
        auditoria.registrar(
            db,
            ator=ator,
            acao="equipe.alterada",
            entidade="equipe",
            entidade_id=equipe.id,
            campos=alterados,
        )
        db.commit()
        log.info("equipe_alterada", equipe_id=str(equipe.id), campos=alterados)
    return _saida_equipes(db, [equipe])[0]


def definir_membro(
    db: Session, ator: UsuarioAutenticado, equipe_id: UUID, usuario_id: UUID, *, responsavel: bool
) -> EquipeSaida:
    """Inclui o usuário na equipe ou muda se ele é responsável."""
    equipe = _equipe(db, equipe_id)
    if usuario_id not in identidade.usuarios_por_ids(db, [usuario_id]):
        raise NotFoundError("Usuário não encontrado.")
    membro = db.scalar(
        select(MembroModel).where(
            MembroModel.equipe_id == equipe.id, MembroModel.usuario_id == usuario_id
        )
    )
    if membro is None:
        db.add(MembroModel(equipe_id=equipe.id, usuario_id=usuario_id, responsavel=responsavel))
        acao = "membro.incluido"
    elif membro.responsavel != responsavel:
        membro.responsavel = responsavel
        acao = "membro.alterado"
    else:
        return _saida_equipes(db, [equipe])[0]
    auditoria.registrar(
        db,
        ator=ator,
        acao=acao,
        entidade="equipe",
        entidade_id=equipe.id,
        campos=["membros"],
    )
    db.commit()
    log.info("membro_definido", equipe_id=str(equipe.id), usuario_id=str(usuario_id), acao=acao)
    return _saida_equipes(db, [equipe])[0]


def remover_membro(
    db: Session, ator: UsuarioAutenticado, equipe_id: UUID, usuario_id: UUID
) -> None:
    equipe = _equipe(db, equipe_id)
    membro = db.scalar(
        select(MembroModel).where(
            MembroModel.equipe_id == equipe.id, MembroModel.usuario_id == usuario_id
        )
    )
    if membro is None:
        raise NotFoundError("Este usuário não é membro da equipe.")
    db.delete(membro)
    auditoria.registrar(
        db,
        ator=ator,
        acao="membro.removido",
        entidade="equipe",
        entidade_id=equipe.id,
        campos=["membros"],
    )
    db.commit()
    log.info("membro_removido", equipe_id=str(equipe.id), usuario_id=str(usuario_id))


# ---------------------------------------------------------------- escalonamento


def _regra(db: Session, regra_id: UUID) -> RegraEscalonamentoModel:
    regra = db.get(RegraEscalonamentoModel, regra_id)
    if regra is None:
        raise NotFoundError("Regra de escalonamento não encontrada.")
    return regra


def listar_regras(db: Session) -> list[RegraSaida]:
    consulta = select(RegraEscalonamentoModel).order_by(
        RegraEscalonamentoModel.equipe_id.nulls_first(), RegraEscalonamentoModel.dias_do_prazo
    )
    return [RegraSaida.model_validate(r) for r in db.scalars(consulta)]


def regras_da_equipe(db: Session, equipe_id: UUID) -> list[RegraSaida]:
    """Regras ativas da equipe; se ela não tiver nenhuma, valem as regras padrão."""

    def ativas(filtro: Any) -> list[RegraSaida]:
        consulta = (
            select(RegraEscalonamentoModel)
            .where(filtro, RegraEscalonamentoModel.ativo.is_(True))
            .order_by(RegraEscalonamentoModel.dias_do_prazo)
        )
        return [RegraSaida.model_validate(r) for r in db.scalars(consulta)]

    return ativas(RegraEscalonamentoModel.equipe_id == equipe_id) or ativas(
        RegraEscalonamentoModel.equipe_id.is_(None)
    )


def criar_regra(db: Session, ator: UsuarioAutenticado, entrada: RegraEntrada) -> RegraSaida:
    if entrada.equipe_id is not None:
        _equipe(db, entrada.equipe_id)
    dados = entrada.model_dump(mode="json") | {"equipe_id": entrada.equipe_id}
    regra = RegraEscalonamentoModel(**dados, ativo=True)
    db.add(regra)
    db.flush()
    auditoria.registrar(
        db,
        ator=ator,
        acao="regra_escalonamento.criada",
        entidade="regra_escalonamento",
        entidade_id=regra.id,
        campos=dados.keys(),
    )
    db.commit()
    log.info("regra_criada", regra_id=str(regra.id))
    return RegraSaida.model_validate(regra)


def atualizar_regra(
    db: Session, ator: UsuarioAutenticado, regra_id: UUID, entrada: RegraAtualizacao
) -> RegraSaida:
    regra = _regra(db, regra_id)
    alterados = _aplicar(regra, entrada.model_dump(mode="json", exclude_unset=True))
    if alterados:
        auditoria.registrar(
            db,
            ator=ator,
            acao="regra_escalonamento.alterada",
            entidade="regra_escalonamento",
            entidade_id=regra.id,
            campos=alterados,
        )
        db.commit()
        log.info("regra_alterada", regra_id=str(regra.id), campos=alterados)
    return RegraSaida.model_validate(regra)


def remover_regra(db: Session, ator: UsuarioAutenticado, regra_id: UUID) -> None:
    regra = _regra(db, regra_id)
    db.delete(regra)
    auditoria.registrar(
        db,
        ator=ator,
        acao="regra_escalonamento.removida",
        entidade="regra_escalonamento",
        entidade_id=regra.id,
    )
    db.commit()
    log.info("regra_removida", regra_id=str(regra.id))
