"""Embeddings falsos: vetor determinístico derivado do hash do texto, sem modelo."""

import hashlib
import math


class FakeEmbeddingProvider:
    def __init__(self, dimensoes: int = 16) -> None:
        self._dimensoes = dimensoes

    @property
    def dimensoes(self) -> int:
        return self._dimensoes

    def embed(self, textos: list[str]) -> list[list[float]]:
        return [self._vetor(t) for t in textos]

    def _vetor(self, texto: str) -> list[float]:
        bruto: list[float] = []
        bloco = 0
        while len(bruto) < self._dimensoes:
            digest = hashlib.sha256(f"{bloco}:{texto}".encode()).digest()
            bruto.extend(b / 255 - 0.5 for b in digest)
            bloco += 1
        bruto = bruto[: self._dimensoes]
        norma = math.sqrt(sum(x * x for x in bruto)) or 1.0
        return [x / norma for x in bruto]
