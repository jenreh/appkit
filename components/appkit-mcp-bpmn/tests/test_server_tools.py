"""Tests for BPMN MCP server tools."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.client import Client
from fastmcp.exceptions import ToolError

from appkit_mcp_bpmn.models import BpmnProcess, BpmnStep
from appkit_mcp_bpmn.server import (
    _error_result,
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
async def test_generate_bpmn_diagram_empty_description(
    bpmn_client: Client,
) -> None:
    """generate_bpmn_diagram rejects empty description with isError=True."""
    with pytest.raises(ToolError, match="empty"):
        await bpmn_client.call_tool(
            "generate_bpmn_diagram", arguments={"description": ""}
        )


@pytest.mark.asyncio
async def test_generate_bpmn_diagram_invalid_type(
    bpmn_client: Client,
) -> None:
    """generate_bpmn_diagram rejects invalid diagram type with isError=True."""
    with pytest.raises(ToolError, match="Invalid diagram_type"):
        await bpmn_client.call_tool(
            "generate_bpmn_diagram",
            arguments={"description": "test", "diagram_type": "invalid"},
        )


@pytest.mark.asyncio
async def test_generate_bpmn_diagram_success(bpmn_client: Client) -> None:
    """generate_bpmn_diagram calls LLM and returns valid result."""
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
            "generate_bpmn_diagram",
            arguments={"description": "Simple approval flow"},
        )

    parsed = json.loads(result.content[0].text)

    assert parsed["success"] is True
    assert parsed["id"] is not None
    assert parsed["download_url"] is not None


@pytest.mark.asyncio
async def test_generate_bpmn_diagram_llm_failure(
    bpmn_client: Client,
) -> None:
    """generate_bpmn_diagram signals isError=True on LLM errors."""
    with (
        patch(
            "appkit_mcp_bpmn.server.BPMNGenerator.generate",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM unavailable"),
        ),
        pytest.raises(ToolError, match="LLM unavailable"),
    ):
        await bpmn_client.call_tool(
            "generate_bpmn_diagram",
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
