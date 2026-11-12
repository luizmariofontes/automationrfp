"""Armazenamento em memória, para testes e desenvolvimento sem MinIO."""

from app.shared.portas import ArquivoNaoEncontradoError


class FakeFileStorage:
    def __init__(self) -> None:
        self.arquivos: dict[tuple[str, str], bytes] = {}

    def salvar(self, bucket: str, chave: str, conteudo: bytes) -> None:
        self.arquivos[(bucket, chave)] = conteudo

    def ler(self, bucket: str, chave: str) -> bytes:
        try:
            return self.arquivos[(bucket, chave)]
        except KeyError:
            raise ArquivoNaoEncontradoError(chave) from None

    def remover(self, bucket: str, chave: str) -> None:
        self.arquivos.pop((bucket, chave), None)

    def existe(self, bucket: str, chave: str) -> bool:
        return (bucket, chave) in self.arquivos
