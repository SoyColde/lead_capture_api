"""create conversations table

Revision ID: 86db0df3185a
Revises: 59eed7aa898a
Create Date: 2026-10-25 03:00:55.004848

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86db0df3185a'
down_revision: Union[str, Sequence[str], None] = '445a14f39e2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True ),
        sa.Column("owner_id", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index(
    'ix_conversations_owner_id',
    'conversations',
    ['owner_id'],
    unique=False
    )       


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_conversations_owner_id",
        table_name="conversations",
    )
    op.drop_table("conversations")
