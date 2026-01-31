"""add_mcp_user_tokens_and_oauth_credentials

Adds the assistant_mcp_user_token table for storing per-user OAuth tokens
and adds oauth_client_id/oauth_client_secret to assistant_mcp_servers.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-10 10:00:00.000000

"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import FernetEngine

from alembic import op
from app import configuration

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def get_encryption_key() -> str:
    """Get encryption key from environment or config."""
    config = configuration.app.database
    return config.encryption_key.get_secret_value()


def upgrade() -> None:
    encryption_key = get_encryption_key()

    # Create assistant_mcp_user_token table
    op.create_table(
        "assistant_mcp_user_token",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("mcp_server_id", sa.Integer(), nullable=False),
        sa.Column(
            "access_token",
            StringEncryptedType(sa.String, encryption_key, FernetEngine),
            nullable=False,
        ),
        sa.Column(
            "refresh_token",
            StringEncryptedType(sa.String, encryption_key, FernetEngine),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["mcp_server_id"],
            ["assistant_mcp_servers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_assistant_mcp_user_token_user_id",
        "assistant_mcp_user_token",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_assistant_mcp_user_token_mcp_server_id",
        "assistant_mcp_user_token",
        ["mcp_server_id"],
        unique=False,
    )
    # Unique constraint: one token per user per server
    op.create_index(
        "ix_assistant_mcp_user_token_user_server",
        "assistant_mcp_user_token",
        ["user_id", "mcp_server_id"],
        unique=True,
    )

    # Add OAuth client credentials to assistant_mcp_servers
    op.add_column(
        "assistant_mcp_servers",
        sa.Column("oauth_client_id", sa.String(), nullable=True),
    )
    op.add_column(
        "assistant_mcp_servers",
        sa.Column(
            "oauth_client_secret",
            StringEncryptedType(sa.String, encryption_key, FernetEngine),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # Remove OAuth client credentials from assistant_mcp_servers
    op.drop_column("assistant_mcp_servers", "oauth_client_secret")
    op.drop_column("assistant_mcp_servers", "oauth_client_id")

    # Drop assistant_mcp_user_token table
    op.drop_index(
        "ix_assistant_mcp_user_token_user_server",
        table_name="assistant_mcp_user_token",
    )
    op.drop_index(
        "ix_assistant_mcp_user_token_mcp_server_id",
        table_name="assistant_mcp_user_token",
    )
    op.drop_index(
        "ix_assistant_mcp_user_token_user_id",
        table_name="assistant_mcp_user_token",
    )
    op.drop_table("assistant_mcp_user_token")
