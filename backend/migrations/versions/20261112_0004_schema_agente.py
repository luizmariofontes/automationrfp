"""schema `agente` e papel do Postgres restrito a ele

O worker do agente conecta com o papel `rfp_agente`, que só lê o schema `agente`.
Ele não recebe permissão em nenhuma tabela do schema `public` (cadastros, requisições,
comunicação, privacidade). Tabelas internas que o agente precisar ler, como a base de
documentos, recebem um GRANT explícito na migração que as criar.

Só o módulo `privacidade` escreve no schema `agente`, com o papel principal da aplicação.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-12
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agente"
PAPEL = "rfp_agente"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    # Papéis valem para o servidor inteiro, então podem já existir (ex.: banco de teste).
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{PAPEL}') THEN
                CREATE ROLE {PAPEL} NOLOGIN;
            END IF;
        END
        $$
        """
    )
    # Permite ao papel da aplicação assumir o papel do agente com SET ROLE (ambiente local).
    op.execute(f"GRANT {PAPEL} TO CURRENT_USER")
    op.execute(f"GRANT USAGE ON SCHEMA {SCHEMA} TO {PAPEL}")
    op.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA {SCHEMA} TO {PAPEL}")
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} GRANT SELECT ON TABLES TO {PAPEL}")


def downgrade() -> None:
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} REVOKE SELECT ON TABLES FROM {PAPEL}")
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA {SCHEMA} FROM {PAPEL}")
    op.execute(f"REVOKE ALL ON SCHEMA {SCHEMA} FROM {PAPEL}")
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    # O papel não é removido: ele é do servidor e pode estar em uso por outro banco.
