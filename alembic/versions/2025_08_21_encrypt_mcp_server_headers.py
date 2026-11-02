"""encrypt_mcp_server_headers

Revision ID: 4149573f35c1
Revises: 1ade698f1234
Create Date: 2025-08-21 17:07:50.319425

"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import FernetEngine

from alembic import op
from app import configuration

# Configure logging for migration
logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "4149573f35c1"
down_revision: str | None = "1ade698f1234"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def get_encryption_key() -> str:
    """Get encryption key from environment or config."""
    config = configuration.app.database
    if config is None:
        raise RuntimeError("Database configuration is missing")
    return config.encryption_key.get_secret_value()


def upgrade() -> None:
    encryption_key = get_encryption_key()

    op.add_column(
        "mcp_server",
        sa.Column(
            "xheaders",
            StringEncryptedType(sa.Unicode(), encryption_key, FernetEngine),
            nullable=True,  # Start as nullable
        ),
    )

    # select all rows and convert headers to encrypted string
    bind = op.get_bind()
    result = bind.execute(sa.text("SELECT id, headers FROM mcp_server"))
    for row in result:
        headers = row.headers or {}
        encrypted_headers = StringEncryptedType(
            sa.Unicode(), encryption_key, FernetEngine
        ).process_bind_param(headers, bind.dialect)
        bind.execute(
            sa.text(
                "UPDATE mcp_server SET xheaders = :encrypted_headers WHERE id = :id"
            ),
            {"encrypted_headers": encrypted_headers, "id": row.id},
        )

    # Now make the column NOT NULL after populating it
    op.alter_column("mcp_server", "xheaders", nullable=False)

    op.drop_column("mcp_server", "headers")
    op.alter_column(
        "mcp_server",
        "xheaders",
        new_column_name="headers",
        existing_type=StringEncryptedType(sa.Unicode(), encryption_key, FernetEngine),
    )


def downgrade() -> None:
    """Convert headers column back from String to JSON."""
    encryption_key = get_encryption_key()

    # First, rename the current headers column to a temporary name
    op.alter_column(
        "mcp_server",
        "headers",
        new_column_name="xheaders",
        existing_type=StringEncryptedType(sa.Unicode(), encryption_key, FernetEngine),
    )

    # Add the new headers column as JSON
    op.add_column(
        "mcp_server",
        sa.Column("headers", sa.JSON(), nullable=True),
    )

    # Convert encrypted data back to JSON
    bind = op.get_bind()
    result = bind.execute(sa.text("SELECT id, xheaders FROM mcp_server"))
    for row in result:
        if row.xheaders:
            try:
                # Try to decrypt the headers
                decrypted_headers = StringEncryptedType(
                    sa.Unicode(), encryption_key, FernetEngine
                ).process_result_value(row.xheaders, bind.dialect)
                bind.execute(
                    sa.text("UPDATE mcp_server SET headers = :headers WHERE id = :id"),
                    {"headers": decrypted_headers, "id": row.id},
                )
            except Exception as e:
                # If decryption fails, set headers to empty dict
                logger.warning("Could not decrypt headers for row %s: %s", row.id, e)
                logger.warning("Setting headers to empty dict for row %s", row.id)
                bind.execute(
                    sa.text("UPDATE mcp_server SET headers = :headers WHERE id = :id"),
                    {"headers": "{}", "id": row.id},
                )

    # Drop the temporary encrypted column
    op.drop_column("mcp_server", "xheaders")
