"""Convert a flat BPMN process JSON into BPMN 2.0 XML.

The LLM produces a flat list of steps with sequential flow, explicit
``next`` jumps, and gateway ``branches``.  This module deterministically
converts that structure into valid, process-only BPMN 2.0 XML (without
``<bpmndi:BPMNDiagram>``).  The separate layouter adds diagram
coordinates afterwards.

JSON schema (simplified)::

    {
        "steps": [
            {
                "id": "start",
                "type": "startEvent",
                "label": "Start",
                "branches": null,
                "next": null,
            },
            {
                "id": "task_1",
                "type": "task",
                "label": "Do work",
                "branches": null,
                "next": null,
            },
            {
                "id": "gw",
                "type": "exclusive",
                "label": "OK?",
                "branches": [
                    {"condition": "Yes", "target": "task_done"},
                    {"condition": "No", "target": "task_1"},
                ],
                "next": null,
            },
            {
                "id": "task_done",
                "type": "task",
                "label": "Done",
                "branches": null,
                "next": null,
            },
            {
                "id": "end",
                "type": "endEvent",
                "label": "End",
                "branches": null,
                "next": null,
            },
        ],
        "lanes": null,
    }
"""

import json
import logging
from typing import Any

from lxml import etree

from appkit_mcp_bpmn.models import BPMN_TYPE_MAP, GATEWAY_TYPES, BpmnProcess
from appkit_mcp_commons.exceptions import ValidationError

logger = logging.getLogger(__name__)

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
DI_NS = "http://www.omg.org/spec/DD/20100524/DI"
TARGET_NS = "http://bpmn.io/schema/bpmn"


def build_bpmn_xml(process_json: BpmnProcess | dict[str, Any] | str) -> str:
    """Convert a flat process JSON into BPMN 2.0 XML.

    Args:
        process_json: ``BpmnProcess`` model, dict, or JSON string
            with ``steps`` (and optional ``lanes``).

    Returns:
        BPMN 2.0 XML string (process-only, no BPMNDiagram section).

    Raises:
        ValidationError: If the JSON is malformed or semantically invalid.
    """
    data = _parse_input(process_json)
    steps = data.get("steps")
    if not steps or not isinstance(steps, list):
        raise ValidationError("JSON must contain a non-empty 'steps' array")

    lanes = data.get("lanes")

    elements, flows = _build_elements_and_flows(steps)

    if not elements:
        raise ValidationError("Process produced no BPMN elements")

    _validate_elements(elements)

    root = _build_definitions()

    has_lanes = lanes and isinstance(lanes, list) and len(lanes) > 0
    if has_lanes:
        _build_collaboration_xml(root, lanes)

    process_el = etree.SubElement(
        root,
        f"{{{BPMN_NS}}}process",
        attrib={"id": "Process_1", "isExecutable": "true"},
    )

    if has_lanes:
        _build_lane_set_xml(process_el, lanes)

    for elem in elements:
        _add_element(process_el, elem)

    for flow in flows:
        _add_sequence_flow(process_el, flow)

    return etree.tostring(
        root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    ).decode("utf-8")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_input(
    process_json: BpmnProcess | dict[str, Any] | str,
) -> dict[str, Any]:
    if isinstance(process_json, BpmnProcess):
        return process_json.model_dump()

    if isinstance(process_json, str):
        try:
            data = json.loads(process_json)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Invalid JSON: {exc}") from exc
    else:
        data = process_json

    if not isinstance(data, dict):
        raise ValidationError("Input must be a JSON object with a 'steps' key")
    return data


def _validate_elements(elements: list[dict[str, str]]) -> None:
    """Check that elements have valid types and unique IDs."""
    all_valid_types = {
        "startEvent",
        "endEvent",
        "task",
        "userTask",
        "serviceTask",
        "sendTask",
        "receiveTask",
        "businessRuleTask",
        "manualTask",
        "scriptTask",
        "callActivity",
        "subProcess",
        "exclusiveGateway",
        "parallelGateway",
        "inclusiveGateway",
        "eventBasedGateway",
        "intermediateCatchEvent",
        "intermediateThrowEvent",
    }

    ids: set[str] = set()
    has_start = False
    has_end = False

    for elem in elements:
        elem_type = elem.get("type", "")
        elem_id = elem.get("id", "")

        if elem_type not in all_valid_types:
            raise ValidationError(
                f"Unknown element type '{elem_type}'. "
                f"Valid types: {sorted(all_valid_types)}"
            )

        if not elem_id:
            raise ValidationError(f"Element of type '{elem_type}' is missing an 'id'")

        if elem_id in ids:
            raise ValidationError(f"Duplicate element id: '{elem_id}'")
        ids.add(elem_id)

        if elem_type == "startEvent":
            has_start = True
        elif elem_type == "endEvent":
            has_end = True

    if not has_start:
        raise ValidationError("Process must contain at least one 'startEvent'")
    if not has_end:
        raise ValidationError("Process must contain at least one 'endEvent'")


def _build_elements_and_flows(
    steps: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Build flat BPMN elements and sequence flows from the step list.

    Flow rules:
    1. Gateway → each branch.target (with condition label)
    2. endEvent → no outgoing flow
    3. step.next is set → flow to next target
    4. Otherwise → flow to steps[idx + 1]
    """
    elements: list[dict[str, str]] = []
    flows: list[dict[str, str]] = []
    flow_counter = 0

    def next_flow_id() -> str:
        nonlocal flow_counter
        flow_counter += 1
        return f"Flow_{flow_counter}"

    for idx, step in enumerate(steps):
        step_type = step.get("type", "")
        step_id = step.get("id", "")
        label = step.get("label", "")
        branches = step.get("branches")
        next_target = step.get("next")

        xml_type = BPMN_TYPE_MAP.get(step_type, step_type)
        elements.append({"type": xml_type, "id": step_id, "label": label})

        if step_type == "endEvent":
            continue

        if step_type in GATEWAY_TYPES and branches:
            for br in branches:
                condition = br.get("condition", "")
                target = br.get("target", "")
                if target:
                    flows.append(_flow(next_flow_id(), step_id, target, condition))
        elif next_target:
            flows.append(_flow(next_flow_id(), step_id, next_target))
        elif idx + 1 < len(steps):
            next_step = steps[idx + 1]
            flows.append(_flow(next_flow_id(), step_id, next_step.get("id", "")))

    return elements, flows


def _flow(
    flow_id: str,
    source: str,
    target: str,
    condition: str = "",
) -> dict[str, str]:
    result: dict[str, str] = {
        "id": flow_id,
        "sourceRef": source,
        "targetRef": target,
    }
    if condition:
        result["condition"] = condition
    return result


def _build_definitions() -> etree._Element:
    nsmap = {
        "bpmn": BPMN_NS,
        "bpmndi": BPMNDI_NS,
        "dc": DC_NS,
        "di": DI_NS,
    }
    return etree.Element(
        f"{{{BPMN_NS}}}definitions",
        attrib={
            "id": "Definitions_1",
            "targetNamespace": TARGET_NS,
        },
        nsmap=nsmap,
    )


def _build_collaboration_xml(
    root: etree._Element,
    _lanes: list[dict[str, Any]],
) -> None:
    """Add a ``<bpmn:collaboration>`` with a single participant."""
    collab = etree.SubElement(
        root,
        f"{{{BPMN_NS}}}collaboration",
        attrib={"id": "Collaboration_1"},
    )
    etree.SubElement(
        collab,
        f"{{{BPMN_NS}}}participant",
        attrib={
            "id": "Participant_1",
            "processRef": "Process_1",
        },
    )


def _build_lane_set_xml(
    process_el: etree._Element,
    lanes: list[dict[str, Any]],
) -> None:
    """Add ``<bpmn:laneSet>`` with lanes to the process element."""
    lane_set = etree.SubElement(
        process_el,
        f"{{{BPMN_NS}}}laneSet",
        attrib={"id": "LaneSet_1"},
    )
    for i, lane in enumerate(lanes, start=1):
        lane_el = etree.SubElement(
            lane_set,
            f"{{{BPMN_NS}}}lane",
            attrib={
                "id": f"Lane_{i}",
                "name": lane.get("name", f"Lane {i}"),
            },
        )
        for step_id in lane.get("steps", []):
            ref = etree.SubElement(lane_el, f"{{{BPMN_NS}}}flowNodeRef")
            ref.text = step_id


def _add_element(
    process: etree._Element,
    elem: dict[str, str],
) -> None:
    tag = f"{{{BPMN_NS}}}{elem['type']}"
    attrib: dict[str, str] = {"id": elem["id"]}
    if elem.get("label"):
        attrib["name"] = elem["label"]
    etree.SubElement(process, tag, attrib=attrib)


def _add_sequence_flow(
    process: etree._Element,
    flow: dict[str, str],
) -> None:
    attrib: dict[str, str] = {
        "id": flow["id"],
        "sourceRef": flow["sourceRef"],
        "targetRef": flow["targetRef"],
    }
    if flow.get("condition"):
        attrib["name"] = flow["condition"]

    sf = etree.SubElement(process, f"{{{BPMN_NS}}}sequenceFlow", attrib=attrib)

    if flow.get("condition"):
        xsi_type = "{http://www.w3.org/2001/XMLSchema-instance}type"
        cond = etree.SubElement(
            sf,
            f"{{{BPMN_NS}}}conditionExpression",
            attrib={xsi_type: "bpmn:tFormalExpression"},
        )
        cond.text = flow["condition"]
