"""Extract flat BPMN JSON process structure from BPMN 2.0 XML.

This is the inverse of :mod:`bpmn_xml_builder`.  It parses a complete
BPMN 2.0 XML document and produces a dict matching the schema expected
by :class:`~appkit_mcp_bpmn.models.BpmnProcess` (steps + lanes).

Layout information (``<bpmndi:BPMNDiagram>``) is stripped.
"""

import logging
import re
import unicodedata
from typing import Any

from lxml import etree

from appkit_mcp_bpmn.models import BPMN_TYPE_MAP, GATEWAY_TYPES, MIN_GATEWAY_BRANCHES
from appkit_mcp_commons.exceptions import ValidationError

logger = logging.getLogger(__name__)

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"

_ELEMENT_TYPES: dict[str, str] = {
    "startEvent": "startEvent",
    "endEvent": "endEvent",
    "task": "task",
    "userTask": "userTask",
    "serviceTask": "serviceTask",
    "sendTask": "sendTask",
    "receiveTask": "receiveTask",
    "businessRuleTask": "businessRuleTask",
    "manualTask": "manualTask",
    "scriptTask": "scriptTask",
    "callActivity": "callActivity",
    "subProcess": "subProcess",
    "intermediateCatchEvent": "intermediateCatchEvent",
    "intermediateThrowEvent": "intermediateThrowEvent",
}

# Reverse mapping: XML gateway tag → JSON short type.
# Exclude "merge" which also maps to parallelGateway; the split-vs-merge
# distinction is resolved in _extract_steps based on outgoing flow count.
_GATEWAY_XML_TO_JSON: dict[str, str] = {
    v: k for k, v in BPMN_TYPE_MAP.items() if k != "merge"
}


def _local(tag: str) -> str:
    """Strip namespace prefix from an XML tag."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _to_snake_case(label: str) -> str:
    """Convert a human-readable label to a snake_case identifier.

    Transliterates Unicode characters (e.g. ä→ae, ü→ue) and strips
    non-alphanumeric characters.
    """
    # NFKD decomposes accented chars; we then drop combining marks
    normalised = unicodedata.normalize("NFKD", label)
    ascii_str = normalised.encode("ascii", "ignore").decode("ascii")
    # Replace non-alphanumeric runs with underscore
    snake = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_str).strip("_").lower()
    return snake or "step"


def extract_process_json(xml: str) -> dict[str, Any]:
    """Extract a flat BPMN JSON structure from BPMN 2.0 XML.

    Opaque XML element IDs (e.g. ``Activity_1o75wn8``) are replaced
    with semantic snake_case identifiers derived from element labels
    so that downstream LLMs can reason about the process structure.

    Args:
        xml: Complete BPMN 2.0 XML string.

    Returns:
        Dict with ``steps`` and ``lanes`` matching the
        :class:`BpmnProcess` schema.

    Raises:
        ValidationError: If the XML cannot be parsed or lacks a process.
    """
    try:
        root = etree.fromstring(xml.encode("utf-8"))
    except etree.XMLSyntaxError as exc:
        raise ValidationError(f"Invalid XML: {exc}") from exc

    process = root.find(f"{{{BPMN_NS}}}process")
    if process is None:
        raise ValidationError("No <bpmn:process> element found")

    flows = _extract_flows(process)
    steps = _extract_steps(process, flows)
    lanes = _extract_lanes(process)

    # Re-map opaque XML IDs to semantic snake_case IDs
    id_map = _build_id_map(steps)
    steps = _remap_step_ids(steps, id_map)
    if lanes:
        lanes = _remap_lane_ids(lanes, id_map)

    return {"steps": steps, "lanes": lanes}


def _extract_flows(
    process: etree._Element,
) -> dict[str, list[dict[str, str]]]:
    """Build a mapping of source element → list of outgoing flow targets.

    Returns:
        Dict keyed by sourceRef, values are lists of
        ``{"target": ..., "condition": ...}`` dicts.
    """
    flows: dict[str, list[dict[str, str]]] = {}
    for sf in process.findall(f"{{{BPMN_NS}}}sequenceFlow"):
        source = sf.get("sourceRef", "")
        target = sf.get("targetRef", "")
        condition = sf.get("name", "")
        if source and target:
            flows.setdefault(source, []).append(
                {"target": target, "condition": condition}
            )
    return flows


def _extract_steps(
    process: etree._Element,
    flows: dict[str, list[dict[str, str]]],
) -> list[dict[str, Any]]:
    """Extract process elements as flat step dicts."""
    steps: list[dict[str, Any]] = []

    for child in process:
        local_name = _local(child.tag)

        # Map XML element type to JSON type
        json_type = _resolve_json_type(local_name)
        if json_type is None:
            continue

        elem_id = child.get("id", "")
        label = child.get("name", "")

        # parallelGateway is split when it has ≥2 outgoing flows,
        # otherwise it's a merge (join) point.
        outgoing_count = len(flows.get(elem_id, []))
        if json_type == "parallel" and outgoing_count < MIN_GATEWAY_BRANCHES:
            json_type = "merge"

        steps.append(
            {
                "id": elem_id,
                "type": json_type,
                "label": label,
                "branches": None,
                "next": None,
            }
        )

    # Now resolve flows into branches/next
    for step in steps:
        step_id = step["id"]
        outgoing = flows.get(step_id, [])
        is_gw = step["type"] in GATEWAY_TYPES

        if outgoing and (is_gw or len(outgoing) > 1):
            # Gateways always use branches; non-gateway elements with
            # multiple outgoing flows also use branches (implicit fork).
            step["branches"] = [
                {"condition": f["condition"], "target": f["target"]} for f in outgoing
            ]
        elif outgoing:
            step["next"] = outgoing[0]["target"]

    return steps


def _resolve_json_type(local_name: str) -> str | None:
    """Map an XML local element name to its JSON step type.

    Returns None for non-step elements (sequenceFlow, laneSet, etc.).
    """
    if local_name in _ELEMENT_TYPES:
        return local_name
    if local_name in _GATEWAY_XML_TO_JSON:
        return _GATEWAY_XML_TO_JSON[local_name]
    return None


def _extract_lanes(
    process: etree._Element,
) -> list[dict[str, Any]] | None:
    """Extract lane definitions from the process's laneSet."""
    lane_set = process.find(f"{{{BPMN_NS}}}laneSet")
    if lane_set is None:
        return None

    lanes: list[dict[str, Any]] = []
    for lane_el in lane_set.findall(f"{{{BPMN_NS}}}lane"):
        name = lane_el.get("name", "")
        step_ids = [
            ref.text for ref in lane_el.findall(f"{{{BPMN_NS}}}flowNodeRef") if ref.text
        ]
        lanes.append({"name": name, "steps": step_ids})

    return lanes if lanes else None


# ---------------------------------------------------------------------------
# ID re-mapping helpers
# ---------------------------------------------------------------------------


_OPAQUE_ID_PATTERN = re.compile(
    r"^(Activity|Gateway|Event|StartEvent|EndEvent|"
    r"ExclusiveGateway|ParallelGateway|InclusiveGateway|"
    r"EventBasedGateway|IntermediateCatchEvent|IntermediateThrowEvent|"
    r"Flow|DataObject|DataStore|Participant|Lane|"
    r"SubProcess|CallActivity|Task|UserTask|ServiceTask|"
    r"SendTask|ReceiveTask|BusinessRuleTask|ManualTask|ScriptTask)_",
)


def _is_opaque_id(xml_id: str) -> bool:
    """Return True if *xml_id* looks auto-generated by a BPMN modeler."""
    return bool(_OPAQUE_ID_PATTERN.match(xml_id))


def _build_id_map(steps: list[dict[str, Any]]) -> dict[str, str]:
    """Map opaque XML IDs to semantic snake_case IDs.

    Only IDs that look auto-generated (e.g. ``Activity_1o75wn8``)
    are replaced.  Already-semantic IDs are kept as-is.
    """
    id_map: dict[str, str] = {}
    used: dict[str, int] = {}

    for step in steps:
        xml_id = step["id"]

        if not _is_opaque_id(xml_id):
            id_map[xml_id] = xml_id
            used[xml_id] = used.get(xml_id, 0) + 1
            continue

        label = step.get("label", "") or ""
        step_type = step["type"]

        base = _to_snake_case(label) if label.strip() else step_type

        count = used.get(base, 0)
        new_id = base if count == 0 else f"{base}_{count}"
        used[base] = count + 1
        id_map[xml_id] = new_id

    return id_map


def _remap_step_ids(
    steps: list[dict[str, Any]],
    id_map: dict[str, str],
) -> list[dict[str, Any]]:
    """Replace XML IDs with semantic IDs in steps."""
    for step in steps:
        step["id"] = id_map.get(step["id"], step["id"])

        if step.get("next") and step["next"] in id_map:
            step["next"] = id_map[step["next"]]

        if step.get("branches"):
            for branch in step["branches"]:
                if branch["target"] in id_map:
                    branch["target"] = id_map[branch["target"]]

    return steps


def _remap_lane_ids(
    lanes: list[dict[str, Any]],
    id_map: dict[str, str],
) -> list[dict[str, Any]]:
    """Replace XML IDs with semantic IDs in lane step references."""
    for lane in lanes:
        lane["steps"] = [id_map.get(sid, sid) for sid in lane["steps"]]
    return lanes
