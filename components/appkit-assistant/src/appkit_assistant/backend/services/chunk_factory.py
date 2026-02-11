"""Chunk Factory for creating standardized Chunk objects.

Provides unified chunk creation with consistent metadata handling
across all AI processors.
"""

from typing import Any

from appkit_assistant.backend.schemas import Chunk, ChunkType, ProcessingStatistics


class ChunkFactory:
    """Factory for creating Chunk objects with processor-specific metadata."""

    def __init__(self, processor_name: str) -> None:
        """Initialize the chunk factory.

        Args:
            processor_name: Name to include in chunk metadata (e.g., "claude_responses")
        """
        self._processor_name = processor_name

    @property
    def processor_name(self) -> str:
        """Get the processor name."""
        return self._processor_name

    def create(
        self,
        chunk_type: ChunkType,
        content: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> Chunk:
        """Create a Chunk with standardized metadata.

        Args:
            chunk_type: The type of chunk (TEXT, THINKING, TOOL_CALL, etc.)
            content: The text content of the chunk
            extra_metadata: Additional metadata to include (values will be stringified)

        Returns:
            A Chunk instance with processor metadata
        """
        metadata: dict[str, str] = {
            "processor": self._processor_name,
        }

        if extra_metadata:
            for key, value in extra_metadata.items():
                if value is not None:
                    metadata[key] = str(value)

        return Chunk(
            type=chunk_type,
            text=content,
            chunk_metadata=metadata,
        )

    def text(self, content: str, delta: str | None = None) -> Chunk:
        """Create a TEXT chunk.

        Args:
            content: The text content
            delta: Optional delta text for streaming

        Returns:
            A TEXT Chunk
        """
        metadata = {"delta": delta} if delta else None
        return self.create(ChunkType.TEXT, content, metadata)

    def thinking(
        self,
        content: str,
        reasoning_id: str | None = None,
        status: str = "in_progress",
        delta: str | None = None,
    ) -> Chunk:
        """Create a THINKING chunk.

        Args:
            content: The thinking content
            reasoning_id: Optional reasoning session ID
            status: Status of the thinking (starting, in_progress, completed)
            delta: Optional delta text for streaming

        Returns:
            A THINKING Chunk
        """
        metadata: dict[str, Any] = {"status": status}
        if reasoning_id:
            metadata["reasoning_id"] = reasoning_id
        if delta is not None:
            metadata["delta"] = delta
        return self.create(ChunkType.THINKING, content, metadata)

    def thinking_result(
        self,
        content: str,
        reasoning_id: str | None = None,
    ) -> Chunk:
        """Create a THINKING_RESULT chunk.

        Args:
            content: The result content
            reasoning_id: Optional reasoning session ID

        Returns:
            A THINKING_RESULT Chunk
        """
        metadata: dict[str, Any] = {"status": "completed"}
        if reasoning_id:
            metadata["reasoning_id"] = reasoning_id
        return self.create(ChunkType.THINKING_RESULT, content, metadata)

    def tool_call(
        self,
        content: str,
        tool_name: str,
        tool_id: str,
        server_label: str | None = None,
        status: str = "starting",
        reasoning_session: str | None = None,
    ) -> Chunk:
        """Create a TOOL_CALL chunk.

        Args:
            content: Description of the tool call
            tool_name: Name of the tool being called
            tool_id: Unique identifier for this tool call
            server_label: Optional MCP server label
            status: Status of the tool call
            reasoning_session: Optional reasoning session ID

        Returns:
            A TOOL_CALL Chunk
        """
        metadata: dict[str, Any] = {
            "tool_name": tool_name,
            "tool_id": tool_id,
            "status": status,
        }
        if server_label:
            metadata["server_label"] = server_label
        if reasoning_session:
            metadata["reasoning_session"] = reasoning_session
        return self.create(ChunkType.TOOL_CALL, content, metadata)

    def tool_result(
        self,
        content: str,
        tool_id: str,
        status: str = "completed",
        is_error: bool = False,
        reasoning_session: str | None = None,
        tool_name: str | None = None,
        server_label: str | None = None,
    ) -> Chunk:
        """Create a TOOL_RESULT chunk.

        Args:
            content: The tool result content
            tool_id: The tool call ID this result corresponds to
            status: Status of the result
            is_error: Whether the result is an error
            reasoning_session: Optional reasoning session ID
            tool_name: Optional tool name for display
            server_label: Optional server label for MCP tools

        Returns:
            A TOOL_RESULT Chunk
        """
        metadata: dict[str, Any] = {
            "tool_id": tool_id,
            "status": status,
            "error": is_error,
        }
        if reasoning_session:
            metadata["reasoning_session"] = reasoning_session
        if tool_name:
            metadata["tool_name"] = tool_name
        if server_label:
            metadata["server_label"] = server_label
        return self.create(ChunkType.TOOL_RESULT, content, metadata)

    def lifecycle(self, stage: str, extra: dict[str, Any] | None = None) -> Chunk:
        """Create a LIFECYCLE chunk.

        Args:
            stage: The lifecycle stage (created, in_progress, done)
            extra: Additional metadata

        Returns:
            A LIFECYCLE Chunk
        """
        metadata: dict[str, Any] = {"stage": stage}
        if extra:
            metadata.update(extra)
        return self.create(ChunkType.LIFECYCLE, stage, metadata)

    def completion(
        self,
        status: str = "response_complete",
        statistics: ProcessingStatistics | None = None,
    ) -> Chunk:
        """Create a COMPLETION chunk.

        Args:
            status: The completion status
            statistics: Optional processing statistics

        Returns:
            A COMPLETION Chunk
        """
        chunk = self.create(
            ChunkType.COMPLETION,
            "Response generation completed",
            {"status": status},
        )
        if statistics:
            chunk.statistics = statistics
        return chunk

    def error(self, message: str, error_type: str = "unknown") -> Chunk:
        """Create an ERROR chunk.

        Args:
            message: The error message
            error_type: The type of error

        Returns:
            An ERROR Chunk
        """
        return self.create(
            ChunkType.ERROR,
            message,
            {"error_type": error_type},
        )

    def auth_required(
        self,
        server_name: str,
        server_id: str | None = None,
        auth_url: str = "",
        state: str = "",
    ) -> Chunk:
        """Create an AUTH_REQUIRED chunk.

        Args:
            server_name: Name of the server requiring auth
            server_id: Optional server ID
            auth_url: The authorization URL
            state: The OAuth state parameter

        Returns:
            An AUTH_REQUIRED Chunk
        """
        metadata: dict[str, Any] = {
            "server_name": server_name,
            "auth_url": auth_url,
            "state": state,
        }
        if server_id:
            metadata["server_id"] = server_id
        return self.create(
            ChunkType.AUTH_REQUIRED,
            f"{server_name} benötigt Ihre Autorisierung",
            metadata,
        )

    def annotation(self, text: str, annotation_data: dict[str, Any]) -> Chunk:
        """Create an ANNOTATION chunk.

        Args:
            text: The annotation text
            annotation_data: Annotation metadata

        Returns:
            An ANNOTATION Chunk
        """
        return self.create(ChunkType.ANNOTATION, text, annotation_data)
