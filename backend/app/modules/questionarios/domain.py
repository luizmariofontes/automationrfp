"""Modelo canônico de questionário.

Excel e formulário web são convertidos para este formato. O restante da aplicação não
sabe de onde a pergunta veio: usa `Localizacao` só para devolver a resposta ao lugar certo.

O texto aqui ainda é o original do cliente. Ele só chega ao agente depois de passar
pela linha de corte e pela anonimização (módulo `privacidade`).
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Canal(StrEnum):
    EXCEL = "excel"
    WEB = "web"


class TipoResposta(StrEnum):
    TEXTO = "texto"
    OPCAO = "opcao"  # uma entre as opções válidas (validação de dados do Excel, select)
    MULTIPLA = "multipla"
    NUMERO = "numero"
    DATA = "data"


class Localizacao(BaseModel):
    """Onde a pergunta está e onde a resposta deve ser escrita, no canal de origem."""

    model_config = ConfigDict(frozen=True)

    # Excel: nome da aba. Web: página ou seção do formulário.
    aba: str
    # Excel: número da linha (a partir de 1). Web: ordem do campo na página.
    linha: int = Field(ge=1)
    # Excel: célula (ex.: "D12"). Web: seletor do campo.
    celula_pergunta: str | None = None
    celula_resposta: str


class Pergunta(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    # Numeração do próprio questionário, quando existe (ex.: "3.2.1").
    numero: str | None = None
    secao: str | None = None
    texto: str = Field(min_length=1)
    tipo: TipoResposta = TipoResposta.TEXTO
    opcoes: tuple[str, ...] = ()
    limite_caracteres: int | None = Field(default=None, ge=1)
    obrigatoria: bool = False
    localizacao: Localizacao

    @model_validator(mode="after")
    def _opcoes_coerentes(self) -> "Pergunta":
        if self.tipo in {TipoResposta.OPCAO, TipoResposta.MULTIPLA} and not self.opcoes:
            raise ValueError("Pergunta de opção precisa da lista de opções válidas.")
        return self


class Aba(BaseModel):
    model_config = ConfigDict(frozen=True)

    nome: str
    perguntas: tuple[Pergunta, ...] = ()
    # Sugestão do leitor: primeira linha de pergunta. O analista confirma ou move.
    linha_de_corte_sugerida: int | None = Field(default=None, ge=1)


class Questionario(BaseModel):
    model_config = ConfigDict(frozen=True)

    canal: Canal
    abas: tuple[Aba, ...]

    @property
    def perguntas(self) -> tuple[Pergunta, ...]:
        return tuple(p for aba in self.abas for p in aba.perguntas)

    def a_partir_do_corte(self, linha_inicial: dict[str, int]) -> tuple[Pergunta, ...]:
        """Perguntas que serão extraídas: as da linha de corte para baixo, em cada aba.

        Aba sem linha de corte confirmada não é extraída.
        """
        return tuple(
            p
            for p in self.perguntas
            if p.localizacao.aba in linha_inicial
            and p.localizacao.linha >= linha_inicial[p.localizacao.aba]
        )
