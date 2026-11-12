"""Portas de infraestrutura. As implementações ficam em `app.adapters`.

Os módulos recebem estas interfaces pela raiz de composição e nunca importam um
adaptador concreto (verificado pelo import-linter).
"""

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class ArquivoNaoEncontradoError(KeyError):
    pass


class FileStorage(Protocol):
    """Armazenamento de arquivos (MinIO). A cifragem por arquivo entra no sprint 3."""

    def salvar(self, bucket: str, chave: str, conteudo: bytes) -> None: ...

    def ler(self, bucket: str, chave: str) -> bytes: ...

    def remover(self, bucket: str, chave: str) -> None: ...

    def existe(self, bucket: str, chave: str) -> bool: ...


class Notificacao(BaseModel):
    model_config = ConfigDict(frozen=True)

    destinatario: str  # e-mail do usuário interno
    titulo: str
    texto: str
    link: str | None = None
    # Liga a mensagem a uma conversa, para a resposta por e-mail voltar ao chat certo.
    referencia: str | None = None


class Notifier(Protocol):
    """Canal de saída: e-mail ou Teams."""

    @property
    def canal(self) -> str: ...

    def notificar(self, notificacao: Notificacao) -> None: ...


class MensagemRecebida(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    remetente: str
    assunto: str
    corpo: str
    recebida_em: datetime
    referencia: str | None = None


class InboundMail(Protocol):
    """Caixa de e-mail do chat: respostas enviadas por e-mail voltam para a conversa."""

    def buscar_novas(self) -> list[MensagemRecebida]: ...

    def marcar_lida(self, mensagem_id: str) -> None: ...


class Chamado(BaseModel):
    model_config = ConfigDict(frozen=True)

    numero: str
    titulo: str
    aberto_em: datetime
    prazo: datetime | None = None


class TicketConnector(Protocol):
    """Sistema de chamados de onde as requisições chegam."""

    def buscar(self, numero: str) -> Chamado | None: ...


class EmbeddingProvider(Protocol):
    @property
    def dimensoes(self) -> int: ...

    def embed(self, textos: list[str]) -> list[list[float]]: ...
