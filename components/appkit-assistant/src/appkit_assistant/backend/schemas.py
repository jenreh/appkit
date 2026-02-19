import uuid
from enum import StrEnum

from pydantic import BaseModel
from sqlmodel import Field


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
    PROCESSING = "processing"  # file processing status
    COMPLETION = "completion"  # when response generation is complete
    AUTH_REQUIRED = "auth_required"  # user needs to authenticate (MCP)
    ERROR = "error"  # when an error occurs
    LIFECYCLE = "lifecycle"


class ProcessingStatistics(BaseModel):
    """Statistics about the processing request."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    tool_uses: dict[str, int] = {}
    model: str | None = None
    processor: str | None = None


class Chunk(BaseModel):
    """Model for text chunks."""

    type: ChunkType
    text: str
    chunk_metadata: dict[str, str | None] = {}
    statistics: ProcessingStatistics | None = None


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
    annotations: list[str] = []  # List of file citations/annotations


class ThinkingType(StrEnum):
    REASONING = "reasoning"
    TOOL_CALL = "tool_call"
    PROCESSING = "processing"


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
    supports_search: bool = False
    supports_skills: bool = False
    keywords: list[str] = []
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
    mcp_server_ids: list[int] = []
    skill_openai_ids: list[str] = []


class MCPAuthType(StrEnum):
    """Enum for MCP server authentication types."""

    NONE = "none"
    API_KEY = "api_key"
    OAUTH_DISCOVERY = "oauth_discovery"


class CommandDefinition(BaseModel):
    """Model for slash command definitions in the command palette."""

    id: str  # Unique command identifier (e.g., "teach", "evaluate")
    label: str  # Display label (e.g., "/teach")
    description: str = ""  # Optional description shown in palette
    icon: str = ""  # Optional icon name
    is_editable: bool = False  # True only for user's own prompts
    user_id: int = 0  # Owner user ID for prompts
    mcp_server_ids: list[int] = []  # MCP servers to auto-select
