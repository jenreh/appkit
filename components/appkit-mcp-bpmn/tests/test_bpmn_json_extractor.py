"""Tests for bpmn_json_extractor — XML → flat JSON extraction."""

import pytest

from appkit_mcp_bpmn.services.bpmn_json_extractor import extract_process_json
from appkit_mcp_commons.exceptions import ValidationError

# ---- Fixtures ----

SIMPLE_BPMN = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="start" name="Start" />
    <bpmn:task id="task_1" name="Do work" />
    <bpmn:endEvent id="end" name="Done" />
    <bpmn:sequenceFlow id="Flow_1" sourceRef="start" targetRef="task_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="task_1" targetRef="end" />
  </bpmn:process>
</bpmn:definitions>
"""

GATEWAY_BPMN = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="start" name="Start" />
    <bpmn:exclusiveGateway id="gw" name="OK?" />
    <bpmn:task id="task_yes" name="Approved" />
    <bpmn:task id="task_no" name="Rejected" />
    <bpmn:endEvent id="end" name="Done" />
    <bpmn:sequenceFlow id="Flow_1" sourceRef="start" targetRef="gw" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="gw" targetRef="task_yes" name="Yes" />
    <bpmn:sequenceFlow id="Flow_3" sourceRef="gw" targetRef="task_no" name="No" />
    <bpmn:sequenceFlow id="Flow_4" sourceRef="task_yes" targetRef="end" />
    <bpmn:sequenceFlow id="Flow_5" sourceRef="task_no" targetRef="end" />
  </bpmn:process>
</bpmn:definitions>
"""

LANES_BPMN = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:laneSet id="LaneSet_1">
      <bpmn:lane id="Lane_1" name="Manager">
        <bpmn:flowNodeRef>start</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>task_1</bpmn:flowNodeRef>
      </bpmn:lane>
      <bpmn:lane id="Lane_2" name="Finance">
        <bpmn:flowNodeRef>end</bpmn:flowNodeRef>
      </bpmn:lane>
    </bpmn:laneSet>
    <bpmn:startEvent id="start" name="Start" />
    <bpmn:task id="task_1" name="Do work" />
    <bpmn:endEvent id="end" name="Done" />
    <bpmn:sequenceFlow id="Flow_1" sourceRef="start" targetRef="task_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="task_1" targetRef="end" />
  </bpmn:process>
</bpmn:definitions>
"""

EXPLICIT_NEXT_BPMN = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="start" name="Start" />
    <bpmn:task id="task_a" name="Task A" />
    <bpmn:task id="task_b" name="Task B" />
    <bpmn:endEvent id="end" name="Done" />
    <bpmn:sequenceFlow id="Flow_1" sourceRef="start" targetRef="task_b" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="task_b" targetRef="task_a" />
    <bpmn:sequenceFlow id="Flow_3" sourceRef="task_a" targetRef="end" />
  </bpmn:process>
</bpmn:definitions>
"""

LAYOUT_BPMN = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="start" name="Start" />
    <bpmn:endEvent id="end" name="Done" />
    <bpmn:sequenceFlow id="Flow_1" sourceRef="start" targetRef="end" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
      <bpmndi:BPMNShape id="start_di" bpmnElement="start">
        <dc:Bounds x="100" y="100" width="36" height="36" />
      </bpmndi:BPMNShape>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>
"""


# ---- Tests ----


def test_extract_simple_linear_flow() -> None:
    """Extracts steps from a simple start → task → end flow."""
    result = extract_process_json(SIMPLE_BPMN)

    assert result["lanes"] is None
    steps = result["steps"]
    assert len(steps) == 3

    assert steps[0]["id"] == "start"
    assert steps[0]["type"] == "startEvent"
    assert steps[0]["label"] == "Start"
    assert steps[0]["branches"] is None
    assert steps[0]["next"] == "task_1"  # explicit target

    assert steps[1]["id"] == "task_1"
    assert steps[1]["type"] == "task"
    assert steps[1]["next"] == "end"  # explicit target

    assert steps[2]["id"] == "end"
    assert steps[2]["type"] == "endEvent"


def test_extract_gateway_branches() -> None:
    """Extracts exclusive gateway with branches."""
    result = extract_process_json(GATEWAY_BPMN)
    steps = result["steps"]

    gw = next(s for s in steps if s["id"] == "gw")
    assert gw["type"] == "exclusive"
    assert gw["branches"] is not None
    assert len(gw["branches"]) == 2

    targets = {b["target"] for b in gw["branches"]}
    assert targets == {"task_yes", "task_no"}

    conditions = {b["condition"] for b in gw["branches"]}
    assert "Yes" in conditions
    assert "No" in conditions


def test_extract_lanes() -> None:
    """Extracts lane definitions."""
    result = extract_process_json(LANES_BPMN)

    assert result["lanes"] is not None
    assert len(result["lanes"]) == 2

    manager_lane = result["lanes"][0]
    assert manager_lane["name"] == "Manager"
    assert "start" in manager_lane["steps"]
    assert "task_1" in manager_lane["steps"]

    finance_lane = result["lanes"][1]
    assert finance_lane["name"] == "Finance"
    assert "end" in finance_lane["steps"]


def test_extract_explicit_next() -> None:
    """Detects explicit jumps (non-sequential flow targets)."""
    result = extract_process_json(EXPLICIT_NEXT_BPMN)
    steps = result["steps"]

    start = next(s for s in steps if s["id"] == "start")
    # start → task_b (skips task_a in list order), so explicit next
    assert start["next"] == "task_b"

    task_b = next(s for s in steps if s["id"] == "task_b")
    # task_b → task_a (backwards jump), explicit next
    assert task_b["next"] == "task_a"

    task_a = next(s for s in steps if s["id"] == "task_a")
    # task_a → end, also explicit now
    assert task_a["next"] == "end"


def test_extract_strips_layout() -> None:
    """BPMNDiagram element is ignored during extraction."""
    result = extract_process_json(LAYOUT_BPMN)

    steps = result["steps"]
    assert len(steps) == 2
    assert steps[0]["type"] == "startEvent"
    assert steps[1]["type"] == "endEvent"


def test_extract_invalid_xml() -> None:
    """Raises ValidationError on malformed XML."""
    with pytest.raises(ValidationError, match="Invalid XML"):
        extract_process_json("<not valid xml")


def test_extract_missing_process() -> None:
    """Raises ValidationError when no process element exists."""
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn">
</bpmn:definitions>
"""
    with pytest.raises(ValidationError, match=r"No.*process"):
        extract_process_json(xml)


def test_roundtrip_simple_flow() -> None:
    """Extract JSON from XML built by bpmn_xml_builder (roundtrip)."""
    from appkit_mcp_bpmn.services.bpmn_xml_builder import build_bpmn_xml

    source_json = {
        "steps": [
            {
                "id": "start",
                "type": "startEvent",
                "label": "Begin",
                "branches": None,
                "next": None,
            },
            {
                "id": "do_work",
                "type": "task",
                "label": "Do Work",
                "branches": None,
                "next": None,
            },
            {
                "id": "end",
                "type": "endEvent",
                "label": "Finish",
                "branches": None,
                "next": None,
            },
        ],
        "lanes": None,
    }
    xml = build_bpmn_xml(source_json)
    extracted = extract_process_json(xml)

    assert len(extracted["steps"]) == 3
    assert extracted["steps"][0]["id"] == "start"
    assert extracted["steps"][0]["type"] == "startEvent"
    assert extracted["steps"][1]["id"] == "do_work"
    assert extracted["steps"][1]["type"] == "task"
    assert extracted["steps"][2]["id"] == "end"
    assert extracted["steps"][2]["type"] == "endEvent"
    assert extracted["lanes"] is None


PARALLEL_BPMN = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="start" name="Start" />
    <bpmn:parallelGateway id="split" name="Fork" />
    <bpmn:task id="task_a" name="Task A" />
    <bpmn:task id="task_b" name="Task B" />
    <bpmn:parallelGateway id="join" name="Join" />
    <bpmn:endEvent id="end" name="Done" />
    <bpmn:sequenceFlow id="f1" sourceRef="start" targetRef="split" />
    <bpmn:sequenceFlow id="f2" sourceRef="split" targetRef="task_a" />
    <bpmn:sequenceFlow id="f3" sourceRef="split" targetRef="task_b" />
    <bpmn:sequenceFlow id="f4" sourceRef="task_a" targetRef="join" />
    <bpmn:sequenceFlow id="f5" sourceRef="task_b" targetRef="join" />
    <bpmn:sequenceFlow id="f6" sourceRef="join" targetRef="end" />
  </bpmn:process>
</bpmn:definitions>
"""


def test_extract_parallel_split_and_merge() -> None:
    """Parallel gateway with 2+ outgoing flows is 'parallel', not 'merge'."""
    result = extract_process_json(PARALLEL_BPMN)
    steps = result["steps"]

    split = next(s for s in steps if s["id"] == "split")
    assert split["type"] == "parallel"
    assert split["branches"] is not None
    assert len(split["branches"]) == 2
    targets = {b["target"] for b in split["branches"]}
    assert targets == {"task_a", "task_b"}

    join = next(s for s in steps if s["id"] == "join")
    assert join["type"] == "merge"
    assert join["branches"] is None
    assert join["next"] == "end"


LOOP_BPMN = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="start" name="Start" />
    <bpmn:task id="task_a" name="Cart" />
    <bpmn:exclusiveGateway id="gw" name="More?" />
    <bpmn:task id="change" name="Change" />
    <bpmn:endEvent id="end" name="Done" />
    <bpmn:sequenceFlow id="f1" sourceRef="start" targetRef="task_a" />
    <bpmn:sequenceFlow id="f2" sourceRef="task_a" targetRef="gw" />
    <bpmn:sequenceFlow id="f3" sourceRef="gw" targetRef="end" name="No" />
    <bpmn:sequenceFlow id="f4" sourceRef="gw" targetRef="change" name="" />
    <bpmn:sequenceFlow id="f5" sourceRef="change" targetRef="task_a" />
  </bpmn:process>
</bpmn:definitions>
"""


def test_extract_loop_with_back_edge() -> None:
    """Gateway branch to a step that loops back is extracted correctly."""
    result = extract_process_json(LOOP_BPMN)
    steps = result["steps"]

    gw = next(s for s in steps if s["id"] == "gw")
    assert gw["type"] == "exclusive"
    targets = {b["target"] for b in gw["branches"]}
    assert "change" in targets
    assert "end" in targets

    change = next(s for s in steps if s["id"] == "change")
    assert change["next"] == "task_a"  # back-edge to earlier step


MULTI_OUTGOING_BPMN = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="start" name="Start" />
    <bpmn:task id="task_a" name="Process" />
    <bpmn:task id="task_b" name="Notify" />
    <bpmn:task id="task_c" name="Log" />
    <bpmn:endEvent id="end" name="Done" />
    <bpmn:sequenceFlow id="f1" sourceRef="start" targetRef="task_a" />
    <bpmn:sequenceFlow id="f2" sourceRef="task_a" targetRef="task_b" />
    <bpmn:sequenceFlow id="f3" sourceRef="task_a" targetRef="task_c" />
    <bpmn:sequenceFlow id="f4" sourceRef="task_b" targetRef="end" />
    <bpmn:sequenceFlow id="f5" sourceRef="task_c" targetRef="end" />
  </bpmn:process>
</bpmn:definitions>
"""


def test_extract_non_gateway_multiple_outgoing() -> None:
    """Non-gateway element with multiple outgoing flows uses branches."""
    result = extract_process_json(MULTI_OUTGOING_BPMN)
    steps = result["steps"]

    task_a = next(s for s in steps if s["id"] == "task_a")
    # task_a has 2 outgoing flows → should use branches, not next
    assert task_a["next"] is None
    assert task_a["branches"] is not None
    assert len(task_a["branches"]) == 2
    targets = {b["target"] for b in task_a["branches"]}
    assert targets == {"task_b", "task_c"}

    # Single outgoing still uses next
    task_b = next(s for s in steps if s["id"] == "task_b")
    assert task_b["next"] == "end"
    assert task_b["branches"] is None
