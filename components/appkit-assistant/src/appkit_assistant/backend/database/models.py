import json
from datetime import UTC, datetime
from typing import Any

import reflex as rx
from sqlalchemy.sql import func
from sqlmodel import Column, DateTime, Field

from appkit_assistant.backend.schemas import MCPAuthType, ThreadStatus
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
