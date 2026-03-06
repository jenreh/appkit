"""Tests for BPMN auto-layout engine (grid-based, ported from bpmn-auto-layout)."""

import pytest

from appkit_mcp_bpmn.services.bpmn_lane_layout import POOL_HEADER_WIDTH
from appkit_mcp_bpmn.services.bpmn_layouter import (
    BpmnNode,
    FlowRef,
    _build_element_graph,
    _check_for_loop,
    _coordinates_to_position,
    _find_element_in_tree,
    _find_process,
    _get_bounds,
    _get_default_size,
    _get_docking_point,
    _get_mid,
    _has_existing_layout,
    _has_other_incoming,
    _is_boundary_event,
    _is_connection,
    _is_future_incoming,
    _is_next_element_tasks,
    _is_type,
    _local,
    _parse_root,
    _remove_existing_diagrams,
    _sign,
    _sort_by_type,
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


# -- Helper function tests -------------------------------------------------


def test_local_extracts_local_name() -> None:
    assert _local("{http://www.example.com}task") == "task"
    assert _local("task") == "task"


def test_is_connection() -> None:
    node = BpmnNode(id="f1", local_type="sequenceFlow")
    assert _is_connection(node)
    node2 = BpmnNode(id="t1", local_type="task")
    assert not _is_connection(node2)


def test_is_boundary_event() -> None:
    node_without = BpmnNode(id="e1", local_type="boundaryEvent")
    assert not _is_boundary_event(node_without)
    host = BpmnNode(id="t1", local_type="task")
    node_with = BpmnNode(
        id="e2",
        local_type="boundaryEvent",
        attached_to_ref=host,
    )
    assert _is_boundary_event(node_with)


def test_find_process_returns_none_for_missing() -> None:
    xml = '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"/>'
    root = _parse_root(xml)
    assert _find_process(root) is None


def test_has_existing_layout_false() -> None:
    root = _parse_root(LINEAR_XML)
    assert not _has_existing_layout(root)


def test_has_existing_layout_true() -> None:
    result = add_diagram_layout(LINEAR_XML)
    root = _parse_root(result)
    assert _has_existing_layout(root)


def test_remove_existing_diagrams() -> None:
    result_xml = add_diagram_layout(LINEAR_XML)
    root = _parse_root(result_xml)
    assert _has_existing_layout(root)
    _remove_existing_diagrams(root)
    assert not _has_existing_layout(root)


def test_sign_positive() -> None:
    assert _sign(5) == 1


def test_sign_negative() -> None:
    assert _sign(-3) == -1


def test_sign_zero() -> None:
    assert _sign(0) == 0


def test_get_mid() -> None:
    bounds = {"x": 100, "y": 200, "width": 50, "height": 80}
    mid = _get_mid(bounds)
    assert mid["x"] == 125.0
    assert mid["y"] == 240.0


def test_get_docking_point_right() -> None:
    mid = {"x": 125.0, "y": 240.0}
    rect = {"x": 100, "y": 200, "width": 50, "height": 80}
    dp = _get_docking_point(mid, rect, "r")
    assert dp["x"] == 150.0
    assert dp["y"] == 240.0


def test_get_docking_point_left() -> None:
    mid = {"x": 125.0, "y": 240.0}
    rect = {"x": 100, "y": 200, "width": 50, "height": 80}
    dp = _get_docking_point(mid, rect, "l")
    assert dp["x"] == 100.0


def test_get_docking_point_top() -> None:
    mid = {"x": 125.0, "y": 240.0}
    rect = {"x": 100, "y": 200, "width": 50, "height": 80}
    dp = _get_docking_point(mid, rect, "t")
    assert dp["y"] == 200.0


def test_get_docking_point_bottom() -> None:
    mid = {"x": 125.0, "y": 240.0}
    rect = {"x": 100, "y": 200, "width": 50, "height": 80}
    dp = _get_docking_point(mid, rect, "b")
    assert dp["y"] == 280.0


def test_get_docking_point_h_left() -> None:
    mid = {"x": 125.0, "y": 240.0}
    rect = {"x": 100, "y": 200, "width": 50, "height": 80}
    dp = _get_docking_point(mid, rect, "h", "top-left")
    assert dp["x"] == 100.0


def test_get_docking_point_h_right() -> None:
    mid = {"x": 125.0, "y": 240.0}
    rect = {"x": 100, "y": 200, "width": 50, "height": 80}
    dp = _get_docking_point(mid, rect, "h", "top-right")
    assert dp["x"] == 150.0


def test_get_docking_point_v_top() -> None:
    mid = {"x": 125.0, "y": 240.0}
    rect = {"x": 100, "y": 200, "width": 50, "height": 80}
    dp = _get_docking_point(mid, rect, "v", "top-left")
    assert dp["y"] == 200.0


def test_get_docking_point_v_bottom() -> None:
    mid = {"x": 125.0, "y": 240.0}
    rect = {"x": 100, "y": 200, "width": 50, "height": 80}
    dp = _get_docking_point(mid, rect, "v", "bottom-left")
    assert dp["y"] == 280.0


def test_get_bounds_basic_task() -> None:
    node = BpmnNode(id="t1", local_type="task")
    bounds = _get_bounds(node, 0, 0, {"x": 0, "y": 0})
    assert bounds["width"] == 100
    assert bounds["height"] == 80
    assert bounds["x"] >= 0
    assert bounds["y"] >= 0


def test_get_bounds_with_shift() -> None:
    node = BpmnNode(id="t1", local_type="task")
    b1 = _get_bounds(node, 0, 0, {"x": 0, "y": 0})
    b2 = _get_bounds(node, 0, 0, {"x": 50, "y": 30})
    assert b2["x"] == b1["x"] + 50
    assert b2["y"] == b1["y"] + 30


def test_layout_skips_existing_layout() -> None:
    """add_diagram_layout returns unchanged XML if layout exists."""
    result1 = add_diagram_layout(LINEAR_XML)
    result2 = add_diagram_layout(result1)
    assert result2 == result1


def test_layout_no_process() -> None:
    """add_diagram_layout returns unchanged XML if no process found."""
    xml = '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"/>'
    assert add_diagram_layout(xml) == xml


def test_default_size_subprocess() -> None:
    node = BpmnNode(id="sp1", local_type="subProcess")
    assert _get_default_size(node) == (100, 80)


def test_default_size_data_object() -> None:
    node = BpmnNode(id="d1", local_type="dataObjectReference")
    assert _get_default_size(node) == (36, 50)


def test_default_size_text_annotation() -> None:
    node = BpmnNode(id="a1", local_type="textAnnotation")
    assert _get_default_size(node) == (100, 30)


def test_default_size_unknown_type() -> None:
    node = BpmnNode(id="u1", local_type="totallyUnknown")
    w, h = _get_default_size(node)
    assert w == 100
    assert h == 80


# -- Boundary event layout test --

BOUNDARY_XML = """\
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1">
    <bpmn:startEvent id="Start_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:task id="Task_1" name="Do Work">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:task>
    <bpmn:boundaryEvent id="Boundary_1" attachedToRef="Task_1">
      <bpmn:outgoing>Flow_3</bpmn:outgoing>
    </bpmn:boundaryEvent>
    <bpmn:endEvent id="End_1">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:task id="Task_Error" name="Handle Error">
      <bpmn:incoming>Flow_3</bpmn:incoming>
      <bpmn:outgoing>Flow_4</bpmn:outgoing>
    </bpmn:task>
    <bpmn:endEvent id="End_2">
      <bpmn:incoming>Flow_4</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1"
                       targetRef="Task_1"/>
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_1"
                       targetRef="End_1"/>
    <bpmn:sequenceFlow id="Flow_3" sourceRef="Boundary_1"
                       targetRef="Task_Error"/>
    <bpmn:sequenceFlow id="Flow_4" sourceRef="Task_Error"
                       targetRef="End_2"/>
  </bpmn:process>
</bpmn:definitions>
"""


def test_layout_boundary_event() -> None:
    """Layout with a boundary event produces shapes for all."""
    result_xml = add_diagram_layout(BOUNDARY_XML)
    assert 'bpmnElement="Boundary_1"' in result_xml
    assert 'bpmnElement="Task_Error"' in result_xml
    root = _parse_root(result_xml)
    shapes = root.xpath(".//*[local-name()='BPMNShape']")
    assert len(shapes) >= 5


def test_build_graph_boundary_event() -> None:
    """Boundary events get attached_to_ref set."""
    root = _parse_root(BOUNDARY_XML)
    ns = "http://www.omg.org/spec/BPMN/20100524/MODEL"
    process = root.find(f".//{{{ns}}}process")
    elements, _flows = _build_element_graph(process)
    boundary = next(e for e in elements if e.id == "Boundary_1")
    assert boundary.attached_to_ref is not None
    assert boundary.attached_to_ref.id == "Task_1"
    host = next(e for e in elements if e.id == "Task_1")
    assert boundary in host.attachers


# -- Parallel gateway layout test --

PARALLEL_XML = """\
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1">
    <bpmn:startEvent id="Start_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:parallelGateway id="PGW_Split">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
      <bpmn:outgoing>Flow_3</bpmn:outgoing>
    </bpmn:parallelGateway>
    <bpmn:task id="Task_A" name="A">
      <bpmn:incoming>Flow_2</bpmn:incoming>
      <bpmn:outgoing>Flow_4</bpmn:outgoing>
    </bpmn:task>
    <bpmn:task id="Task_B" name="B">
      <bpmn:incoming>Flow_3</bpmn:incoming>
      <bpmn:outgoing>Flow_5</bpmn:outgoing>
    </bpmn:task>
    <bpmn:parallelGateway id="PGW_Join">
      <bpmn:incoming>Flow_4</bpmn:incoming>
      <bpmn:incoming>Flow_5</bpmn:incoming>
      <bpmn:outgoing>Flow_6</bpmn:outgoing>
    </bpmn:parallelGateway>
    <bpmn:endEvent id="End_1">
      <bpmn:incoming>Flow_6</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1"
                       targetRef="PGW_Split"/>
    <bpmn:sequenceFlow id="Flow_2" sourceRef="PGW_Split"
                       targetRef="Task_A"/>
    <bpmn:sequenceFlow id="Flow_3" sourceRef="PGW_Split"
                       targetRef="Task_B"/>
    <bpmn:sequenceFlow id="Flow_4" sourceRef="Task_A"
                       targetRef="PGW_Join"/>
    <bpmn:sequenceFlow id="Flow_5" sourceRef="Task_B"
                       targetRef="PGW_Join"/>
    <bpmn:sequenceFlow id="Flow_6" sourceRef="PGW_Join"
                       targetRef="End_1"/>
  </bpmn:process>
</bpmn:definitions>
"""


def test_layout_parallel_gateway() -> None:
    """Layout with parallel split-join produces all shapes and edges."""
    result = add_diagram_layout(PARALLEL_XML)
    assert 'bpmnElement="PGW_Split"' in result
    assert 'bpmnElement="PGW_Join"' in result
    root = _parse_root(result)
    shapes = root.xpath(".//*[local-name()='BPMNShape']")
    edges = root.xpath(".//*[local-name()='BPMNEdge']")
    assert len(shapes) == 6
    assert len(edges) == 6


# -- Sub process layout test --

SUBPROCESS_XML = """\
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1">
    <bpmn:startEvent id="Start_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:subProcess id="Sub_1" name="Sub">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:subProcess>
    <bpmn:endEvent id="End_1">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1"
                       targetRef="Sub_1"/>
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Sub_1"
                       targetRef="End_1"/>
  </bpmn:process>
</bpmn:definitions>
"""


def test_layout_subprocess() -> None:
    """Layout with a subprocess produces shapes for all elements."""
    result = add_diagram_layout(SUBPROCESS_XML)
    assert 'bpmnElement="Sub_1"' in result
    root = _parse_root(result)
    shapes = root.xpath(".//*[local-name()='BPMNShape']")
    assert len(shapes) == 3


# -- Empty process test --


def test_layout_empty_process() -> None:
    """Process with only sequence flows but no flow nodes."""
    xml = """\
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1">
    <bpmn:sequenceFlow id="F1" sourceRef="x" targetRef="y"/>
  </bpmn:process>
</bpmn:definitions>
"""
    result = add_diagram_layout(xml)
    assert result == xml


# -- Helper function tests (internal) --


def test_coordinates_to_position() -> None:
    pos = _coordinates_to_position(2, 3)
    assert pos["x"] > 0
    assert pos["y"] > 0
    assert pos["width"] > 0
    assert pos["height"] > 0


def test_is_next_element_tasks_all_tasks() -> None:
    nodes = [
        BpmnNode(id="t1", local_type="task"),
        BpmnNode(id="t2", local_type="userTask"),
    ]
    assert _is_next_element_tasks(nodes)


def test_is_next_element_tasks_mixed() -> None:
    nodes = [
        BpmnNode(id="t1", local_type="task"),
        BpmnNode(id="g1", local_type="exclusiveGateway"),
    ]
    assert not _is_next_element_tasks(nodes)


def test_sort_by_type() -> None:
    nodes = [
        BpmnNode(id="t1", local_type="task"),
        BpmnNode(id="g1", local_type="exclusiveGateway"),
        BpmnNode(id="t2", local_type="task"),
    ]
    result = _sort_by_type(nodes, "bpmn:Gateway")
    assert result[0].id == "g1"


def test_has_other_incoming_false() -> None:
    node = BpmnNode(id="t1", local_type="task")
    assert not _has_other_incoming(node)


def test_has_other_incoming_true() -> None:
    src = BpmnNode(id="src", local_type="task")
    tgt = BpmnNode(id="tgt", local_type="task")
    flow = FlowRef(id="f1", source_ref=src, target_ref=tgt)
    tgt.incoming.append(flow)
    assert _has_other_incoming(tgt)


def test_find_element_in_tree_found() -> None:
    a = BpmnNode(id="a", local_type="task")
    b = BpmnNode(id="b", local_type="task")
    flow = FlowRef(id="f1", source_ref=a, target_ref=b)
    a.outgoing.append(flow)
    assert _find_element_in_tree(a, b)


def test_find_element_in_tree_not_found() -> None:
    a = BpmnNode(id="a", local_type="task")
    b = BpmnNode(id="b", local_type="task")
    assert not _find_element_in_tree(a, b)


def test_find_element_in_tree_self() -> None:
    a = BpmnNode(id="a", local_type="task")
    assert _find_element_in_tree(a, a)


def test_is_future_incoming_false() -> None:
    node = BpmnNode(id="n", local_type="task")
    assert not _is_future_incoming(node, set())


def test_is_future_incoming_true() -> None:
    src1 = BpmnNode(id="s1", local_type="task")
    src2 = BpmnNode(id="s2", local_type="task")
    tgt = BpmnNode(id="tgt", local_type="task")
    f1 = FlowRef(id="f1", source_ref=src1, target_ref=tgt)
    f2 = FlowRef(id="f2", source_ref=src2, target_ref=tgt)
    tgt.incoming = [f1, f2]
    # s1 visited, s2 not - future incoming exists
    assert _is_future_incoming(tgt, {"s1"})


def test_check_for_loop_true() -> None:
    # a → b → c → a: when checking c, a is visited but c not
    a = BpmnNode(id="a", local_type="task")
    b = BpmnNode(id="b", local_type="task")
    c = BpmnNode(id="c", local_type="task")
    f1 = FlowRef(id="f1", source_ref=a, target_ref=b)
    f2 = FlowRef(id="f2", source_ref=b, target_ref=c)
    f3 = FlowRef(id="f3", source_ref=c, target_ref=a)
    a.outgoing = [f1]
    b.outgoing = [f2]
    c.outgoing = [f3]
    a.incoming = [f3]
    b.incoming = [f1]
    c.incoming = [f2]
    # c is the element, visited = {a, b}; incoming from b IS visited
    # Need c with incoming from an unvisited node that loops
    # Actually: check b with visited={a}:
    # b.incoming=[f1 from a] → a IS visited → skip
    # Let's test differently: a→b, c→b, b→c (loop)
    x = BpmnNode(id="x", local_type="task")
    y = BpmnNode(id="y", local_type="task")
    fx = FlowRef(id="fx", source_ref=x, target_ref=y)
    fy = FlowRef(id="fy", source_ref=y, target_ref=x)
    x.outgoing = [fx]
    y.outgoing = [fy]
    x.incoming = [fy]
    y.incoming = [fx]
    # check y, visited = {} → source x not in visited
    # _find_element_in_tree(y, x) → y→x→y found
    assert _check_for_loop(y, set())


def test_check_for_loop_false() -> None:
    a = BpmnNode(id="a", local_type="task")
    b = BpmnNode(id="b", local_type="task")
    f1 = FlowRef(id="f1", source_ref=a, target_ref=b)
    b.incoming = [f1]
    assert not _check_for_loop(b, {"a"})


def test_get_docking_point_invalid_direction() -> None:
    mid = {"x": 100.0, "y": 100.0}
    rect = {"x": 50, "y": 50, "width": 100, "height": 100}
    with pytest.raises(ValueError, match="Unexpected"):
        _get_docking_point(mid, rect, "z")


# -- Multiple back-edge overlap test --

MULTI_BACK_EDGE_XML = """\
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1">
    <bpmn:startEvent id="Start_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:userTask id="Task_Search" name="Search products">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:incoming>Flow_back_short</bpmn:incoming>
      <bpmn:incoming>Flow_back_long</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:userTask id="Task_View" name="View product">
      <bpmn:incoming>Flow_2</bpmn:incoming>
      <bpmn:outgoing>Flow_3</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:exclusiveGateway id="GW_1">
      <bpmn:incoming>Flow_3</bpmn:incoming>
      <bpmn:outgoing>Flow_4</bpmn:outgoing>
      <bpmn:outgoing>Flow_back_short</bpmn:outgoing>
    </bpmn:exclusiveGateway>
    <bpmn:userTask id="Task_Cart" name="Add to cart">
      <bpmn:incoming>Flow_4</bpmn:incoming>
      <bpmn:outgoing>Flow_5</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:userTask id="Task_ViewCart" name="View cart">
      <bpmn:incoming>Flow_5</bpmn:incoming>
      <bpmn:outgoing>Flow_6</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:exclusiveGateway id="GW_2">
      <bpmn:incoming>Flow_6</bpmn:incoming>
      <bpmn:outgoing>Flow_7</bpmn:outgoing>
      <bpmn:outgoing>Flow_8</bpmn:outgoing>
    </bpmn:exclusiveGateway>
    <bpmn:userTask id="Task_Continue" name="Continue shopping">
      <bpmn:incoming>Flow_7</bpmn:incoming>
      <bpmn:outgoing>Flow_back_long</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:userTask id="Task_Shipping" name="Enter shipping">
      <bpmn:incoming>Flow_8</bpmn:incoming>
      <bpmn:outgoing>Flow_9</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:endEvent id="End_1">
      <bpmn:incoming>Flow_9</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1"
                       targetRef="Task_Search"/>
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_Search"
                       targetRef="Task_View"/>
    <bpmn:sequenceFlow id="Flow_3" sourceRef="Task_View"
                       targetRef="GW_1"/>
    <bpmn:sequenceFlow id="Flow_4" sourceRef="GW_1"
                       targetRef="Task_Cart"/>
    <bpmn:sequenceFlow id="Flow_back_short" sourceRef="GW_1"
                       targetRef="Task_Search"/>
    <bpmn:sequenceFlow id="Flow_5" sourceRef="Task_Cart"
                       targetRef="Task_ViewCart"/>
    <bpmn:sequenceFlow id="Flow_6" sourceRef="Task_ViewCart"
                       targetRef="GW_2"/>
    <bpmn:sequenceFlow id="Flow_7" sourceRef="GW_2"
                       targetRef="Task_Continue"/>
    <bpmn:sequenceFlow id="Flow_8" sourceRef="GW_2"
                       targetRef="Task_Shipping"/>
    <bpmn:sequenceFlow id="Flow_9" sourceRef="Task_Shipping"
                       targetRef="End_1"/>
    <bpmn:sequenceFlow id="Flow_back_long" sourceRef="Task_Continue"
                       targetRef="Task_Search"/>
  </bpmn:process>
</bpmn:definitions>
"""


def test_multiple_back_edges_no_overlap() -> None:
    """Two back-edges to the same target must use different corridors."""
    result_xml = add_diagram_layout(MULTI_BACK_EDGE_XML)
    root = _parse_root(result_xml)

    edges = root.xpath(".//*[local-name()='BPMNEdge']")
    short_edge = next(e for e in edges if e.get("bpmnElement") == "Flow_back_short")
    long_edge = next(e for e in edges if e.get("bpmnElement") == "Flow_back_long")

    def _get_waypoint_ys(edge_el: object) -> list[float]:
        return [
            float(wp.get("y")) for wp in edge_el.xpath(".//*[local-name()='waypoint']")
        ]

    short_ys = _get_waypoint_ys(short_edge)
    long_ys = _get_waypoint_ys(long_edge)

    # The horizontal corridors (middle waypoints) must be at different y
    short_corridor_y = short_ys[1]
    long_corridor_y = long_ys[1]
    assert short_corridor_y != long_corridor_y, (
        f"Back-edges overlap: both at y={short_corridor_y}"
    )


# -- Swimlane layout tests -------------------------------------------------

LANE_XML = """\
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:collaboration id="Collaboration_1">
    <bpmn:participant id="Participant_1" processRef="Process_1"/>
  </bpmn:collaboration>
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:laneSet id="LaneSet_1">
      <bpmn:lane id="Lane_1" name="Manager">
        <bpmn:flowNodeRef>Start_1</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Task_A</bpmn:flowNodeRef>
      </bpmn:lane>
      <bpmn:lane id="Lane_2" name="Worker">
        <bpmn:flowNodeRef>Task_B</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>End_1</bpmn:flowNodeRef>
      </bpmn:lane>
    </bpmn:laneSet>
    <bpmn:startEvent id="Start_1">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:task id="Task_A" name="Review">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:task>
    <bpmn:task id="Task_B" name="Execute">
      <bpmn:incoming>Flow_2</bpmn:incoming>
      <bpmn:outgoing>Flow_3</bpmn:outgoing>
    </bpmn:task>
    <bpmn:endEvent id="End_1">
      <bpmn:incoming>Flow_3</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1"
                       targetRef="Task_A"/>
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_A"
                       targetRef="Task_B"/>
    <bpmn:sequenceFlow id="Flow_3" sourceRef="Task_B"
                       targetRef="End_1"/>
  </bpmn:process>
</bpmn:definitions>
"""


def test_layout_with_lanes_produces_participant_shape() -> None:
    """Layout with lanes generates a BPMNShape for the participant."""
    result = add_diagram_layout(LANE_XML)
    assert 'bpmnElement="Participant_1"' in result
    assert 'isHorizontal="true"' in result


def test_layout_with_lanes_produces_lane_shapes() -> None:
    """Layout with lanes generates BPMNShape for each lane."""
    result = add_diagram_layout(LANE_XML)
    assert 'bpmnElement="Lane_1"' in result
    assert 'bpmnElement="Lane_2"' in result


def test_layout_with_lanes_uses_collaboration_plane() -> None:
    """BPMNPlane references the collaboration, not the process."""
    result = add_diagram_layout(LANE_XML)
    assert 'bpmnElement="Collaboration_1"' in result


def test_layout_with_lanes_all_elements_present() -> None:
    """All flow elements still get BPMNShape entries."""
    result = add_diagram_layout(LANE_XML)
    root = _parse_root(result)
    shapes = root.xpath(".//*[local-name()='BPMNShape']")
    bpmn_elements = {s.get("bpmnElement") for s in shapes}
    # 4 flow nodes + 1 participant + 2 lanes = 7 shapes
    assert "Start_1" in bpmn_elements
    assert "Task_A" in bpmn_elements
    assert "Task_B" in bpmn_elements
    assert "End_1" in bpmn_elements
    assert "Participant_1" in bpmn_elements
    assert "Lane_1" in bpmn_elements
    assert "Lane_2" in bpmn_elements
    assert len(shapes) == 7


def test_layout_with_lanes_edges_present() -> None:
    """All sequence flow edges exist in the layout."""
    result = add_diagram_layout(LANE_XML)
    root = _parse_root(result)
    edges = root.xpath(".//*[local-name()='BPMNEdge']")
    assert len(edges) == 3


def test_layout_with_lanes_elements_shifted_right() -> None:
    """Elements have x > POOL_HEADER_WIDTH to clear the pool label."""

    result = add_diagram_layout(LANE_XML)
    root = _parse_root(result)

    for el_id in ("Start_1", "Task_A", "Task_B", "End_1"):
        shape = next(
            s
            for s in root.xpath(".//*[local-name()='BPMNShape']")
            if s.get("bpmnElement") == el_id
        )
        bounds = shape.xpath(".//*[local-name()='Bounds']")[0]
        x = float(bounds.get("x"))
        assert x >= POOL_HEADER_WIDTH, (
            f"Element {el_id} x={x} is less than POOL_HEADER_WIDTH"
        )


def test_layout_with_lanes_lane1_above_lane2() -> None:
    """Lane 1 (Manager) elements have lower y than Lane 2 (Worker)."""
    result = add_diagram_layout(LANE_XML)
    root = _parse_root(result)

    def _get_y(el_id: str) -> float:
        shape = next(
            s
            for s in root.xpath(".//*[local-name()='BPMNShape']")
            if s.get("bpmnElement") == el_id
        )
        return float(shape.xpath(".//*[local-name()='Bounds']")[0].get("y"))

    # Lane 1 elements should be above Lane 2 elements
    assert _get_y("Start_1") < _get_y("Task_B")
    assert _get_y("Task_A") < _get_y("End_1")
