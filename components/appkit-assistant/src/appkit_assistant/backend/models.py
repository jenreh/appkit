import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import reflex as rx
from pydantic import BaseModel
from sqlalchemy.sql import func
from sqlmodel import Column, DateTime, Field

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
    AUTH_REQUIRED = "auth_required"  # user needs to authenticate (MCP)
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
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    original_text: str | None = None  # To store original text if edited
    editable: bool = False
    type: MessageType
    done: bool = False
    attachments: list[str] = []  # List of filenames for display


class ThinkingType(StrEnum):
    REASONING = "reasoning"
    TOOL_CALL = "tool_call"


class ThinkingStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


class Thinking(BaseModel):
    type: ThinkingType
    id: str  # reasoning_session_id or tool_id
    text: str
    status: ThinkingStatus = ThinkingStatus.IN_PROGRESS
    tool_name: str | None = None
    parameters: str | None = None
    result: str | None = None
    error: str | None = None


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
    requires_role: str | None = None


class Suggestion(BaseModel):
    prompt: str
    icon: str = ""


class UploadedFile(BaseModel):
    """Model for tracking uploaded files in the composer."""

    filename: str
    file_path: str
    size: int = 0


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
