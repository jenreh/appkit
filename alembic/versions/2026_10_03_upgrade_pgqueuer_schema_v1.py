"""Upgrade pgqueuer schema for pgqueuer 1.x

pgqueuer >= 1.1 (appkit-commons[pgqueuer] extra) dequeues with
the ``attempts`` and ``slot`` columns and the ``failed`` status. Mirrors the
idempotent statements of ``pgq upgrade`` for pgqueuer 1.4.

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f7
Create Date: 2026-10-03 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"  # pragma: allowlist secret
down_revision: str | None = "a1b2c3d4e5f7"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ID_TABLES = ("pgqueuer", "pgqueuer_statistics", "pgqueuer_schedules")


def upgrade() -> None:
    op.execute(
        "ALTER TABLE pgqueuer ADD COLUMN IF NOT EXISTS attempts INT NOT NULL DEFAULT 0"
    )
    op.execute("ALTER TABLE pgqueuer ADD COLUMN IF NOT EXISTS slot BIGINT")
    op.execute("ALTER TYPE pgqueuer_status ADD VALUE IF NOT EXISTS 'failed'")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS pgqueuer_ep_prio_id_idx ON pgqueuer
            (entrypoint, priority DESC, id ASC) WHERE status = 'queued'
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS pgqueuer_ep_ea_idx ON pgqueuer
            (entrypoint, execute_after) WHERE status = 'queued'
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS pgqueuer_picked_slot_idx ON pgqueuer
            (entrypoint, slot) WHERE (status = 'picked' AND slot IS NOT NULL)
        """
    )
    for table in _ID_TABLES:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN id TYPE BIGINT")
        op.execute(
            f"""
            DO $$
            DECLARE
                seq TEXT := pg_get_serial_sequence('{table}', 'id');
            BEGIN
                IF seq IS NOT NULL THEN
                    EXECUTE format('ALTER SEQUENCE %s AS BIGINT', seq);
                END IF;
            END $$;
            """
        )


def downgrade() -> None:
    # Enum values and widened ids are kept: both are backwards compatible.
    op.execute("DROP INDEX IF EXISTS pgqueuer_picked_slot_idx")
    op.execute("DROP INDEX IF EXISTS pgqueuer_ep_ea_idx")
    op.execute("DROP INDEX IF EXISTS pgqueuer_ep_prio_id_idx")
    op.execute("ALTER TABLE pgqueuer DROP COLUMN IF EXISTS slot")
    op.execute("ALTER TABLE pgqueuer DROP COLUMN IF EXISTS attempts")
