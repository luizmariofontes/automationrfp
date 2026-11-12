"""Caixa de entrada falsa: os testes colocam mensagens em `caixa`."""

from app.shared.portas import MensagemRecebida


class FakeInboundMail:
    def __init__(self, mensagens: list[MensagemRecebida] | None = None) -> None:
        self.caixa: list[MensagemRecebida] = list(mensagens or [])
        self.lidas: set[str] = set()

    def buscar_novas(self) -> list[MensagemRecebida]:
        return [m for m in self.caixa if m.id not in self.lidas]

    def marcar_lida(self, mensagem_id: str) -> None:
        self.lidas.add(mensagem_id)
