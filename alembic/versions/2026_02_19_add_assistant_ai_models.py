"""Add assistant_ai_models table with credentials

Revision ID: f3g4h5i6j7k8
Revises: e2ed9f7ab897
Create Date: 2026-02-19 10:00:00.000000

"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3g4h5i6j7k8"
down_revision: str | None = "e2ed9f7ab897"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NOW = datetime.now(UTC)

# Seed data: (
#   model_id, text, icon, model, processor_type,
#   stream, temperature,
#   supports_tools, supports_attachments, supports_search, supports_skills,
#   active, requires_role,
#   api_key, base_url, on_azure
# )
_SEED_MODELS = [
    # OpenAI models
    (
        "gpt-5-mini",
        "GPT 5 Mini",
        "openai",
        "gpt-5-mini",
        "openai",
        True,
        1.0,
        True,
        True,
        True,
        False,
        True,
        "assistant-basic_models",
        None,
        None,
        False,
    ),
    (
        "gpt-5.1",
        "GPT 5.1",
        "openai",
        "gpt-5.1",
        "openai",
        True,
        1.0,
        True,
        True,
        True,
        False,
        True,
        "assistant-advanced_models",
        None,
        None,
        False,
    ),
    # OpenAI with skills
    (
        "gpt-5.2",
        "GPT 5.2",
        "openai",
        "gpt-5.2",
        "openai_skills",
        True,
        1.0,
        True,
        True,
        True,
        True,
        True,
        "assistant-advanced_models",
        None,
        None,
        False,
    ),
    # Perplexity models
    (
        "sonar",
        "Perplexity Sonar",
        "perplexity",
        "sonar",
        "perplexity",
        True,
        0.05,
        False,
        False,
        False,
        False,
        True,
        "perplexity_models",
        None,
        None,
        False,
    ),
    (
        "sonar-pro",
        "Perplexity Sonar Pro",
        "perplexity",
        "sonar-pro",
        "perplexity",
        True,
        0.05,
        False,
        False,
        False,
        False,
        True,
        "perplexity_models",
        None,
        None,
        False,
    ),
    (
        "sonar-deep-research",
        "Perplexity Deep Research",
        "perplexity",
        "sonar-deep-research",
        "perplexity",
        True,
        0.05,
        False,
        False,
        False,
        False,
        True,
        "perplexity_models",
        None,
        None,
        False,
    ),
    (
        "sonar-reasoning",
        "Perplexity Reasoning",
        "perplexity",
        "sonar-reasoning",
        "perplexity",
        True,
        0.05,
        False,
        False,
        False,
        False,
        True,
        "perplexity_models",
        None,
        None,
        False,
    ),
    # Anthropic Claude models
    (
        "claude-haiku-4.5",
        "Claude 4.5 Haiku",
        "anthropic",
        "claude-haiku-4-5",
        "claude",
        True,
        1.0,
        True,
        False,
        False,
        False,
        True,
        "assistant-basic_models",
        None,
        None,
        False,
    ),
    (
        "claude-sonnet-4.5",
        "Claude 4.5 Sonnet",
        "anthropic",
        "claude-sonnet-4-5",
        "claude",
        True,
        1.0,
        True,
        False,
        False,
        False,
        False,
        "assistant-advanced_models",
        None,
        None,
        False,
    ),
    # Google Gemini models
    (
        "gemini-3-pro-preview",
        "Gemini 3 Pro",
        "googlegemini",
        "gemini-3-pro-preview",
        "gemini",
        True,
        0.05,
        True,
        False,
        False,
        False,
        True,
        "assistant-advanced_models",
        None,
        None,
        False,
    ),
    (
        "gemini-3-flash-preview",
        "Gemini 3 Flash",
        "googlegemini",
        "gemini-3-flash-preview",
        "gemini",
        True,
        0.05,
        True,
        False,
        False,
        False,
        True,
        "assistant-basic_models",
        None,
        None,
        False,
    ),
]


def upgrade() -> None:
    op.create_table(
        "assistant_ai_models",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("model_id", sa.String(length=100), nullable=False, unique=True),
        sa.Column("text", sa.String(length=100), nullable=False),
        sa.Column(
            "icon",
            sa.String(length=50),
            nullable=False,
            server_default="codesandbox",
        ),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("processor_type", sa.String(length=50), nullable=False),
        sa.Column("stream", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "temperature",
            sa.Float(),
            nullable=False,
            server_default="0.05",
        ),
        sa.Column(
            "supports_tools",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "supports_attachments",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "supports_search",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "supports_skills",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("requires_role", sa.String(), nullable=True),
        sa.Column("api_key", sa.Text(), nullable=True),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column(
            "on_azure",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # Seed with current hardcoded models
    ai_models_table = sa.table(
        "assistant_ai_models",
        sa.column("model_id", sa.String),
        sa.column("text", sa.String),
        sa.column("icon", sa.String),
        sa.column("model", sa.String),
        sa.column("processor_type", sa.String),
        sa.column("stream", sa.Boolean),
        sa.column("temperature", sa.Float),
        sa.column("supports_tools", sa.Boolean),
        sa.column("supports_attachments", sa.Boolean),
        sa.column("supports_search", sa.Boolean),
        sa.column("supports_skills", sa.Boolean),
        sa.column("active", sa.Boolean),
        sa.column("requires_role", sa.String),
        sa.column("api_key", sa.Text),
        sa.column("base_url", sa.String),
        sa.column("on_azure", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    op.bulk_insert(
        ai_models_table,
        [
            {
                "model_id": row[0],
                "text": row[1],
                "icon": row[2],
                "model": row[3],
                "processor_type": row[4],
                "stream": row[5],
                "temperature": row[6],
                "supports_tools": row[7],
                "supports_attachments": row[8],
                "supports_search": row[9],
                "supports_skills": row[10],
                "active": row[11],
                "requires_role": row[12],
                "api_key": row[13],
                "base_url": row[14],
                "on_azure": row[15],
                "created_at": _NOW,
            }
            for row in _SEED_MODELS
        ],
    )


def downgrade() -> None:
    op.drop_table("assistant_ai_models")
