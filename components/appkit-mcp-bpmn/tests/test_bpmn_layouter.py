"""Tests for BPMN auto-layout engine (grid-based, ported from bpmn-auto-layout)."""

from appkit_mcp_bpmn.services.bpmn_layouter import (
    BpmnNode,
    _build_element_graph,
    _get_default_size,
    _is_type,
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

# Linear: Start -> Task -> End
LINEAR_XML = """
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1">
    <bpmn:startEvent id="Start_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:task id="Task_1" name="Do Work">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:task>
    <bpmn:endEvent id="End_1">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1" targetRef="Task_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="End_1" />
  </bpmn:process>
</bpmn:definitions>
"""

# Gateway: Start -> XGW -> Task A / Task B -> End
GATEWAY_XML = """
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1">
    <bpmn:startEvent id="Start_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:exclusiveGateway id="GW_1">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
      <bpmn:outgoing>Flow_3</bpmn:outgoing>
    </bpmn:exclusiveGateway>
    <bpmn:task id="Task_A" name="Path A">
      <bpmn:incoming>Flow_2</bpmn:incoming>
      <bpmn:outgoing>Flow_4</bpmn:outgoing>
    </bpmn:task>
    <bpmn:task id="Task_B" name="Path B">
      <bpmn:incoming>Flow_3</bpmn:incoming>
      <bpmn:outgoing>Flow_5</bpmn:outgoing>
    </bpmn:task>
    <bpmn:endEvent id="End_1">
      <bpmn:incoming>Flow_4</bpmn:incoming>
      <bpmn:incoming>Flow_5</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1" targetRef="GW_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="GW_1" targetRef="Task_A" />
    <bpmn:sequenceFlow id="Flow_3" sourceRef="GW_1" targetRef="Task_B" />
    <bpmn:sequenceFlow id="Flow_4" sourceRef="Task_A" targetRef="End_1" />
    <bpmn:sequenceFlow id="Flow_5" sourceRef="Task_B" targetRef="End_1" />
  </bpmn:process>
</bpmn:definitions>
"""


# -- _build_element_graph tests ---


def test_build_element_graph_linear() -> None:
    """Build graph for a linear process and verify nodes and flows."""
    root = _parse_root(LINEAR_XML)
    ns = "http://www.omg.org/spec/BPMN/20100524/MODEL"
    process = root.find(f".//{{{ns}}}process")
    assert process is not None

    elements, flows = _build_element_graph(process)

    assert any(e.id == "Start_1" for e in elements)
    assert any(e.id == "Task_1" for e in elements)
    assert any(e.id == "End_1" for e in elements)
    assert len(elements) == 3
    assert len(flows) == 2

    # Check outgoing/incoming references
    start_node = next(e for e in elements if e.id == "Start_1")
    assert len(start_node.outgoing) == 1
    assert start_node.outgoing[0].target_ref.id == "Task_1"


def test_build_element_graph_cyclic() -> None:
    """Build graph for a cyclic process and verify flow references."""
    root = _parse_root(CYCLIC_XML)
    ns = "http://www.omg.org/spec/BPMN/20100524/MODEL"
    process = root.find(f".//{{{ns}}}process")
    assert process is not None

    elements, flows = _build_element_graph(process)

    assert len(elements) == 3
    assert len(flows) == 3

    task_b = next(e for e in elements if e.id == "Task_B")
    assert len(task_b.outgoing) == 1
    assert task_b.outgoing[0].target_ref.id == "Task_A"


# -- _is_type tests ---


def test_is_type_task() -> None:
    """_is_type matches task variants."""
    node = BpmnNode(id="t1", local_type="task")
    assert _is_type(node, "bpmn:Task")


def test_is_type_gateway() -> None:
    """_is_type matches gateway variants."""
    node = BpmnNode(id="g1", local_type="exclusiveGateway")
    assert _is_type(node, "bpmn:Gateway")
    assert _is_type(node, "bpmn:ExclusiveGateway")


def test_is_type_event() -> None:
    """_is_type matches event variants."""
    node = BpmnNode(id="e1", local_type="startEvent")
    assert _is_type(node, "bpmn:Event")


def test_is_type_negative() -> None:
    """_is_type returns False for non-matching types."""
    node = BpmnNode(id="t1", local_type="task")
    assert not _is_type(node, "bpmn:Gateway")
    assert not _is_type(node, "bpmn:Event")
    assert not _is_type(node, "bpmn:UnknownType")


# -- _get_default_size tests ---


def test_default_size_task() -> None:
    """Tasks get 100x80."""
    node = BpmnNode(id="t1", local_type="task")
    assert _get_default_size(node) == (100, 80)


def test_default_size_gateway() -> None:
    """Gateways get 50x50."""
    node = BpmnNode(id="g1", local_type="exclusiveGateway")
    assert _get_default_size(node) == (50, 50)


def test_default_size_event() -> None:
    """Events get 36x36."""
    node = BpmnNode(id="e1", local_type="startEvent")
    assert _get_default_size(node) == (36, 36)


# -- End-to-end layout tests ---


def test_layout_linear_process() -> None:
    """Layout a simple Start -> Task -> End process."""
    result_xml = add_diagram_layout(LINEAR_XML)

    assert "bpmndi:BPMNDiagram" in result_xml
    assert "bpmndi:BPMNShape" in result_xml
    assert 'bpmnElement="Start_1"' in result_xml
    assert 'bpmnElement="Task_1"' in result_xml
    assert 'bpmnElement="End_1"' in result_xml

    # Edges should be present
    assert 'bpmnElement="Flow_1"' in result_xml
    assert 'bpmnElement="Flow_2"' in result_xml


def test_layout_cyclic_graph_end_to_end() -> None:
    """Ensure add_diagram_layout generates layout for cyclic graphs."""
    result_xml = add_diagram_layout(CYCLIC_XML)

    assert "bpmndi:BPMNDiagram" in result_xml
    assert "bpmndi:BPMNShape" in result_xml
    assert 'bpmnElement="Task_A"' in result_xml
    assert 'bpmnElement="Task_B"' in result_xml


def test_layout_gateway_process() -> None:
    """Layout a process with an exclusive gateway branching."""
    result_xml = add_diagram_layout(GATEWAY_XML)

    assert "bpmndi:BPMNDiagram" in result_xml
    assert 'bpmnElement="GW_1"' in result_xml
    assert 'bpmnElement="Task_A"' in result_xml
    assert 'bpmnElement="Task_B"' in result_xml
    assert 'bpmnElement="End_1"' in result_xml


def test_back_edge_routing_logic() -> None:
    """Ensure back-edges (Flow_3: B->A) have extended waypoints."""
    result_xml = add_diagram_layout(CYCLIC_XML)

    assert 'bpmnElement="Flow_3"' in result_xml

    root = _parse_root(result_xml)

    edges = root.xpath(".//*[local-name()='BPMNEdge']")
    target_edge = next((e for e in edges if e.get("bpmnElement") == "Flow_3"), None)

    assert target_edge is not None, "Back-edge Flow_3 not found in DI"

    waypoints = target_edge.xpath(".//*[local-name()='waypoint']")
    assert len(waypoints) >= 3, (
        f"Expected at least 3 waypoints for back-edge, got {len(waypoints)}"
    )


def test_layout_shapes_have_bounds() -> None:
    """All shapes in output must have valid bounds attributes."""
    result_xml = add_diagram_layout(LINEAR_XML)
    root = _parse_root(result_xml)

    shapes = root.xpath(".//*[local-name()='BPMNShape']")
    assert len(shapes) == 3

    for shape in shapes:
        bounds_list = shape.xpath(".//*[local-name()='Bounds']")
        bounds = bounds_list[0] if bounds_list else None
        assert bounds is not None, f"Shape {shape.get('bpmnElement')} missing Bounds"
        assert float(bounds.get("x")) >= 0
        assert float(bounds.get("y")) >= 0
        assert float(bounds.get("width")) > 0
        assert float(bounds.get("height")) > 0


def test_layout_edges_have_waypoints() -> None:
    """All edges in output must have at least 2 waypoints."""
    result_xml = add_diagram_layout(LINEAR_XML)
    root = _parse_root(result_xml)

    edges = root.xpath(".//*[local-name()='BPMNEdge']")
    assert len(edges) == 2

    for edge in edges:
        waypoints = edge.xpath(".//*[local-name()='waypoint']")
        assert len(waypoints) >= 2, (
            f"Edge {edge.get('bpmnElement')} has {len(waypoints)} waypoints"
        )
