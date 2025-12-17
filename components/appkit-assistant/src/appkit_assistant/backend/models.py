from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import reflex as rx
from pydantic import BaseModel
from sqlalchemy.sql import func
from sqlmodel import Column, DateTime, Field

from appkit_commons.database.configuration import DatabaseConfig
from appkit_commons.database.entities import EncryptedJSON, EncryptedString
from appkit_commons.registry import service_registry

db_config = service_registry().get(DatabaseConfig)
SECRET_VALUE = db_config.encryption_key.get_secret_value()


class ChunkType(StrEnum):
    """Enum for chunk types."""

    TEXT = "text"  # default
    ANNOTATION = "annotation"  # for text annotations
    IMAGE = "image"
    IMAGE_PARTIAL = "image_partial"  # for streaming image generation
    THINKING = "thinking"  # when the model is "thinking" / reasoning
    THINKING_RESULT = "thinking_result"  # when the "thinking" is done
    ACTION = "action"  # when the user needs to take action
    TOOL_RESULT = "tool_result"  # result from a tool
    TOOL_CALL = "tool_call"  # calling a tool
    COMPLETION = "completion"  # when response generation is complete
    ERROR = "error"  # when an error occurs
    LIFECYCLE = "lifecycle"


class Chunk(BaseModel):
    """Model for text chunks."""

    type: ChunkType
    text: str
    chunk_metadata: dict[str, str] = {}


class ThreadStatus(StrEnum):
    """Enum for thread status."""

    NEW = "new"
    ACTIVE = "active"
    IDLE = "idle"
    WAITING = "waiting"
    ERROR = "error"
    DELETED = "deleted"
    ARCHIVED = "archived"


class MessageType(StrEnum):
    """Enum for message types."""

    HUMAN = "human"
    SYSTEM = "system"
    ASSISTANT = "assistant"
    TOOL_USE = "tool_use"
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"


class Message(BaseModel):
    text: str
    editable: bool = False
    type: MessageType
    done: bool = False


class AIModel(BaseModel):
    id: str
    text: str
    icon: str = "codesandbox"
    stream: bool = False
    tenant_key: str = ""
    project_id: int = 0
    model: str = "default"
    temperature: float = 0.05
    supports_tools: bool = False
    supports_attachments: bool = False
    keywords: list[str] = []
    disabled: bool = False


class Suggestion(BaseModel):
    prompt: str
    icon: str = ""


class ThreadModel(BaseModel):
    thread_id: str
    title: str = ""
    active: bool = False
    state: ThreadStatus = ThreadStatus.NEW
    prompt: str | None = ""
    messages: list[Message] = []
    ai_model: str = ""


class MCPAuthType(StrEnum):
    """Enum for MCP server authentication types."""

    NONE = "none"
    API_KEY = "api_key"
    OAUTH_DISCOVERY = "oauth_discovery"


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
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )
