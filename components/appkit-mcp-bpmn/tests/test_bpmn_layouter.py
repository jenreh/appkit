"""Tests for BPMN auto-layout engine, specifically for cyclic graphs."""

from appkit_mcp_bpmn.services.bpmn_layouter import (
    _assign_layers,
    _build_graph,
    _identify_back_edges,
    _parse_root,
    add_diagram_layout,
)

# A simple BPMN with a loop: Start -> Task A -> Task B -> Task A (loop)
CYCLIC_XML = """
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1">
    <bpmn:startEvent id="StartEvent_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:task id="Task_A" name="A">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:incoming>Flow_3</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:task>
    <bpmn:task id="Task_B" name="B">
      <bpmn:incoming>Flow_2</bpmn:incoming>
      <bpmn:outgoing>Flow_3</bpmn:outgoing>
    </bpmn:task>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Task_A" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_A" targetRef="Task_B" />
    <bpmn:sequenceFlow id="Flow_3" sourceRef="Task_B" targetRef="Task_A" />
  </bpmn:process>
</bpmn:definitions>
"""


def test_layout_cyclic_graph_end_to_end() -> None:
    """Ensure add_diagram_layout generates layout for cyclic graphs without hanging."""
    # This call should return almost instantly. If it hangs,
    # the test framework will eventualy time out.
    result_xml = add_diagram_layout(CYCLIC_XML)

    # Basic assertions to ensure layout was generated
    assert "bpmndi:BPMNDiagram" in result_xml
    assert "bpmndi:BPMNShape" in result_xml
    assert 'bpmnElement="Task_A"' in result_xml
    assert 'bpmnElement="Task_B"' in result_xml


def test_identify_back_edges() -> None:
    """Test standard DFS cycle detection."""
    # Graph: Start -> A -> B -> A
    # Back edge should be B -> A if we start from Start
    nodes = {
        "Start": "startEvent",
        "A": "task",
        "B": "task",
    }
    outgoing = {
        "Start": ["A"],
        "A": ["B"],
        "B": ["A"],
    }

    # Since dictionary order is preserved, and we iterate keys,
    # forcing Start first ensures we see the cycle relative to natural flow.
    back_edges = _identify_back_edges(nodes, outgoing)

    assert back_edges == {("B", "A")}


def test_assign_layers_cyclic() -> None:
    """Test that layers are correctly assigned despite cycles."""
    root = _parse_root(CYCLIC_XML)
    process = root.find(".//{http://www.omg.org/spec/BPMN/20100524/MODEL}process")
    assert process is not None

    nodes, outgoing, incoming, _ = _build_graph(process)

    # This should not hang
    layers = _assign_layers(nodes, outgoing, incoming)

    # Expected layers: Start(0) -> A(1) -> B(2)
    # The back-edge B->A is ignored
    assert layers["StartEvent_1"] == 0
    assert layers["Task_A"] == 1
    assert layers["Task_B"] == 2


def test_back_edge_routing_logic() -> None:
    """Ensure back-edges (Process Flow 3: B->A) have extended waypoints."""
    # Flow_3 goes from Task_B (Layer 2) back to Task_A (Layer 1).
    result_xml = add_diagram_layout(CYCLIC_XML)

    # Check simple string presence first to confirm generation
    assert 'bpmnElement="Flow_3"' in result_xml

    # Parse to check waypoints
    root = _parse_root(result_xml)

    # Helper to find edge. lxml needs namespaces map or wildcard
    # Using local-name wildcard for robustness in test
    edges = root.xpath(".//*[local-name()='BPMNEdge']")
    target_edge = next((e for e in edges if e.get("bpmnElement") == "Flow_3"), None)

    assert target_edge is not None, "Back-edge Flow_3 not found in DI structure"

    waypoints = target_edge.findall(".//*[local-name()='waypoint']")
    assert len(waypoints) == 5, (
        f"Expected 5 waypoints for back-edge, got {len(waypoints)}"
    )

    # Check vertical routing
    ys = [float(wp.get("y")) for wp in waypoints]
    start_y = ys[0]
    gutter_y = ys[2]

    assert gutter_y > start_y + 30, (
        "Back-edge should route significantly below the start node"
    )
