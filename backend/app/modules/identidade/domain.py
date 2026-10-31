"""Conceitos do módulo de identidade."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Papel(StrEnum):
    ADMIN = "admin"
    ANALISTA = "analista"
    VALIDADOR = "validador"
    GESTOR_CONHECIMENTO = "gestor_conhecimento"


@dataclass(frozen=True)
class UsuarioAutenticado:
    """Usuário da requisição atual. É o que os outros módulos recebem."""

    id: UUID
    email: str
    nome: str
    papeis: frozenset[Papel]

    def tem_papel(self, *papeis: Papel) -> bool:
        # Administrador tem acesso a tudo.
        return Papel.ADMIN in self.papeis or any(p in self.papeis for p in papeis)
