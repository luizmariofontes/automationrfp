"""Política de envio de dados ao provedor de LLM (app/shared/llm.py)."""

import pytest
from pydantic import BaseModel, ValidationError
from structlog.testing import capture_logs

from app.adapters.llm.factory import build_llm_gateway, build_llm_provider
from app.adapters.llm.fake import FakeLLMProvider
from app.shared.config import Settings
from app.shared.llm import (
    ClasseDado,
    LLMBloqueadoError,
    LLMGateway,
    LLMRequest,
    PoliticaLLM,
    Segmento,
)

SEGREDO_PERGUNTA = "pergunta-canario-7731"
SEGREDO_TRECHO = "trecho-canario-9942"


class Resposta(BaseModel):
    texto: str = "ok"


def _pedido() -> LLMRequest:
    return LLMRequest(
        prompt_versao="agente-v1",
        segmentos=(
            Segmento(classe=ClasseDado.INSTRUCAO, texto="Responda com base nos trechos."),
            Segmento(classe=ClasseDado.PERGUNTA, texto=SEGREDO_PERGUNTA),
            Segmento(classe=ClasseDado.MEMORIA, texto="exemplo aprovado"),
            Segmento(classe=ClasseDado.TRECHO_BASE, texto=SEGREDO_TRECHO),
        ),
    )


def _settings(**kwargs: object) -> Settings:
    return Settings(_env_file=None, app_env="test", **kwargs)  # type: ignore[arg-type]


def _classes(pedido: LLMRequest) -> set[ClasseDado]:
    return {s.classe for s in pedido.segmentos}


def test_padrao_envia_tudo_ao_provedor_externo():
    provedor = FakeLLMProvider(externo=True)
    gateway = LLMGateway(provedor, PoliticaLLM.from_settings(_settings()))

    assert gateway.generate(_pedido(), Resposta) == Resposta()
    assert _classes(provedor.chamadas[0]) == set(ClasseDado)


def test_chave_geral_bloqueia_qualquer_provedor():
    provedor = FakeLLMProvider()
    gateway = LLMGateway(provedor, PoliticaLLM.from_settings(_settings(llm_enabled=False)))

    with pytest.raises(LLMBloqueadoError):
        gateway.generate(_pedido(), Resposta)
    assert provedor.chamadas == []


def test_trechos_da_base_retidos_para_provedor_externo():
    provedor = FakeLLMProvider(externo=True)
    politica = PoliticaLLM.from_settings(_settings(llm_envia_trechos_base=False))

    LLMGateway(provedor, politica).generate(_pedido(), Resposta)

    enviado = provedor.chamadas[0]
    assert ClasseDado.TRECHO_BASE not in _classes(enviado)
    assert all(SEGREDO_TRECHO not in s.texto for s in enviado.segmentos)
    assert {ClasseDado.INSTRUCAO, ClasseDado.PERGUNTA, ClasseDado.MEMORIA} == _classes(enviado)


def test_memoria_retida_para_provedor_externo():
    provedor = FakeLLMProvider(externo=True)
    politica = PoliticaLLM.from_settings(_settings(llm_envia_memoria=False))

    LLMGateway(provedor, politica).generate(_pedido(), Resposta)

    assert ClasseDado.MEMORIA not in _classes(provedor.chamadas[0])


def test_provedor_interno_recebe_tudo_mesmo_com_restricoes():
    provedor = FakeLLMProvider(externo=False)
    politica = PoliticaLLM(
        exige_retencao_zero=True,
        classes_retidas=frozenset({ClasseDado.TRECHO_BASE, ClasseDado.MEMORIA}),
    )

    LLMGateway(provedor, politica).generate(_pedido(), Resposta)

    assert _classes(provedor.chamadas[0]) == set(ClasseDado)


def test_instrucao_e_pergunta_nunca_sao_retidas():
    provedor = FakeLLMProvider(externo=True)
    politica = PoliticaLLM(classes_retidas=frozenset(ClasseDado))

    LLMGateway(provedor, politica).generate(_pedido(), Resposta)

    assert _classes(provedor.chamadas[0]) == {ClasseDado.INSTRUCAO, ClasseDado.PERGUNTA}


def test_exigencia_de_retencao_zero_bloqueia_provedor_externo():
    provedor = FakeLLMProvider(externo=True)
    gateway = LLMGateway(provedor, PoliticaLLM(exige_retencao_zero=True, retencao="padrao"))

    with pytest.raises(LLMBloqueadoError):
        gateway.generate(_pedido(), Resposta)
    assert provedor.chamadas == []

    liberado = LLMGateway(provedor, PoliticaLLM(exige_retencao_zero=True, retencao="zero"))
    liberado.generate(_pedido(), Resposta)
    assert len(provedor.chamadas) == 1


def test_configuracao_incoerente_falha_na_subida():
    with pytest.raises(ValidationError, match="LLM_RETENCAO=zero"):
        _settings(llm_provider="anthropic", llm_model="m", llm_exige_retencao_zero=True)
    with pytest.raises(ValidationError, match="LLM_MODEL"):
        _settings(llm_provider="anthropic")
    # Com o fake, a exigência não impede o desenvolvimento local.
    assert _settings(llm_exige_retencao_zero=True).llm_provider == "fake"


def test_log_registra_classes_e_tamanhos_sem_texto():
    provedor = FakeLLMProvider(externo=True)
    politica = PoliticaLLM.from_settings(_settings(llm_envia_trechos_base=False))

    with capture_logs() as logs:
        LLMGateway(provedor, politica).generate(_pedido(), Resposta)

    (evento,) = [e for e in logs if e["event"] == "llm_chamada"]
    assert evento["externo"] is True
    assert evento["retencao"] == "padrao"
    assert evento["prompt_versao"] == "agente-v1"
    assert evento["enviados"]["pergunta"] == len(SEGREDO_PERGUNTA)
    assert evento["retidos"] == ["trecho_base"]
    assert SEGREDO_PERGUNTA not in repr(logs)
    assert SEGREDO_TRECHO not in repr(logs)


def test_fabrica_devolve_fake_e_recusa_adaptador_inexistente():
    gateway = build_llm_gateway(_settings())
    assert gateway.provedor.nome == "fake"
    assert gateway.provedor.externo is False
    assert gateway.generate(_pedido(), Resposta) == Resposta()

    with pytest.raises(NotImplementedError):
        build_llm_provider(_settings(llm_provider="openai", llm_model="m"))
