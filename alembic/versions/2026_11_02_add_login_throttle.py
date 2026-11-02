"""Add the login throttle table.

Failed password logins are counted per hashed email and client address in
``auth_login_throttle`` (appkit-user >= 1.18), so the limit holds across
workers and restarts. Keys are SHA-256 hex digests; no email or address is
stored in clear text.

Revision ID: 3437afddcf55
Revises: b3c4d5e6f7a8
Create Date: 2026-11-02 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3437afddcf55"  # pragma: allowlist secret
down_revision: str | None = "b3c4d5e6f7a8"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "auth_login_throttle"
_INDEX = "idx_login_throttle_window_started"


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table(_TABLE):
        return
    op.create_table(
        _TABLE,
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("key", name="pk_auth_login_throttle"),
    )
    op.create_index(_INDEX, _TABLE, ["window_started_at"])


def downgrade() -> None:
    op.drop_index(_INDEX, table_name=_TABLE)
    op.drop_table(_TABLE)
