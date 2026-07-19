"""add_audit_log trigger (PostgreSQL)

Make audit_log truly append-only via BEFORE UPDATE/DELETE trigger.
No-op on SQLite (dialect guard).

Revision ID: 87ce70d45d0f
Revises:
Create Date: 2026-07-19 04:02:44.039334

"""

from collections.abc import Sequence

from alembic import op

revision: str = "87ce70d45d0f"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION reject_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only: UPDATE and DELETE are not permitted';
END;
$$ LANGUAGE plpgsql;
"""

DROP_TRIGGER_STMT = "DROP TRIGGER IF EXISTS trg_reject_audit_log_modification ON audit_log;"

CREATE_TRIGGER_STMT = """
CREATE TRIGGER trg_reject_audit_log_modification
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW
    EXECUTE FUNCTION reject_audit_log_modification();
"""

DROP_TRIGGER = "DROP TRIGGER IF EXISTS trg_reject_audit_log_modification ON audit_log;"
DROP_FUNCTION = "DROP FUNCTION IF EXISTS reject_audit_log_modification();"


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return
    op.execute(TRIGGER_FUNCTION)
    op.execute(DROP_TRIGGER_STMT)
    op.execute(CREATE_TRIGGER_STMT)


def downgrade() -> None:
    if not _is_postgres():
        return
    op.execute(DROP_TRIGGER)
    op.execute(DROP_FUNCTION)
