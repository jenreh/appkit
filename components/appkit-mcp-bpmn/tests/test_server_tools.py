"""Tests for BPMN MCP server tools."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.client import Client
from fastmcp.exceptions import ToolError

from appkit_mcp_bpmn.models import BpmnProcess, BpmnStep
from appkit_mcp_bpmn.server import (
    _error_result,
    _validate_and_save,
    create_bpmn_mcp_server,
)

VALID_BPMN = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="Event_Start" name="Start" />
    <bpmn:task id="Activity_1" name="Do Something" />
    <bpmn:endEvent id="Event_End" name="End" />
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Event_Start" targetRef="Activity_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Activity_1" targetRef="Event_End" />
  </bpmn:process>
</bpmn:definitions>
"""


def test_create_server() -> None:
    """Factory function returns a FastMCP instance."""
    mcp = create_bpmn_mcp_server()
    assert mcp is not None
    assert mcp.name == "appkit-bpmn"


def test_create_server_custom_name() -> None:
    """Factory function accepts a custom name."""
    mcp = create_bpmn_mcp_server(name="my-bpmn")
    assert mcp.name == "my-bpmn"


def test_validate_and_save_valid(tmp_path: Path) -> None:
    """_validate_and_save succeeds with valid BPMN XML."""
    storage = str(tmp_path / "bpmn")
    result_json = _validate_and_save(VALID_BPMN, storage)
    result = json.loads(result_json)

    assert result["success"] is True
    assert result["id"] is not None
    assert result["download_url"] is not None
    assert result["view_url"] is not None


def test_validate_and_save_invalid_xml(tmp_path: Path) -> None:
    """_validate_and_save raises ValueError for invalid XML."""
    with pytest.raises(ValueError, match="Validation failed"):
        _validate_and_save("<invalid>", str(tmp_path))


def test_error_result_format() -> None:
    """_error_result returns properly structured JSON."""
    result_json = _error_result("Something went wrong")
    result = json.loads(result_json)

    assert result["success"] is False
    assert result["error"] == "Something went wrong"
    assert result["id"] is None
    assert result["download_url"] is None
    assert result["view_url"] is None


@pytest.mark.asyncio
async def test_save_bpmn_diagram_tool(bpmn_client: Client) -> None:
    """save_bpmn_diagram tool validates and saves XML."""
    result = await bpmn_client.call_tool(
        "save_bpmn_diagram", arguments={"xml": VALID_BPMN}
    )
    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is True
    assert parsed["id"] is not None


@pytest.mark.asyncio
async def test_save_bpmn_diagram_empty_xml(bpmn_client: Client) -> None:
    """save_bpmn_diagram rejects empty XML with isError=True."""
    with pytest.raises(ToolError, match="empty"):
        await bpmn_client.call_tool("save_bpmn_diagram", arguments={"xml": ""})


@pytest.mark.asyncio
async def test_new_bpmn_diagram_empty_description(
    bpmn_client: Client,
) -> None:
    """new_bpmn_diagram rejects empty description with isError=True."""
    with pytest.raises(ToolError, match="empty"):
        await bpmn_client.call_tool("new_bpmn_diagram", arguments={"description": ""})


@pytest.mark.asyncio
async def test_new_bpmn_diagram_invalid_type(
    bpmn_client: Client,
) -> None:
    """new_bpmn_diagram rejects invalid diagram type with isError=True."""
    with pytest.raises(ToolError, match="Invalid diagram_type"):
        await bpmn_client.call_tool(
            "new_bpmn_diagram",
            arguments={"description": "test", "diagram_type": "invalid"},
        )


@pytest.mark.asyncio
async def test_new_bpmn_diagram_success(bpmn_client: Client) -> None:
    """new_bpmn_diagram calls LLM and returns valid result."""
    mock_process = BpmnProcess(
        steps=[
            BpmnStep(
                id="Event_Start",
                type="startEvent",
                label="Start",
            ),
            BpmnStep(
                id="Activity_1",
                type="task",
                label="Do Something",
            ),
            BpmnStep(
                id="Event_End",
                type="endEvent",
                label="End",
            ),
        ]
    )

    with patch(
        "appkit_mcp_bpmn.server.BPMNGenerator.generate",
        new_callable=AsyncMock,
        return_value=mock_process,
    ):
        result = await bpmn_client.call_tool(
            "new_bpmn_diagram",
            arguments={"description": "Simple approval flow"},
        )

    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is True
    assert parsed["id"] is not None
    assert parsed["download_url"] is not None


@pytest.mark.asyncio
async def test_new_bpmn_diagram_llm_failure(
    bpmn_client: Client,
) -> None:
    """new_bpmn_diagram signals isError=True on LLM errors."""
    with (
        patch(
            "appkit_mcp_bpmn.server.BPMNGenerator.generate",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM unavailable"),
        ),
        pytest.raises(ToolError, match="LLM unavailable"),
    ):
        await bpmn_client.call_tool(
            "new_bpmn_diagram",
            arguments={"description": "A workflow"},
        )


@pytest.mark.asyncio
async def test_get_bpmn_xml_success(bpmn_client: Client) -> None:
    """get_bpmn_xml returns XML for a previously saved diagram."""
    # First save a diagram
    save_result = await bpmn_client.call_tool(
        "save_bpmn_diagram", arguments={"xml": VALID_BPMN}
    )
    saved = json.loads(save_result.content[0].text)
    diagram_id = saved["id"]

    # Now retrieve it
    result = await bpmn_client.call_tool(
        "get_bpmn_xml", arguments={"diagram_id": diagram_id}
    )
    xml = result.content[0].text

    assert "bpmn:definitions" in xml
    assert "bpmn:process" in xml


@pytest.mark.asyncio
async def test_get_bpmn_xml_not_found(bpmn_client: Client) -> None:
    """get_bpmn_xml returns error for unknown diagram ID."""
    result = await bpmn_client.call_tool(
        "get_bpmn_xml", arguments={"diagram_id": "nonexistent-id"}
    )
    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is False
    assert "not found" in parsed["error"].lower()


@pytest.mark.asyncio
async def test_get_bpmn_xml_empty_id(bpmn_client: Client) -> None:
    """get_bpmn_xml rejects empty diagram_id."""
    result = await bpmn_client.call_tool("get_bpmn_xml", arguments={"diagram_id": ""})
    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is False
    assert "empty" in parsed["error"].lower()


@pytest.mark.asyncio
async def test_update_bpmn_diagram_success(bpmn_client: Client) -> None:
    """update_bpmn_diagram loads, modifies via LLM, and saves new version."""
    # Save a diagram first
    save_result = await bpmn_client.call_tool(
        "save_bpmn_diagram", arguments={"xml": VALID_BPMN}
    )
    saved = json.loads(save_result.content[0].text)
    diagram_id = saved["id"]

    mock_process = BpmnProcess(
        steps=[
            BpmnStep(id="Event_Start", type="startEvent", label="Start"),
            BpmnStep(id="Activity_1", type="task", label="Do Something"),
            BpmnStep(id="Activity_2", type="task", label="Review"),
            BpmnStep(id="Event_End", type="endEvent", label="End"),
        ]
    )

    with patch(
        "appkit_mcp_bpmn.server.BPMNGenerator.generate",
        new_callable=AsyncMock,
        return_value=mock_process,
    ):
        result = await bpmn_client.call_tool(
            "update_bpmn_diagram",
            arguments={
                "diagram_id": diagram_id,
                "update_prompt": "Add a review step",
            },
        )

    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is True
    # New version gets a new ID
    assert parsed["id"] is not None
    assert parsed["id"] != diagram_id
    assert parsed["download_url"] is not None


@pytest.mark.asyncio
async def test_update_bpmn_diagram_not_found(bpmn_client: Client) -> None:
    """update_bpmn_diagram raises error for unknown diagram."""
    with pytest.raises(ToolError, match="not found"):
        await bpmn_client.call_tool(
            "update_bpmn_diagram",
            arguments={
                "diagram_id": "nonexistent-id",
                "update_prompt": "Add a step",
            },
        )


@pytest.mark.asyncio
async def test_update_bpmn_diagram_empty_id(bpmn_client: Client) -> None:
    """update_bpmn_diagram raises error for empty diagram_id."""
    with pytest.raises(ToolError, match="empty"):
        await bpmn_client.call_tool(
            "update_bpmn_diagram",
            arguments={"diagram_id": "", "update_prompt": "Add a step"},
        )


@pytest.mark.asyncio
async def test_update_bpmn_diagram_empty_prompt(bpmn_client: Client) -> None:
    """update_bpmn_diagram raises error for empty update_prompt."""
    with pytest.raises(ToolError, match="empty"):
        await bpmn_client.call_tool(
            "update_bpmn_diagram",
            arguments={"diagram_id": "some-id", "update_prompt": ""},
        )


@pytest.mark.asyncio
async def test_update_bpmn_diagram_llm_failure(bpmn_client: Client) -> None:
    """update_bpmn_diagram signals error on LLM failure."""
    save_result = await bpmn_client.call_tool(
        "save_bpmn_diagram", arguments={"xml": VALID_BPMN}
    )
    saved = json.loads(save_result.content[0].text)
    diagram_id = saved["id"]

    with (
        patch(
            "appkit_mcp_bpmn.server.BPMNGenerator.generate",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM unavailable"),
        ),
        pytest.raises(ToolError, match="LLM unavailable"),
    ):
        await bpmn_client.call_tool(
            "update_bpmn_diagram",
            arguments={
                "diagram_id": diagram_id,
                "update_prompt": "Add a step",
            },
        )


# --- save_or_update tests ---


@pytest.mark.asyncio
async def test_save_or_update_success(bpmn_client: Client) -> None:
    """save_or_update validates and overwrites stored XML in-place."""
    save_result = await bpmn_client.call_tool(
        "save_bpmn_diagram",
        arguments={"xml": VALID_BPMN, "prompt": "Original"},
    )
    saved = json.loads(save_result.content[0].text)
    diagram_id = saved["id"]

    result = await bpmn_client.call_tool(
        "save_or_update",
        arguments={"diagram_id": diagram_id, "xml": VALID_BPMN},
    )
    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is True
    assert parsed["id"] == diagram_id


@pytest.mark.asyncio
async def test_save_or_update_not_found(bpmn_client: Client) -> None:
    """save_or_update returns error for unknown diagram_id."""
    result = await bpmn_client.call_tool(
        "save_or_update",
        arguments={"diagram_id": "nonexistent-id", "xml": VALID_BPMN},
    )
    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is False
    assert "not found" in parsed["error"].lower()


@pytest.mark.asyncio
async def test_save_or_update_empty_id(bpmn_client: Client) -> None:
    """save_or_update returns error for empty diagram_id."""
    result = await bpmn_client.call_tool(
        "save_or_update",
        arguments={"diagram_id": "", "xml": VALID_BPMN},
    )
    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is False


@pytest.mark.asyncio
async def test_save_or_update_empty_xml(bpmn_client: Client) -> None:
    """save_or_update returns error for empty XML."""
    result = await bpmn_client.call_tool(
        "save_or_update",
        arguments={"diagram_id": "some-id", "xml": ""},
    )
    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is False


@pytest.mark.asyncio
async def test_save_or_update_invalid_xml(bpmn_client: Client) -> None:
    """save_or_update returns error for invalid BPMN XML."""
    save_result = await bpmn_client.call_tool(
        "save_bpmn_diagram",
        arguments={"xml": VALID_BPMN},
    )
    saved = json.loads(save_result.content[0].text)
    diagram_id = saved["id"]

    result = await bpmn_client.call_tool(
        "save_or_update",
        arguments={"diagram_id": diagram_id, "xml": "<not-bpmn/>"},
    )
    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is False
    assert "validation" in parsed["error"].lower()


# --- rename_bpmn_diagram tests ---


@pytest.mark.asyncio
async def test_rename_bpmn_diagram_success(bpmn_client: Client) -> None:
    """rename_bpmn_diagram updates the name of an existing diagram."""
    save_result = await bpmn_client.call_tool(
        "save_bpmn_diagram",
        arguments={"xml": VALID_BPMN, "prompt": "Original prompt"},
    )
    saved = json.loads(save_result.content[0].text)
    diagram_id = saved["id"]

    result = await bpmn_client.call_tool(
        "rename_bpmn_diagram",
        arguments={"diagram_id": diagram_id, "name": "My Workflow"},
    )
    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is True
    assert parsed["id"] == diagram_id
    assert parsed["name"] == "My Workflow"


@pytest.mark.asyncio
async def test_rename_bpmn_diagram_trims_whitespace(bpmn_client: Client) -> None:
    """rename_bpmn_diagram trims leading/trailing whitespace."""
    save_result = await bpmn_client.call_tool(
        "save_bpmn_diagram", arguments={"xml": VALID_BPMN}
    )
    saved = json.loads(save_result.content[0].text)
    diagram_id = saved["id"]

    result = await bpmn_client.call_tool(
        "rename_bpmn_diagram",
        arguments={"diagram_id": diagram_id, "name": "  Trimmed Name  "},
    )
    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is True
    assert parsed["name"] == "Trimmed Name"


@pytest.mark.asyncio
async def test_rename_bpmn_diagram_not_found(bpmn_client: Client) -> None:
    """rename_bpmn_diagram returns error for unknown diagram."""
    result = await bpmn_client.call_tool(
        "rename_bpmn_diagram",
        arguments={"diagram_id": "nonexistent-id", "name": "New Name"},
    )
    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is False
    assert "not found" in parsed["error"].lower()


@pytest.mark.asyncio
async def test_rename_bpmn_diagram_empty_id(bpmn_client: Client) -> None:
    """rename_bpmn_diagram returns error for empty diagram_id."""
    result = await bpmn_client.call_tool(
        "rename_bpmn_diagram",
        arguments={"diagram_id": "", "name": "New Name"},
    )
    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is False
    assert "empty" in parsed["error"].lower()


@pytest.mark.asyncio
async def test_rename_bpmn_diagram_empty_name(bpmn_client: Client) -> None:
    """rename_bpmn_diagram returns error for empty name."""
    result = await bpmn_client.call_tool(
        "rename_bpmn_diagram",
        arguments={"diagram_id": "some-id", "name": ""},
    )
    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is False
    assert "empty" in parsed["error"].lower()


@pytest.mark.asyncio
async def test_rename_bpmn_diagram_too_long(bpmn_client: Client) -> None:
    """rename_bpmn_diagram rejects names exceeding 128 characters."""
    result = await bpmn_client.call_tool(
        "rename_bpmn_diagram",
        arguments={"diagram_id": "some-id", "name": "A" * 129},
    )
    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is False
    assert "128" in parsed["error"]


@pytest.mark.asyncio
async def test_save_bpmn_diagram_includes_name(bpmn_client: Client) -> None:
    """save_bpmn_diagram returns name derived from prompt."""
    result = await bpmn_client.call_tool(
        "save_bpmn_diagram",
        arguments={"xml": VALID_BPMN, "prompt": "My approval flow"},
    )
    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is True
    assert parsed["name"] == "My approval flow"


@pytest.mark.asyncio
async def test_save_bpmn_diagram_default_name(bpmn_client: Client) -> None:
    """save_bpmn_diagram uses fallback name when prompt is empty."""
    result = await bpmn_client.call_tool(
        "save_bpmn_diagram", arguments={"xml": VALID_BPMN}
    )
    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is True
    assert parsed["name"].startswith("Diagram ")
