"""add is_public column to document

Revision ID: a350262b7524
Revises: 87ce70d45d0f
Create Date: 2026-07-19 23:00:16.406323

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a350262b7524"
down_revision: str | None = "87ce70d45d0f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.alter_column("document", "is_public", server_default=None)


def downgrade() -> None:
    op.drop_column("document", "is_public")
