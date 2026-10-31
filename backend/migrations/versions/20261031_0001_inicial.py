"""Inicial: extensões do Postgres usadas pelo projeto.

- vector: embeddings da base de conhecimento e da biblioteca (pgvector)
- unaccent: busca textual em português sem depender de acentos

Revision ID: 0001
Revises:
Create Date: 2026-10-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS unaccent")
    op.execute("DROP EXTENSION IF EXISTS vector")
