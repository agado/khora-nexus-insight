"""add user_department M2M table, remove is_cross_department

Revision ID: 2a1b3c4d5e6f
Revises: 52c42983f7ce
Create Date: 2026-07-17 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2a1b3c4d5e6f"
down_revision: str | Sequence[str] | None = "52c42983f7ce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_department",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["department.id"]),
        sa.PrimaryKeyConstraint("user_id", "department_id"),
    )

    conn = op.get_bind()

    cross_users = conn.execute(
        sa.text('SELECT id FROM "user" WHERE is_cross_department = true')
    ).fetchall()
    dep_ids = [row[0] for row in conn.execute(sa.text("SELECT id FROM department")).fetchall()]
    for (uid,) in cross_users:
        for did in dep_ids:
            conn.execute(
                sa.text("INSERT INTO user_department (user_id, department_id) VALUES (:uid, :did)"),
                {"uid": uid, "did": did},
            )

    restricted_users = conn.execute(
        sa.text('SELECT id, department_id FROM "user" WHERE is_cross_department = false')
    ).fetchall()
    for uid, did in restricted_users:
        conn.execute(
            sa.text("INSERT INTO user_department (user_id, department_id) VALUES (:uid, :did)"),
            {"uid": uid, "did": did},
        )

    op.drop_column("user", "is_cross_department")


def downgrade() -> None:
    op.add_column(
        "user",
        sa.Column("is_cross_department", sa.Boolean(), nullable=False, server_default="false"),
    )
    conn = op.get_bind()
    all_dept_count = conn.execute(sa.text("SELECT count(*) FROM department")).scalar()
    users = conn.execute(sa.text('SELECT id FROM "user"')).fetchall()
    for (uid,) in users:
        user_depts = conn.execute(
            sa.text("SELECT department_id FROM user_department WHERE user_id = :uid"),
            {"uid": uid},
        ).fetchall()
        is_cross = len(user_depts) >= all_dept_count
        conn.execute(
            sa.text('UPDATE "user" SET is_cross_department = :cross WHERE id = :uid'),
            {"cross": is_cross, "uid": uid},
        )
    op.alter_column("user", "is_cross_department", server_default=None)
    op.drop_table("user_department")
