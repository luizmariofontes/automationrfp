"""Cadastros e auditoria das ações de administrador."""

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.modules.auditoria.models import RegistroModel
from app.modules.cadastros import service
from app.modules.cadastros.domain import ClienteEntrada, formatar_cnpj, normalizar_cnpj
from app.modules.identidade import service as identidade
from app.modules.identidade.service import Papel

SENHA = "senha-de-teste-123"
# Clientes fictícios; os CNPJs têm dígitos verificadores válidos.
AURORA = {
    "sigla": "aur",
    "nome": "Banco Aurora S.A.",
    "outros_nomes": ["Banco Aurora", "banco aurora", "  "],
    "cnpj": "11.222.333/0001-81",
    "dominios": ["BancoAurora.example", "@aurora.example"],
    "apelidos": ["Aurora"],
    "modelo_implantacao_padrao": "hosting",
}
BOREAL = {"sigla": "BOR", "nome": "Seguradora Boreal"}


@pytest.fixture
def usuarios(db):
    criados = {
        papel: identidade.criar_usuario(
            db,
            email=f"{papel.value}@empresa.example",
            nome=papel.value.title(),
            papeis={papel},
            senha=SENHA,
        )
        for papel in (Papel.ADMIN, Papel.ANALISTA, Papel.VALIDADOR)
    }
    db.commit()
    return criados


def _entrar(client, papel: Papel):
    resp = client.post(
        "/api/v1/auth/login", json={"email": f"{papel.value}@empresa.example", "senha": SENHA}
    )
    assert resp.status_code == 200


@pytest.fixture
def admin(client, usuarios):
    _entrar(client, Papel.ADMIN)
    return client


def _auditoria(db) -> list[RegistroModel]:
    db.expire_all()
    return list(db.scalars(select(RegistroModel).order_by(RegistroModel.ocorrido_em)))


# ---------------------------------------------------------------- CNPJ


def test_cnpj_numerico_e_alfanumerico():
    assert normalizar_cnpj("11.222.333/0001-81") == "11222333000181"
    assert formatar_cnpj("11222333000181") == "11.222.333/0001-81"
    # Exemplo de CNPJ alfanumérico divulgado pela Receita Federal.
    assert normalizar_cnpj("12.ABC.345/01DE-35") == "12ABC34501DE35"
    for invalido in ("11.222.333/0001-82", "00000000000000", "123", "12ABC34501DE3X"):
        with pytest.raises(ValueError, match="CNPJ inválido"):
            normalizar_cnpj(invalido)


def test_erro_de_validacao_nao_repete_o_valor_recebido(admin):
    resp = admin.post(
        "/api/v1/cadastros/clientes",
        json={"sigla": "ZZ", "nome": "Cliente Sigiloso", "cnpj": "99.999.999/9999-00"},
    )
    assert resp.status_code == 422
    assert "99.999.999" not in resp.text
    assert "Sigiloso" not in resp.text


# ---------------------------------------------------------------- clientes


def test_criar_cliente_normaliza_e_audita(admin, db, usuarios):
    resp = admin.post("/api/v1/cadastros/clientes", json=AURORA)
    assert resp.status_code == 201, resp.text
    cliente = resp.json()
    assert cliente["sigla"] == "AUR"
    assert cliente["cnpj"] == "11222333000181"
    assert cliente["outros_nomes"] == ["Banco Aurora"]
    assert cliente["dominios"] == ["bancoaurora.example", "aurora.example"]
    assert cliente["modelo_implantacao_padrao"] == "hosting"
    assert cliente["ativo"] is True

    (registro,) = _auditoria(db)
    assert registro.acao == "cliente.criado"
    assert registro.entidade_id == cliente["id"]
    assert registro.ator_id == usuarios[Papel.ADMIN].id
    assert registro.request_id == resp.headers["X-Request-ID"]
    # A auditoria guarda nomes de campos, nunca os valores.
    assert "sigla" in registro.campos
    assert "Aurora" not in " ".join(registro.campos)


def test_sigla_e_cnpj_unicos(admin):
    assert admin.post("/api/v1/cadastros/clientes", json=AURORA).status_code == 201
    mesma_sigla = admin.post("/api/v1/cadastros/clientes", json={"sigla": "AUR", "nome": "Outro"})
    assert mesma_sigla.status_code == 409
    mesmo_cnpj = admin.post(
        "/api/v1/cadastros/clientes",
        json={"sigla": "OUT", "nome": "Outro", "cnpj": "11222333000181"},
    )
    assert mesmo_cnpj.status_code == 409


def test_atualizar_cliente_audita_so_o_que_mudou(admin, db):
    cliente = admin.post("/api/v1/cadastros/clientes", json=AURORA).json()
    url = f"/api/v1/cadastros/clientes/{cliente['id']}"

    resp = admin.patch(
        url, json={"nome": "Banco Aurora S.A.", "apelidos": ["Aurora", "BA"], "cnpj": None}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["apelidos"] == ["Aurora", "BA"]
    assert resp.json()["cnpj"] is None
    assert resp.json()["modelo_implantacao_padrao"] == "hosting"  # não enviado: não muda

    registros = _auditoria(db)
    assert [r.acao for r in registros] == ["cliente.criado", "cliente.alterado"]
    assert registros[1].campos == ["apelidos", "cnpj"]

    # Nada mudou: nada é auditado.
    assert admin.patch(url, json={"apelidos": ["Aurora", "BA"]}).status_code == 200
    assert len(_auditoria(db)) == 2

    assert admin.patch(url, json={"ativo": False}).json()["ativo"] is False
    assert admin.patch(url, json={"campo_inexistente": 1}).status_code == 422


def test_modelo_de_implantacao_e_valor_fechado():
    with pytest.raises(ValidationError):
        ClienteEntrada.model_validate(BOREAL | {"modelo_implantacao_padrao": "nuvem"})


def test_termos_do_cliente(admin, db):
    cliente = admin.post("/api/v1/cadastros/clientes", json=AURORA).json()
    termos = service.termos_do_cliente(db, cliente["id"])
    assert set(termos) == {
        "AUR",
        "Banco Aurora S.A.",
        "Banco Aurora",
        "Aurora",
        "bancoaurora.example",
        "aurora.example",
        "11222333000181",
        "11.222.333/0001-81",
    }


# ---------------------------------------------------------------- permissões


def test_so_admin_altera_cadastros(client, usuarios, db):
    assert client.get("/api/v1/cadastros/clientes").status_code == 401

    _entrar(client, Papel.ANALISTA)
    assert client.get("/api/v1/cadastros/clientes").status_code == 200
    assert client.get("/api/v1/cadastros/equipes").status_code == 200
    assert client.post("/api/v1/cadastros/clientes", json=BOREAL).status_code == 403
    assert client.post("/api/v1/cadastros/equipes", json={"nome": "X"}).status_code == 403
    assert client.get("/api/v1/cadastros/regras-escalonamento").status_code == 403
    assert client.get("/api/v1/cadastros/usuarios").status_code == 403
    assert client.get("/api/v1/auditoria").status_code == 403

    _entrar(client, Papel.VALIDADOR)
    # Validador não vê a lista de clientes, só as equipes.
    assert client.get("/api/v1/cadastros/clientes").status_code == 403
    assert client.get("/api/v1/cadastros/equipes").status_code == 200
    assert _auditoria(db) == []


# ---------------------------------------------------------------- equipes e membros


def test_equipes_e_membros(admin, db, usuarios):
    equipe = admin.post(
        "/api/v1/cadastros/equipes",
        json={"nome": " Segurança  da Informação ", "escopo": "ISO 27001, LGPD", "email": ""},
    ).json()
    assert equipe["nome"] == "Segurança da Informação"
    assert equipe["email"] is None
    assert equipe["membros"] == []
    repetida = admin.post("/api/v1/cadastros/equipes", json={"nome": "Segurança da Informação"})
    assert repetida.status_code == 409

    lista = admin.get("/api/v1/cadastros/usuarios").json()
    assert {u["email"] for u in lista} == {f"{p.value}@empresa.example" for p in usuarios}

    validador = str(usuarios[Papel.VALIDADOR].id)
    analista = str(usuarios[Papel.ANALISTA].id)
    base = f"/api/v1/cadastros/equipes/{equipe['id']}/membros"
    assert admin.put(f"{base}/{validador}", json={}).status_code == 200
    resp = admin.put(f"{base}/{analista}", json={"responsavel": True})
    # Responsáveis vêm primeiro.
    assert [(m["email"], m["responsavel"]) for m in resp.json()["membros"]] == [
        ("analista@empresa.example", True),
        ("validador@empresa.example", False),
    ]
    assert admin.put(f"{base}/{validador}", json={"responsavel": True}).status_code == 200
    assert admin.put(f"{base}/{validador}", json={"responsavel": True}).status_code == 200
    assert admin.put(f"{base}/{equipe['id']}", json={}).status_code == 404  # não é usuário

    assert admin.delete(f"{base}/{analista}").status_code == 204
    assert admin.delete(f"{base}/{analista}").status_code == 404
    (unica,) = admin.get("/api/v1/cadastros/equipes").json()
    assert [m["email"] for m in unica["membros"]] == ["validador@empresa.example"]

    assert [r.acao for r in _auditoria(db)] == [
        "equipe.criada",
        "membro.incluido",
        "membro.incluido",
        "membro.alterado",
        "membro.removido",
    ]


def test_atualizar_equipe(admin, db):
    equipe = admin.post("/api/v1/cadastros/equipes", json={"nome": "Infra"}).json()
    resp = admin.patch(
        f"/api/v1/cadastros/equipes/{equipe['id']}",
        json={"escopo": "Datacenter e redes", "email": "Infra@Empresa.example", "ativo": False},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == "infra@empresa.example"
    assert resp.json()["ativo"] is False
    assert _auditoria(db)[-1].campos == ["ativo", "email", "escopo"]
    assert [e.nome for e in service.listar_equipes(db, apenas_ativas=True)] == []


# ---------------------------------------------------------------- escalonamento


def test_regras_de_escalonamento(admin, db):
    equipe = admin.post("/api/v1/cadastros/equipes", json={"nome": "Jurídico"}).json()
    url = "/api/v1/cadastros/regras-escalonamento"
    padrao = admin.post(
        url,
        json={
            "nome": "Lembrete",
            "dias_do_prazo": -2,
            "destinatario": "validador",
            "canais": ["teams", "email", "email"],
        },
    )
    assert padrao.status_code == 201, padrao.text
    assert padrao.json()["canais"] == ["email", "teams"]
    assert padrao.json()["equipe_id"] is None

    # Sem regra própria, a equipe usa as regras padrão.
    assert [r.nome for r in service.regras_da_equipe(db, equipe["id"])] == ["Lembrete"]

    propria = admin.post(
        url,
        json={
            "equipe_id": equipe["id"],
            "nome": "Atraso",
            "dias_do_prazo": 1,
            "destinatario": "responsavel_equipe",
            "canais": ["email"],
        },
    ).json()
    assert [r.nome for r in service.regras_da_equipe(db, equipe["id"])] == ["Atraso"]

    assert admin.patch(f"{url}/{propria['id']}", json={"ativo": False}).json()["ativo"] is False
    assert [r.nome for r in service.regras_da_equipe(db, equipe["id"])] == ["Lembrete"]

    invalidas = [
        {"nome": "x", "dias_do_prazo": 0, "destinatario": "cliente", "canais": ["email"]},
        {"nome": "x", "dias_do_prazo": 0, "destinatario": "admin", "canais": []},
        {"nome": "x", "dias_do_prazo": 0, "destinatario": "admin", "canais": ["sms"]},
        {"nome": "x", "dias_do_prazo": 99, "destinatario": "admin", "canais": ["email"]},
    ]
    for corpo in invalidas:
        assert admin.post(url, json=corpo).status_code == 422
    sem_equipe = {
        "equipe_id": padrao.json()["id"],
        "nome": "x",
        "dias_do_prazo": 0,
        "destinatario": "admin",
        "canais": ["email"],
    }
    assert admin.post(url, json=sem_equipe).status_code == 404

    assert admin.delete(f"{url}/{propria['id']}").status_code == 204
    assert admin.delete(f"{url}/{propria['id']}").status_code == 404
    assert len(admin.get(url).json()) == 1
    assert [r.acao for r in _auditoria(db)][-1] == "regra_escalonamento.removida"


# ---------------------------------------------------------------- auditoria


def test_consulta_da_auditoria(admin, db):
    admin.post("/api/v1/cadastros/clientes", json=AURORA)
    admin.post("/api/v1/cadastros/clientes", json=BOREAL)
    admin.post("/api/v1/cadastros/equipes", json={"nome": "Infra"})

    tudo = admin.get("/api/v1/auditoria").json()
    assert tudo["total"] == 3
    assert tudo["itens"][0]["acao"] == "equipe.criada"  # mais recente primeiro
    assert tudo["itens"][0]["ator_email"] == "admin@empresa.example"

    clientes = admin.get("/api/v1/auditoria", params={"entidade": "cliente", "limite": 1}).json()
    assert clientes["total"] == 2
    assert len(clientes["itens"]) == 1
    # Nenhum dado do cliente aparece na trilha.
    assert "Aurora" not in admin.get("/api/v1/auditoria").text


def test_pronto_quando_do_sprint_2(admin, db):
    """O admin cadastra 3 equipes e 2 clientes, com as ações na auditoria."""
    for nome in ("Segurança", "Infraestrutura", "Jurídico"):
        assert admin.post("/api/v1/cadastros/equipes", json={"nome": nome}).status_code == 201
    for cliente in (AURORA, BOREAL):
        assert admin.post("/api/v1/cadastros/clientes", json=cliente).status_code == 201

    assert len(admin.get("/api/v1/cadastros/equipes").json()) == 3
    assert len(admin.get("/api/v1/cadastros/clientes").json()) == 2
    acoes = [r.acao for r in _auditoria(db)]
    assert acoes.count("equipe.criada") == 3
    assert acoes.count("cliente.criado") == 2
