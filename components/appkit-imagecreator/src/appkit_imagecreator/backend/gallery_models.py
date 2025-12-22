"""Database models and repository for the image gallery.

This module provides the GeneratedImage model and GeneratedImageRepository
for persisting user-generated images.
"""

from datetime import UTC, datetime
from typing import Any

import reflex as rx
from pydantic import BaseModel, computed_field
from sqlalchemy import JSON, Column, DateTime, LargeBinary
from sqlmodel import Field

from appkit_commons.configuration.configuration import ReflexConfig
from appkit_commons.registry import service_registry


def get_image_api_base_url() -> str:
    """Get the base URL for the image API based on configuration.

    Returns the backend URL with port for development (separate ports),
    or just the deploy URL for production (single port).
    """
    reflex_config = service_registry().get(ReflexConfig)
    if reflex_config.single_port:
        return reflex_config.deploy_url
    return f"{reflex_config.deploy_url}:{reflex_config.backend_port}"


class GeneratedImage(rx.Model, table=True):
    """Model for storing generated images in the database.

    Stores image metadata including prompt, style, model configuration,
    and the binary image data as a BLOB.
    """

    __tablename__ = "imagecreator_generated_images"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, nullable=False)
    prompt: str = Field(max_length=4000, nullable=False)
    enhanced_prompt: str | None = Field(default=None, max_length=8000, nullable=True)
    style: str | None = Field(default=None, max_length=100, nullable=True)
    model: str = Field(max_length=100, nullable=False)
    image_data: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    content_type: str = Field(max_length=50, nullable=False, default="image/png")
    width: int = Field(nullable=False)
    height: int = Field(nullable=False)
    quality: str | None = Field(default=None, max_length=20, nullable=True)
    config: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )


class GeneratedImageModel(BaseModel):
    """Pydantic model for GeneratedImage data transfer (without binary data)."""

    id: int
    user_id: int
    prompt: str
    enhanced_prompt: str | None = None
    style: str | None = None
    model: str
    content_type: str = "image/png"
    width: int
    height: int
    quality: str | None = None
    config: dict[str, Any] | None = None
    created_at: datetime | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def image_url(self) -> str:
        """Generate the API URL to download the image."""
        base_url = get_image_api_base_url()
        return f"{base_url}/api/images/{self.id}"
