from datetime import UTC, datetime, timedelta

import pytest
from fastapi import APIRouter, Depends
from pydantic import ValidationError
from sqlalchemy import select

from app.modules.identidade import service
from app.modules.identidade.models import SessaoModel, UsuarioModel
from app.modules.identidade.service import Papel
from app.shared.config import Settings

SENHA = "senha-de-teste-123"


@pytest.fixture
def analista(db):
    u = service.criar_usuario(
        db, email="Ana@Empresa.com", nome="Ana", papeis={Papel.ANALISTA}, senha=SENHA
    )
    db.commit()
    return u


def _login(client, email="ana@empresa.com", senha=SENHA):
    return client.post("/api/v1/auth/login", json={"email": email, "senha": senha})


def test_provedores(client):
    assert client.get("/api/v1/auth/providers").json() == {"local": True, "oidc": False}


def test_login_ok_define_cookie_httponly(client, analista):
    resp = _login(client, email="  ANA@empresa.com ")
    assert resp.status_code == 200
    assert resp.json()["email"] == "ana@empresa.com"
    assert resp.json()["papeis"] == ["analista"]
    cookie = resp.headers["set-cookie"]
    assert "rfp_sessao=" in cookie
    assert "HttpOnly" in cookie
    assert "samesite=lax" in cookie.lower()


def test_sessao_guarda_apenas_hash_do_token(client, analista, db):
    _login(client)
    token = client.cookies.get("rfp_sessao")
    sessao = db.scalar(select(SessaoModel))
    assert sessao is not None
    assert token not in sessao.token_hash
    assert len(sessao.token_hash) == 64


def test_me_com_e_sem_sessao(client, analista):
    assert client.get("/api/v1/auth/me").status_code == 401
    _login(client)
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Ana"


def test_senha_errada_e_email_inexistente_tem_mesma_mensagem(client, analista):
    errada = _login(client, senha="outra-senha-qualquer")
    inexistente = _login(client, email="ninguem@empresa.com")
    assert errada.status_code == inexistente.status_code == 401
    assert errada.json()["error"]["message"] == inexistente.json()["error"]["message"]


def test_bloqueio_apos_falhas(client, analista, db):
    for _ in range(5):
        _login(client, senha="senha-errada-123")
    # Mesmo com a senha certa, o usuário fica bloqueado.
    assert _login(client).status_code == 401
    usuario = db.scalar(select(UsuarioModel).where(UsuarioModel.email == "ana@empresa.com"))
    db.refresh(usuario)
    assert usuario.bloqueado_ate is not None
    # Passado o bloqueio, entra normalmente.
    usuario.bloqueado_ate = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    assert _login(client).status_code == 200


def test_usuario_inativo_nao_entra(client, analista, db):
    usuario = db.scalar(select(UsuarioModel))
    usuario.ativo = False
    db.commit()
    assert _login(client).status_code == 401


def test_logout_encerra_a_sessao(client, analista):
    _login(client)
    token = client.cookies.get("rfp_sessao")
    assert client.post("/api/v1/auth/logout").status_code == 204
    # O token antigo não vale mais, mesmo se reapresentado.
    client.cookies.set("rfp_sessao", token)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_sessao_expirada(client, analista, db):
    _login(client)
    sessao = db.scalar(select(SessaoModel))
    sessao.expira_em = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401


def test_exigir_papeis(app, client, db, analista):
    router = APIRouter()

    @router.get("/_teste/admin")
    def so_admin(u=Depends(service.exigir_papeis(Papel.ADMIN))):  # noqa: B008
        return {"ok": True}

    @router.get("/_teste/analista")
    def so_analista(u=Depends(service.exigir_papeis(Papel.ANALISTA))):  # noqa: B008
        return {"ok": True}

    app.include_router(router)
    assert client.get("/_teste/analista").status_code == 401
    _login(client)
    assert client.get("/_teste/analista").status_code == 200
    assert client.get("/_teste/admin").status_code == 403

    service.criar_usuario(
        db, email="adm@empresa.com", nome="Adm", papeis={Papel.ADMIN}, senha=SENHA
    )
    db.commit()
    _login(client, email="adm@empresa.com")
    # Administrador passa em qualquer exigência de papel.
    assert client.get("/_teste/analista").status_code == 200


def test_email_duplicado(db, analista):
    from app.shared.errors import ConflictError

    with pytest.raises(ConflictError):
        service.criar_usuario(db, email="ana@empresa.com", nome="Outra", papeis=set(), senha=SENHA)


def test_senha_curta_recusada(db):
    with pytest.raises(ValueError, match="pelo menos"):
        service.criar_usuario(db, email="x@empresa.com", nome="X", papeis=set(), senha="curta")


def test_login_local_desativado(app, client, analista):
    from app.shared.config import get_settings

    app.dependency_overrides[get_settings] = lambda: Settings(auth_local_enabled=False)
    assert _login(client).status_code == 404
    assert client.get("/api/v1/auth/providers").json()["local"] is False


def test_producao_recusa_login_local():
    with pytest.raises(ValidationError, match="AUTH_LOCAL_ENABLED"):
        Settings(app_env="producao", auth_local_enabled=True, session_cookie_secure=True)
    with pytest.raises(ValidationError, match="SESSION_COOKIE_SECURE"):
        Settings(app_env="producao", auth_local_enabled=False)
    Settings(app_env="producao", auth_local_enabled=False, session_cookie_secure=True)
