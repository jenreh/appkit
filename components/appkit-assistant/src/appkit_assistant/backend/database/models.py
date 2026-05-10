import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from appkit_assistant.backend.schemas import AIModel, MCPAuthType, ThreadStatus
from appkit_commons.database.entities import ArrayType, Base, EncryptedString


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


class MCPServer(Base):
    """Model for MCP (Model Context Protocol) server configuration."""

    __tablename__ = "assistant_mcp_servers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), default="")
    url: Mapped[str] = mapped_column(nullable=False)
    headers: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    prompt: Mapped[str | None] = mapped_column(String(2000), default="")

    auth_type: Mapped[str] = mapped_column(default=MCPAuthType.NONE, nullable=False)
    discovery_url: Mapped[str | None] = mapped_column(default=None)

    oauth_client_id: Mapped[str | None] = mapped_column(default=None)
    oauth_client_secret: Mapped[str | None] = mapped_column(
        EncryptedString, default=None
    )

    oauth_issuer: Mapped[str | None] = mapped_column(default=None)
    oauth_authorize_url: Mapped[str | None] = mapped_column(default=None)
    oauth_token_url: Mapped[str | None] = mapped_column(default=None)
    oauth_scopes: Mapped[str | None] = mapped_column(default=None)

    oauth_discovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    required_role: Mapped[str | None] = mapped_column(default=None)

    inject_user_id: Mapped[bool] = mapped_column(default=True, nullable=False)


class SystemPrompt(Base):
    """Model for system prompt versioning and management."""

    __tablename__ = "assistant_system_prompt"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class AssistantThread(Base):
    """Model for storing chat threads in the database."""

    __tablename__ = "assistant_thread"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    thread_id: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    title: Mapped[str] = mapped_column(default="", nullable=False)
    state: Mapped[str] = mapped_column(default=ThreadStatus.NEW, nullable=False)
    ai_model: Mapped[str] = mapped_column(default="", nullable=False)
    active: Mapped[bool] = mapped_column(default=False, nullable=False)
    messages: Mapped[list[dict[str, Any]]] = mapped_column(
        EncryptedJSON, default=list, nullable=False
    )
    mcp_server_ids: Mapped[list[int]] = mapped_column(
        ArrayType(Integer), default=list, nullable=False
    )
    skill_openai_ids: Mapped[list[str]] = mapped_column(
        ArrayType(String), default=list, nullable=False
    )
    vector_store_id: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=func.now(),
        nullable=False,
    )


class AssistantMCPUserToken(Base):
    """Model for storing user-specific OAuth tokens for MCP servers."""

    __tablename__ = "assistant_mcp_user_token"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    mcp_server_id: Mapped[int] = mapped_column(index=True, nullable=False)

    access_token: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(EncryptedString, default=None)

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=func.now(),
        nullable=False,
    )


class AssistantFileUpload(Base):
    """Model for tracking files uploaded to OpenAI for vector search."""

    __tablename__ = "assistant_file_uploads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    openai_file_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    vector_store_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    vector_store_name: Mapped[str] = mapped_column(
        String(255), default="", nullable=False
    )
    thread_id: Mapped[int] = mapped_column(index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    file_size: Mapped[int] = mapped_column(default=0, nullable=False)
    ai_model: Mapped[str] = mapped_column(
        String(100), default="", nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=func.now(),
        nullable=False,
    )


class UserPrompt(Base):
    """Model for user-defined prompts."""

    __tablename__ = "assistant_user_prompts"
    __table_args__ = (
        Index("ix_user_prompt_lookup", "user_id", "handle"),
        Index("ix_user_prompt_listing", "user_id", "is_latest"),
        Index("ix_user_prompt_shared", "is_shared", "is_latest"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    handle: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)

    version: Mapped[int] = mapped_column(nullable=False)
    is_latest: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_shared: Mapped[bool] = mapped_column(default=False, nullable=False)

    mcp_server_ids: Mapped[list[int]] = mapped_column(
        ArrayType(Integer), default=list, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class Skill(Base):
    """Model for OpenAI skill management."""

    __tablename__ = "assistant_skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    openai_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), default=None)
    default_version: Mapped[str] = mapped_column(
        String(20), default="1", nullable=False
    )
    latest_version: Mapped[str] = mapped_column(String(20), default="1", nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    required_role: Mapped[str | None] = mapped_column(default=None)
    api_key_hash: Mapped[str | None] = mapped_column(
        String(64), default=None, index=True
    )
    last_synced: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class AssistantAIModel(Base):
    """Database model for AI model configuration."""

    __tablename__ = "assistant_ai_models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    text: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), default="codesandbox", nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    processor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    stream: Mapped[bool] = mapped_column(default=False, nullable=False)
    temperature: Mapped[float] = mapped_column(default=0.05, nullable=False)
    supports_tools: Mapped[bool] = mapped_column(default=False, nullable=False)
    supports_attachments: Mapped[bool] = mapped_column(default=False, nullable=False)
    supports_search: Mapped[bool] = mapped_column(default=False, nullable=False)
    supports_skills: Mapped[bool] = mapped_column(default=False, nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    requires_role: Mapped[str | None] = mapped_column(default=None)
    api_key: Mapped[str | None] = mapped_column(EncryptedString, default=None)
    base_url: Mapped[str | None] = mapped_column(String(500), default=None)
    on_azure: Mapped[bool] = mapped_column(default=False, nullable=False)
    enable_tracking: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
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


class UserSkillSelection(Base):
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

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    skill_openai_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
