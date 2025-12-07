"""rename_assistant_tables

Revision ID: 2fb362971fc4
Revises: db3b5623e5a4
Create Date: 2025-12-07 22:57:29.964421

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2fb362971fc4"
down_revision: str | None = "db3b5623e5a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table("mcp_server", "assistant_mcp_servers")
    op.rename_table("openai_agent", "assistant_agents")
    op.rename_table("system_prompt", "assistant_system_prompt")


def downgrade() -> None:
    op.rename_table("assistant_mcp_servers", "mcp_server")
    op.rename_table("assistant_agents", "openai_agent")
    op.rename_table("assistant_system_prompt", "system_prompt")
