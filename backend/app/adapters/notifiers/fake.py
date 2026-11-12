"""Notificador falso: guarda o que seria enviado, sem rede."""

from app.shared.portas import Notificacao


class FakeNotifier:
    def __init__(self, canal: str = "email") -> None:
        self._canal = canal
        self.enviadas: list[Notificacao] = []

    @property
    def canal(self) -> str:
        return self._canal

    def notificar(self, notificacao: Notificacao) -> None:
        self.enviadas.append(notificacao)
