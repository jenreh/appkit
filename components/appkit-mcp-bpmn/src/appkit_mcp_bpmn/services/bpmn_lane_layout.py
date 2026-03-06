"""Swimlane layout support for BPMN auto-layout.

Handles parsing lane definitions from BPMN XML, rearranging the element
grid so elements are grouped by lane, and generating DI shapes for
the pool participant and each lane.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from lxml import etree

from appkit_mcp_bpmn.services.grid import Grid

logger = logging.getLogger(__name__)

# -- Constants (duplicated from bpmn_layouter to avoid circular imports) ---

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
POOL_HEADER_WIDTH = 30
DEFAULT_CELL_WIDTH = 150
DEFAULT_CELL_HEIGHT = 140


# -- Data model ------------------------------------------------------------


@dataclass
class LaneInfo:
    """Parsed lane definition from BPMN XML."""

    id: str
    name: str
    element_ids: list[str] = field(default_factory=list)


# -- XML parsing -----------------------------------------------------------


def parse_lane_info(process: etree._Element) -> list[LaneInfo] | None:
    """Extract lane definitions from a ``<bpmn:laneSet>`` in *process*.

    Returns:
        List of ``LaneInfo`` objects, or ``None`` if no lanes exist.
    """
    lane_set = process.find(f"{{{BPMN_NS}}}laneSet")
    if lane_set is None:
        lane_set = process.find("laneSet")
    if lane_set is None:
        return None

    lane_els = lane_set.findall(f"{{{BPMN_NS}}}lane")
    if not lane_els:
        lane_els = lane_set.findall("lane")
    if not lane_els:
        return None

    result: list[LaneInfo] = []
    for lane_el in lane_els:
        lane_id = lane_el.get("id", "")
        name = lane_el.get("name", "")
        refs = _collect_flow_node_refs(lane_el)
        result.append(LaneInfo(id=lane_id, name=name, element_ids=refs))

    return result if result else None


def _collect_flow_node_refs(lane_el: etree._Element) -> list[str]:
    """Collect ``<flowNodeRef>`` text values from a lane element."""
    for ns in (BPMN_NS, ""):
        tag = f"{{{ns}}}flowNodeRef" if ns else "flowNodeRef"
        refs = [ref_el.text.strip() for ref_el in lane_el.findall(tag) if ref_el.text]
        if refs:
            return refs
    return []


def find_collaboration(root: etree._Element) -> etree._Element | None:
    """Find the first ``<bpmn:collaboration>`` in *root*."""
    for ns in (BPMN_NS, ""):
        tag = f"{{{ns}}}collaboration" if ns else "collaboration"
        elems = root.findall(tag)
        if elems:
            return elems[0]
    return None


def find_participant(root: etree._Element) -> etree._Element | None:
    """Find the first ``<bpmn:participant>`` in *root*."""
    for ns in (BPMN_NS, ""):
        tag = f".//{{{ns}}}participant" if ns else ".//participant"
        elems = root.findall(tag)
        if elems:
            return elems[0]
    return None


# -- Grid rearrangement ----------------------------------------------------


def rearrange_grid_for_lanes(
    grid: Grid,
    lanes: list[LaneInfo],
) -> tuple[Grid, dict[int, tuple[int, int]]]:
    """Rearrange *grid* so elements are grouped by their lane.

    Elements keep their column positions from the flow-based layout but
    are assigned to contiguous row ranges based on lane membership.

    Args:
        grid: Original flow-based grid layout.
        lanes: Parsed lane definitions.

    Returns:
        A tuple of ``(new_grid, lane_row_ranges)`` where
        ``lane_row_ranges[lane_idx] = (start_row, end_row)`` inclusive.
    """
    positions = grid.elements_by_position()

    elem_to_lane = _build_elem_to_lane_map(lanes)

    lane_elements: dict[int, list[tuple[int, int, Any]]] = defaultdict(list)
    for pos in positions:
        el = pos["element"]
        lane_idx = elem_to_lane.get(el.id, 0)
        lane_elements[lane_idx].append((pos["row"], pos["col"], el))

    for elems_list in lane_elements.values():
        elems_list.sort()

    positioned: list[tuple[Any, int, int]] = []
    lane_row_ranges: dict[int, tuple[int, int]] = {}
    current_row = 0

    for lane_idx in range(len(lanes)):
        elems = lane_elements.get(lane_idx, [])
        if not elems:
            lane_row_ranges[lane_idx] = (current_row, current_row)
            current_row += 1
            continue

        unique_rows = sorted({r for r, _, _ in elems})
        row_remap = {r: i for i, r in enumerate(unique_rows)}
        lane_height = len(unique_rows)

        start_row = current_row
        for orig_row, col, el in elems:
            new_row = current_row + row_remap[orig_row]
            positioned.append((el, new_row, col))

        lane_row_ranges[lane_idx] = (start_row, start_row + lane_height - 1)
        current_row += lane_height

    new_grid = Grid.from_positions(positioned)

    logger.debug(
        "Rearranged grid for %d lanes: %d rows",
        len(lanes),
        new_grid.get_grid_dimensions()[0],
    )

    return new_grid, lane_row_ranges


def _build_elem_to_lane_map(lanes: list[LaneInfo]) -> dict[str, int]:
    """Build element-id → lane-index mapping."""
    mapping: dict[str, int] = {}
    for idx, lane in enumerate(lanes):
        for eid in lane.element_ids:
            mapping[eid] = idx
    return mapping


# -- Lane shape generation -------------------------------------------------


def generate_lane_shapes(
    lanes: list[LaneInfo],
    lane_row_ranges: dict[int, tuple[int, int]],
    grid_cols: int,
    participant_id: str,
) -> list[dict[str, Any]]:
    """Generate BPMNShape data for the pool participant and each lane.

    Returns:
        List of shape dicts (participant first, then lanes) with
        ``is_horizontal=True`` set for proper rendering.
    """
    shapes: list[dict[str, Any]] = []

    content_width = grid_cols * DEFAULT_CELL_WIDTH
    total_width = POOL_HEADER_WIDTH + content_width

    if lane_row_ranges:
        max_end_row = max(end for _, end in lane_row_ranges.values())
        total_height = (max_end_row + 1) * DEFAULT_CELL_HEIGHT
    else:
        total_height = DEFAULT_CELL_HEIGHT

    # Participant (pool) shape
    shapes.append(
        {
            "id": f"{participant_id}_di",
            "bpmn_element": participant_id,
            "bounds": {
                "x": 0,
                "y": 0,
                "width": total_width,
                "height": total_height,
            },
            "is_horizontal": True,
        }
    )

    # Individual lane shapes
    for lane_idx, lane in enumerate(lanes):
        start_row, end_row = lane_row_ranges.get(lane_idx, (0, 0))
        lane_height = (end_row - start_row + 1) * DEFAULT_CELL_HEIGHT
        lane_y = start_row * DEFAULT_CELL_HEIGHT

        shapes.append(
            {
                "id": f"{lane.id}_di",
                "bpmn_element": lane.id,
                "bounds": {
                    "x": POOL_HEADER_WIDTH,
                    "y": lane_y,
                    "width": content_width,
                    "height": lane_height,
                },
                "is_horizontal": True,
            }
        )

    return shapes
