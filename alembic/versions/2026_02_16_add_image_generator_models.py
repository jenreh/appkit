"""Add image generator models table

Revision ID: a1b2c3d4e5f6
Revises: f9g0h1i2j3k4
Create Date: 2026-02-16 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import FernetEngine

from alembic import op  # noqa: I001
from app import configuration

# revision identifiers, used by Alembic.
revision: str = "g0h1i2j3k4l5"
down_revision: str | None = "f9g0h1i2j3k4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def get_encryption_key() -> str:
    """Get encryption key from environment or config."""
    config = configuration.app.database
    return str(config.encryption_key.get_secret_value())


# Processor type constants
_OPENAI = "appkit_imagecreator.backend.generators.openai.OpenAIImageGenerator"
_GOOGLE = "appkit_imagecreator.backend.generators.nano_banana.NanoBananaImageGenerator"
_BFL = (
    "appkit_imagecreator.backend.generators"
    ".black_forest_labs.BlackForestLabsImageGenerator"
)


def upgrade() -> None:
    encryption_key = get_encryption_key()

    op.create_table(
        "imagecreator_generator_models",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("model_id", sa.String(100), nullable=False, unique=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("processor_type", sa.String(255), nullable=False),
        sa.Column(
            "api_key",
            StringEncryptedType(sa.Unicode(), encryption_key, FernetEngine),
            nullable=False,
            default="",
        ),
        sa.Column("base_url", sa.String(), nullable=True),
        sa.Column("extra_config", sa.JSON(), nullable=True),
        sa.Column("required_role", sa.String(), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_imagecreator_generator_models_active",
        "imagecreator_generator_models",
        ["active"],
    )

    # Seed default generators (API keys are placeholders — update via UI)
    table = sa.table(
        "imagecreator_generator_models",
        sa.column("model_id", sa.String),
        sa.column("model", sa.String),
        sa.column("label", sa.String),
        sa.column("processor_type", sa.String),
        sa.column(
            "api_key",
            StringEncryptedType(sa.Unicode(), encryption_key, FernetEngine),
        ),
        sa.column("base_url", sa.String),
        sa.column("extra_config", sa.JSON),
        sa.column("active", sa.Boolean),
    )

    op.bulk_insert(
        table,
        [
            {
                "model_id": "gpt-image-1-mini",
                "model": "gpt-image-1-mini",
                "label": "OpenAI GPT-Image-1 mini (Azure)",
                "processor_type": _OPENAI,
                "api_key": "PLACEHOLDER",
                "base_url": None,
                "extra_config": {
                    "on_azure": True,
                    "moderation": "low",
                    "output_compression": 90,
                    "output_format": "jpeg",
                    "quality": "high",
                    "background": "auto",
                },
                "active": True,
            },
            {
                "model_id": "gpt-image-1.5",
                "model": "gpt-image-1.5",
                "label": "OpenAI GPT-Image-1.5 (Azure)",
                "processor_type": _OPENAI,
                "api_key": "PLACEHOLDER",
                "base_url": None,
                "extra_config": {
                    "on_azure": True,
                    "input_fidelity": "high",
                    "moderation": "low",
                    "output_compression": 95,
                    "output_format": "jpeg",
                    "quality": "high",
                    "background": "auto",
                },
                "active": True,
            },
            {
                "model_id": "nano-banana",
                "model": "gemini-2.5-flash-image",
                "label": "Google Nano Banana",
                "processor_type": _GOOGLE,
                "api_key": "PLACEHOLDER",
                "base_url": None,
                "extra_config": {},
                "active": True,
            },
            {
                "model_id": "nano-banana-pro",
                "model": "gemini-3-pro-image-preview",
                "label": "Google Nano Banana Pro",
                "processor_type": _GOOGLE,
                "api_key": "PLACEHOLDER",
                "base_url": None,
                "extra_config": {},
                "active": True,
            },
            {
                "model_id": "azure-flux1-kontext-pro",
                "model": "FLUX.1-Kontext-pro",
                "label": "Blackforest Labs FLUX.1-Kontext-pro (Azure)",
                "processor_type": _OPENAI,
                "api_key": "PLACEHOLDER",
                "base_url": None,
                "extra_config": {
                    "on_azure": True,
                    "moderation": "low",
                    "output_compression": 95,
                    "output_format": "jpeg",
                    "quality": "hd",
                    "background": "auto",
                },
                "active": True,
            },
            {
                "model_id": "azure-flux-2-pro",
                "model": "flux-2-pro",
                "label": "Blackforest Labs FLUX.2-pro (Azure)",
                "processor_type": _BFL,
                "api_key": "PLACEHOLDER",
                "base_url": None,
                "extra_config": {
                    "on_azure": True,
                    "safety_tolerance": 6,
                    "output_format": "jpeg",
                },
                "active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_imagecreator_generator_models_active",
        table_name="imagecreator_generator_models",
    )
    op.drop_table("imagecreator_generator_models")
