"""Tests for BPMN generator service (structured output)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from appkit_mcp_bpmn.models import BpmnElement, BpmnProcessJson
from appkit_mcp_bpmn.services.bpmn_generator import BPMNGenerator

SIMPLE_PROCESS = BpmnProcessJson(
    process=[
        BpmnElement(type="startEvent", id="Start", label="Start"),
        BpmnElement(type="task", id="Task_1", label="Do something"),
        BpmnElement(type="endEvent", id="End", label="Done"),
    ]
)

SIMPLE_PROCESS_JSON = json.dumps(SIMPLE_PROCESS.model_dump())


def _mock_parse_response(
    output_parsed: BpmnProcessJson | None = None,
    output_text: str | None = None,
) -> MagicMock:
    """Create a mock response from responses.parse()."""
    resp = MagicMock()
    resp.output_parsed = output_parsed
    resp.output_text = output_text
    return resp


def _mock_create_response(output_text: str | None = None) -> MagicMock:
    """Create a mock response from responses.create() (retry path)."""
    resp = MagicMock()
    resp.output_text = output_text
    return resp


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
async def test_generate_calls_openai_responses_parse() -> None:
    """generate() uses responses.parse() API with text_format."""
    gen = BPMNGenerator()

    mock_response = _mock_parse_response(output_parsed=SIMPLE_PROCESS)
    mock_client = AsyncMock()
    mock_client.responses.parse = AsyncMock(return_value=mock_response)

    result = await gen.generate("Simple approval process", client=mock_client)

    assert isinstance(result, BpmnProcessJson)
    assert len(result.process) == 3
    assert result.process[0].type == "startEvent"
    mock_client.responses.parse.assert_called_once()

    call_kwargs = mock_client.responses.parse.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o"
    assert "input" in call_kwargs
    assert call_kwargs["text_format"] is BpmnProcessJson


@pytest.mark.asyncio
async def test_generate_empty_output() -> None:
    """generate() raises RuntimeError when output_parsed is None."""
    gen = BPMNGenerator()

    mock_response = _mock_parse_response(output_parsed=None)
    mock_client = AsyncMock()
    mock_client.responses.parse = AsyncMock(return_value=mock_response)

    with pytest.raises(RuntimeError, match="empty structured response"):
        await gen.generate("Bad workflow", client=mock_client)


@pytest.mark.asyncio
async def test_generate_retries_on_validation_error() -> None:
    """generate() retries via responses.create() when parse() raises ValidationError."""
    gen = BPMNGenerator()

    # First call (parse) raises ValidationError
    mock_client = AsyncMock()
    mock_client.responses.parse = AsyncMock(
        side_effect=ValidationError.from_exception_data(
            title="BpmnProcessJson",
            line_errors=[],
        ),
    )

    # Retry call (create) returns valid JSON
    retry_resp = _mock_create_response(output_text=SIMPLE_PROCESS_JSON)
    mock_client.responses.create = AsyncMock(return_value=retry_resp)

    result = await gen.generate("Test workflow", client=mock_client)

    assert isinstance(result, BpmnProcessJson)
    assert len(result.process) == 3
    mock_client.responses.parse.assert_called_once()
    mock_client.responses.create.assert_called_once()


@pytest.mark.asyncio
async def test_generate_retry_also_fails() -> None:
    """generate() raises RuntimeError when both parse and retry fail."""
    gen = BPMNGenerator()

    mock_client = AsyncMock()
    mock_client.responses.parse = AsyncMock(
        side_effect=ValidationError.from_exception_data(
            title="BpmnProcessJson",
            line_errors=[],
        ),
    )

    # Retry also returns invalid JSON (missing startEvent)
    invalid_json = json.dumps({"process": [{"type": "task", "id": "T1"}]})
    retry_resp = _mock_create_response(output_text=invalid_json)
    mock_client.responses.create = AsyncMock(return_value=retry_resp)

    with pytest.raises(RuntimeError, match="fallback repair failed"):
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

    mock_response = _mock_parse_response(output_parsed=SIMPLE_PROCESS)
    mock_client = AsyncMock()
    mock_client.responses.parse = AsyncMock(return_value=mock_response)

    await gen.generate("Test", diagram_type="collaboration", client=mock_client)

    call_kwargs = mock_client.responses.parse.call_args.kwargs
    assert "collaboration" in call_kwargs["input"]
