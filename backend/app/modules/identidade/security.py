"""Hash de senha (argon2id) e tokens de sessão."""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()

# Hash usado quando o e-mail não existe, para que a resposta leve o mesmo tempo
# e não revele quais e-mails estão cadastrados.
_HASH_FICTICIO = _hasher.hash("senha-ficticia-para-tempo-constante")

SENHA_MINIMA = 10


def hash_senha(senha: str) -> str:
    if len(senha) < SENHA_MINIMA:
        raise ValueError(f"A senha precisa ter pelo menos {SENHA_MINIMA} caracteres.")
    return _hasher.hash(senha)


def verificar_senha(senha: str, senha_hash: str | None) -> bool:
    try:
        return _hasher.verify(senha_hash or _HASH_FICTICIO, senha) and senha_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def novo_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
