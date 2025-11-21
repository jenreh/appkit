from enum import StrEnum

import reflex as rx
from pydantic import BaseModel
from sqlmodel import Field

from appkit_commons.database.entities import EncryptedString


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


class MCPServer(rx.Model, table=True):
    """Model for MCP (Model Context Protocol) server configuration."""

    __tablename__ = "mcp_server"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, max_length=100, nullable=False)
    description: str = Field(default="", max_length=255, nullable=True)
    url: str = Field(nullable=False)
    headers: str = Field(nullable=False, sa_type=EncryptedString)
    prompt: str = Field(default="", max_length=2000, nullable=True)
