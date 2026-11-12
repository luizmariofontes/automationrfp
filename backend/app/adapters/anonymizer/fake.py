"""Anonimizador simples, para testes e para exercitar o contrato antes do sprint 6.

Cobre só duas das quatro etapas do detector real: termos do cadastro do cliente e regex
(e-mail, CNPJ, CPF). Não usa NER, então NÃO serve para dados reais.
"""

import re

from app.shared.anonimizacao import (
    EntradaAnonimizacao,
    LinhaAnonimizada,
    Marcador,
    Ocorrencia,
    OrigemDeteccao,
    ResultadoAnonimizacao,
    TipoMarcador,
)

_REGEX: tuple[tuple[TipoMarcador, re.Pattern[str]], ...] = (
    (TipoMarcador.EMAIL, re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    (TipoMarcador.CNPJ, re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")),
    (TipoMarcador.CPF, re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")),
)

_CLIENTE = Marcador(tipo=TipoMarcador.CLIENTE)


def _palavra_inteira(termo: str) -> str:
    return rf"(?<!\w){re.escape(termo)}(?!\w)"


class _Marcadores:
    """Mantém o mesmo marcador para o mesmo valor dentro de uma requisição."""

    def __init__(self) -> None:
        self.correspondencia: dict[str, str] = {}
        self._por_valor: dict[tuple[TipoMarcador, str], Marcador] = {}
        self._contadores: dict[TipoMarcador, int] = {}

    def cliente(self, valor: str) -> Marcador:
        self.correspondencia.setdefault(str(_CLIENTE), valor)
        return _CLIENTE

    def para(self, tipo: TipoMarcador, valor: str) -> Marcador:
        chave = (tipo, valor.casefold())
        if chave not in self._por_valor:
            self._contadores[tipo] = self._contadores.get(tipo, 0) + 1
            marcador = Marcador(tipo=tipo, indice=self._contadores[tipo])
            self._por_valor[chave] = marcador
            self.correspondencia[str(marcador)] = valor
        return self._por_valor[chave]


class FakeAnonymizer:
    def anonimizar(self, entrada: EntradaAnonimizacao) -> ResultadoAnonimizacao:
        marcadores = _Marcadores()
        # Termos mais longos primeiro, para "Banco Aurora S.A." vencer "Aurora".
        termos = sorted({t for t in entrada.termos_cliente if t.strip()}, key=len, reverse=True)
        padrao_cliente = (
            re.compile("|".join(_palavra_inteira(t) for t in termos), re.IGNORECASE)
            if termos
            else None
        )
        permitidos = [
            re.compile(_palavra_inteira(p), re.IGNORECASE)
            for p in entrada.lista_permissoes
            if p.strip()
        ]

        linhas: list[LinhaAnonimizada] = []
        for linha in entrada.linhas:
            corte = entrada.linha_inicial.get(linha.aba)
            if corte is None or linha.linha < corte:
                continue  # acima da linha de corte: não é extraído
            ocorrencias = self._detectar(linha.texto, padrao_cliente, permitidos, marcadores)
            linhas.append(
                LinhaAnonimizada(
                    aba=linha.aba,
                    linha=linha.linha,
                    texto=_substituir(linha.texto, ocorrencias),
                    ocorrencias=tuple(ocorrencias),
                )
            )
        return ResultadoAnonimizacao(
            linhas=tuple(linhas), correspondencia=marcadores.correspondencia
        )

    @staticmethod
    def _detectar(
        texto: str,
        padrao_cliente: re.Pattern[str] | None,
        permitidos: list[re.Pattern[str]],
        marcadores: _Marcadores,
    ) -> list[Ocorrencia]:
        ocupados = [m.span() for p in permitidos for m in p.finditer(texto)]
        achados: list[Ocorrencia] = []

        def registrar(m: re.Match[str], marcador: Marcador, origem: OrigemDeteccao) -> None:
            achados.append(
                Ocorrencia(inicio=m.start(), fim=m.end(), marcador=marcador, origem=origem)
            )
            ocupados.append(m.span())

        def livre(m: re.Match[str]) -> bool:
            return all(m.end() <= a or m.start() >= b for a, b in ocupados)

        if padrao_cliente:
            for m in padrao_cliente.finditer(texto):
                if livre(m):
                    registrar(m, marcadores.cliente(m.group(0)), OrigemDeteccao.CADASTRO)
        for tipo, padrao in _REGEX:
            for m in padrao.finditer(texto):
                if livre(m):
                    registrar(m, marcadores.para(tipo, m.group(0)), OrigemDeteccao.REGEX)
        return sorted(achados, key=lambda o: o.inicio)


def _substituir(texto: str, ocorrencias: list[Ocorrencia]) -> str:
    partes: list[str] = []
    cursor = 0
    for o in ocorrencias:
        partes.append(texto[cursor : o.inicio])
        partes.append(str(o.marcador))
        cursor = o.fim
    partes.append(texto[cursor:])
    return "".join(partes)
