"""Auto-layout engine for BPMN 2.0 diagrams.

Ported from bpmn-io/bpmn-auto-layout (MIT License).

Uses a grid-based layout algorithm:
1. Parse BPMN XML to build an element graph.
2. Place elements into a 2D grid via depth-first traversal.
3. Convert grid positions to pixel coordinates.
4. Generate BPMNShape and BPMNEdge DI elements.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from lxml import etree

from appkit_mcp_bpmn.services.bpmn_lane_layout import (
    POOL_HEADER_WIDTH,
    find_collaboration,
    find_participant,
    generate_lane_shapes,
    parse_lane_info,
    rearrange_grid_for_lanes,
)
from appkit_mcp_bpmn.services.grid import Grid

logger = logging.getLogger(__name__)

# -- XML namespaces -------------------------------------------------------

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
DI_NS = "http://www.omg.org/spec/DD/20100524/DI"

# -- Layout constants (matching JS library) --------------------------------

DEFAULT_CELL_WIDTH = 150
DEFAULT_CELL_HEIGHT = 140
DEFAULT_TASK_WIDTH = 100
DEFAULT_TASK_HEIGHT = 80
_MAX_DIRECT_PATH_ELEMENTS = 2
_DIRECT_WAYPOINT_COUNT = 2

# -- Type sets for classification ------------------------------------------

_EVENT_TAGS = frozenset(
    {
        "startEvent",
        "endEvent",
        "intermediateCatchEvent",
        "intermediateThrowEvent",
        "boundaryEvent",
    }
)
_GATEWAY_TAGS = frozenset(
    {
        "exclusiveGateway",
        "parallelGateway",
        "inclusiveGateway",
        "eventBasedGateway",
        "complexGateway",
    }
)
_TASK_TAGS = frozenset(
    {
        "task",
        "userTask",
        "serviceTask",
        "scriptTask",
        "manualTask",
        "businessRuleTask",
        "sendTask",
        "receiveTask",
        "callActivity",
    }
)
_SUBPROCESS_TAGS = frozenset({"subProcess", "adHocSubProcess"})
_FLOW_NODE_TAGS = _EVENT_TAGS | _GATEWAY_TAGS | _TASK_TAGS | _SUBPROCESS_TAGS


# -- Element model ---------------------------------------------------------


@dataclass
class BpmnNode:
    """Lightweight wrapper representing a BPMN element during layout."""

    id: str
    local_type: str  # e.g. "task", "startEvent"

    incoming: list[FlowRef] = field(default_factory=list)
    outgoing: list[FlowRef] = field(default_factory=list)
    attached_to_ref: BpmnNode | None = None
    attachers: list[BpmnNode] = field(default_factory=list)
    is_expanded: bool = False

    # Set during layout
    di: dict[str, Any] | None = None
    grid_position: dict[str, int] | None = None
    grid: Grid | None = None  # populated for subprocesses


@dataclass
class FlowRef:
    """Represents a sequence flow connection."""

    id: str
    source_ref: BpmnNode | None = None
    target_ref: BpmnNode | None = None


# -- Type helpers ----------------------------------------------------------

_TYPE_MAP: dict[str, frozenset[str] | str] = {
    "bpmn:Task": _TASK_TAGS,
    "bpmn:Gateway": _GATEWAY_TAGS,
    "bpmn:Event": _EVENT_TAGS,
    "bpmn:SubProcess": _SUBPROCESS_TAGS,
    "bpmn:SequenceFlow": "sequenceFlow",
    "bpmn:ExclusiveGateway": "exclusiveGateway",
    "bpmn:DataObjectReference": "dataObjectReference",
    "bpmn:DataStoreReference": "dataStoreReference",
    "bpmn:TextAnnotation": "textAnnotation",
    "bpmn:Participant": "participant",
    "bpmn:Lane": "lane",
}


def _is_type(node: BpmnNode, bpmn_type: str) -> bool:
    """Check if *node* matches *bpmn_type* (supports base-type matching)."""
    match = _TYPE_MAP.get(bpmn_type)
    if match is None:
        return False
    if isinstance(match, frozenset):
        return node.local_type in match
    return node.local_type == match


def _is_connection(node: BpmnNode) -> bool:
    return node.local_type == "sequenceFlow"


def _is_boundary_event(node: BpmnNode) -> bool:
    return node.attached_to_ref is not None


_SIZE_MAP: list[tuple[str, tuple[int, int]]] = [
    ("bpmn:SubProcess", (DEFAULT_TASK_WIDTH, DEFAULT_TASK_HEIGHT)),
    ("bpmn:Task", (DEFAULT_TASK_WIDTH, DEFAULT_TASK_HEIGHT)),
    ("bpmn:Gateway", (50, 50)),
    ("bpmn:Event", (36, 36)),
    ("bpmn:DataObjectReference", (36, 50)),
    ("bpmn:DataStoreReference", (50, 50)),
    ("bpmn:TextAnnotation", (DEFAULT_TASK_WIDTH, 30)),
]


def _get_default_size(node: BpmnNode) -> tuple[int, int]:
    """Return ``(width, height)`` for the element type."""
    for bpmn_type, size in _SIZE_MAP:
        if _is_type(node, bpmn_type):
            return size
    return (DEFAULT_TASK_WIDTH, DEFAULT_TASK_HEIGHT)


# -- XML helpers -----------------------------------------------------------


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_root(xml: str) -> etree._Element:
    xml_bytes = xml.strip().encode("utf-8")
    if xml_bytes.startswith(b"\xef\xbb\xbf"):
        xml_bytes = xml_bytes[3:]
    return etree.fromstring(xml_bytes)  # noqa: S320


def _find_process(root: etree._Element) -> etree._Element | None:
    for ns in (BPMN_NS, ""):
        tag = f"{{{ns}}}process" if ns else "process"
        procs = root.findall(f".//{tag}")
        if procs:
            return procs[0]
    return None


def _has_existing_layout(root: etree._Element) -> bool:
    return bool(root.findall(f".//{{{BPMNDI_NS}}}BPMNShape"))


def _remove_existing_diagrams(root: etree._Element) -> None:
    for tag in (f"{{{BPMNDI_NS}}}BPMNDiagram", "BPMNDiagram"):
        for old in root.findall(tag):
            root.remove(old)


# -- Build element graph ---------------------------------------------------


def _build_element_graph(
    process: etree._Element,
) -> tuple[list[BpmnNode], list[FlowRef]]:
    """Build ``BpmnNode`` / ``FlowRef`` graph from XML process children."""
    nodes_by_id: dict[str, BpmnNode] = {}
    flows: list[FlowRef] = []
    boundary_refs: dict[str, str] = {}

    for child in process:
        lt = _local(child.tag)
        elem_id = child.get("id")
        if not elem_id:
            continue
        if lt in _FLOW_NODE_TAGS:
            node = BpmnNode(id=elem_id, local_type=lt)
            nodes_by_id[elem_id] = node
            if lt == "boundaryEvent":
                attached_to = child.get("attachedToRef")
                if attached_to:
                    boundary_refs[elem_id] = attached_to

    for child in process:
        lt = _local(child.tag)
        if lt != "sequenceFlow":
            continue
        flow_id = child.get("id")
        src_id = child.get("sourceRef")
        tgt_id = child.get("targetRef")
        if not (flow_id and src_id and tgt_id):
            continue
        src_node = nodes_by_id.get(src_id)
        tgt_node = nodes_by_id.get(tgt_id)
        if not src_node or not tgt_node:
            continue
        flow = FlowRef(id=flow_id, source_ref=src_node, target_ref=tgt_node)
        flows.append(flow)
        src_node.outgoing.append(flow)
        tgt_node.incoming.append(flow)

    for boundary_id, host_id in boundary_refs.items():
        boundary_node = nodes_by_id.get(boundary_id)
        host_node = nodes_by_id.get(host_id)
        if boundary_node and host_node:
            boundary_node.attached_to_ref = host_node
            host_node.attachers.append(boundary_node)

    return list(nodes_by_id.values()), flows


# -- Grid layout -----------------------------------------------------------


def _has_other_incoming(element: BpmnNode) -> bool:
    from_host = [
        e
        for e in element.incoming
        if e.source_ref is not element
        and e.source_ref is not None
        and e.source_ref.attached_to_ref is None
    ]
    from_attached = [
        e
        for e in element.incoming
        if e.source_ref is not element
        and e.source_ref is not None
        and e.source_ref.attached_to_ref is not element
    ]
    return len(from_host) > 0 or len(from_attached) > 0


def _find_element_in_tree(
    current: BpmnNode,
    target: BpmnNode,
    visited: set[str] | None = None,
) -> bool:
    if visited is None:
        visited = set()
    if current is target:
        return True
    if current.id in visited:
        return False
    visited.add(current.id)
    for flow in current.outgoing:
        if flow.target_ref and _find_element_in_tree(flow.target_ref, target, visited):
            return True
    return False


def _is_future_incoming(element: BpmnNode, visited: set[str]) -> bool:
    if len(element.incoming) > 1:
        for edge in element.incoming:
            if edge.source_ref and edge.source_ref.id not in visited:
                return True
    return False


def _check_for_loop(element: BpmnNode, visited: set[str]) -> bool:
    for edge in element.incoming:
        if edge.source_ref and edge.source_ref.id not in visited:
            return _find_element_in_tree(element, edge.source_ref)
    return False


def _is_next_element_tasks(elements: list[BpmnNode]) -> bool:
    return all(_is_type(el, "bpmn:Task") for el in elements)


def _sort_by_type(arr: list[BpmnNode], bpmn_type: str) -> list[BpmnNode]:
    matching = [el for el in arr if _is_type(el, bpmn_type)]
    non_matching = [el for el in arr if not _is_type(el, bpmn_type)]
    return matching + non_matching


def _handle_outgoing(
    element: BpmnNode,
    grid: Grid,
    visited: set[str],
    stack: list[BpmnNode],
) -> list[BpmnNode]:
    """Place outgoing successors into the grid."""
    next_elements: list[BpmnNode] = []
    outgoing_nodes = [
        f.target_ref for f in element.outgoing if f.target_ref is not None
    ]

    previous: BpmnNode | None = None
    if len(outgoing_nodes) > 1 and _is_next_element_tasks(outgoing_nodes):
        grid.adjust_grid_position(element)

    for idx, next_el in enumerate(outgoing_nodes):
        if next_el.id in visited:
            continue
        if (
            (previous or stack)
            and _is_future_incoming(next_el, visited)
            and not _check_for_loop(next_el, visited)
        ):
            continue

        if previous is None:
            grid.add_after(element, next_el)
        elif _is_type(element, "bpmn:ExclusiveGateway") and _is_type(
            next_el, "bpmn:ExclusiveGateway"
        ):
            grid.add_after(previous, next_el)
        else:
            ref = outgoing_nodes[idx - 1] if idx > 0 else element
            grid.add_below(ref, next_el)

        if next_el is not element:
            previous = next_el
        next_elements.insert(0, next_el)
        visited.add(next_el.id)

    return _sort_by_type(next_elements, "bpmn:ExclusiveGateway")


def _handle_incoming(
    element: BpmnNode,
    grid: Grid,
    visited: set[str],
) -> None:
    """Adjust grid position for elements with multiple incoming."""
    sources = [
        f.source_ref
        for f in element.incoming
        if f.source_ref and f.source_ref.id in visited
    ]
    if len(sources) > 1:
        grid.adjust_column_for_multiple_incoming(sources, element)
        grid.adjust_row_for_multiple_incoming(sources, element)


def _handle_attachers(
    element: BpmnNode,
    grid: Grid,
    visited: set[str],
) -> list[BpmnNode]:
    """Handle boundary-event outgoing connections."""
    next_elements: list[BpmnNode] = []
    for attacher in element.attachers:
        for flow in reversed(attacher.outgoing):
            tgt = flow.target_ref
            if not tgt or tgt.id in visited:
                continue
            _insert_below_right(tgt, element, grid)
            next_elements.append(tgt)
            visited.add(tgt.id)
    return next_elements


def _insert_below_right(
    new_element: BpmnNode,
    host: BpmnNode,
    grid: Grid,
) -> None:
    row, col = grid.find(host)
    if grid.get(row + 1, col) or grid.get(row + 1, col + 1):
        grid.create_row(row)
    grid.add(new_element, (row + 1, col + 1))


def _create_grid_layout(elements: list[BpmnNode]) -> Grid:
    """Place all elements into a grid via DFS traversal."""
    grid = Grid()
    non_boundary = [el for el in elements if not _is_boundary_event(el)]
    if not non_boundary:
        return grid

    visited: set[str] = set()
    while len(visited) < len(non_boundary):
        starting = [
            el
            for el in elements
            if not _is_connection(el)
            and not _is_boundary_event(el)
            and (not el.incoming or not _has_other_incoming(el))
            and el.id not in visited
        ]
        stack: list[BpmnNode] = list(starting)
        for el in starting:
            grid.add(el)
            visited.add(el.id)

        _handle_grid_stack(grid, visited, stack)

        if grid.get_elements_total() != len(non_boundary):
            grid_ids = {el.id for el in grid.get_all_elements()}
            missing = [
                el
                for el in elements
                if el.id not in grid_ids and not _is_boundary_event(el)
            ]
            if missing:
                stack.append(missing[0])
                grid.add(missing[0])
                visited.add(missing[0].id)
                _handle_grid_stack(grid, visited, stack)

    return grid


def _handle_grid_stack(
    grid: Grid,
    visited: set[str],
    stack: list[BpmnNode],
) -> None:
    while stack:
        current = stack.pop()
        _handle_incoming(current, grid, visited)
        next_out = _handle_outgoing(current, grid, visited, stack)
        next_att = _handle_attachers(current, grid, visited)
        stack.extend(next_out + next_att)


# -- Position / coordinate helpers -----------------------------------------


def _coordinates_to_position(row: int, col: int) -> dict[str, int]:
    return {
        "x": col * DEFAULT_CELL_WIDTH,
        "y": row * DEFAULT_CELL_HEIGHT,
        "width": DEFAULT_CELL_WIDTH,
        "height": DEFAULT_CELL_HEIGHT,
    }


def _get_bounds(
    node: BpmnNode,
    row: int,
    col: int,
    shift: dict[str, int],
    attached_to: BpmnNode | None = None,
) -> dict[str, int]:
    w, h = _get_default_size(node)
    sx, sy = shift["x"], shift["y"]

    if attached_to is None:
        if node.is_expanded and node.grid:
            dims = node.grid.get_grid_dimensions()
            ew = dims[1] * DEFAULT_CELL_WIDTH + w
            eh = dims[0] * DEFAULT_CELL_HEIGHT + h
        else:
            ew, eh = w, h
        return {
            "x": col * DEFAULT_CELL_WIDTH + (DEFAULT_CELL_WIDTH - w) // 2 + sx,
            "y": row * DEFAULT_CELL_HEIGHT + (DEFAULT_CELL_HEIGHT - h) // 2 + sy,
            "width": ew,
            "height": eh,
        }

    host_bounds = attached_to.di["bounds"]
    return {
        "x": round(host_bounds["x"] + host_bounds["width"] / 2 - w / 2),
        "y": round(host_bounds["y"] + host_bounds["height"] - h / 2),
        "width": w,
        "height": h,
    }


def _get_mid(bounds: dict[str, int]) -> dict[str, float]:
    return {
        "x": bounds["x"] + bounds["width"] / 2,
        "y": bounds["y"] + bounds["height"] / 2,
    }


def _get_docking_point(
    point: dict[str, float],
    rect: dict[str, int],
    direction: str = "r",
    target_orientation: str = "top-left",
) -> dict[str, float]:
    if direction == "h":
        direction = "l" if "left" in target_orientation else "r"
    if direction == "v":
        direction = "t" if "top" in target_orientation else "b"

    if direction == "t":
        return {"x": point["x"], "y": float(rect["y"])}
    if direction == "r":
        return {"x": float(rect["x"] + rect["width"]), "y": point["y"]}
    if direction == "b":
        return {"x": point["x"], "y": float(rect["y"] + rect["height"])}
    if direction == "l":
        return {"x": float(rect["x"]), "y": point["y"]}
    raise ValueError(f"Unexpected docking direction: {direction}")


def _sign(value: int) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


# -- Connection routing ----------------------------------------------------


def _is_direct_path_blocked(
    source: BpmnNode,
    target: BpmnNode,
    layout_grid: Grid,
) -> bool:
    s_row = source.grid_position["row"]
    s_col = source.grid_position["col"]
    t_row = target.grid_position["row"]
    t_col = target.grid_position["col"]

    dx = t_col - s_col
    dy = t_row - s_row
    total = 0
    if dx:
        total += len(layout_grid.get_elements_in_range((s_row, s_col), (s_row, t_col)))
    if dy:
        total += len(layout_grid.get_elements_in_range((s_row, t_col), (t_row, t_col)))
    return total > _MAX_DIRECT_PATH_ELEMENTS


def _direct_manhattan_connect(
    source: BpmnNode,
    target: BpmnNode,
    layout_grid: Grid,
) -> list[str] | None:
    s_row = source.grid_position["row"]
    s_col = source.grid_position["col"]
    t_row = target.grid_position["row"]
    t_col = target.grid_position["col"]

    dx = t_col - s_col
    dy = t_row - s_row

    if not (dx > 0 and dy != 0):
        return None

    # Prefer horizontal-first: go right at source row, then up/down at
    # target column.  This places the vertical segment at the *target*
    # column, which naturally separates edges going to different targets
    # and reduces vertical overlap.
    bend_hv = (s_row, t_col)
    total_hv = len(layout_grid.get_elements_in_range((s_row, s_col), bend_hv))
    total_hv += len(layout_grid.get_elements_in_range(bend_hv, (t_row, t_col)))
    if total_hv <= _MAX_DIRECT_PATH_ELEMENTS:
        return ["h", "v"]

    # Fallback: vertical-first (up/down at source col, then right).
    bend_vh = (t_row, s_col)
    total_vh = len(layout_grid.get_elements_in_range((s_row, s_col), bend_vh))
    total_vh += len(layout_grid.get_elements_in_range(bend_vh, (t_row, t_col)))
    if total_vh <= _MAX_DIRECT_PATH_ELEMENTS:
        return ["v", "h"]

    return None


def _get_max_expanded_between(
    source: BpmnNode,
    target: BpmnNode,
    layout_grid: Grid,
) -> int:
    host_src = source.attached_to_ref or source
    host_tgt = target.attached_to_ref or target
    try:
        s_row, s_col = layout_grid.find(host_src)
        _, t_col = layout_grid.find(host_tgt)
    except ValueError:
        return 0

    first_col = min(s_col, t_col)
    last_col = max(s_col, t_col)

    result = 0
    for el in layout_grid.get_all_elements():
        if (
            el.grid_position
            and el.grid_position["row"] == s_row
            and first_col < el.grid_position["col"] < last_col
            and el.grid
        ):
            dims = el.grid.get_grid_dimensions()
            result = max(result, dims[0])
    return result


@dataclass
class _ConnCtx:
    """Pre-computed values shared by all connection routing strategies."""

    src_bounds: dict[str, int]
    tgt_bounds: dict[str, int]
    src_mid: dict[str, float]
    tgt_mid: dict[str, float]
    dx: int
    dy: int
    dock_src: str
    dock_tgt: str
    base_src_grid: Grid | None
    base_tgt_grid: Grid | None


def _route_self_loop(
    source: BpmnNode,
    ctx: _ConnCtx,
) -> list[dict[str, float]]:
    """Route a self-loop connection (source == target cell)."""
    pos = _coordinates_to_position(
        source.grid_position["row"], source.grid_position["col"]
    )
    if ctx.base_src_grid:
        loop_x = (
            pos["x"]
            + (ctx.base_src_grid.get_grid_dimensions()[1] + 1) * DEFAULT_CELL_WIDTH
        )
    else:
        loop_x = pos["x"] + DEFAULT_CELL_WIDTH
    return [
        _get_docking_point(ctx.src_mid, ctx.src_bounds, "r", ctx.dock_src),
        {"x": float(loop_x), "y": ctx.src_mid["y"]},
        {"x": float(loop_x), "y": float(pos["y"])},
        {"x": ctx.tgt_mid["x"], "y": float(pos["y"])},
        _get_docking_point(ctx.tgt_mid, ctx.tgt_bounds, "t", ctx.dock_tgt),
    ]


def _has_overlapping_back_edge(
    source: BpmnNode,
    target: BpmnNode,
    layout_grid: Grid,
) -> bool:
    """Check if a shorter same-row back-edge overlaps the bottom corridor.

    When True, the caller should route via top to avoid overlapping
    horizontal segments with the shorter back-edge.
    """
    src_pos = source.grid_position
    tgt_pos = target.grid_position
    if not src_pos or not tgt_pos or src_pos["row"] != tgt_pos["row"]:
        return False

    src_row = src_pos["row"]
    src_col = src_pos["col"]
    tgt_col = tgt_pos["col"]
    span = src_col - tgt_col

    for el in layout_grid.get_all_elements():
        if not el.grid_position or el.grid_position["row"] != src_row:
            continue
        el_col = el.grid_position["col"]
        for flow in el.outgoing:
            ft = flow.target_ref
            if ft is None or not ft.grid_position:
                continue
            if el is source and ft is target:
                continue
            ft_col = ft.grid_position["col"]
            ft_row = ft.grid_position["row"]
            if ft_row != src_row or el_col <= ft_col:
                continue
            other_span = el_col - ft_col
            if max(tgt_col, ft_col) < min(src_col, el_col):
                if span > other_span:
                    return True
                if span == other_span and src_col > el_col:
                    return True
    return False


def _route_back_edge(
    source: BpmnNode,
    target: BpmnNode,
    ctx: _ConnCtx,
    layout_grid: Grid,
) -> list[dict[str, float]]:
    """Route a back-edge (target is to the left of source)."""
    pos = _coordinates_to_position(
        source.grid_position["row"], source.grid_position["col"]
    )
    if ctx.src_mid["y"] >= ctx.tgt_mid["y"]:
        if _has_overlapping_back_edge(source, target, layout_grid):
            top_y = pos["y"]
            return [
                _get_docking_point(ctx.src_mid, ctx.src_bounds, "t"),
                {"x": ctx.src_mid["x"], "y": float(top_y)},
                {"x": ctx.tgt_mid["x"], "y": float(top_y)},
                _get_docking_point(ctx.tgt_mid, ctx.tgt_bounds, "t"),
            ]
        max_exp = _get_max_expanded_between(source, target, layout_grid)
        if ctx.base_src_grid:
            bottom_y = (
                pos["y"]
                + (ctx.base_src_grid.get_grid_dimensions()[0] + 1) * DEFAULT_CELL_HEIGHT
            )
        elif max_exp:
            bottom_y = pos["y"] + DEFAULT_CELL_HEIGHT + max_exp * DEFAULT_CELL_HEIGHT
        else:
            bottom_y = pos["y"] + DEFAULT_CELL_HEIGHT
        return [
            _get_docking_point(ctx.src_mid, ctx.src_bounds, "b"),
            {"x": ctx.src_mid["x"], "y": float(bottom_y)},
            {"x": ctx.tgt_mid["x"], "y": float(bottom_y)},
            _get_docking_point(ctx.tgt_mid, ctx.tgt_bounds, "b"),
        ]
    bend_y = ctx.src_mid["y"] - DEFAULT_CELL_HEIGHT / 2
    return [
        _get_docking_point(ctx.src_mid, ctx.src_bounds, "t"),
        {"x": ctx.src_mid["x"], "y": bend_y},
        {"x": ctx.tgt_mid["x"], "y": bend_y},
        _get_docking_point(ctx.tgt_mid, ctx.tgt_bounds, "t"),
    ]


def _route_horizontal(
    source: BpmnNode,
    target: BpmnNode,
    ctx: _ConnCtx,
    layout_grid: Grid,
) -> list[dict[str, float]]:
    """Route a horizontal connection (same row, forward direction)."""
    if _is_direct_path_blocked(source, target, layout_grid):
        pos = _coordinates_to_position(
            source.grid_position["row"],
            source.grid_position["col"],
        )
        if ctx.base_src_grid:
            bottom_y = (
                pos["y"]
                + (ctx.base_src_grid.get_grid_dimensions()[0] + 1) * DEFAULT_CELL_HEIGHT
            )
        else:
            bottom_y = pos["y"] + DEFAULT_CELL_HEIGHT
        return [
            _get_docking_point(ctx.src_mid, ctx.src_bounds, "b"),
            {"x": ctx.src_mid["x"], "y": float(bottom_y)},
            {"x": ctx.tgt_mid["x"], "y": float(bottom_y)},
            _get_docking_point(ctx.tgt_mid, ctx.tgt_bounds, "b"),
        ]
    first = _get_docking_point(ctx.src_mid, ctx.src_bounds, "h", ctx.dock_src)
    last = _get_docking_point(ctx.tgt_mid, ctx.tgt_bounds, "h", ctx.dock_tgt)
    if ctx.base_src_grid:
        first["y"] = ctx.src_bounds["y"] + DEFAULT_TASK_HEIGHT / 2
    if ctx.base_tgt_grid:
        last["y"] = ctx.tgt_bounds["y"] + DEFAULT_TASK_HEIGHT / 2
    return [first, last]


def _route_vertical(
    source: BpmnNode,
    target: BpmnNode,
    ctx: _ConnCtx,
    layout_grid: Grid,
) -> list[dict[str, float]]:
    """Route a vertical connection (same column)."""
    if _is_direct_path_blocked(source, target, layout_grid):
        y_offset = -_sign(ctx.dy) * DEFAULT_CELL_HEIGHT / 2
        return [
            _get_docking_point(ctx.src_mid, ctx.src_bounds, "r"),
            {
                "x": ctx.src_mid["x"] + DEFAULT_CELL_WIDTH / 2,
                "y": ctx.src_mid["y"],
            },
            {
                "x": ctx.tgt_mid["x"] + DEFAULT_CELL_WIDTH / 2,
                "y": ctx.tgt_mid["y"] + y_offset,
            },
            {
                "x": ctx.tgt_mid["x"],
                "y": ctx.tgt_mid["y"] + y_offset,
            },
            _get_docking_point(
                ctx.tgt_mid,
                ctx.tgt_bounds,
                "b" if y_offset > 0 else "t",
            ),
        ]
    return [
        _get_docking_point(ctx.src_mid, ctx.src_bounds, "v", ctx.dock_src),
        _get_docking_point(ctx.tgt_mid, ctx.tgt_bounds, "v", ctx.dock_tgt),
    ]


def _connect_elements(
    source: BpmnNode,
    target: BpmnNode,
    layout_grid: Grid,
) -> list[dict[str, float]]:
    """Compute waypoints to connect *source* to *target*."""
    src_bounds = source.di["bounds"]
    tgt_bounds = target.di["bounds"]
    src_mid = _get_mid(src_bounds)
    tgt_mid = _get_mid(tgt_bounds)

    dx = target.grid_position["col"] - source.grid_position["col"]
    dy = target.grid_position["row"] - source.grid_position["row"]

    vert_src = "bottom" if dy > 0 else "top"
    horiz_src = "right" if dx > 0 else "left"
    vert_tgt = "top" if dy > 0 else "bottom"
    horiz_tgt = "left" if dx > 0 else "right"

    ctx = _ConnCtx(
        src_bounds=src_bounds,
        tgt_bounds=tgt_bounds,
        src_mid=src_mid,
        tgt_mid=tgt_mid,
        dx=dx,
        dy=dy,
        dock_src=f"{vert_src}-{horiz_src}",
        dock_tgt=f"{vert_tgt}-{horiz_tgt}",
        base_src_grid=source.grid
        or (source.attached_to_ref.grid if source.attached_to_ref else None),
        base_tgt_grid=target.grid,
    )

    if dx == 0 and dy == 0:
        return _route_self_loop(source, ctx)
    if dx < 0:
        return _route_back_edge(source, target, ctx, layout_grid)
    if dy == 0:
        return _route_horizontal(source, target, ctx, layout_grid)
    if dx == 0:
        return _route_vertical(source, target, ctx, layout_grid)

    direct = _direct_manhattan_connect(source, target, layout_grid)
    if direct:
        start = _get_docking_point(ctx.src_mid, ctx.src_bounds, direct[0], ctx.dock_src)
        end = _get_docking_point(ctx.tgt_mid, ctx.tgt_bounds, direct[1], ctx.dock_tgt)
        mid = (
            {"x": end["x"], "y": start["y"]}
            if direct[0] == "h"
            else {"x": start["x"], "y": end["y"]}
        )
        return [start, mid, end]

    # Z-path through midpoint corridor — the corridor x-position depends
    # on the target, so edges to different targets use different corridors.
    corridor_x = (ctx.src_mid["x"] + ctx.tgt_mid["x"]) / 2
    return [
        _get_docking_point(ctx.src_mid, ctx.src_bounds, "r", ctx.dock_src),
        {"x": corridor_x, "y": ctx.src_mid["y"]},
        {"x": corridor_x, "y": ctx.tgt_mid["y"]},
        _get_docking_point(ctx.tgt_mid, ctx.tgt_bounds, "l", ctx.dock_tgt),
    ]


# -- DI generation ---------------------------------------------------------


def _create_element_di(
    node: BpmnNode,
    row: int,
    col: int,
    shift: dict[str, int],
) -> list[dict[str, Any]]:
    """Create DI shape data for element and its boundary events."""
    bounds = _get_bounds(node, row, col, shift)
    di_data = {
        "id": node.id + "_di",
        "bpmn_element": node.id,
        "bounds": bounds,
        "is_marker_visible": _is_type(node, "bpmn:ExclusiveGateway"),
        "is_expanded": node.is_expanded,
    }
    node.di = di_data
    node.grid_position = {"row": row, "col": col}
    shapes = [di_data]

    for idx, att in enumerate(node.attachers):
        att.grid_position = {"row": row, "col": col}
        att_bounds = _get_bounds(att, row, col, shift, node)
        att_bounds["x"] = (
            bounds["x"]
            + (idx + 1) * (bounds["width"] // (len(node.attachers) + 1))
            - att_bounds["width"] // 2
        )
        att_di = {
            "id": att.id + "_di",
            "bpmn_element": att.id,
            "bounds": att_bounds,
            "is_marker_visible": False,
            "is_expanded": False,
        }
        att.di = att_di
        shapes.append(att_di)

    return shapes


def _create_connection_di(
    node: BpmnNode,
    layout_grid: Grid,
) -> list[dict[str, Any]]:
    """Create DI edge data for outgoing connections."""
    edges: list[dict[str, Any]] = []

    for flow in node.outgoing:
        if not flow.target_ref or not flow.target_ref.di:
            continue
        waypoints = _connect_elements(node, flow.target_ref, layout_grid)
        edges.append(
            {
                "id": flow.id + "_di",
                "bpmn_element": flow.id,
                "waypoints": waypoints,
            }
        )

    for att in node.attachers:
        for flow in att.outgoing:
            if not flow.target_ref or not flow.target_ref.di:
                continue
            waypoints = _connect_elements(att, flow.target_ref, layout_grid)
            _ensure_exit_bottom(att, waypoints)
            edges.append(
                {
                    "id": flow.id + "_di",
                    "bpmn_element": flow.id,
                    "waypoints": waypoints,
                }
            )

    return edges


def _ensure_exit_bottom(
    source: BpmnNode,
    waypoints: list[dict[str, float]],
) -> None:
    """Correct boundary-event waypoints to exit from the bottom."""
    if not source.di or not waypoints:
        return

    src_bounds = source.di["bounds"]
    src_mid = _get_mid(src_bounds)
    dock = _get_docking_point(src_mid, src_bounds, "b")

    if waypoints[0]["x"] == dock["x"] and waypoints[0]["y"] == dock["y"]:
        return

    row = source.grid_position["row"] if source.grid_position else 0
    col = source.grid_position["col"] if source.grid_position else 0
    base_grid = source.grid or (
        source.attached_to_ref.grid if source.attached_to_ref else None
    )

    if base_grid:
        dims = base_grid.get_grid_dimensions()
        bottom_y = (row + dims[0] + 1) * DEFAULT_CELL_HEIGHT
        right_x = (col + dims[1] + 1) * DEFAULT_CELL_WIDTH
    else:
        bottom_y = (row + 1) * DEFAULT_CELL_HEIGHT
        right_x = (col + 1) * DEFAULT_CELL_WIDTH

    if len(waypoints) == _DIRECT_WAYPOINT_COUNT:
        new_start = [
            dock,
            {"x": dock["x"], "y": float(bottom_y)},
            {"x": float(right_x), "y": float(bottom_y)},
            {
                "x": float(right_x),
                "y": float(row * DEFAULT_CELL_HEIGHT + DEFAULT_CELL_HEIGHT / 2),
            },
        ]
        waypoints[0:1] = new_start
        return

    new_start = [
        dock,
        {"x": dock["x"], "y": float(bottom_y)},
        {"x": waypoints[1]["x"], "y": float(bottom_y)},
    ]
    waypoints[0:1] = new_start


def _generate_di(
    layout_grid: Grid,
    shift: dict[str, int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate all DI shapes and edges from the grid."""
    shapes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    positions = layout_grid.elements_by_position()

    for pos in positions:
        dis = _create_element_di(pos["element"], pos["row"], pos["col"], shift)
        shapes.extend(dis)

    for pos in positions:
        conn_dis = _create_connection_di(pos["element"], layout_grid)
        edges.extend(conn_dis)

    return shapes, edges


# -- XML output ------------------------------------------------------------


def _build_diagram_xml(
    root: etree._Element,
    process_id: str,
    shapes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> None:
    """Write ``<bpmndi:BPMNDiagram>`` with shapes and edges into *root*."""
    nsmap = {"bpmndi": BPMNDI_NS, "dc": DC_NS, "di": DI_NS}
    diagram = etree.SubElement(
        root,
        f"{{{BPMNDI_NS}}}BPMNDiagram",
        attrib={"id": "BPMNDiagram_1"},
        nsmap=nsmap,
    )
    plane = etree.SubElement(
        diagram,
        f"{{{BPMNDI_NS}}}BPMNPlane",
        attrib={"id": "BPMNPlane_1", "bpmnElement": process_id},
    )

    for sd in shapes:
        attrib: dict[str, str] = {
            "id": sd["id"],
            "bpmnElement": sd["bpmn_element"],
        }
        if sd.get("is_marker_visible"):
            attrib["isMarkerVisible"] = "true"
        if sd.get("is_expanded"):
            attrib["isExpanded"] = "true"
        if sd.get("is_horizontal"):
            attrib["isHorizontal"] = "true"

        shape = etree.SubElement(plane, f"{{{BPMNDI_NS}}}BPMNShape", attrib=attrib)
        b = sd["bounds"]
        etree.SubElement(
            shape,
            f"{{{DC_NS}}}Bounds",
            attrib={
                "x": str(b["x"]),
                "y": str(b["y"]),
                "width": str(b["width"]),
                "height": str(b["height"]),
            },
        )

    for ed in edges:
        edge = etree.SubElement(
            plane,
            f"{{{BPMNDI_NS}}}BPMNEdge",
            attrib={
                "id": ed["id"],
                "bpmnElement": ed["bpmn_element"],
            },
        )
        for wp in ed["waypoints"]:
            etree.SubElement(
                edge,
                f"{{{DI_NS}}}waypoint",
                attrib={
                    "x": str(round(wp["x"])),
                    "y": str(round(wp["y"])),
                },
            )


# -- Public API ------------------------------------------------------------


def add_diagram_layout(xml: str) -> str:
    """Add or replace the ``<bpmndi:BPMNDiagram>`` section in *xml*.

    If the XML already contains a non-empty BPMNDiagram (with at least
    one BPMNShape), return *xml* unchanged.

    Args:
        xml: BPMN 2.0 XML string with at least one ``<bpmn:process>``.

    Returns:
        BPMN XML string with a complete BPMNDiagram section.
    """
    root = _parse_root(xml)

    if _has_existing_layout(root):
        existing = root.findall(f".//{{{BPMNDI_NS}}}BPMNShape")
        logger.debug(
            "BPMNDiagram already present with %d shapes - skipping",
            len(existing),
        )
        return xml

    _remove_existing_diagrams(root)

    process = _find_process(root)
    if process is None:
        logger.warning("No <process> found - cannot generate layout")
        return xml

    process_id = process.get("id", "Process_1")
    elements, _ = _build_element_graph(process)

    if not elements:
        logger.warning("No flow nodes found - cannot generate layout")
        return xml

    grid = _create_grid_layout(elements)

    # Lane-aware layout
    lanes = parse_lane_info(process)
    lane_shapes: list[dict[str, Any]] = []
    plane_element = process_id
    shift: dict[str, int] = {"x": 0, "y": 0}

    if lanes:
        collaboration = find_collaboration(root)
        participant = find_participant(root)

        grid, lane_row_ranges = rearrange_grid_for_lanes(grid, lanes)
        shift = {"x": POOL_HEADER_WIDTH, "y": 0}

        if participant is not None:
            _, max_cols = grid.get_grid_dimensions()
            lane_shapes = generate_lane_shapes(
                lanes,
                lane_row_ranges,
                max_cols,
                participant.get("id", "Participant_1"),
            )

        if collaboration is not None:
            plane_element = collaboration.get("id", "Collaboration_1")

    shapes, edges = _generate_di(grid, shift)
    all_shapes = lane_shapes + shapes

    _build_diagram_xml(root, plane_element, all_shapes, edges)

    result = etree.tostring(
        root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    ).decode("utf-8")

    logger.info(
        "Auto-layout generated: %d shapes, %d edges",
        len(all_shapes),
        len(edges),
    )
    return result
