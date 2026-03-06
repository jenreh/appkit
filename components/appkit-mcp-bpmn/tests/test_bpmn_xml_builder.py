"""Tests for BPMN XML builder service (flat model)."""

import json

import pytest

from appkit_mcp_bpmn.models import BpmnBranch, BpmnProcess, BpmnStep
from appkit_mcp_bpmn.services.bpmn_layouter import add_diagram_layout
from appkit_mcp_bpmn.services.bpmn_xml_builder import build_bpmn_xml
from appkit_mcp_commons.exceptions import ValidationError

SIMPLE_PROCESS = BpmnProcess(
    steps=[
        BpmnStep(id="start", type="startEvent", label="Start"),
        BpmnStep(id="task_1", type="task", label="Do Work"),
        BpmnStep(id="end", type="endEvent", label="Done"),
    ],
)

SIMPLE_DICT = {
    "steps": [
        {
            "id": "start",
            "type": "startEvent",
            "label": "Start",
            "branches": None,
            "next": None,
        },
        {
            "id": "task_1",
            "type": "task",
            "label": "Do Work",
            "branches": None,
            "next": None,
        },
        {
            "id": "end",
            "type": "endEvent",
            "label": "Done",
            "branches": None,
            "next": None,
        },
    ],
    "lanes": None,
}

GATEWAY_PROCESS = BpmnProcess(
    steps=[
        BpmnStep(id="start", type="startEvent", label="Start"),
        BpmnStep(
            id="gw_decide",
            type="exclusive",
            label="Decision",
            branches=[
                BpmnBranch(condition="Yes", target="task_a"),
                BpmnBranch(condition="No", target="task_b"),
            ],
        ),
        BpmnStep(id="task_a", type="task", label="Approve"),
        BpmnStep(id="task_b", type="task", label="Reject", next="end"),
        BpmnStep(id="end", type="endEvent", label="Done"),
    ],
)


# --- Basic construction ---


def test_build_from_dict() -> None:
    """build_bpmn_xml accepts a dict input."""
    xml = build_bpmn_xml(SIMPLE_DICT)

    assert "definitions" in xml
    assert "Process_1" in xml
    assert "start" in xml
    assert "task_1" in xml
    assert "end" in xml
    assert "sequenceFlow" in xml


def test_build_from_json_string() -> None:
    """build_bpmn_xml accepts a JSON string."""
    xml = build_bpmn_xml(json.dumps(SIMPLE_DICT))

    assert "definitions" in xml
    assert "start" in xml


def test_build_from_pydantic_model() -> None:
    """build_bpmn_xml accepts a BpmnProcess model."""
    xml = build_bpmn_xml(SIMPLE_PROCESS)

    assert "start" in xml
    assert "task_1" in xml
    assert 'name="Do Work"' in xml
    assert "sequenceFlow" in xml


# --- Gateway handling ---


def test_build_with_gateway() -> None:
    """build_bpmn_xml correctly handles gateway branches."""
    xml = build_bpmn_xml(GATEWAY_PROCESS)

    assert "gw_decide" in xml
    assert "task_a" in xml
    assert "task_b" in xml
    assert "exclusiveGateway" in xml


def test_build_with_parallel_gateway() -> None:
    """build_bpmn_xml handles parallel + merge steps."""
    proc = BpmnProcess(
        steps=[
            BpmnStep(id="start", type="startEvent", label="Start"),
            BpmnStep(
                id="split",
                type="parallel",
                label="Split",
                branches=[
                    BpmnBranch(condition="", target="task_a"),
                    BpmnBranch(condition="", target="task_b"),
                ],
            ),
            BpmnStep(id="task_a", type="task", label="A"),
            BpmnStep(id="task_b", type="task", label="B", next="sync"),
            BpmnStep(id="sync", type="merge", label="Sync"),
            BpmnStep(id="end", type="endEvent", label="Done"),
        ],
    )
    xml = build_bpmn_xml(proc)

    assert "parallelGateway" in xml
    assert "split" in xml
    assert "sync" in xml


def test_build_condition_expression() -> None:
    """build_bpmn_xml adds conditionExpression for branches."""
    xml = build_bpmn_xml(GATEWAY_PROCESS)

    assert "conditionExpression" in xml
    assert "Yes" in xml
    assert "No" in xml


# --- Validation errors ---


def test_build_invalid_json_string() -> None:
    """build_bpmn_xml raises ValidationError for invalid JSON."""
    with pytest.raises(ValidationError, match="Invalid JSON"):
        build_bpmn_xml("{not valid json")


def test_build_missing_steps_key() -> None:
    """build_bpmn_xml raises ValidationError when 'steps' is missing."""
    with pytest.raises(ValidationError, match="non-empty 'steps'"):
        build_bpmn_xml({"elements": []})


def test_build_empty_steps() -> None:
    """build_bpmn_xml raises ValidationError for empty steps."""
    with pytest.raises(ValidationError, match="non-empty 'steps'"):
        build_bpmn_xml({"steps": []})


# --- Element types ---


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
    steps: list[dict] = [
        {
            "id": "start",
            "type": "startEvent",
            "label": "Start",
            "branches": None,
            "next": None,
        },
    ]
    for i, t in enumerate(types):
        steps.append(
            {
                "id": f"t_{i}",
                "type": t,
                "label": t,
                "branches": None,
                "next": None,
            }
        )
    steps.append(
        {
            "id": "end",
            "type": "endEvent",
            "label": "End",
            "branches": None,
            "next": None,
        }
    )

    xml = build_bpmn_xml({"steps": steps, "lanes": None})

    for t in types:
        assert t in xml


# --- Explicit jumps ---


def test_explicit_next_creates_flow() -> None:
    """next field creates a sequence flow to a non-adjacent step."""
    proc = BpmnProcess(
        steps=[
            BpmnStep(id="start", type="startEvent", label="Start"),
            BpmnStep(
                id="gw",
                type="exclusive",
                label="Check",
                branches=[
                    BpmnBranch(condition="Fast", target="end"),
                    BpmnBranch(condition="Slow", target="task_b"),
                ],
            ),
            BpmnStep(id="task_b", type="task", label="B"),
            BpmnStep(id="end", type="endEvent", label="End"),
        ],
    )
    xml = build_bpmn_xml(proc)

    # Gateway branch should jump to "end" directly
    assert 'sourceRef="gw" targetRef="end"' in xml
    # Other branch goes to task_b
    assert 'sourceRef="gw" targetRef="task_b"' in xml


# --- Swimlanes ---


def test_build_with_lanes() -> None:
    """build_bpmn_xml produces laneSet when lanes are defined."""
    proc = BpmnProcess(
        steps=[
            BpmnStep(id="start", type="startEvent", label="Start"),
            BpmnStep(id="task_a", type="task", label="A"),
            BpmnStep(id="end", type="endEvent", label="End"),
        ],
        lanes=[
            {"name": "Manager", "steps": ["start", "task_a"]},
            {"name": "Worker", "steps": ["end"]},
        ],
    )
    xml = build_bpmn_xml(proc)

    assert "laneSet" in xml
    assert "Manager" in xml
    assert "Worker" in xml
    assert "collaboration" in xml
    assert "participant" in xml


def test_build_and_layout_with_lanes() -> None:
    """End-to-end: build XML with lanes, then layout produces valid DI."""

    proc = BpmnProcess(
        steps=[
            BpmnStep(id="start", type="startEvent", label="Start"),
            BpmnStep(id="task_a", type="task", label="A"),
            BpmnStep(id="task_b", type="task", label="B"),
            BpmnStep(id="end", type="endEvent", label="End"),
        ],
        lanes=[
            {"name": "Manager", "steps": ["start", "task_a"]},
            {"name": "Worker", "steps": ["task_b", "end"]},
        ],
    )
    xml = build_bpmn_xml(proc)
    result = add_diagram_layout(xml)

    assert "bpmndi:BPMNDiagram" in result
    assert 'bpmnElement="Collaboration_1"' in result
    assert 'bpmnElement="Participant_1"' in result
    assert 'bpmnElement="Lane_1"' in result
    assert 'bpmnElement="Lane_2"' in result
    assert 'isHorizontal="true"' in result
