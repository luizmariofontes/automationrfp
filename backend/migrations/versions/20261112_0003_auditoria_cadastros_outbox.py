"""auditoria, cadastros e outbox

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _agora() -> sa.Column[sa.DateTime]:
    return sa.Column(
        "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


def upgrade() -> None:
    # ------------------------------------------------------------ outbox
    op.create_table(
        "shared_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tipo", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        _agora(),
        sa.Column("entregue_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tentativas", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shared_outbox")),
    )
    op.create_index(op.f("ix_shared_outbox_tipo"), "shared_outbox", ["tipo"])
    op.create_index(op.f("ix_shared_outbox_criado_em"), "shared_outbox", ["criado_em"])
    op.create_index(op.f("ix_shared_outbox_entregue_em"), "shared_outbox", ["entregue_em"])

    # ------------------------------------------------------------ auditoria
    op.create_table(
        "auditoria_registro",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "ocorrido_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ator_id", sa.Uuid(), nullable=True),
        sa.Column("ator_email", sa.String(length=254), nullable=True),
        sa.Column("acao", sa.String(length=64), nullable=False),
        sa.Column("entidade", sa.String(length=64), nullable=False),
        sa.Column("entidade_id", sa.String(length=64), nullable=False),
        sa.Column("campos", postgresql.ARRAY(sa.String(length=64)), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auditoria_registro")),
    )
    op.create_index(
        op.f("ix_auditoria_registro_ocorrido_em"), "auditoria_registro", ["ocorrido_em"]
    )
    op.create_index(op.f("ix_auditoria_registro_ator_id"), "auditoria_registro", ["ator_id"])
    op.create_index(op.f("ix_auditoria_registro_entidade"), "auditoria_registro", ["entidade"])
    op.create_index(
        op.f("ix_auditoria_registro_entidade_id"), "auditoria_registro", ["entidade_id"]
    )

    # ------------------------------------------------------------ cadastros
    op.create_table(
        "cadastros_cliente",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sigla", sa.String(length=12), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("outros_nomes", postgresql.ARRAY(sa.String(length=200)), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=True),
        sa.Column("dominios", postgresql.ARRAY(sa.String(length=253)), nullable=False),
        sa.Column("apelidos", postgresql.ARRAY(sa.String(length=200)), nullable=False),
        sa.Column("modelo_implantacao_padrao", sa.String(length=16), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        _agora(),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cadastros_cliente")),
        sa.UniqueConstraint("cnpj", name=op.f("uq_cadastros_cliente_cnpj")),
    )
    op.create_index(op.f("ix_cadastros_cliente_sigla"), "cadastros_cliente", ["sigla"], unique=True)
    op.create_table(
        "cadastros_equipe",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("escopo", sa.Text(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        _agora(),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cadastros_equipe")),
        sa.UniqueConstraint("nome", name=op.f("uq_cadastros_equipe_nome")),
    )
    op.create_table(
        "cadastros_membro",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("equipe_id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("responsavel", sa.Boolean(), nullable=False),
        _agora(),
        sa.ForeignKeyConstraint(
            ["equipe_id"],
            ["cadastros_equipe.id"],
            name=op.f("fk_cadastros_membro_equipe_id_cadastros_equipe"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["identidade_usuario.id"],
            name=op.f("fk_cadastros_membro_usuario_id_identidade_usuario"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cadastros_membro")),
        sa.UniqueConstraint("equipe_id", "usuario_id", name=op.f("uq_cadastros_membro_equipe_id")),
    )
    op.create_index(op.f("ix_cadastros_membro_equipe_id"), "cadastros_membro", ["equipe_id"])
    op.create_index(op.f("ix_cadastros_membro_usuario_id"), "cadastros_membro", ["usuario_id"])
    op.create_table(
        "cadastros_regra_escalonamento",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("equipe_id", sa.Uuid(), nullable=True),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("dias_do_prazo", sa.Integer(), nullable=False),
        sa.Column("destinatario", sa.String(length=32), nullable=False),
        sa.Column("canais", postgresql.ARRAY(sa.String(length=16)), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        _agora(),
        sa.ForeignKeyConstraint(
            ["equipe_id"],
            ["cadastros_equipe.id"],
            name=op.f("fk_cadastros_regra_escalonamento_equipe_id_cadastros_equipe"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cadastros_regra_escalonamento")),
    )
    op.create_index(
        op.f("ix_cadastros_regra_escalonamento_equipe_id"),
        "cadastros_regra_escalonamento",
        ["equipe_id"],
    )


def downgrade() -> None:
    op.drop_table("cadastros_regra_escalonamento")
    op.drop_table("cadastros_membro")
    op.drop_table("cadastros_equipe")
    op.drop_table("cadastros_cliente")
    op.drop_table("auditoria_registro")
    op.drop_table("shared_outbox")
