"""Contrato do agente: o único retrato de uma requisição que `motor_respostas` aceita.

São seis campos, todos já anonimizados pelo módulo `privacidade`. O contrato recusa
campos extras, para que nome, sigla, chamado, prazos ou identidade de quem validou não
cheguem ao agente por descuido (ver "O que o agente vê" no README).
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

NOME_SCHEMA_AGENTE = "agente"


class ModeloImplantacao(StrEnum):
    """Único atributo do cliente que pode mudar uma resposta."""

    ON_PREMISE = "on_premise"
    HOSTING = "hosting"


class VisaoAgente(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    # Pergunta do questionário, a partir da linha de corte, anonimizada e confirmada.
    pergunta: str = Field(min_length=1)
    modelo_implantacao: ModeloImplantacao
    # Resposta gerada pelo próprio agente; usa marcadores como {{CLIENTE}}.
    resposta_agente: str | None = None
    # Correção feita por validador ou analista, anonimizada ao salvar.
    resposta_corrigida: str | None = None
    # Comentários do validador, anonimizados ao salvar.
    comentarios: str | None = None
    # None enquanto o item não foi revisado.
    aprovacao: bool | None = None

    @property
    def revisado(self) -> bool:
        return self.aprovacao is not None
