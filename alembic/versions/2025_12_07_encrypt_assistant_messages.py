"""encrypt assistant messages

Revision ID: 2ad7a1d57f3d
Revises: 2fb362971fc4
Create Date: 2025-12-07 23:29:05.597758

"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from cryptography.fernet import Fernet
from sqlalchemy.dialects import postgresql

from appkit_commons.database.entities import get_cipher_key

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2ad7a1d57f3d"
down_revision: str | None = "2fb362971fc4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Rename old column
    op.alter_column("assistant_thread", "messages", new_column_name="messages_old")

    # 2. Add new column
    op.add_column("assistant_thread", sa.Column("messages", sa.String(), nullable=True))

    # 3. Migrate data
    connection = op.get_bind()
    cipher_key = get_cipher_key()
    cipher = Fernet(cipher_key)

    # Select all rows
    result = connection.execute(
        sa.text("SELECT id, messages_old FROM assistant_thread")
    )
    for row in result:
        row_id = row[0]
        messages_json = row[1]

        if messages_json is not None:
            # Serialize to string
            json_str = json.dumps(messages_json)
            # Encrypt
            encrypted_str = cipher.encrypt(json_str.encode()).decode()

            # Update
            connection.execute(
                sa.text("UPDATE assistant_thread SET messages = :msg WHERE id = :id"),
                {"msg": encrypted_str, "id": row_id},
            )

    # 4. Drop old column
    op.drop_column("assistant_thread", "messages_old")


def downgrade() -> None:
    # Reverse
    op.alter_column(
        "assistant_thread", "messages", new_column_name="messages_encrypted"
    )
    op.add_column(
        "assistant_thread",
        sa.Column(
            "messages",
            postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
    )

    connection = op.get_bind()
    cipher_key = get_cipher_key()
    cipher = Fernet(cipher_key)

    result = connection.execute(
        sa.text("SELECT id, messages_encrypted FROM assistant_thread")
    )
    for row in result:
        row_id = row[0]
        encrypted_str = row[1]

        if encrypted_str is not None:
            try:
                decrypted_bytes = cipher.decrypt(encrypted_str.encode())
                json_str = decrypted_bytes.decode()

                connection.execute(
                    sa.text(
                        "UPDATE assistant_thread SET messages = :msg::json WHERE id = :id"
                    ),
                    {"msg": json_str, "id": row_id},
                )
            except Exception:  # noqa: S110
                pass

    op.drop_column("assistant_thread", "messages_encrypted")
