"""Conceitos e validações do módulo de cadastros.

As mensagens de validação nunca repetem o valor recebido: ele pode ser dado de cliente.
"""

import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.shared.agente import ModeloImplantacao

_SIGLA = re.compile(r"[A-Z0-9][A-Z0-9_-]{1,11}")
_DOMINIO = re.compile(r"(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}")
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_CNPJ = re.compile(r"[A-Z0-9]{12}\d{2}")
_PESOS = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def _digito(base: str) -> str:
    # Vale para o CNPJ numérico e para o alfanumérico: o valor do caractere é ASCII - 48.
    soma = sum((ord(c) - 48) * p for c, p in zip(base, _PESOS[-len(base) :], strict=True))
    resto = soma % 11
    return "0" if resto < 2 else str(11 - resto)


def normalizar_cnpj(valor: str) -> str:
    """Devolve os 14 caracteres sem pontuação, ou recusa se os dígitos não conferem."""
    limpo = re.sub(r"[.\-/\s]", "", valor).upper()
    if not _CNPJ.fullmatch(limpo) or len(set(limpo)) == 1:
        raise ValueError("CNPJ inválido.")
    dv1 = _digito(limpo[:12])
    if limpo[12:] != dv1 + _digito(limpo[:12] + dv1):
        raise ValueError("CNPJ inválido.")
    return limpo


def formatar_cnpj(cnpj: str) -> str:
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def _sigla(valor: str) -> str:
    valor = valor.strip().upper()
    if not _SIGLA.fullmatch(valor):
        raise ValueError("A sigla deve ter de 2 a 12 letras ou números.")
    return valor


def _texto(valor: str) -> str:
    valor = " ".join(valor.split())
    if not valor:
        raise ValueError("O texto não pode ficar vazio.")
    return valor


def _termos(valores: list[str]) -> list[str]:
    """Remove vazios e repetidos (sem diferenciar maiúsculas), mantendo a ordem."""
    vistos: set[str] = set()
    saida: list[str] = []
    for bruto in valores:
        termo = " ".join(bruto.split())
        if termo and termo.casefold() not in vistos:
            vistos.add(termo.casefold())
            saida.append(termo)
    return saida


def _dominios(valores: list[str]) -> list[str]:
    saida = _termos([v.strip().lower().removeprefix("@") for v in valores])
    if any(not _DOMINIO.fullmatch(d) for d in saida):
        raise ValueError("Domínio inválido. Use o formato empresa.com.br.")
    return saida


def _email(valor: str | None) -> str | None:
    if valor is None or not valor.strip():
        return None
    valor = valor.strip().lower()
    if not _EMAIL.fullmatch(valor):
        raise ValueError("E-mail inválido.")
    return valor


def _cnpj(valor: str | None) -> str | None:
    if valor is None or not valor.strip():
        return None
    return normalizar_cnpj(valor)


Sigla = Annotated[str, Field(max_length=32), AfterValidator(_sigla)]
Nome = Annotated[str, Field(max_length=200), AfterValidator(_texto)]
NomeCurto = Annotated[str, Field(max_length=120), AfterValidator(_texto)]
Termos = Annotated[list[Annotated[str, Field(max_length=200)]], Field(max_length=50)]
ListaTermos = Annotated[Termos, AfterValidator(_termos)]
ListaDominios = Annotated[Termos, AfterValidator(_dominios)]
Cnpj = Annotated[str | None, Field(max_length=32), AfterValidator(_cnpj)]
EmailOpcional = Annotated[str | None, Field(max_length=254), AfterValidator(_email)]


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- clientes


class ClienteEntrada(_Entrada):
    sigla: Sigla
    nome: Nome
    outros_nomes: ListaTermos = []
    cnpj: Cnpj = None
    dominios: ListaDominios = []
    apelidos: ListaTermos = []
    modelo_implantacao_padrao: ModeloImplantacao | None = None


class ClienteAtualizacao(_Entrada):
    """Só os campos enviados são alterados."""

    sigla: Sigla | None = None
    nome: Nome | None = None
    outros_nomes: ListaTermos | None = None
    cnpj: Cnpj = None
    dominios: ListaDominios | None = None
    apelidos: ListaTermos | None = None
    modelo_implantacao_padrao: ModeloImplantacao | None = None
    ativo: bool | None = None


class ClienteSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sigla: str
    nome: str
    outros_nomes: list[str]
    cnpj: str | None
    dominios: list[str]
    apelidos: list[str]
    modelo_implantacao_padrao: ModeloImplantacao | None
    ativo: bool
    atualizado_em: datetime


# ---------------------------------------------------------------- equipes


class EquipeEntrada(_Entrada):
    nome: NomeCurto
    escopo: Annotated[str, Field(max_length=4000)] = ""
    email: EmailOpcional = None


class EquipeAtualizacao(_Entrada):
    nome: NomeCurto | None = None
    escopo: Annotated[str, Field(max_length=4000)] | None = None
    email: EmailOpcional = None
    ativo: bool | None = None


class MembroEntrada(_Entrada):
    responsavel: bool = False


class MembroSaida(BaseModel):
    usuario_id: UUID
    nome: str
    email: str
    responsavel: bool


class EquipeSaida(BaseModel):
    id: UUID
    nome: str
    escopo: str
    email: str | None
    ativo: bool
    membros: list[MembroSaida]


class UsuarioSaida(BaseModel):
    id: UUID
    nome: str
    email: str
    papeis: list[str]


# ---------------------------------------------------------------- escalonamento


class Destinatario(StrEnum):
    VALIDADOR = "validador"  # quem está com a tarefa
    RESPONSAVEL_EQUIPE = "responsavel_equipe"
    ANALISTA = "analista"  # analista dono da requisição
    ADMIN = "admin"


class Canal(StrEnum):
    EMAIL = "email"
    TEAMS = "teams"


def _canais(valores: list[Canal]) -> list[Canal]:
    return sorted(set(valores))


Canais = Annotated[list[Canal], Field(min_length=1, max_length=8), AfterValidator(_canais)]
DiasDoPrazo = Annotated[int, Field(ge=-60, le=60)]


class RegraEntrada(_Entrada):
    equipe_id: UUID | None = None
    nome: NomeCurto
    dias_do_prazo: DiasDoPrazo
    destinatario: Destinatario
    canais: Canais


class RegraAtualizacao(_Entrada):
    nome: NomeCurto | None = None
    dias_do_prazo: DiasDoPrazo | None = None
    destinatario: Destinatario | None = None
    canais: Canais | None = None
    ativo: bool | None = None


class RegraSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    equipe_id: UUID | None
    nome: str
    dias_do_prazo: int
    destinatario: Destinatario
    canais: list[Canal]
    ativo: bool
