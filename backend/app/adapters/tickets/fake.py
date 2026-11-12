"""Sistema de chamados falso, com chamados fixos."""

from app.shared.portas import Chamado


class FakeTicketConnector:
    def __init__(self, chamados: list[Chamado] | None = None) -> None:
        self.chamados = {c.numero: c for c in chamados or []}

    def buscar(self, numero: str) -> Chamado | None:
        return self.chamados.get(numero)
