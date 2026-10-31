"""Rotas de autenticação: /api/v1/auth."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.modules.identidade import service
from app.modules.identidade.domain import Papel, UsuarioAutenticado
from app.shared.config import Settings, get_settings
from app.shared.db import get_session

router = APIRouter(prefix="/api/v1/auth", tags=["autenticação"])

DbDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


class LoginEntrada(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    senha: str = Field(min_length=1, max_length=256)


class UsuarioSaida(BaseModel):
    id: str
    email: str
    nome: str
    papeis: list[Papel]

    @classmethod
    def de(cls, u: UsuarioAutenticado) -> "UsuarioSaida":
        return cls(id=str(u.id), email=u.email, nome=u.nome, papeis=sorted(u.papeis))


class Provedores(BaseModel):
    local: bool
    oidc: bool


@router.get("/providers", response_model=Provedores)
def provedores(settings: SettingsDep) -> Provedores:
    """Quais formas de login estão ativas, para a tela de login decidir o que mostrar."""
    return Provedores(local=settings.auth_local_enabled, oidc=settings.auth_oidc_enabled)


@router.post("/login", response_model=UsuarioSaida)
def login(
    entrada: LoginEntrada, response: Response, db: DbDep, settings: SettingsDep
) -> UsuarioSaida:
    usuario, token = service.login_local(db, settings, email=entrada.email, senha=entrada.senha)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return UsuarioSaida.de(usuario)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: DbDep,
    settings: SettingsDep,
    token: Annotated[str | None, Depends(service.token_da_sessao)],
) -> None:
    service.logout(db, token)
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/me", response_model=UsuarioSaida)
def me(usuario: Annotated[UsuarioAutenticado, Depends(service.usuario_atual)]) -> UsuarioSaida:
    return UsuarioSaida.de(usuario)
