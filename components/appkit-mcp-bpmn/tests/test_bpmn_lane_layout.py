"""Tests for BPMN swimlane layout support."""

from lxml import etree

from appkit_mcp_bpmn.services.bpmn_lane_layout import (
    LaneInfo,
    find_collaboration,
    find_participant,
    generate_lane_shapes,
    parse_lane_info,
    rearrange_grid_for_lanes,
)
from appkit_mcp_bpmn.services.grid import Grid

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"


def _make_process_with_lanes() -> etree._Element:
    """Build a minimal process element with a laneSet."""
    ns = BPMN_NS
    root = etree.Element(f"{{{ns}}}definitions")
    process = etree.SubElement(root, f"{{{ns}}}process", attrib={"id": "P1"})
    lane_set = etree.SubElement(process, f"{{{ns}}}laneSet", attrib={"id": "LS1"})

    lane1 = etree.SubElement(
        lane_set, f"{{{ns}}}lane", attrib={"id": "L1", "name": "Manager"}
    )
    ref1 = etree.SubElement(lane1, f"{{{ns}}}flowNodeRef")
    ref1.text = "start"
    ref2 = etree.SubElement(lane1, f"{{{ns}}}flowNodeRef")
    ref2.text = "task_a"

    lane2 = etree.SubElement(
        lane_set, f"{{{ns}}}lane", attrib={"id": "L2", "name": "Worker"}
    )
    ref3 = etree.SubElement(lane2, f"{{{ns}}}flowNodeRef")
    ref3.text = "task_b"
    ref4 = etree.SubElement(lane2, f"{{{ns}}}flowNodeRef")
    ref4.text = "end"

    return process


def _make_definitions_with_collaboration() -> etree._Element:
    """Build definitions with collaboration + participant."""
    ns = BPMN_NS
    root = etree.Element(f"{{{ns}}}definitions")
    collab = etree.SubElement(root, f"{{{ns}}}collaboration", attrib={"id": "Collab_1"})
    etree.SubElement(
        collab,
        f"{{{ns}}}participant",
        attrib={"id": "Part_1", "processRef": "P1"},
    )
    return root


# -- parse_lane_info tests --


def test_parse_lane_info_returns_lanes() -> None:
    process = _make_process_with_lanes()
    lanes = parse_lane_info(process)
    assert lanes is not None
    assert len(lanes) == 2
    assert lanes[0].id == "L1"
    assert lanes[0].name == "Manager"
    assert lanes[0].element_ids == ["start", "task_a"]
    assert lanes[1].id == "L2"
    assert lanes[1].name == "Worker"
    assert lanes[1].element_ids == ["task_b", "end"]


def test_parse_lane_info_returns_none_without_lanes() -> None:
    ns = BPMN_NS
    process = etree.Element(f"{{{ns}}}process", attrib={"id": "P1"})
    assert parse_lane_info(process) is None


# -- find_collaboration / find_participant tests --


def test_find_collaboration() -> None:
    root = _make_definitions_with_collaboration()
    collab = find_collaboration(root)
    assert collab is not None
    assert collab.get("id") == "Collab_1"


def test_find_collaboration_none() -> None:
    ns = BPMN_NS
    root = etree.Element(f"{{{ns}}}definitions")
    assert find_collaboration(root) is None


def test_find_participant() -> None:
    root = _make_definitions_with_collaboration()
    part = find_participant(root)
    assert part is not None
    assert part.get("id") == "Part_1"


def test_find_participant_none() -> None:
    ns = BPMN_NS
    root = etree.Element(f"{{{ns}}}definitions")
    assert find_participant(root) is None


# -- rearrange_grid_for_lanes tests --


class _FakeNode:
    """Minimal stand-in for BpmnNode in grid tests."""

    def __init__(self, nid: str) -> None:
        self.id = nid


def test_rearrange_groups_by_lane() -> None:
    """Elements in different lanes end up in different row ranges."""
    a = _FakeNode("start")
    b = _FakeNode("task_a")
    c = _FakeNode("task_b")
    d = _FakeNode("end")

    grid = Grid.from_positions([(a, 0, 0), (b, 0, 1), (c, 0, 2), (d, 0, 3)])

    lanes = [
        LaneInfo(id="L1", name="Manager", element_ids=["start", "task_a"]),
        LaneInfo(id="L2", name="Worker", element_ids=["task_b", "end"]),
    ]

    new_grid, lane_ranges = rearrange_grid_for_lanes(grid, lanes)

    # Lane 1 on row 0, lane 2 on row 1
    assert lane_ranges[0] == (0, 0)
    assert lane_ranges[1] == (1, 1)

    assert new_grid.get(0, 0) is a
    assert new_grid.get(0, 1) is b
    assert new_grid.get(1, 2) is c
    assert new_grid.get(1, 3) is d


def test_rearrange_preserves_multi_row_lane() -> None:
    """A lane with elements on different original rows keeps multiple rows."""
    a = _FakeNode("a")
    b = _FakeNode("b")
    c = _FakeNode("c")

    grid = Grid.from_positions([(a, 0, 0), (b, 1, 1), (c, 0, 2)])

    lanes = [
        LaneInfo(id="L1", name="Alpha", element_ids=["a", "b"]),
        LaneInfo(id="L2", name="Beta", element_ids=["c"]),
    ]

    _new_grid, lane_ranges = rearrange_grid_for_lanes(grid, lanes)

    # Lane Alpha has elements on 2 original rows → 2 new rows
    assert lane_ranges[0] == (0, 1)
    assert lane_ranges[1] == (2, 2)


def test_rearrange_empty_lane() -> None:
    """An empty lane gets a single row."""
    a = _FakeNode("a")
    grid = Grid.from_positions([(a, 0, 0)])

    lanes = [
        LaneInfo(id="L1", name="Empty", element_ids=[]),
        LaneInfo(id="L2", name="Full", element_ids=["a"]),
    ]

    _new_grid, lane_ranges = rearrange_grid_for_lanes(grid, lanes)

    assert lane_ranges[0] == (0, 0)  # empty lane gets row 0
    assert lane_ranges[1] == (1, 1)  # 'a' on row 1


# -- generate_lane_shapes tests --


def test_generate_lane_shapes_structure() -> None:
    lanes = [
        LaneInfo(id="L1", name="A", element_ids=["x"]),
        LaneInfo(id="L2", name="B", element_ids=["y"]),
    ]
    lane_ranges = {0: (0, 0), 1: (1, 1)}

    shapes = generate_lane_shapes(lanes, lane_ranges, 3, "Part_1")

    # 1 participant + 2 lanes = 3 shapes
    assert len(shapes) == 3

    participant = shapes[0]
    assert participant["bpmn_element"] == "Part_1"
    assert participant["is_horizontal"] is True
    assert participant["bounds"]["x"] == 0
    assert participant["bounds"]["y"] == 0

    lane1 = shapes[1]
    assert lane1["bpmn_element"] == "L1"
    assert lane1["bounds"]["x"] == 30  # POOL_HEADER_WIDTH
    assert lane1["bounds"]["y"] == 0

    lane2 = shapes[2]
    assert lane2["bpmn_element"] == "L2"
    assert lane2["bounds"]["y"] > 0
