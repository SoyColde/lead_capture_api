
"""Create pending actions table

Revision ID: 445a14f39e2c
Revises: fdfe0b1c3e84
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Identificadores de la migración
revision: str = "445a14f39e2c"
down_revision: Union[str, Sequence[str], None] = "fdfe0b1c3e84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crear la tabla de acciones pendientes."""

    op.create_table(
        "pending_actions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("requested_by", sa.String(), nullable=True),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'executed')",
            name="ck_pending_actions_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_pending_actions_id",
        "pending_actions",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    """Eliminar la tabla de acciones pendientes."""

    op.drop_index(
        "ix_pending_actions_id",
        table_name="pending_actions",
    )

    op.drop_table("pending_actions")
