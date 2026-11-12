"""Provedor falso: respostas fixas, sem rede e sem custo. Usado em testes e no dev local."""

from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from app.shared.llm import LLMRequest, ProvedorInfo

T = TypeVar("T", bound=BaseModel)

Responder = Callable[[LLMRequest, type[BaseModel]], BaseModel]


class FakeLLMProvider:
    """Guarda os pedidos recebidos em `chamadas`, para os testes conferirem o que saiu.

    `externo=True` simula um provedor de fora, para exercitar a política sem rede.
    """

    def __init__(self, responder: Responder | None = None, *, externo: bool = False) -> None:
        self._responder = responder
        self._info = ProvedorInfo(nome="fake", modelo="fake", externo=externo)
        self.chamadas: list[LLMRequest] = []

    @property
    def info(self) -> ProvedorInfo:
        return self._info

    def generate(self, request: LLMRequest, schema: type[T]) -> T:
        self.chamadas.append(request)
        if self._responder is None:
            # Sem resposta programada, o schema precisa ter valores padrão.
            return schema()
        return schema.model_validate(self._responder(request, schema).model_dump())
