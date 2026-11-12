"""Porta `Anonymizer`: anonimização do questionário a partir da linha de corte.

O analista escolhe, em cada aba, a linha inicial. Linhas acima dela não são extraídas
nem devolvidas. Nas demais, cada identificador vira um marcador tipado
(`{{CLIENTE}}`, `{{PESSOA_1}}`, `{{EMAIL_2}}`), consistente dentro da requisição:
o mesmo valor recebe sempre o mesmo marcador.

A implementação real (cadastro, regex, Presidio e lista de permissões) entra no sprint 6,
dentro do módulo `privacidade`.
"""

import re
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class TipoMarcador(StrEnum):
    CLIENTE = "CLIENTE"
    PESSOA = "PESSOA"
    ORGANIZACAO = "ORGANIZACAO"
    LOCAL = "LOCAL"
    CNPJ = "CNPJ"
    CPF = "CPF"
    EMAIL = "EMAIL"
    TELEFONE = "TELEFONE"
    URL = "URL"
    OUTRO = "OUTRO"


class OrigemDeteccao(StrEnum):
    CADASTRO = "cadastro"
    REGEX = "regex"
    NER = "ner"
    MANUAL = "manual"


_FORMATO = re.compile(r"\{\{([A-Z]+)(?:_(\d+))?\}\}")


class Marcador(BaseModel):
    """`{{TIPO}}` ou `{{TIPO_N}}`. O cliente da requisição é sempre `{{CLIENTE}}`."""

    model_config = ConfigDict(frozen=True)

    tipo: TipoMarcador
    indice: int | None = Field(default=None, ge=1)

    def __str__(self) -> str:
        sufixo = "" if self.indice is None else f"_{self.indice}"
        return f"{{{{{self.tipo.value}{sufixo}}}}}"

    @classmethod
    def ler(cls, texto: str) -> "Marcador":
        m = _FORMATO.fullmatch(texto)
        if not m:
            raise ValueError("Marcador inválido.")
        return cls(tipo=TipoMarcador(m.group(1)), indice=int(m.group(2)) if m.group(2) else None)

    @staticmethod
    def encontrar(texto: str) -> list["Marcador"]:
        """Marcadores presentes num texto, na ordem em que aparecem."""
        achados: list[Marcador] = []
        for m in _FORMATO.finditer(texto):
            if m.group(1) in TipoMarcador.__members__:
                achados.append(Marcador.ler(m.group(0)))
        return achados


class LinhaOriginal(BaseModel):
    model_config = ConfigDict(frozen=True)

    aba: str
    linha: int = Field(ge=1)  # número da linha na planilha, começando em 1
    texto: str


class EntradaAnonimizacao(BaseModel):
    model_config = ConfigDict(frozen=True)

    linhas: tuple[LinhaOriginal, ...]
    # Linha de corte por aba. Aba sem linha inicial não é extraída.
    linha_inicial: dict[str, int]
    # Identificadores do cadastro do cliente: sigla, nomes, CNPJ, domínios e apelidos.
    termos_cliente: tuple[str, ...] = ()
    # Produtos da empresa e normas que não devem ser mascarados.
    lista_permissoes: tuple[str, ...] = ()


class Ocorrencia(BaseModel):
    """Trecho substituído. `inicio` e `fim` são posições no texto original da linha."""

    model_config = ConfigDict(frozen=True)

    inicio: int = Field(ge=0)
    fim: int = Field(ge=1)
    marcador: Marcador
    origem: OrigemDeteccao


class LinhaAnonimizada(BaseModel):
    model_config = ConfigDict(frozen=True)

    aba: str
    linha: int
    texto: str
    ocorrencias: tuple[Ocorrencia, ...] = ()


class ResultadoAnonimizacao(BaseModel):
    model_config = ConfigDict(frozen=True)

    linhas: tuple[LinhaAnonimizada, ...]
    # Marcador (como texto) para o valor real. Vai para o cofre do módulo `privacidade`,
    # cifrado com a chave da requisição. Nunca vai para log nem para o schema `agente`.
    correspondencia: dict[str, str]


class Anonymizer(Protocol):
    def anonimizar(self, entrada: EntradaAnonimizacao) -> ResultadoAnonimizacao: ...


def restaurar(texto: str, correspondencia: dict[str, str]) -> str:
    """Troca os marcadores pelos valores reais (usado na exportação)."""
    return _FORMATO.sub(lambda m: correspondencia.get(m.group(0), m.group(0)), texto)
