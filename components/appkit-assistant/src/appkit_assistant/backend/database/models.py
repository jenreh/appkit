import json
from datetime import UTC, datetime
from typing import Any

import reflex as rx
from sqlalchemy import Index, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func
from sqlmodel import Column, DateTime, Field

from appkit_assistant.backend.schemas import AIModel, MCPAuthType, ThreadStatus
from appkit_commons.database.configuration import DatabaseConfig
from appkit_commons.database.entities import EncryptedString
from appkit_commons.registry import service_registry

db_config = service_registry().get(DatabaseConfig)
SECRET_VALUE = db_config.encryption_key.get_secret_value()


class EncryptedJSON(EncryptedString):
    """Custom type for storing encrypted JSON data."""

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is not None:
            value = json.dumps(value)
        return super().process_bind_param(value, dialect)

    def process_result_value(self, value: Any, dialect: Any) -> Any | None:
        value = super().process_result_value(value, dialect)
        if value is not None:
            return json.loads(value)
        return value


class MCPServer(rx.Model, table=True):
    """Model for MCP (Model Context Protocol) server configuration."""

    __tablename__ = "assistant_mcp_servers"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, max_length=100, nullable=False)
    description: str = Field(default="", max_length=255, nullable=True)
    url: str = Field(nullable=False)
    headers: str = Field(nullable=False, sa_type=EncryptedString)
    prompt: str = Field(default="", max_length=2000, nullable=True)

    # Authentication type
    auth_type: str = Field(default=MCPAuthType.NONE, nullable=False)

    # Optional discovery URL override
    discovery_url: str | None = Field(default=None, nullable=True)

    # OAuth client credentials (encrypted)
    oauth_client_id: str | None = Field(default=None, nullable=True)
    oauth_client_secret: str | None = Field(
        default=None, nullable=True, sa_type=EncryptedString
    )

    # Cached OAuth/Discovery metadata (read-only for user mostly)
    oauth_issuer: str | None = Field(default=None, nullable=True)
    oauth_authorize_url: str | None = Field(default=None, nullable=True)
    oauth_token_url: str | None = Field(default=None, nullable=True)
    oauth_scopes: str | None = Field(
        default=None, nullable=True
    )  # Space separated scopes

    # Timestamp when discovery was last successfully run
    oauth_discovered_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    active: bool = Field(default=True, nullable=False)
    required_role: str | None = Field(default=None, nullable=True)


class SystemPrompt(rx.Model, table=True):
    """Model for system prompt versioning and management.

    Each save creates a new immutable version. Supports up to 20,000 characters.
    """

    __tablename__ = "assistant_system_prompt"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=200, nullable=False)
    prompt: str = Field(max_length=20000, nullable=False)
    version: int = Field(nullable=False)
    user_id: int = Field(nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AssistantThread(rx.Model, table=True):
    """Model for storing chat threads in the database."""

    __tablename__ = "assistant_thread"

    id: int | None = Field(default=None, primary_key=True)
    thread_id: str = Field(unique=True, index=True, nullable=False)
    user_id: int = Field(index=True, nullable=False)
    title: str = Field(default="", nullable=False)
    state: str = Field(default=ThreadStatus.NEW, nullable=False)
    ai_model: str = Field(default="", nullable=False)
    active: bool = Field(default=False, nullable=False)
    messages: list[dict[str, Any]] = Field(default=[], sa_column=Column(EncryptedJSON))
    mcp_server_ids: list[int] = Field(
        default=[], sa_column=Column(ARRAY(Integer), nullable=False)
    )
    skill_openai_ids: list[str] = Field(
        default=[], sa_column=Column(ARRAY(String), nullable=False)
    )
    vector_store_id: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )


class AssistantMCPUserToken(rx.Model, table=True):
    """Model for storing user-specific OAuth tokens for MCP servers.

    Each user can have one token per MCP server. Tokens are encrypted at rest.
    """

    __tablename__ = "assistant_mcp_user_token"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, nullable=False)
    mcp_server_id: int = Field(
        index=True, nullable=False, foreign_key="assistant_mcp_servers.id"
    )

    # Tokens are encrypted at rest
    access_token: str = Field(nullable=False, sa_type=EncryptedString)
    refresh_token: str | None = Field(
        default=None, nullable=True, sa_type=EncryptedString
    )

    # Token expiry timestamp
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )


class AssistantFileUpload(rx.Model, table=True):
    """Model for tracking files uploaded to OpenAI for vector search.

    Each file is associated with a thread and vector store.
    """

    __tablename__ = "assistant_file_uploads"

    id: int | None = Field(default=None, primary_key=True)
    filename: str = Field(max_length=255, nullable=False)
    openai_file_id: str = Field(max_length=255, nullable=False, index=True)
    vector_store_id: str = Field(max_length=255, nullable=False, index=True)
    vector_store_name: str = Field(max_length=255, default="", nullable=False)
    thread_id: int = Field(
        index=True, nullable=False, foreign_key="assistant_thread.id"
    )
    user_id: int = Field(index=True, nullable=False)
    file_size: int = Field(default=0, nullable=False)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )


class UserPrompt(rx.Model, table=True):
    """Model for user-defined prompts.

    Handles are unique per user. Prompts can be shared with other users.
    Single table design with versioning (similar to SystemPrompt).
    """

    __tablename__ = "assistant_user_prompts"
    __table_args__ = (
        Index("ix_user_prompt_lookup", "user_id", "handle"),
        Index("ix_user_prompt_listing", "user_id", "is_latest"),
        Index("ix_user_prompt_shared", "is_shared", "is_latest"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, nullable=False)
    handle: str = Field(max_length=50, nullable=False)
    description: str = Field(default="", max_length=100, nullable=False)
    prompt_text: str = Field(max_length=20000, nullable=False)

    # Versioning fields
    version: int = Field(nullable=False)
    is_latest: bool = Field(default=False, nullable=False)
    is_shared: bool = Field(default=False, nullable=False)

    # Associated MCP server IDs (stored as integer array)
    mcp_server_ids: list[int] = Field(
        default=[], sa_column=Column(ARRAY(Integer), nullable=False)
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )


class Skill(rx.Model, table=True):
    """Model for OpenAI skill management.

    Stores metadata synced from the OpenAI Skills API alongside
    local administration state (active toggle, role restriction).
    The ``api_key_hash`` links the skill to the API key that was
    used to create/sync it so that skills can be filtered by model.
    """

    __tablename__ = "assistant_skills"

    id: int | None = Field(default=None, primary_key=True)
    openai_id: str = Field(unique=True, max_length=255, nullable=False)
    name: str = Field(max_length=100, nullable=False)
    description: str = Field(default="", max_length=500, nullable=True)
    default_version: str = Field(default="1", max_length=20, nullable=False)
    latest_version: str = Field(default="1", max_length=20, nullable=False)
    active: bool = Field(default=True, nullable=False)
    required_role: str | None = Field(default=None, nullable=True)
    api_key_hash: str | None = Field(
        default=None, max_length=64, nullable=True, index=True
    )
    last_synced: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )


class AssistantAIModel(rx.Model, table=True):
    """Database model for AI model configuration.

    Stores model metadata, capabilities, and processor assignment
    for dynamic admin-driven management.
    """

    __tablename__ = "assistant_ai_models"

    id: int | None = Field(default=None, primary_key=True)
    model_id: str = Field(unique=True, max_length=100, nullable=False)
    text: str = Field(max_length=100, nullable=False)
    icon: str = Field(default="codesandbox", max_length=50, nullable=False)
    model: str = Field(max_length=100, nullable=False)
    processor_type: str = Field(max_length=50, nullable=False)
    stream: bool = Field(default=False, nullable=False)
    temperature: float = Field(default=0.05, nullable=False)
    supports_tools: bool = Field(default=False, nullable=False)
    supports_attachments: bool = Field(default=False, nullable=False)
    supports_search: bool = Field(default=False, nullable=False)
    supports_skills: bool = Field(default=False, nullable=False)
    active: bool = Field(default=True, nullable=False)
    requires_role: str | None = Field(default=None, nullable=True)
    # Per-model API credentials (override global config when set)
    api_key: str | None = Field(default=None, nullable=True, sa_type=EncryptedString)
    base_url: str | None = Field(default=None, nullable=True, max_length=500)
    on_azure: bool = Field(default=False, nullable=False)
    enable_tracking: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )

    def to_ai_model(self) -> AIModel:
        """Convert DB record to runtime AIModel schema."""
        return AIModel(
            id=self.model_id,
            text=self.text,
            icon=self.icon,
            model=self.model,
            stream=self.stream,
            temperature=self.temperature,
            supports_tools=self.supports_tools,
            supports_attachments=self.supports_attachments,
            supports_search=self.supports_search,
            supports_skills=self.supports_skills,
            requires_role=self.requires_role,
            active=self.active,
        )


class UserSkillSelection(rx.Model, table=True):
    """Model for user-specific skill enable/disable preferences."""

    __tablename__ = "assistant_user_skill_selections"
    __table_args__ = (
        Index(
            "ix_user_skill_unique",
            "user_id",
            "skill_openai_id",
            unique=True,
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, nullable=False)
    skill_openai_id: str = Field(max_length=255, nullable=False, index=True)
    enabled: bool = Field(default=False, nullable=False)
