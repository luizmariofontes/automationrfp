"""Contratos do sprint 2: visão do agente, anonimização, modelo canônico e adaptadores falsos."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.adapters.anonymizer.fake import FakeAnonymizer
from app.adapters.embeddings.fake import FakeEmbeddingProvider
from app.adapters.mail.fake import FakeInboundMail
from app.adapters.notifiers.fake import FakeNotifier
from app.adapters.storage.fake import FakeFileStorage
from app.adapters.tickets.fake import FakeTicketConnector
from app.modules.questionarios.service import (
    Aba,
    Canal,
    Localizacao,
    Pergunta,
    Questionario,
    TipoResposta,
)
from app.shared.agente import ModeloImplantacao, VisaoAgente
from app.shared.anonimizacao import (
    Anonymizer,
    EntradaAnonimizacao,
    LinhaOriginal,
    Marcador,
    OrigemDeteccao,
    TipoMarcador,
    restaurar,
)
from app.shared.portas import (
    ArquivoNaoEncontradoError,
    Chamado,
    EmbeddingProvider,
    FileStorage,
    InboundMail,
    MensagemRecebida,
    Notificacao,
    Notifier,
    TicketConnector,
)

# Cliente fictício. Estes valores não podem aparecer em nada que vá para o agente.
CANARIOS = ("Banco Aurora", "AURORA", "12.345.678/0001-95", "compras@bancoaurora.example")

# ---------------------------------------------------------------- VisaoAgente


def test_visao_agente_tem_exatamente_os_seis_campos():
    assert set(VisaoAgente.model_fields) == {
        "pergunta",
        "resposta_agente",
        "resposta_corrigida",
        "modelo_implantacao",
        "comentarios",
        "aprovacao",
    }


@pytest.mark.parametrize(
    "extra",
    ["cliente", "sigla", "cnpj", "chamado", "prazo", "validador_id", "arquivo", "requisicao_id"],
)
def test_visao_agente_recusa_campos_extras(extra):
    with pytest.raises(ValidationError):
        VisaoAgente.model_validate(
            {"pergunta": "Há criptografia?", "modelo_implantacao": "hosting", extra: "x"}
        )


def test_visao_agente_modelo_de_implantacao_e_valor_fechado():
    with pytest.raises(ValidationError):
        VisaoAgente.model_validate({"pergunta": "x", "modelo_implantacao": "nuvem"})
    visao = VisaoAgente(pergunta="x", modelo_implantacao=ModeloImplantacao.ON_PREMISE)
    assert visao.revisado is False
    assert visao.model_copy(update={"aprovacao": False}).revisado is True


# ---------------------------------------------------------------- marcadores


def test_marcador_ida_e_volta():
    assert str(Marcador(tipo=TipoMarcador.CLIENTE)) == "{{CLIENTE}}"
    assert str(Marcador(tipo=TipoMarcador.PESSOA, indice=2)) == "{{PESSOA_2}}"
    assert Marcador.ler("{{EMAIL_3}}") == Marcador(tipo=TipoMarcador.EMAIL, indice=3)
    with pytest.raises(ValueError, match="inválido"):
        Marcador.ler("{{cliente}}")
    achados = Marcador.encontrar("O {{CLIENTE}} usa {{QUALQUER}} e {{CNPJ_1}}.")
    assert [str(m) for m in achados] == ["{{CLIENTE}}", "{{CNPJ_1}}"]


# ---------------------------------------------------------------- anonimização


def _entrada(**kwargs) -> EntradaAnonimizacao:
    linhas = (
        LinhaOriginal(aba="RFP", linha=1, texto="Questionário do Banco Aurora - confidencial"),
        LinhaOriginal(aba="RFP", linha=2, texto="Contato: compras@bancoaurora.example"),
        LinhaOriginal(aba="RFP", linha=5, texto="O Banco Aurora exige ISO 27001?"),
        LinhaOriginal(
            aba="RFP",
            linha=6,
            texto="Envie evidências a compras@bancoaurora.example (CNPJ 12.345.678/0001-95).",
        ),
        LinhaOriginal(aba="RFP", linha=7, texto="A Aurora Cloud atende a aurora?"),
        LinhaOriginal(aba="Anexo", linha=3, texto="Aba sem linha de corte: AURORA"),
    )
    base = {
        "linhas": linhas,
        "linha_inicial": {"RFP": 5},
        "termos_cliente": ("Banco Aurora", "AURORA"),
    }
    return EntradaAnonimizacao(**(base | kwargs))


def test_anonimizador_respeita_a_linha_de_corte():
    resultado = FakeAnonymizer().anonimizar(_entrada())
    # Linhas acima do corte e abas sem corte não são extraídas.
    assert [(linha.aba, linha.linha) for linha in resultado.linhas] == [
        ("RFP", 5),
        ("RFP", 6),
        ("RFP", 7),
    ]


def test_anonimizador_nao_deixa_canario_no_texto():
    resultado = FakeAnonymizer().anonimizar(_entrada())
    texto = "\n".join(linha.texto for linha in resultado.linhas)
    for canario in CANARIOS:
        assert canario.casefold() not in texto.casefold()
    assert resultado.linhas[0].texto == "O {{CLIENTE}} exige ISO 27001?"
    assert resultado.linhas[1].texto == "Envie evidências a {{EMAIL_1}} (CNPJ {{CNPJ_1}})."


def test_anonimizador_marcadores_tipados_e_consistentes():
    entrada = _entrada(
        linhas=(
            LinhaOriginal(aba="RFP", linha=5, texto="Fale com ana@aurora.example."),
            LinhaOriginal(aba="RFP", linha=6, texto="Ou bia@aurora.example, ou ANA@aurora.example"),
        ),
        termos_cliente=(),
    )
    resultado = FakeAnonymizer().anonimizar(entrada)
    assert resultado.linhas[1].texto == "Ou {{EMAIL_2}}, ou {{EMAIL_1}}"
    assert resultado.correspondencia == {
        "{{EMAIL_1}}": "ana@aurora.example",
        "{{EMAIL_2}}": "bia@aurora.example",
    }
    ocorrencia = resultado.linhas[0].ocorrencias[0]
    assert ocorrencia.origem is OrigemDeteccao.REGEX
    assert entrada.linhas[0].texto[ocorrencia.inicio : ocorrencia.fim] == "ana@aurora.example"


def test_anonimizador_lista_de_permissoes_protege_produto():
    resultado = FakeAnonymizer().anonimizar(_entrada(lista_permissoes=("Aurora Cloud",)))
    # O produto da empresa fica; a menção ao cliente na mesma linha é mascarada.
    assert resultado.linhas[2].texto == "A Aurora Cloud atende a {{CLIENTE}}?"


def test_restaurar_devolve_os_valores_reais():
    resultado = FakeAnonymizer().anonimizar(_entrada())
    original = "Envie evidências a compras@bancoaurora.example (CNPJ 12.345.678/0001-95)."
    assert restaurar(resultado.linhas[1].texto, resultado.correspondencia) == original
    # Marcador desconhecido é mantido como está.
    assert restaurar("{{PESSOA_9}}", resultado.correspondencia) == "{{PESSOA_9}}"


def test_invariancia_clientes_diferentes_geram_a_mesma_entrada_para_o_agente():
    def anonimizado(cliente: str) -> str:
        entrada = EntradaAnonimizacao(
            linhas=(LinhaOriginal(aba="A", linha=1, texto=f"O {cliente} exige SSO?"),),
            linha_inicial={"A": 1},
            termos_cliente=(cliente,),
        )
        return FakeAnonymizer().anonimizar(entrada).linhas[0].texto

    assert (
        anonimizado("Banco Aurora")
        == anonimizado("Seguradora Boreal")
        == "O {{CLIENTE}} exige SSO?"
    )


# ---------------------------------------------------------------- modelo canônico


def _pergunta(id_: str, aba: str, linha: int, **kwargs) -> Pergunta:
    local = Localizacao(aba=aba, linha=linha, celula_resposta=f"D{linha}")
    return Pergunta(id=id_, texto="Pergunta?", localizacao=local, **kwargs)


def test_questionario_a_partir_do_corte():
    q = Questionario(
        canal=Canal.EXCEL,
        abas=(
            Aba(
                nome="Segurança",
                perguntas=(_pergunta("a", "Segurança", 3), _pergunta("b", "Segurança", 8)),
                linha_de_corte_sugerida=3,
            ),
            Aba(nome="Capa", perguntas=(_pergunta("c", "Capa", 2),)),
        ),
    )
    assert [p.id for p in q.perguntas] == ["a", "b", "c"]
    assert [p.id for p in q.a_partir_do_corte({"Segurança": 5})] == ["b"]


def test_pergunta_de_opcao_exige_opcoes():
    with pytest.raises(ValidationError):
        _pergunta("a", "A", 1, tipo=TipoResposta.OPCAO)
    assert _pergunta("a", "A", 1, tipo=TipoResposta.OPCAO, opcoes=("Sim", "Não")).opcoes


# ---------------------------------------------------------------- adaptadores falsos


def test_falsos_implementam_as_portas():
    storage: FileStorage = FakeFileStorage()
    notifier: Notifier = FakeNotifier("teams")
    inbound: InboundMail = FakeInboundMail()
    tickets: TicketConnector = FakeTicketConnector()
    embeddings: EmbeddingProvider = FakeEmbeddingProvider()
    anonymizer: Anonymizer = FakeAnonymizer()
    assert all([storage, notifier, inbound, tickets, embeddings, anonymizer])


def test_storage_falso():
    storage = FakeFileStorage()
    storage.salvar("originais", "req-1/planilha.xlsx", b"conteudo")
    assert storage.existe("originais", "req-1/planilha.xlsx")
    assert storage.ler("originais", "req-1/planilha.xlsx") == b"conteudo"
    storage.remover("originais", "req-1/planilha.xlsx")
    assert not storage.existe("originais", "req-1/planilha.xlsx")
    with pytest.raises(ArquivoNaoEncontradoError):
        storage.ler("originais", "req-1/planilha.xlsx")


def test_notificador_e_caixa_de_entrada_falsos():
    notifier = FakeNotifier("teams")
    notifier.notificar(Notificacao(destinatario="ana@empresa.example", titulo="Prazo", texto="x"))
    assert notifier.canal == "teams"
    assert len(notifier.enviadas) == 1

    mensagem = MensagemRecebida(
        id="m1",
        remetente="ana@empresa.example",
        assunto="Re: pergunta 12",
        corpo="ok",
        recebida_em=datetime(2026, 11, 12, tzinfo=UTC),
    )
    inbound = FakeInboundMail([mensagem])
    assert inbound.buscar_novas() == [mensagem]
    inbound.marcar_lida("m1")
    assert inbound.buscar_novas() == []


def test_chamados_e_embeddings_falsos():
    chamado = Chamado(numero="CH-1", titulo="RFP", aberto_em=datetime(2026, 11, 12, tzinfo=UTC))
    tickets = FakeTicketConnector([chamado])
    assert tickets.buscar("CH-1") == chamado
    assert tickets.buscar("CH-2") is None

    embeddings = FakeEmbeddingProvider(dimensoes=24)
    a, b, a2 = embeddings.embed(["criptografia", "backup", "criptografia"])
    assert len(a) == embeddings.dimensoes == 24
    assert a == a2
    assert a != b
    assert abs(sum(x * x for x in a) - 1.0) < 1e-9
