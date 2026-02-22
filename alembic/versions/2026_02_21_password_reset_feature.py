"""password_reset_feature

Revision ID: cad2e9f4g5h6
Revises: d2e3f4g5h6i7
Create Date: 2026-02-21 15:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cad2e9f4g5h6"
down_revision: str | None = "d2e3f4g5h6i7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create password reset related tables."""

    # Create password reset tokens table
    op.create_table(
        "auth_password_reset_tokens",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.INTEGER(), nullable=False),
        sa.Column("token", sa.VARCHAR(length=64), nullable=False),
        sa.Column("email", sa.VARCHAR(length=200), nullable=True),
        sa.Column("reset_type", sa.VARCHAR(length=50), nullable=False),
        sa.Column("is_used", sa.BOOLEAN(), nullable=False, server_default="false"),
        sa.Column("expires_at", sa.TIMESTAMP(), nullable=False),
        sa.Column(
            "created",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth_users.id"],
            name="fk_password_reset_tokens_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_password_reset_tokens"),
        sa.UniqueConstraint("token", name="uq_password_reset_tokens_token"),
    )

    # Create indexes for password reset tokens
    op.create_index(
        "idx_password_reset_tokens_token_expires",
        "auth_password_reset_tokens",
        ["token", "expires_at"],
    )
    op.create_index(
        "idx_password_reset_tokens_user_id_used",
        "auth_password_reset_tokens",
        ["user_id", "is_used"],
    )

    # Create password history table
    op.create_table(
        "auth_password_history",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.INTEGER(), nullable=False),
        sa.Column("password_hash", sa.VARCHAR(length=200), nullable=False),
        sa.Column(
            "changed_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("change_reason", sa.VARCHAR(length=50), nullable=True),
        sa.Column(
            "created",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth_users.id"],
            name="fk_password_history_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_password_history"),
        sa.UniqueConstraint(
            "user_id", "password_hash", name="uq_password_history_user_hash"
        ),
    )

    # Create index for password history
    op.create_index(
        "idx_password_history_user_id_changed",
        "auth_password_history",
        ["user_id", "changed_at"],
    )

    # Create password reset requests table for rate limiting
    op.create_table(
        "auth_password_reset_requests",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("email", sa.VARCHAR(length=200), nullable=False),
        sa.Column("ip_address", sa.VARCHAR(length=45), nullable=True),
        sa.Column(
            "created",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_password_reset_requests"),
    )


def downgrade() -> None:
    """Drop password reset related tables."""
    op.drop_table("auth_password_reset_requests")

    op.drop_index(
        "idx_password_history_user_id_changed", table_name="auth_password_history"
    )
    op.drop_table("auth_password_history")

    op.drop_index(
        "idx_password_reset_tokens_user_id_used",
        table_name="auth_password_reset_tokens",
    )
    op.drop_index(
        "idx_password_reset_tokens_token_expires",
        table_name="auth_password_reset_tokens",
    )
    op.drop_table("auth_password_reset_tokens")
