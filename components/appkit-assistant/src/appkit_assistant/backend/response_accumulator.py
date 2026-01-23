import logging
import uuid
from typing import Any

from appkit_assistant.backend.models import (
    Chunk,
    ChunkType,
    Message,
    MessageType,
    Thinking,
    ThinkingStatus,
    ThinkingType,
)

logger = logging.getLogger(__name__)


class ResponseAccumulator:
    """
    Accumulates chunks from streaming response into structured data
    (Messages, Thinking items, etc.) for UI display.
    """

    def __init__(self):
        self.current_reasoning_session: str = ""
        self.current_tool_session: str = ""
        self.thinking_items: list[Thinking] = []
        self.image_chunks: list[Chunk] = []
        self.messages: list[Message] = []
        self.show_thinking: bool = False
        self.current_activity: str = ""

        # State for auth/errors
        self.pending_auth_server_id: str = ""
        self.pending_auth_server_name: str = ""
        self.pending_auth_url: str = ""
        self.auth_required: bool = False
        self.error: str | None = None

    @property
    def auth_required_data(self) -> dict[str, str]:
        """Return the auth data as a dictionary for compatibility."""
        return {
            "server_id": self.pending_auth_server_id,
            "server_name": self.pending_auth_server_name,
            "auth_url": self.pending_auth_url,
        }

    def attach_messages_ref(self, messages: list[Message]) -> None:
        """Attach a reference to the mutable messages list from state."""
        self.messages = messages

    def process_chunk(self, chunk: Chunk) -> None:
        """Process a single chunk and update internal state."""
        if chunk.type == ChunkType.TEXT:
            if self.messages and self.messages[-1].type == MessageType.ASSISTANT:
                self.messages[-1].text += chunk.text

        elif chunk.type in (ChunkType.THINKING, ChunkType.THINKING_RESULT):
            self._handle_reasoning_chunk(chunk)

        elif chunk.type in (
            ChunkType.TOOL_CALL,
            ChunkType.TOOL_RESULT,
            ChunkType.ACTION,
        ):
            self._handle_tool_chunk(chunk)

        elif chunk.type in (ChunkType.IMAGE, ChunkType.IMAGE_PARTIAL):
            self.image_chunks.append(chunk)

        elif chunk.type == ChunkType.COMPLETION:
            self.show_thinking = False

        elif chunk.type == ChunkType.AUTH_REQUIRED:
            self._handle_auth_required_chunk(chunk)

        elif chunk.type == ChunkType.ERROR:
            # We append it to the message text if it's not a hard error,
            # or creates a new message?
            # Existing logic was appending a new message.
            self.messages.append(Message(text=chunk.text, type=MessageType.ERROR))
            self.error = chunk.text

        else:
            logger.warning("Unhandled chunk type: %s", chunk.type)

    def _get_or_create_tool_session(self, chunk: Chunk) -> str:
        tool_id = chunk.chunk_metadata.get("tool_id")
        if tool_id:
            self.current_tool_session = tool_id
            return tool_id

        if chunk.type == ChunkType.TOOL_CALL:
            # Count existing tool calls
            tool_count = sum(
                1 for i in self.thinking_items if i.type == ThinkingType.TOOL_CALL
            )
            self.current_tool_session = f"tool_{tool_count}"
            return self.current_tool_session

        if self.current_tool_session:
            return self.current_tool_session

        # Fallback
        tool_count = sum(
            1 for i in self.thinking_items if i.type == ThinkingType.TOOL_CALL
        )
        self.current_tool_session = f"tool_{tool_count}"
        return self.current_tool_session

    def _handle_reasoning_chunk(self, chunk: Chunk) -> None:
        if chunk.type == ChunkType.THINKING:
            self.show_thinking = True
            self.current_activity = "Denke nach..."

        reasoning_session = self._get_or_create_reasoning_session(chunk)

        status = ThinkingStatus.IN_PROGRESS
        text = ""
        if chunk.type == ChunkType.THINKING:
            text = chunk.text
        elif chunk.type == ChunkType.THINKING_RESULT:
            status = ThinkingStatus.COMPLETED

        item = self._get_or_create_thinking_item(
            reasoning_session, ThinkingType.REASONING, text=text, status=status
        )

        if chunk.type == ChunkType.THINKING:
            # Check if this is a streaming delta (has "delta" in metadata)
            is_delta = chunk.chunk_metadata.get("delta") is not None
            if is_delta:
                # Streaming delta - append directly without separator
                item.text = (item.text or "") + chunk.text
            elif item.text and item.text != text:
                # Non-delta chunk with different text - append with newline
                item.text += f"\n{chunk.text}"
            else:
                # Initial text
                item.text = text
        elif chunk.type == ChunkType.THINKING_RESULT:
            item.status = ThinkingStatus.COMPLETED
            if chunk.text:
                item.text += f" {chunk.text}"

    def _get_or_create_reasoning_session(self, chunk: Chunk) -> str:
        reasoning_session = chunk.chunk_metadata.get("reasoning_session")
        if reasoning_session:
            return reasoning_session

        last_item = self.thinking_items[-1] if self.thinking_items else None

        should_create_new = (
            not self.current_reasoning_session
            or (last_item and last_item.type == ThinkingType.TOOL_CALL)
            or (
                last_item
                and last_item.type == ThinkingType.REASONING
                and last_item.status == ThinkingStatus.COMPLETED
            )
        )

        if should_create_new:
            self.current_reasoning_session = f"reasoning_{uuid.uuid4().hex[:8]}"

        return self.current_reasoning_session

    def _handle_tool_chunk(self, chunk: Chunk) -> None:
        tool_id = self._get_or_create_tool_session(chunk)

        tool_name = chunk.chunk_metadata.get("tool_name", "Unknown")
        server_label = chunk.chunk_metadata.get("server_label", "")
        # Use server_label.tool_name format if both available
        if server_label and tool_name and tool_name != "Unknown":
            display_name = f"{server_label}.{tool_name}"
        else:
            display_name = tool_name

        logger.debug(
            "Tool chunk received: type=%s, tool_id=%s, tool_name=%s, "
            "server_label=%s, display_name=%s",
            chunk.type,
            tool_id,
            tool_name,
            server_label,
            display_name,
        )

        # Only update activity display if we have a real tool name
        if (
            chunk.type == ChunkType.TOOL_CALL
            and display_name
            and display_name != "Unknown"
        ):
            self.current_activity = f"Nutze Werkzeug: {display_name}..."

        status = ThinkingStatus.IN_PROGRESS
        text = ""
        parameters = None
        result = None
        error = None

        if chunk.type == ChunkType.TOOL_CALL:
            parameters = chunk.chunk_metadata.get("parameters", chunk.text)
            text = chunk.chunk_metadata.get("description", "")
        elif chunk.type == ChunkType.TOOL_RESULT:
            # Check error flag from metadata - don't rely on text content
            # as valid results may contain words like "error" in data
            # Note: metadata values may be strings, so check for "True" string
            error_value = chunk.chunk_metadata.get("error")
            is_error = error_value is True or error_value == "True"
            status = ThinkingStatus.ERROR if is_error else ThinkingStatus.COMPLETED
            result = chunk.text
            if is_error:
                error = chunk.text
        else:
            text = chunk.text

        # Only pass tool_name if we have a real value
        effective_tool_name = display_name if display_name != "Unknown" else None

        item = self._get_or_create_thinking_item(
            tool_id,
            ThinkingType.TOOL_CALL,
            text=text,
            status=status,
            tool_name=effective_tool_name,
            parameters=parameters,
            result=result,
            error=error,
        )

        if chunk.type == ChunkType.TOOL_CALL:
            item.parameters = parameters
            item.text = text
            # Only update tool_name if we have a better value and item needs it
            if (
                display_name
                and display_name != "Unknown"
                and (not item.tool_name or item.tool_name == "Unknown")
            ):
                item.tool_name = display_name
            item.status = ThinkingStatus.IN_PROGRESS
        elif chunk.type == ChunkType.TOOL_RESULT:
            item.status = status
            item.result = result
            item.error = error
        elif chunk.type == ChunkType.ACTION:
            item.text += f"\n---\nAktion: {chunk.text}"

    def _get_or_create_thinking_item(
        self, item_id: str, thinking_type: ThinkingType, **kwargs: Any
    ) -> Thinking:
        for item in self.thinking_items:
            if item.type == thinking_type and item.id == item_id:
                return item

        new_item = Thinking(type=thinking_type, id=item_id, **kwargs)
        self.thinking_items.append(new_item)
        return new_item

    def _handle_auth_required_chunk(self, chunk: Chunk) -> None:
        self.pending_auth_server_id = chunk.chunk_metadata.get("server_id", "")
        self.pending_auth_server_name = chunk.chunk_metadata.get("server_name", "")
        self.pending_auth_url = chunk.chunk_metadata.get("auth_url", "")
        self.auth_required = True
