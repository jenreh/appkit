"""Message Converter Protocol and vendor-specific adapters.

Provides a unified interface for converting internal Message objects
to vendor-specific API formats.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Protocol, TypeVar

from appkit_assistant.backend.schemas import Message, MessageType
from appkit_assistant.backend.system_prompt_cache import get_system_prompt

logger = logging.getLogger(__name__)

# Type variable for converted message format
T = TypeVar("T")


class MessageConverterProtocol(Protocol[T]):
    """Protocol for message format converters."""

    async def convert(
        self,
        messages: list[Message],
        mcp_prompt: str = "",
        file_blocks: list[dict[str, Any]] | None = None,
    ) -> T:
        """Convert messages to vendor-specific format.

        Args:
            messages: List of internal Message objects
            mcp_prompt: Optional MCP tool prompt to inject
            file_blocks: Optional file content blocks (for Claude)

        Returns:
            Vendor-specific message format
        """
        ...


class BaseMessageConverter(ABC):
    """Base class for message converters with shared utilities."""

    # Common role mapping
    ROLE_MAP = {
        MessageType.HUMAN: "user",
        MessageType.ASSISTANT: "assistant",
        MessageType.SYSTEM: "system",
    }

    def _build_mcp_section(self, mcp_prompt: str) -> str:
        """Build the MCP tool selection prompt section.

        Args:
            mcp_prompt: The MCP tool prompts

        Returns:
            Formatted MCP section or empty string
        """
        if not mcp_prompt:
            return ""
        return (
            "### Tool-Auswahlrichtlinien (Einbettung externer Beschreibungen)\n"
            f"{mcp_prompt}"
        )

    async def _get_system_prompt_with_mcp(self, mcp_prompt: str = "") -> str:
        """Get the system prompt with MCP section injected.

        Args:
            mcp_prompt: Optional MCP tool prompt

        Returns:
            Complete system prompt
        """
        system_prompt_template = await get_system_prompt()
        mcp_section = self._build_mcp_section(mcp_prompt)
        return system_prompt_template.format(mcp_prompts=mcp_section)

    @abstractmethod
    async def convert(
        self,
        messages: list[Message],
        mcp_prompt: str = "",
        file_blocks: list[dict[str, Any]] | None = None,
    ) -> Any:
        """Convert messages to vendor-specific format."""


class ClaudeMessageConverter(BaseMessageConverter):
    """Converter for Claude Messages API format."""

    async def convert(
        self,
        messages: list[Message],
        mcp_prompt: str = "",
        file_blocks: list[dict[str, Any]] | None = None,
    ) -> tuple[list[dict[str, Any]], str]:
        """Convert messages to Claude API format.

        Args:
            messages: List of internal Message objects
            mcp_prompt: Optional MCP tool prompt
            file_blocks: Optional file content blocks to attach to last user message

        Returns:
            Tuple of (claude_messages, system_prompt)
        """
        claude_messages = []

        for i, msg in enumerate(messages):
            if msg.type == MessageType.SYSTEM:
                continue  # System messages handled separately

            role = "user" if msg.type == MessageType.HUMAN else "assistant"

            # Build content
            content: list[dict[str, Any]] = []

            # For the last user message, attach files if present
            is_last_user = role == "user" and i == len(messages) - 1 and file_blocks

            if is_last_user and file_blocks:
                content.extend(file_blocks)

            # Add text content
            content.append({"type": "text", "text": msg.text})

            claude_messages.append(
                {
                    "role": role,
                    "content": content if len(content) > 1 else msg.text,
                }
            )

        # Build system prompt
        system_prompt = await self._get_system_prompt_with_mcp(mcp_prompt)

        return claude_messages, system_prompt


class OpenAIResponsesConverter(BaseMessageConverter):
    """Converter for OpenAI Responses API format."""

    def __init__(self, use_system_prompt: bool = True) -> None:
        """Initialize the converter.

        Args:
            use_system_prompt: Whether to prepend system prompt
        """
        self._use_system_prompt = use_system_prompt

    async def convert(
        self,
        messages: list[Message],
        mcp_prompt: str = "",
        file_blocks: list[dict[str, Any]] | None = None,  # noqa: ARG002
    ) -> list[dict[str, Any]]:
        """Convert messages to OpenAI Responses API format.

        Args:
            messages: List of internal Message objects
            mcp_prompt: Optional MCP tool prompt
            file_blocks: Not used for OpenAI Responses

        Returns:
            List of formatted messages with content arrays
        """
        input_messages = []

        # Add system message as first message
        if self._use_system_prompt:
            system_text = await self._get_system_prompt_with_mcp(mcp_prompt)
            input_messages.append(
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_text}],
                }
            )

        # Add conversation messages
        for msg in messages:
            if msg.type == MessageType.SYSTEM:
                continue  # System messages handled above

            role = "user" if msg.type == MessageType.HUMAN else "assistant"
            content_type = "input_text" if role == "user" else "output_text"
            input_messages.append(
                {"role": role, "content": [{"type": content_type, "text": msg.text}]}
            )

        return input_messages


class OpenAIChatConverter(BaseMessageConverter):
    """Converter for OpenAI Chat Completions API format.

    Note: This format merges consecutive same-role messages and uses
    simple string content instead of content arrays.
    """

    async def convert(
        self,
        messages: list[Message],
        mcp_prompt: str = "",  # noqa: ARG002
        file_blocks: list[dict[str, Any]] | None = None,  # noqa: ARG002
    ) -> list[dict[str, str]]:
        """Convert messages to OpenAI Chat Completions format.

        Merges consecutive user/assistant messages with blank line separator.

        Args:
            messages: List of internal Message objects
            mcp_prompt: Not used for chat completions
            file_blocks: Not used for chat completions

        Returns:
            List of role/content dicts
        """
        formatted: list[dict[str, str]] = []

        for msg in messages or []:
            if msg.type not in self.ROLE_MAP:
                continue

            role = self.ROLE_MAP[msg.type]

            # Merge consecutive user/assistant messages
            if formatted and role != "system" and formatted[-1]["role"] == role:
                formatted[-1]["content"] = formatted[-1]["content"] + "\n\n" + msg.text
            else:
                formatted.append({"role": role, "content": msg.text})

        return formatted


class GeminiMessageConverter(BaseMessageConverter):
    """Converter for Gemini GenAI API format.

    Note: Requires google.genai.types for Content/Part objects.
    """

    async def convert(
        self,
        messages: list[Message],
        mcp_prompt: str = "",
        file_blocks: list[dict[str, Any]] | None = None,  # noqa: ARG002
    ) -> tuple[list[Any], str | None]:
        """Convert messages to Gemini Content objects.

        Args:
            messages: List of internal Message objects
            mcp_prompt: Optional MCP tool prompt
            file_blocks: Not used for Gemini

        Returns:
            Tuple of (contents list, system_instruction)
        """
        # Import here to avoid hard dependency
        from google.genai import types  # noqa: PLC0415

        contents: list[types.Content] = []
        system_instruction: str | None = None

        # Build MCP section
        mcp_section = ""
        if mcp_prompt:
            mcp_section = f"\n\n{self._build_mcp_section(mcp_prompt)}"

        # Get system prompt
        system_prompt_template = await get_system_prompt()
        if system_prompt_template:
            system_instruction = system_prompt_template.format(mcp_prompts=mcp_section)

        for msg in messages:
            if msg.type == MessageType.SYSTEM:
                # Append to system instruction
                if system_instruction:
                    system_instruction += f"\n{msg.text}"
                else:
                    system_instruction = msg.text
            elif msg.type in (MessageType.HUMAN, MessageType.ASSISTANT):
                role = "user" if msg.type == MessageType.HUMAN else "model"
                contents.append(
                    types.Content(role=role, parts=[types.Part(text=msg.text)])
                )

        return contents, system_instruction
