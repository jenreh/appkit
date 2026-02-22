"""Tests for message converter services."""

from unittest.mock import AsyncMock, patch

import pytest

from appkit_assistant.backend.schemas import Message, MessageType
from appkit_assistant.backend.services.message_converter import (
    ClaudeMessageConverter,
    GeminiMessageConverter,
    OpenAIChatConverter,
    OpenAIResponsesConverter,
)


class TestClaudeMessageConverter:
    """Test suite for ClaudeMessageConverter."""

    @pytest.mark.asyncio
    async def test_convert_simple_messages(self) -> None:
        """convert() transforms messages to Claude format."""
        converter = ClaudeMessageConverter()
        messages = [
            Message(text="Hello", type=MessageType.HUMAN),
            Message(text="Hi there!", type=MessageType.ASSISTANT),
        ]

        with patch(
            "appkit_assistant.backend.services.message_converter.get_system_prompt",
            new_callable=AsyncMock,
            return_value="System prompt: {mcp_prompts}",
        ):
            claude_msgs, system_prompt = await converter.convert(messages)

        assert len(claude_msgs) == 2
        assert claude_msgs[0]["role"] == "user"
        assert claude_msgs[0]["content"] == "Hello"
        assert claude_msgs[1]["role"] == "assistant"
        assert claude_msgs[1]["content"] == "Hi there!"
        assert system_prompt == "System prompt: "

    @pytest.mark.asyncio
    async def test_convert_skips_system_messages(self) -> None:
        """convert() excludes SYSTEM messages from conversation."""
        converter = ClaudeMessageConverter()
        messages = [
            Message(text="System context", type=MessageType.SYSTEM),
            Message(text="User question", type=MessageType.HUMAN),
        ]

        with patch(
            "appkit_assistant.backend.services.message_converter.get_system_prompt",
            new_callable=AsyncMock,
            return_value="System: {mcp_prompts}",
        ):
            claude_msgs, _ = await converter.convert(messages)

        assert len(claude_msgs) == 1
        assert claude_msgs[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_convert_with_mcp_prompt(self) -> None:
        """convert() injects MCP prompts into system prompt."""
        converter = ClaudeMessageConverter()
        messages = [Message(text="Hello", type=MessageType.HUMAN)]

        with patch(
            "appkit_assistant.backend.services.message_converter.get_system_prompt",
            new_callable=AsyncMock,
            return_value="Base prompt\n{mcp_prompts}",
        ):
            _, system_prompt = await converter.convert(
                messages, mcp_prompt="Tool: search\nTool: fetch"
            )

        assert "Tool-Auswahlrichtlinien" in system_prompt
        assert "Tool: search" in system_prompt
        assert "Tool: fetch" in system_prompt

    @pytest.mark.asyncio
    async def test_convert_with_file_blocks(self) -> None:
        """convert() attaches file blocks to last user message."""
        converter = ClaudeMessageConverter()
        messages = [
            Message(text="First question", type=MessageType.HUMAN),
            Message(text="Answer", type=MessageType.ASSISTANT),
            Message(text="Follow-up", type=MessageType.HUMAN),
        ]
        file_blocks = [
            {"type": "document", "source": {"type": "text", "text": "File content"}}
        ]

        with patch(
            "appkit_assistant.backend.services.message_converter.get_system_prompt",
            new_callable=AsyncMock,
            return_value="System: {mcp_prompts}",
        ):
            claude_msgs, _ = await converter.convert(messages, file_blocks=file_blocks)

        # Last message should have file blocks + text
        last_msg = claude_msgs[-1]
        assert last_msg["role"] == "user"
        assert isinstance(last_msg["content"], list)
        assert len(last_msg["content"]) == 2  # file block + text block
        assert last_msg["content"][0]["type"] == "document"
        assert last_msg["content"][1]["type"] == "text"

    @pytest.mark.asyncio
    async def test_convert_no_file_blocks_for_non_last_user(self) -> None:
        """convert() only attaches files to the last user message."""
        converter = ClaudeMessageConverter()
        messages = [
            Message(text="First", type=MessageType.HUMAN),
            Message(text="Second", type=MessageType.ASSISTANT),
        ]
        file_blocks = [{"type": "document"}]

        with patch(
            "appkit_assistant.backend.services.message_converter.get_system_prompt",
            new_callable=AsyncMock,
            return_value="System: {mcp_prompts}",
        ):
            claude_msgs, _ = await converter.convert(messages, file_blocks=file_blocks)

        # First message should be simple string (not list)
        assert isinstance(claude_msgs[0]["content"], str)


class TestOpenAIResponsesConverter:
    """Test suite for OpenAIResponsesConverter."""

    @pytest.mark.asyncio
    async def test_convert_with_system_prompt(self) -> None:
        """convert() prepends system message when use_system_prompt=True."""
        converter = OpenAIResponsesConverter(use_system_prompt=True)
        messages = [Message(text="Hello", type=MessageType.HUMAN)]

        with patch(
            "appkit_assistant.backend.services.message_converter.get_system_prompt",
            new_callable=AsyncMock,
            return_value="System context: {mcp_prompts}",
        ):
            result = await converter.convert(messages)

        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[0]["content"][0]["type"] == "input_text"
        assert "System context" in result[0]["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_convert_without_system_prompt(self) -> None:
        """convert() omits system message when use_system_prompt=False."""
        converter = OpenAIResponsesConverter(use_system_prompt=False)
        messages = [Message(text="Hello", type=MessageType.HUMAN)]

        result = await converter.convert(messages)

        assert len(result) == 1
        assert result[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_convert_message_roles(self) -> None:
        """convert() uses correct role and content type for each message."""
        converter = OpenAIResponsesConverter(use_system_prompt=False)
        messages = [
            Message(text="User message", type=MessageType.HUMAN),
            Message(text="Assistant response", type=MessageType.ASSISTANT),
        ]

        result = await converter.convert(messages)

        assert result[0]["role"] == "user"
        assert result[0]["content"][0]["type"] == "input_text"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"][0]["type"] == "output_text"

    @pytest.mark.asyncio
    async def test_convert_skips_system_messages_in_conversation(self) -> None:
        """convert() skips SYSTEM messages from conversation history."""
        converter = OpenAIResponsesConverter(use_system_prompt=False)
        messages = [
            Message(text="System info", type=MessageType.SYSTEM),
            Message(text="User message", type=MessageType.HUMAN),
        ]

        result = await converter.convert(messages)

        assert len(result) == 1
        assert result[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_convert_with_mcp_prompt(self) -> None:
        """convert() includes MCP prompt in system message."""
        converter = OpenAIResponsesConverter(use_system_prompt=True)
        messages = []

        with patch(
            "appkit_assistant.backend.services.message_converter.get_system_prompt",
            new_callable=AsyncMock,
            return_value="Base: {mcp_prompts}",
        ):
            result = await converter.convert(messages, mcp_prompt="MCP tools")

        system_text = result[0]["content"][0]["text"]
        assert "Tool-Auswahlrichtlinien" in system_text
        assert "MCP tools" in system_text


class TestOpenAIChatConverter:
    """Test suite for OpenAIChatConverter."""

    @pytest.mark.asyncio
    async def test_convert_simple_messages(self) -> None:
        """convert() transforms messages to chat format."""
        converter = OpenAIChatConverter()
        messages = [
            Message(text="Hello", type=MessageType.HUMAN),
            Message(text="Hi!", type=MessageType.ASSISTANT),
        ]

        result = await converter.convert(messages)

        assert len(result) == 2
        assert result[0] == {"role": "user", "content": "Hello"}
        assert result[1] == {"role": "assistant", "content": "Hi!"}

    @pytest.mark.asyncio
    async def test_convert_merges_consecutive_same_role(self) -> None:
        """convert() merges consecutive messages with same role."""
        converter = OpenAIChatConverter()
        messages = [
            Message(text="First user", type=MessageType.HUMAN),
            Message(text="Second user", type=MessageType.HUMAN),
            Message(text="Assistant reply", type=MessageType.ASSISTANT),
        ]

        result = await converter.convert(messages)

        assert len(result) == 2
        assert result[0]["content"] == "First user\n\nSecond user"
        assert result[1]["content"] == "Assistant reply"

    @pytest.mark.asyncio
    async def test_convert_preserves_system_messages(self) -> None:
        """convert() includes system messages."""
        converter = OpenAIChatConverter()
        messages = [
            Message(text="System context", type=MessageType.SYSTEM),
            Message(text="User message", type=MessageType.HUMAN),
        ]

        result = await converter.convert(messages)

        assert len(result) == 2
        assert result[0] == {"role": "system", "content": "System context"}

    @pytest.mark.asyncio
    async def test_convert_does_not_merge_system_messages(self) -> None:
        """convert() does not merge system messages with others."""
        converter = OpenAIChatConverter()
        messages = [
            Message(text="System 1", type=MessageType.SYSTEM),
            Message(text="User", type=MessageType.HUMAN),
            Message(text="System 2", type=MessageType.SYSTEM),
        ]

        result = await converter.convert(messages)

        # System messages should not be merged with user messages
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_convert_handles_empty_messages(self) -> None:
        """convert() handles empty message list."""
        converter = OpenAIChatConverter()

        result = await converter.convert([])

        assert result == []


class TestGeminiMessageConverter:
    """Test suite for GeminiMessageConverter."""

    @pytest.mark.asyncio
    async def test_convert_basic_messages(self) -> None:
        """convert() transforms messages to Gemini Content objects."""
        converter = GeminiMessageConverter()
        messages = [
            Message(text="Hello", type=MessageType.HUMAN),
            Message(text="Hi there", type=MessageType.ASSISTANT),
        ]

        with patch(
            "appkit_assistant.backend.services.message_converter.get_system_prompt",
            new_callable=AsyncMock,
            return_value="System: {mcp_prompts}",
        ):
            contents, system_instruction = await converter.convert(messages)

        assert len(contents) == 2
        assert contents[0].role == "user"
        assert contents[0].parts[0].text == "Hello"
        assert contents[1].role == "model"
        assert contents[1].parts[0].text == "Hi there"

    @pytest.mark.asyncio
    async def test_convert_system_instruction(self) -> None:
        """convert() returns system instruction."""
        converter = GeminiMessageConverter()
        messages = [Message(text="Hello", type=MessageType.HUMAN)]

        with patch(
            "appkit_assistant.backend.services.message_converter.get_system_prompt",
            new_callable=AsyncMock,
            return_value="Base prompt: {mcp_prompts}",
        ):
            _, system_instruction = await converter.convert(messages)

        assert system_instruction == "Base prompt: "

    @pytest.mark.asyncio
    async def test_convert_with_mcp_prompt(self) -> None:
        """convert() includes MCP section in system instruction."""
        converter = GeminiMessageConverter()
        messages = []

        with patch(
            "appkit_assistant.backend.services.message_converter.get_system_prompt",
            new_callable=AsyncMock,
            return_value="Base: {mcp_prompts}",
        ):
            _, system_instruction = await converter.convert(
                messages, mcp_prompt="MCP tools"
            )

        assert "Tool-Auswahlrichtlinien" in system_instruction
        assert "MCP tools" in system_instruction

    @pytest.mark.asyncio
    async def test_convert_appends_system_messages_to_instruction(self) -> None:
        """convert() appends SYSTEM messages to system_instruction."""
        converter = GeminiMessageConverter()
        messages = [
            Message(text="System context 1", type=MessageType.SYSTEM),
            Message(text="User message", type=MessageType.HUMAN),
            Message(text="System context 2", type=MessageType.SYSTEM),
        ]

        with patch(
            "appkit_assistant.backend.services.message_converter.get_system_prompt",
            new_callable=AsyncMock,
            return_value="Base: {mcp_prompts}",
        ):
            contents, system_instruction = await converter.convert(messages)

        assert len(contents) == 1  # Only user message
        assert "System context 1" in system_instruction
        assert "System context 2" in system_instruction

    @pytest.mark.asyncio
    async def test_convert_role_mapping(self) -> None:
        """convert() maps HUMAN to user and ASSISTANT to model."""
        converter = GeminiMessageConverter()
        messages = [
            Message(text="User", type=MessageType.HUMAN),
            Message(text="Assistant", type=MessageType.ASSISTANT),
        ]

        with patch(
            "appkit_assistant.backend.services.message_converter.get_system_prompt",
            new_callable=AsyncMock,
            return_value="System: {mcp_prompts}",
        ):
            contents, _ = await converter.convert(messages)

        assert contents[0].role == "user"
        assert contents[1].role == "model"
