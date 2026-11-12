"""Porta do LLM e política de envio de dados ao provedor.

Todo acesso a um modelo passa por `LLMGateway`. Ele aplica a política vigente antes de
cada chamada e registra o que foi enviado (classes de dado e tamanhos, nunca o texto).
Assim a decisão "o que pode sair para qual provedor" fica em configuração:

- `LLM_ENABLED=false` desliga qualquer chamada (chave geral).
- `LLM_PROVIDER` troca o provedor sem mexer no agente.
- `LLM_RETENCAO` declara o que o contrato com o provedor garante (`padrao` ou `zero`).
  É uma declaração: o código não tem como conferir isso junto ao provedor.
- `LLM_EXIGE_RETENCAO_ZERO=true` recusa provedor externo sem retenção zero.
- `LLM_ENVIA_TRECHOS_BASE=false` e `LLM_ENVIA_MEMORIA=false` retêm essas classes de
  dado quando o provedor é externo.

O registro `llm_chamada` no log é a trilha para avaliar a decisão depois.
"""

from dataclasses import dataclass
from enum import StrEnum
from http import HTTPStatus
from typing import Literal, Protocol, TypeVar

import structlog
from pydantic import BaseModel, ConfigDict

from app.shared.config import Settings
from app.shared.errors import AppError

log = structlog.get_logger("llm")

T = TypeVar("T", bound=BaseModel)


class ClasseDado(StrEnum):
    """De onde vem cada parte do prompt. A política decide por classe, não por texto."""

    INSTRUCAO = "instrucao"  # prompt versionado do agente
    PERGUNTA = "pergunta"  # pergunta já anonimizada
    MEMORIA = "memoria"  # exemplos da memória do agente, já anonimizados
    TRECHO_BASE = "trecho_base"  # trechos da base interna de documentos (RAG)


# Classes que a política pode reter. Instrução e pergunta são o mínimo de uma chamada:
# para não enviá-las, desligue o LLM (`LLM_ENABLED=false`).
CLASSES_RETIVEIS = frozenset({ClasseDado.MEMORIA, ClasseDado.TRECHO_BASE})


class Segmento(BaseModel):
    model_config = ConfigDict(frozen=True)

    classe: ClasseDado
    texto: str


class LLMRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    prompt_versao: str
    segmentos: tuple[Segmento, ...]


@dataclass(frozen=True)
class ProvedorInfo:
    nome: str
    modelo: str
    externo: bool  # True quando o texto sai da infraestrutura da empresa


class LLMProvider(Protocol):
    """Porta implementada pelos adaptadores em `app.adapters.llm`."""

    @property
    def info(self) -> ProvedorInfo: ...

    def generate(self, request: LLMRequest, schema: type[T]) -> T: ...


class LLMBloqueadoError(AppError):
    """A política vigente não permite a chamada."""

    status_code = HTTPStatus.SERVICE_UNAVAILABLE
    code = "llm_bloqueado"


class PoliticaLLM(BaseModel):
    model_config = ConfigDict(frozen=True)

    habilitado: bool = True
    retencao: Literal["padrao", "zero"] = "padrao"
    exige_retencao_zero: bool = False
    classes_retidas: frozenset[ClasseDado] = frozenset()

    @classmethod
    def from_settings(cls, settings: Settings) -> "PoliticaLLM":
        retidas: set[ClasseDado] = set()
        if not settings.llm_envia_trechos_base:
            retidas.add(ClasseDado.TRECHO_BASE)
        if not settings.llm_envia_memoria:
            retidas.add(ClasseDado.MEMORIA)
        return cls(
            habilitado=settings.llm_enabled,
            retencao=settings.llm_retencao,
            exige_retencao_zero=settings.llm_exige_retencao_zero,
            classes_retidas=frozenset(retidas),
        )

    def aplicar(self, request: LLMRequest, provedor: ProvedorInfo) -> LLMRequest:
        """Devolve o pedido que pode ser enviado a este provedor, ou recusa a chamada."""
        if not self.habilitado:
            raise LLMBloqueadoError("O uso do LLM está desligado (LLM_ENABLED=false).")
        if not provedor.externo:
            return request
        if self.exige_retencao_zero and self.retencao != "zero":
            raise LLMBloqueadoError(
                "A política exige retenção zero e o provedor externo não a tem declarada."
            )
        retidas = self.classes_retidas & CLASSES_RETIVEIS
        if not retidas:
            return request
        permitidos = tuple(s for s in request.segmentos if s.classe not in retidas)
        return request.model_copy(update={"segmentos": permitidos})


def _tamanhos(request: LLMRequest) -> dict[str, int]:
    total: dict[str, int] = {}
    for s in request.segmentos:
        total[s.classe.value] = total.get(s.classe.value, 0) + len(s.texto)
    return total


class LLMGateway:
    """Único ponto de chamada ao modelo. Os módulos recebem o gateway, nunca o adaptador."""

    def __init__(self, provider: LLMProvider, politica: PoliticaLLM) -> None:
        self._provider = provider
        self._politica = politica

    @property
    def politica(self) -> PoliticaLLM:
        return self._politica

    @property
    def provedor(self) -> ProvedorInfo:
        return self._provider.info

    def generate(self, request: LLMRequest, schema: type[T]) -> T:
        info = self._provider.info
        try:
            permitido = self._politica.aplicar(request, info)
        except LLMBloqueadoError:
            log.warning("llm_bloqueado", provedor=info.nome, prompt_versao=request.prompt_versao)
            raise
        resultado = self._provider.generate(permitido, schema)
        enviados = _tamanhos(permitido)
        # Só classes e contagens de caracteres: o texto nunca vai para o log.
        log.info(
            "llm_chamada",
            provedor=info.nome,
            modelo=info.modelo,
            externo=info.externo,
            retencao=self._politica.retencao if info.externo else "local",
            prompt_versao=request.prompt_versao,
            enviados=enviados,
            retidos=sorted(set(_tamanhos(request)) - set(enviados)),
        )
        return resultado
