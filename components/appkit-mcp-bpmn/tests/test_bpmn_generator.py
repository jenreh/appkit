"""Tests for BPMN generator service (structured output)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from appkit_mcp_bpmn.models import BpmnElement, BpmnProcessJson
from appkit_mcp_bpmn.services.bpmn_generator import BPMNGenerator

SIMPLE_PROCESS = BpmnProcessJson(
    process=[
        BpmnElement(type="startEvent", id="Start", label="Start"),
        BpmnElement(type="task", id="Task_1", label="Do something"),
        BpmnElement(type="endEvent", id="End", label="Done"),
    ]
)


def test_generator_has_system_prompt() -> None:
    """BPMNGenerator loads a system prompt on init."""
    gen = BPMNGenerator()
    assert gen._system_prompt is not None
    assert len(gen._system_prompt) > 50


@pytest.mark.asyncio
async def test_generate_raises_without_client() -> None:
    """generate() raises RuntimeError when no client is provided."""
    gen = BPMNGenerator()

    with pytest.raises(RuntimeError, match="OpenAI client not provided"):
        await gen.generate("Simple approval process")


@pytest.mark.asyncio
async def test_generate_calls_openai_responses() -> None:
    """generate() uses responses.parse() API with text_format."""
    gen = BPMNGenerator()

    # Mock response.output_parsed
    mock_response = MagicMock()
    mock_response.output_parsed = SIMPLE_PROCESS

    mock_client = AsyncMock()
    mock_client.responses.parse = AsyncMock(
        return_value=mock_response,
    )

    result = await gen.generate("Simple approval process", client=mock_client)

    assert isinstance(result, BpmnProcessJson)
    assert len(result.process) == 3
    assert result.process[0].type == "startEvent"
    mock_client.responses.parse.assert_called_once()

    call_args = mock_client.responses.parse.call_args
    assert call_args.kwargs["model"] == "gpt-4o"
    assert "input" in call_args.kwargs
    assert call_args.kwargs["text_format"] is BpmnProcessJson


@pytest.mark.asyncio
async def test_generate_empty_output() -> None:
    """generate() raises RuntimeError when output_parsed is None."""
    gen = BPMNGenerator()

    mock_response = MagicMock()
    mock_response.output_parsed = None

    mock_client = AsyncMock()
    mock_client.responses.parse = AsyncMock(
        return_value=mock_response,
    )

    with pytest.raises(RuntimeError, match="empty structured response"):
        await gen.generate("Bad workflow", client=mock_client)


@pytest.mark.asyncio
async def test_generate_invalid_json() -> None:
    """generate() raises RuntimeError when Pydantic validation fails."""
    gen = BPMNGenerator()

    # Mock a response with invalid data that fails Pydantic validation
    mock_response = MagicMock()
    # Return something that's not a valid BpmnProcessJson
    mock_response.output_parsed = None

    mock_client = AsyncMock()
    mock_client.responses.parse = AsyncMock(
        return_value=mock_response,
    )

    with pytest.raises(RuntimeError, match="empty structured response"):
        await gen.generate("Test workflow", client=mock_client)


@pytest.mark.asyncio
async def test_generate_llm_exception() -> None:
    """generate() raises RuntimeError when LLM call fails."""
    gen = BPMNGenerator()

    mock_client = AsyncMock()
    mock_client.responses.parse = AsyncMock(
        side_effect=Exception("API error"),
    )

    with pytest.raises(RuntimeError, match="Failed to generate"):
        await gen.generate("Test workflow", client=mock_client)


@pytest.mark.asyncio
async def test_generate_uses_diagram_type() -> None:
    """generate() includes diagram_type in the prompt."""
    gen = BPMNGenerator()

    mock_response = MagicMock()
    mock_response.output_parsed = SIMPLE_PROCESS

    mock_client = AsyncMock()
    mock_client.responses.parse = AsyncMock(
        return_value=mock_response,
    )

    await gen.generate("Test", diagram_type="collaboration", client=mock_client)

    call_args = mock_client.responses.parse.call_args
    messages = call_args.kwargs["input"]
    user_msg = messages[1]["content"]
    assert "collaboration" in user_msg
