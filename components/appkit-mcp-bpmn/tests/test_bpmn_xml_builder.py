"""Tests for BPMN XML builder service."""

import json

import pytest

from appkit_mcp_bpmn.models import BpmnBranch, BpmnElement, BpmnProcessJson
from appkit_mcp_bpmn.services.bpmn_xml_builder import build_bpmn_xml
from appkit_mcp_commons.exceptions import ValidationError

SIMPLE_JSON = {
    "process": [
        {"type": "startEvent", "id": "Start_1", "label": "Start"},
        {"type": "task", "id": "Task_1", "label": "Do Work"},
        {"type": "endEvent", "id": "End_1", "label": "Done"},
    ]
}

GATEWAY_JSON = {
    "process": [
        {"type": "startEvent", "id": "Start_1", "label": "Start"},
        {
            "type": "exclusiveGateway",
            "id": "GW_1",
            "label": "Decision",
            "has_join": True,
            "branches": [
                {
                    "condition": "Yes",
                    "path": [
                        {"type": "task", "id": "Task_A", "label": "Approve"},
                    ],
                },
                {
                    "condition": "No",
                    "path": [
                        {"type": "task", "id": "Task_B", "label": "Reject"},
                    ],
                },
            ],
        },
        {"type": "endEvent", "id": "End_1", "label": "Done"},
    ]
}


def test_build_from_dict() -> None:
    """build_bpmn_xml accepts a dict input."""
    xml = build_bpmn_xml(SIMPLE_JSON)

    assert "definitions" in xml
    assert "Process_1" in xml
    assert "Start_1" in xml
    assert "Task_1" in xml
    assert "End_1" in xml
    assert "sequenceFlow" in xml


def test_build_from_json_string() -> None:
    """build_bpmn_xml accepts a JSON string."""
    xml = build_bpmn_xml(json.dumps(SIMPLE_JSON))

    assert "definitions" in xml
    assert "Start_1" in xml


def test_build_from_pydantic_model() -> None:
    """build_bpmn_xml accepts a BpmnProcessJson model."""
    model = BpmnProcessJson(
        process=[
            BpmnElement(type="startEvent", id="S1", label="Begin"),
            BpmnElement(type="userTask", id="T1", label="Review"),
            BpmnElement(type="endEvent", id="E1", label="End"),
        ]
    )
    xml = build_bpmn_xml(model)

    assert "S1" in xml
    assert "T1" in xml
    assert 'name="Review"' in xml
    assert "sequenceFlow" in xml


def test_build_with_gateway() -> None:
    """build_bpmn_xml correctly handles gateway branches."""
    xml = build_bpmn_xml(GATEWAY_JSON)

    assert "GW_1" in xml
    assert "Task_A" in xml
    assert "Task_B" in xml
    assert "GW_1_join" in xml
    assert "exclusiveGateway" in xml


def test_build_with_pydantic_gateway() -> None:
    """build_bpmn_xml handles BpmnProcessJson with gateway branches."""
    model = BpmnProcessJson(
        process=[
            BpmnElement(type="startEvent", id="S1", label="Start"),
            BpmnElement(
                type="parallelGateway",
                id="PG1",
                label="Split",
                has_join=True,
                branches=[
                    BpmnBranch(
                        condition="",
                        path=[
                            BpmnElement(type="serviceTask", id="A1", label="Task A"),
                        ],
                    ),
                    BpmnBranch(
                        condition="",
                        path=[
                            BpmnElement(type="serviceTask", id="B1", label="Task B"),
                        ],
                    ),
                ],
            ),
            BpmnElement(type="endEvent", id="E1", label="End"),
        ]
    )
    xml = build_bpmn_xml(model)

    assert "PG1" in xml
    assert "PG1_join" in xml
    assert "A1" in xml
    assert "B1" in xml


def test_build_invalid_json_string() -> None:
    """build_bpmn_xml raises ValidationError for invalid JSON."""
    with pytest.raises(ValidationError, match="Invalid JSON"):
        build_bpmn_xml("{not valid json")


def test_build_missing_process_key() -> None:
    """build_bpmn_xml raises ValidationError when 'process' key missing."""
    with pytest.raises(ValidationError, match="non-empty 'process' array"):
        build_bpmn_xml({"elements": []})


def test_build_empty_process() -> None:
    """build_bpmn_xml raises ValidationError for empty process array."""
    with pytest.raises(ValidationError, match="non-empty 'process' array"):
        build_bpmn_xml({"process": []})


def test_build_unknown_element_type() -> None:
    """build_bpmn_xml raises ValidationError for unknown element types."""
    data = {
        "process": [
            {"type": "startEvent", "id": "S1"},
            {"type": "unknownType", "id": "X1"},
            {"type": "endEvent", "id": "E1"},
        ]
    }
    with pytest.raises(ValidationError, match="Unknown element type"):
        build_bpmn_xml(data)


def test_build_missing_id() -> None:
    """build_bpmn_xml raises ValidationError for missing element id."""
    data = {
        "process": [
            {"type": "startEvent", "id": "S1"},
            {"type": "task", "label": "Missing ID"},
            {"type": "endEvent", "id": "E1"},
        ]
    }
    with pytest.raises(ValidationError, match="missing an 'id'"):
        build_bpmn_xml(data)


def test_build_duplicate_id() -> None:
    """build_bpmn_xml raises ValidationError for duplicate element ids."""
    data = {
        "process": [
            {"type": "startEvent", "id": "S1"},
            {"type": "task", "id": "S1", "label": "Duplicate"},
            {"type": "endEvent", "id": "E1"},
        ]
    }
    with pytest.raises(ValidationError, match="Duplicate element id"):
        build_bpmn_xml(data)


def test_build_missing_start_event() -> None:
    """build_bpmn_xml raises ValidationError when no startEvent."""
    data = {
        "process": [
            {"type": "task", "id": "T1"},
            {"type": "endEvent", "id": "E1"},
        ]
    }
    with pytest.raises(ValidationError, match="startEvent"):
        build_bpmn_xml(data)


def test_build_missing_end_event() -> None:
    """build_bpmn_xml raises ValidationError when no endEvent."""
    data = {
        "process": [
            {"type": "startEvent", "id": "S1"},
            {"type": "task", "id": "T1"},
        ]
    }
    with pytest.raises(ValidationError, match="endEvent"):
        build_bpmn_xml(data)


def test_build_all_task_types() -> None:
    """build_bpmn_xml supports all task/activity types."""
    types = [
        "userTask",
        "serviceTask",
        "scriptTask",
        "manualTask",
        "sendTask",
        "receiveTask",
        "businessRuleTask",
        "callActivity",
        "subProcess",
    ]
    elements: list[dict[str, str]] = [
        {"type": "startEvent", "id": "S1"},
    ]
    for i, t in enumerate(types):
        elements.append({"type": t, "id": f"T_{i}", "label": t})
    elements.append({"type": "endEvent", "id": "E1"})

    xml = build_bpmn_xml({"process": elements})

    for t in types:
        assert t in xml


def test_build_condition_expression() -> None:
    """build_bpmn_xml adds conditionExpression for gateway branches."""
    xml = build_bpmn_xml(GATEWAY_JSON)

    assert "conditionExpression" in xml
    assert "Yes" in xml
    assert "No" in xml
