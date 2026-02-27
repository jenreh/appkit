"""Tests for SystemPromptBuilder.

Covers MCP section building, template formatting, and prefix support.
"""

from unittest.mock import AsyncMock, patch

import pytest

from appkit_assistant.backend.services.system_prompt_builder import (
    SystemPromptBuilder,
    get_system_prompt_builder,
)


@pytest.fixture
def builder() -> SystemPromptBuilder:
    return SystemPromptBuilder()


class TestBuildMcpSection:
    def test_empty_prompt(self, builder: SystemPromptBuilder) -> None:
        assert builder._build_mcp_section("") == ""

    def test_with_prompt(self, builder: SystemPromptBuilder) -> None:
        result = builder._build_mcp_section("Use search tool")
        assert SystemPromptBuilder.MCP_SECTION_HEADER in result
        assert "Use search tool" in result


class TestBuild:
    @pytest.mark.asyncio
    async def test_build_without_mcp(self, builder: SystemPromptBuilder) -> None:
        with patch(
            "appkit_assistant.backend.services.system_prompt_builder.get_system_prompt",
            new_callable=AsyncMock,
            return_value="System prompt {mcp_prompts}",
        ):
            result = await builder.build()
            assert "System prompt" in result
            assert "{mcp_prompts}" not in result

    @pytest.mark.asyncio
    async def test_build_with_mcp(self, builder: SystemPromptBuilder) -> None:
        with patch(
            "appkit_assistant.backend.services.system_prompt_builder.get_system_prompt",
            new_callable=AsyncMock,
            return_value="Base {mcp_prompts}",
        ):
            result = await builder.build(mcp_prompt="tool: search")
            assert "tool: search" in result
            assert SystemPromptBuilder.MCP_SECTION_HEADER in result


class TestBuildWithPrefix:
    @pytest.mark.asyncio
    async def test_no_prefix(self, builder: SystemPromptBuilder) -> None:
        with patch(
            "appkit_assistant.backend.services.system_prompt_builder.get_system_prompt",
            new_callable=AsyncMock,
            return_value="Prompt {mcp_prompts}",
        ):
            result = await builder.build_with_prefix()
            assert result.startswith("Prompt")

    @pytest.mark.asyncio
    async def test_with_prefix(self, builder: SystemPromptBuilder) -> None:
        with patch(
            "appkit_assistant.backend.services.system_prompt_builder.get_system_prompt",
            new_callable=AsyncMock,
            return_value="Prompt {mcp_prompts}",
        ):
            result = await builder.build_with_prefix(prefix="\n\n")
            assert result.startswith("\n\n")


class TestGetSystemPromptBuilder:
    def test_returns_singleton(self) -> None:
        b1 = get_system_prompt_builder()
        b2 = get_system_prompt_builder()
        assert b1 is b2
        assert isinstance(b1, SystemPromptBuilder)
