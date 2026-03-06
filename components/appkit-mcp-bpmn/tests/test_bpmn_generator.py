"""Tests for BPMN generator service (flat model, structured output)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from appkit_mcp_bpmn.models import BpmnProcess, BpmnStep
from appkit_mcp_bpmn.services.bpmn_generator import BPMNGenerator

SIMPLE_PROCESS = BpmnProcess(
    steps=[
        BpmnStep(id="start", type="startEvent", label="Start"),
        BpmnStep(id="task_1", type="task", label="Do something"),
        BpmnStep(id="end", type="endEvent", label="Done"),
    ],
)

SIMPLE_PROCESS_JSON = json.dumps(SIMPLE_PROCESS.model_dump())


def _mock_create_response(
    output_text: str | None = None,
) -> MagicMock:
    """Create a mock response from responses.create()."""
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
async def test_generate_calls_openai_responses_create() -> None:
    """generate() uses responses.create() with json_schema format."""
    gen = BPMNGenerator()

    mock_response = _mock_create_response(output_text=SIMPLE_PROCESS_JSON)
    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=mock_response)

    result = await gen.generate("Simple approval process", client=mock_client)

    assert isinstance(result, BpmnProcess)
    assert len(result.steps) == 3
    assert result.steps[0].type == "startEvent"
    mock_client.responses.create.assert_called_once()

    call_kwargs = mock_client.responses.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o"
    assert "input" in call_kwargs
    assert call_kwargs["text"]["format"]["name"] == "BpmnProcess"


@pytest.mark.asyncio
async def test_generate_empty_output() -> None:
    """generate() raises RuntimeError when output_text is empty."""
    gen = BPMNGenerator()

    mock_response = _mock_create_response(output_text=None)
    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=mock_response)

    with pytest.raises(RuntimeError, match="empty structured response"):
        await gen.generate("Bad workflow", client=mock_client)


@pytest.mark.asyncio
async def test_generate_retries_on_validation_error() -> None:
    """generate() retries when response fails Pydantic validation."""
    gen = BPMNGenerator()

    # First call returns invalid JSON, second returns valid
    bad_response = _mock_create_response(
        output_text='{"steps": "not a list", "lanes": null}'
    )
    good_response = _mock_create_response(output_text=SIMPLE_PROCESS_JSON)

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(side_effect=[bad_response, good_response])

    result = await gen.generate("Test workflow", client=mock_client)

    assert isinstance(result, BpmnProcess)
    assert len(result.steps) == 3
    assert mock_client.responses.create.call_count == 2


@pytest.mark.asyncio
async def test_generate_retry_exhausted() -> None:
    """generate() raises RuntimeError when all retries exhausted."""
    gen = BPMNGenerator()

    bad_response = _mock_create_response(
        output_text='{"steps": "invalid", "lanes": null}'
    )
    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=bad_response)

    with pytest.raises(RuntimeError, match="invalid BPMN JSON"):
        await gen.generate("Test workflow", client=mock_client, max_retries=2)

    # 1 initial + 2 retries + fallback repair = 3 API calls
    assert mock_client.responses.create.call_count == 3


@pytest.mark.asyncio
async def test_generate_retry_accumulates_errors() -> None:
    """Each retry includes accumulated error history."""
    gen = BPMNGenerator()

    bad = _mock_create_response(output_text='{"steps": "bad", "lanes": null}')
    good = _mock_create_response(output_text=SIMPLE_PROCESS_JSON)

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(side_effect=[bad, bad, good])

    result = await gen.generate("Test workflow", client=mock_client, max_retries=3)

    assert isinstance(result, BpmnProcess)
    assert mock_client.responses.create.call_count == 3

    # Third call's input should reference prior errors
    third_call_input = mock_client.responses.create.call_args_list[2].kwargs["input"]
    assert isinstance(third_call_input, list)
    prompt_text = third_call_input[-1]["content"]
    assert "Attempt 1" in prompt_text
    assert "Attempt 2" in prompt_text


@pytest.mark.asyncio
async def test_generate_llm_exception() -> None:
    """generate() raises RuntimeError when LLM call fails."""
    gen = BPMNGenerator()

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(
        side_effect=Exception("API error"),
    )

    with pytest.raises(RuntimeError, match="Failed to generate"):
        await gen.generate("Test workflow", client=mock_client)


@pytest.mark.asyncio
async def test_generate_uses_diagram_type() -> None:
    """generate() includes diagram_type in the prompt."""
    gen = BPMNGenerator()

    mock_response = _mock_create_response(output_text=SIMPLE_PROCESS_JSON)
    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=mock_response)

    await gen.generate(
        "Test",
        diagram_type="collaboration",
        client=mock_client,
    )

    call_kwargs = mock_client.responses.create.call_args.kwargs
    assert "collaboration" in call_kwargs["input"][0]["content"]
