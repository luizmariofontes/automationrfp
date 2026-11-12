"""Escolha do provedor de LLM a partir da configuração (usada pela raiz de composição)."""

from app.adapters.llm.fake import FakeLLMProvider
from app.shared.config import Settings
from app.shared.llm import LLMGateway, LLMProvider, PoliticaLLM


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "fake":
        return FakeLLMProvider()
    # Os adaptadores reais entram no sprint 7. Cada um implementa `LLMProvider`, declara
    # `externo=True` e usa só chamadas síncronas (sem API de lote, arquivos ou threads).
    raise NotImplementedError(
        f"O adaptador de LLM '{settings.llm_provider}' ainda não foi implementado."
    )


def build_llm_gateway(settings: Settings) -> LLMGateway:
    return LLMGateway(build_llm_provider(settings), PoliticaLLM.from_settings(settings))
