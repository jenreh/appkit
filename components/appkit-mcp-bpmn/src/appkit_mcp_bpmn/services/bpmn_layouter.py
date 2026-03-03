"""Auto-layout engine for BPMN 2.0 diagrams.

Generates ``<bpmndi:BPMNDiagram>`` sections with proper BPMNShape/BPMNEdge
coordinates from a BPMN process model.  This removes the need for the LLM
to produce pixel-perfect layout information — it only needs to generate
the process semantics.

Layout algorithm:
1. Parse process elements and sequence flows to build a directed graph.
2. Assign *layers* via BFS from start events (left-to-right columns).
3. Within each layer, space elements vertically.
4. Generate BPMNShape bounds and BPMNEdge waypoints.
"""

import logging
from collections import defaultdict, deque

from lxml import etree

logger = logging.getLogger(__name__)

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
DI_NS = "http://www.omg.org/spec/DD/20100524/DI"

# Element sizes (width, height)
EVENT_SIZE = (36, 36)
TASK_SIZE = (100, 80)
GATEWAY_SIZE = (50, 50)
SUBPROCESS_SIZE = (120, 80)

# Layout spacing
HORIZONTAL_SPACING = 180  # Distance between layer centres
VERTICAL_SPACING = 100  # Distance between elements in the same layer
LEFT_MARGIN = 180  # x-offset for the first layer
TOP_MARGIN = 200  # y-offset for the "main lane"
SNAP_TOLERANCE = 5  # Pixel threshold for straight-line routing

# Local-name sets for classification
_EVENT_TAGS = {
    "startEvent",
    "endEvent",
    "intermediateCatchEvent",
    "intermediateThrowEvent",
    "boundaryEvent",
}
_GATEWAY_TAGS = {
    "exclusiveGateway",
    "parallelGateway",
    "inclusiveGateway",
    "eventBasedGateway",
    "complexGateway",
}
_TASK_TAGS = {
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
_SUBPROCESS_TAGS = {"subProcess", "adHocSubProcess"}

_FLOW_NODE_TAGS = _EVENT_TAGS | _GATEWAY_TAGS | _TASK_TAGS | _SUBPROCESS_TAGS


def _element_size(local_name: str) -> tuple[int, int]:
    """Return ``(width, height)`` for the given BPMN element type."""
    if local_name in _EVENT_TAGS:
        return EVENT_SIZE
    if local_name in _GATEWAY_TAGS:
        return GATEWAY_SIZE
    if local_name in _SUBPROCESS_TAGS:
        return SUBPROCESS_SIZE
    return TASK_SIZE


def _local(tag: str) -> str:
    """Extract local name from a possibly-namespaced tag."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_root(xml: str) -> etree._Element:
    """Parse XML string into an lxml root element, stripping any BOM."""
    xml_bytes = xml.strip().encode("utf-8")
    if xml_bytes.startswith(b"\xef\xbb\xbf"):
        xml_bytes = xml_bytes[3:]
    return etree.fromstring(xml_bytes)  # noqa: S320


def _find_process(
    root: etree._Element,
) -> etree._Element | None:
    """Return the first ``<process>`` element, or *None*."""
    processes = root.findall(f".//{{{BPMN_NS}}}process")
    if not processes:
        processes = root.findall(".//process")
    return processes[0] if processes else None


def _has_existing_layout(root: etree._Element) -> bool:
    """Return *True* if the root already has BPMNShapes."""
    return bool(root.findall(f".//{{{BPMNDI_NS}}}BPMNShape"))


def _remove_stub_diagrams(root: etree._Element) -> None:
    """Remove any empty/stub BPMNDiagram elements."""
    for old_diag in root.findall(f"{{{BPMNDI_NS}}}BPMNDiagram"):
        root.remove(old_diag)
    for old_diag in root.findall("BPMNDiagram"):
        root.remove(old_diag)


def _build_graph(
    process: etree._Element,
) -> tuple[
    dict[str, str],
    dict[str, list[str]],
    dict[str, list[str]],
    list[dict[str, str]],
]:
    """Build adjacency lists from process children.

    Returns:
        ``(nodes, outgoing, incoming, flows)`` where *nodes* maps
        element id to local tag name.
    """
    nodes: dict[str, str] = {}
    outgoing: dict[str, list[str]] = defaultdict(list)
    incoming: dict[str, list[str]] = defaultdict(list)
    flows: list[dict[str, str]] = []

    for child in process:
        local = _local(child.tag)
        if local in _FLOW_NODE_TAGS:
            elem_id = child.get("id")
            if elem_id:
                nodes[elem_id] = local
        elif local == "sequenceFlow":
            flow_id = child.get("id")
            source = child.get("sourceRef")
            target = child.get("targetRef")
            if flow_id and source and target:
                flows.append({"id": flow_id, "sourceRef": source, "targetRef": target})
                outgoing[source].append(target)
                incoming[target].append(source)

    return nodes, outgoing, incoming, flows


def _assign_layers(
    nodes: dict[str, str],
    outgoing: dict[str, list[str]],
    incoming: dict[str, list[str]],
) -> dict[str, int]:
    """Assign layer indices via BFS from start events."""
    start_ids = [nid for nid, tag in nodes.items() if tag == "startEvent"]
    if not start_ids:
        start_ids = [nid for nid in nodes if nid not in incoming]
    if not start_ids:
        start_ids = [next(iter(nodes))]

    layer_of: dict[str, int] = {}
    queue: deque[str] = deque()
    for sid in start_ids:
        layer_of[sid] = 0
        queue.append(sid)

    while queue:
        nid = queue.popleft()
        current_layer = layer_of[nid]
        for target in outgoing.get(nid, []):
            new_layer = current_layer + 1
            if target not in layer_of or layer_of[target] < new_layer:
                layer_of[target] = new_layer
                queue.append(target)

    # Unreachable nodes go after the last layer
    max_layer = max(layer_of.values()) if layer_of else 0
    for nid in nodes:
        if nid not in layer_of:
            max_layer += 1
            layer_of[nid] = max_layer

    return layer_of


def _compute_positions(
    nodes: dict[str, str],
    layer_of: dict[str, int],
) -> dict[str, tuple[int, int, int, int]]:
    """Compute ``(x, y, width, height)`` for every node."""
    layers: dict[int, list[str]] = defaultdict(list)
    for nid, layer in layer_of.items():
        layers[layer].append(nid)

    positions: dict[str, tuple[int, int, int, int]] = {}
    for layer_idx in sorted(layers):
        layer_nodes = layers[layer_idx]
        x = LEFT_MARGIN + layer_idx * HORIZONTAL_SPACING

        count = len(layer_nodes)
        total_height = sum(_element_size(nodes[n])[1] for n in layer_nodes)
        total_height += (count - 1) * (VERTICAL_SPACING - 50)
        y_start = TOP_MARGIN - total_height // 2

        y_cursor = y_start
        for nid in layer_nodes:
            w, h = _element_size(nodes[nid])
            positions[nid] = (x, y_cursor, w, h)
            y_cursor += h + (VERTICAL_SPACING - 50)

    return positions


def _build_diagram_xml(
    root: etree._Element,
    process_id: str,
    nodes: dict[str, str],
    positions: dict[str, tuple[int, int, int, int]],
    flows: list[dict[str, str]],
) -> None:
    """Append ``<bpmndi:BPMNDiagram>`` with shapes and edges to *root*."""
    nsmap = {
        "bpmndi": BPMNDI_NS,
        "dc": DC_NS,
        "di": DI_NS,
    }
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

    _add_shapes(plane, nodes, positions)
    _add_edges(plane, positions, flows)


def _add_shapes(
    plane: etree._Element,
    nodes: dict[str, str],
    positions: dict[str, tuple[int, int, int, int]],
) -> None:
    """Append ``<bpmndi:BPMNShape>`` elements for every node."""
    for nid, (x, y, w, h) in positions.items():
        attrib: dict[str, str] = {
            "id": f"{nid}_di",
            "bpmnElement": nid,
        }
        if nodes[nid] in _GATEWAY_TAGS:
            attrib["isMarkerVisible"] = "true"

        shape = etree.SubElement(plane, f"{{{BPMNDI_NS}}}BPMNShape", attrib=attrib)
        etree.SubElement(
            shape,
            f"{{{DC_NS}}}Bounds",
            attrib={
                "x": str(x),
                "y": str(y),
                "width": str(w),
                "height": str(h),
            },
        )


def _add_edges(
    plane: etree._Element,
    positions: dict[str, tuple[int, int, int, int]],
    flows: list[dict[str, str]],
) -> None:
    """Append ``<bpmndi:BPMNEdge>`` elements for every sequence flow."""
    for flow in flows:
        fid = flow["id"]
        src = flow["sourceRef"]
        tgt = flow["targetRef"]

        if src not in positions or tgt not in positions:
            continue

        sx, sy, sw, sh = positions[src]
        tx, ty, _tw, th = positions[tgt]

        src_x = sx + sw
        src_y = sy + sh // 2
        tgt_x = tx
        tgt_y = ty + th // 2

        edge = etree.SubElement(
            plane,
            f"{{{BPMNDI_NS}}}BPMNEdge",
            attrib={"id": f"{fid}_di", "bpmnElement": fid},
        )

        if abs(src_y - tgt_y) < SNAP_TOLERANCE:
            _add_waypoint(edge, src_x, src_y)
            _add_waypoint(edge, tgt_x, tgt_y)
        else:
            mid_x = (src_x + tgt_x) // 2
            _add_waypoint(edge, src_x, src_y)
            _add_waypoint(edge, mid_x, src_y)
            _add_waypoint(edge, mid_x, tgt_y)
            _add_waypoint(edge, tgt_x, tgt_y)


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
            "BPMNDiagram already present with %d shapes — skipping",
            len(existing),
        )
        return xml

    _remove_stub_diagrams(root)

    process = _find_process(root)
    if process is None:
        logger.warning("No <process> found — cannot generate layout")
        return xml

    process_id = process.get("id", "Process_1")
    nodes, outgoing, incoming, flows = _build_graph(process)

    if not nodes:
        logger.warning("No flow nodes found — cannot generate layout")
        return xml

    layer_of = _assign_layers(nodes, outgoing, incoming)
    positions = _compute_positions(nodes, layer_of)
    _build_diagram_xml(root, process_id, nodes, positions, flows)

    result = etree.tostring(
        root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    ).decode("utf-8")

    logger.info(
        "Auto-layout generated: %d shapes, %d edges",
        len(positions),
        len(flows),
    )
    return result


def _add_waypoint(
    parent: etree._Element,
    x: int,
    y: int,
) -> None:
    """Append a ``<di:waypoint>`` child element."""
    etree.SubElement(
        parent,
        f"{{{DI_NS}}}waypoint",
        attrib={"x": str(x), "y": str(y)},
    )
