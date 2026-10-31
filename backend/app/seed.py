"""Dados de exemplo para o ambiente local: `python -m app.seed`.

Cria um usuário para cada papel, todos com a senha SEED_PASSWORD (padrão: rfp-local-123).
Só roda com APP_ENV=local ou homologacao. Pode ser executado mais de uma vez.
"""

import sys

from app.modules.identidade import service as identidade
from app.modules.identidade.service import Papel
from app.shared.config import get_settings
from app.shared.db import get_sessionmaker
from app.shared.errors import ConflictError

USUARIOS_EXEMPLO = [
    ("admin@rfp.local", "Admin Local", {Papel.ADMIN}),
    ("analista@rfp.local", "Analista Local", {Papel.ANALISTA}),
    ("validador@rfp.local", "Validador Local", {Papel.VALIDADOR}),
    ("conhecimento@rfp.local", "Gestor de Conhecimento Local", {Papel.GESTOR_CONHECIMENTO}),
]


def main() -> int:
    settings = get_settings()
    if settings.app_env not in {"local", "homologacao"}:
        print(f"seed recusado: APP_ENV={settings.app_env}")
        return 1

    with get_sessionmaker()() as db:
        for email, nome, papeis in USUARIOS_EXEMPLO:
            try:
                identidade.criar_usuario(
                    db, email=email, nome=nome, papeis=papeis, senha=settings.seed_password
                )
                db.commit()
                print(f"criado: {email} ({', '.join(sorted(papeis))})")
            except ConflictError:
                db.rollback()
                print(f"já existe: {email}")
    print("Senha de todos: valor de SEED_PASSWORD (padrão rfp-local-123).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
