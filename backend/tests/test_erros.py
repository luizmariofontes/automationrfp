from fastapi import APIRouter
from pydantic import BaseModel

from app.shared.errors import NotFoundError


class Entrada(BaseModel):
    nome: str


def _rotas_de_teste(app):
    router = APIRouter()

    @router.get("/_teste/nao-encontrado")
    def nao_encontrado():
        raise NotFoundError("Requisição não encontrada.", details={"id": "42"})

    @router.get("/_teste/inesperado")
    def inesperado():
        raise RuntimeError("detalhe interno que não deve vazar")

    @router.post("/_teste/validacao")
    def validacao(entrada: Entrada):
        return entrada

    app.include_router(router)


def test_erro_de_negocio_tem_formato_padrao(app, client):
    _rotas_de_teste(app)
    resp = client.get("/_teste/nao-encontrado")
    assert resp.status_code == 404
    erro = resp.json()["error"]
    assert erro["code"] == "nao_encontrado"
    assert erro["details"] == {"id": "42"}
    assert erro["request_id"] == resp.headers["X-Request-ID"]


def test_erro_inesperado_nao_vaza_detalhes(app, client):
    _rotas_de_teste(app)
    resp = client.get("/_teste/inesperado")
    assert resp.status_code == 500
    assert "detalhe interno" not in resp.text
    assert resp.json()["error"]["code"] == "erro_interno"


def test_validacao_nao_ecoa_valor_recebido(app, client):
    _rotas_de_teste(app)
    resp = client.post("/_teste/validacao", json={"nome": {"cnpj": "12.345.678/0001-90"}})
    assert resp.status_code == 422
    assert "12.345.678" not in resp.text
    assert resp.json()["error"]["code"] == "validacao"


def test_rota_inexistente(client):
    resp = client.get("/nao-existe")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "nao_encontrado"
