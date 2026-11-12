"""Serviço público do módulo de identidade.

Outros módulos usam daqui:
- `usuario_atual` e `exigir_papeis(...)`: dependências do FastAPI para proteger rotas;
- `UsuarioAutenticado` e `Papel`: tipos do usuário logado;
- `criar_usuario`: usado pelo seed e, no sprint 2, pela administração.
"""

from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.modules.identidade.domain import Papel, UsuarioAutenticado
from app.modules.identidade.models import SessaoModel, UsuarioModel
from app.modules.identidade.repository import IdentidadeRepository
from app.modules.identidade.security import hash_senha, hash_token, novo_token, verificar_senha
from app.shared.config import Settings, get_settings
from app.shared.db import get_session
from app.shared.errors import AppError, ConflictError, ForbiddenError, UnauthorizedError
from app.shared.logging import get_logger

__all__ = [
    "Papel",
    "UsuarioAutenticado",
    "criar_usuario",
    "exigir_papeis",
    "listar_usuarios",
    "token_da_sessao",
    "usuario_atual",
    "usuarios_por_ids",
]

log = get_logger(__name__)

MENSAGEM_LOGIN_INVALIDO = "E-mail ou senha incorretos."


class LoginLocalDesativadoError(AppError):
    status_code = 404
    code = "login_local_desativado"


def _agora() -> datetime:
    return datetime.now(UTC)


def _para_autenticado(u: UsuarioModel) -> UsuarioAutenticado:
    return UsuarioAutenticado(
        id=u.id,
        email=u.email,
        nome=u.nome,
        papeis=frozenset(Papel(p) for p in u.papeis),
    )


def normalizar_email(email: str) -> str:
    return email.strip().lower()


# ---------------------------------------------------------------- usuários


def criar_usuario(
    db: Session,
    *,
    email: str,
    nome: str,
    papeis: set[Papel],
    senha: str | None = None,
) -> UsuarioAutenticado:
    repo = IdentidadeRepository(db)
    email = normalizar_email(email)
    if repo.usuario_por_email(email):
        raise ConflictError("Já existe um usuário com este e-mail.")
    usuario = UsuarioModel(
        email=email,
        nome=nome.strip(),
        papeis=sorted(p.value for p in papeis),
        senha_hash=hash_senha(senha) if senha else None,
        ativo=True,
        falhas_login=0,
    )
    repo.adicionar(usuario)
    db.flush()
    log.info("usuario_criado", usuario_id=str(usuario.id), papeis=usuario.papeis)
    return _para_autenticado(usuario)


def listar_usuarios(db: Session, *, apenas_ativos: bool = True) -> list[UsuarioAutenticado]:
    return [_para_autenticado(u) for u in IdentidadeRepository(db).listar(apenas_ativos)]


def usuarios_por_ids(db: Session, ids: Iterable[UUID]) -> dict[UUID, UsuarioAutenticado]:
    return {u.id: _para_autenticado(u) for u in IdentidadeRepository(db).por_ids(set(ids))}


# ---------------------------------------------------------------- login local


def login_local(
    db: Session, settings: Settings, *, email: str, senha: str
) -> tuple[UsuarioAutenticado, str]:
    """Valida e-mail e senha e abre uma sessão. Devolve o usuário e o token do cookie."""
    if not settings.auth_local_enabled:
        raise LoginLocalDesativadoError("Login local desativado neste ambiente.")

    repo = IdentidadeRepository(db)
    agora = _agora()
    usuario = repo.usuario_por_email(normalizar_email(email))

    if usuario and usuario.bloqueado_ate and usuario.bloqueado_ate > agora:
        verificar_senha(senha, None)  # mantém o tempo de resposta
        log.warning("login_bloqueado", usuario_id=str(usuario.id))
        raise UnauthorizedError(MENSAGEM_LOGIN_INVALIDO)

    senha_ok = verificar_senha(senha, usuario.senha_hash if usuario else None)
    if not usuario or not usuario.ativo or not senha_ok:
        if usuario:
            usuario.falhas_login += 1
            if usuario.falhas_login >= settings.login_max_falhas:
                usuario.bloqueado_ate = agora + timedelta(minutes=settings.login_bloqueio_minutos)
                usuario.falhas_login = 0
                log.warning("login_bloqueio_aplicado", usuario_id=str(usuario.id))
            db.commit()
        log.info("login_falhou", usuario_existe=usuario is not None)
        raise UnauthorizedError(MENSAGEM_LOGIN_INVALIDO)

    usuario.falhas_login = 0
    usuario.bloqueado_ate = None
    usuario.ultimo_login_em = agora
    token = _abrir_sessao(repo, settings, usuario, metodo="local", agora=agora)
    db.commit()
    log.info("login_ok", usuario_id=str(usuario.id), metodo="local")
    return _para_autenticado(usuario), token


def _abrir_sessao(
    repo: IdentidadeRepository,
    settings: Settings,
    usuario: UsuarioModel,
    *,
    metodo: str,
    agora: datetime,
) -> str:
    token = novo_token()
    repo.adicionar(
        SessaoModel(
            usuario_id=usuario.id,
            token_hash=hash_token(token),
            metodo=metodo,
            expira_em=agora + timedelta(hours=settings.session_ttl_hours),
        )
    )
    return token


def logout(db: Session, token: str | None) -> None:
    if token:
        IdentidadeRepository(db).encerrar_sessao(hash_token(token), _agora())
        db.commit()


def usuario_da_sessao(db: Session, token: str | None) -> UsuarioAutenticado | None:
    if not token:
        return None
    repo = IdentidadeRepository(db)
    sessao = repo.sessao_valida(hash_token(token), _agora())
    if not sessao:
        return None
    usuario = repo.usuario_por_id(sessao.usuario_id)
    if not usuario or not usuario.ativo:
        return None
    return _para_autenticado(usuario)


# ---------------------------------------------------------------- dependências


def token_da_sessao(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> str | None:
    """Token de sessão lido do cookie HttpOnly."""
    return request.cookies.get(settings.session_cookie_name)


def usuario_atual(
    db: Annotated[Session, Depends(get_session)],
    token: Annotated[str | None, Depends(token_da_sessao)],
) -> UsuarioAutenticado:
    usuario = usuario_da_sessao(db, token)
    if usuario is None:
        raise UnauthorizedError("Sessão inválida ou expirada. Entre novamente.")
    return usuario


def exigir_papeis(*papeis: Papel) -> Callable[..., UsuarioAutenticado]:
    """Dependência que exige ao menos um dos papéis (administrador sempre passa)."""

    def _verificar(
        usuario: Annotated[UsuarioAutenticado, Depends(usuario_atual)],
    ) -> UsuarioAutenticado:
        if not usuario.tem_papel(*papeis):
            raise ForbiddenError("Você não tem permissão para esta ação.")
        return usuario

    return _verificar
