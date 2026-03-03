"""Convert a JSON process description to BPMN 2.0 XML.

The LLM produces a simple JSON structure describing the process flow.
This module deterministically converts that JSON into valid, process-only
BPMN 2.0 XML (without ``<bpmndi:BPMNDiagram>``).  The separate layouter
adds diagram coordinates afterwards.

JSON schema (simplified)::

    {
        "process": [
            {"type": "startEvent", "id": "start_1", "label": "Order Received"},
            {"type": "userTask", "id": "task_1", "label": "Review Order"},
            {
                "type": "exclusiveGateway",
                "id": "gw_1",
                "label": "Approved?",
                "has_join": true,
                "branches": [
                    {
                        "condition": "Yes",
                        "path": [
                            {"type": "serviceTask", "id": "t_2", "label": "Process"}
                        ],
                    },
                    {
                        "condition": "No",
                        "path": [
                            {"type": "serviceTask", "id": "t_3", "label": "Reject"}
                        ],
                    },
                ],
            },
            {"type": "endEvent", "id": "end_1", "label": "Done"},
        ]
    }
"""

import json
import logging
from typing import Any

from lxml import etree

from appkit_mcp_bpmn.models import BpmnProcessJson
from appkit_mcp_commons.exceptions import ValidationError

logger = logging.getLogger(__name__)

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
DI_NS = "http://www.omg.org/spec/DD/20100524/DI"
TARGET_NS = "http://bpmn.io/schema/bpmn"

_VALID_ELEMENT_TYPES = {
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

_GATEWAY_TYPES = {
    "exclusiveGateway",
    "parallelGateway",
    "inclusiveGateway",
    "eventBasedGateway",
}


def build_bpmn_xml(process_json: BpmnProcessJson | dict[str, Any] | str) -> str:
    """Convert a JSON process description into BPMN 2.0 XML.

    Args:
        process_json: ``BpmnProcessJson`` model, dict, or JSON string
            with a ``process`` key containing the ordered element list.

    Returns:
        BPMN 2.0 XML string (process-only, no BPMNDiagram section).

    Raises:
        ValidationError: If the JSON is malformed or semantically invalid.
    """
    data = _parse_input(process_json)
    elements = data.get("process")
    if not elements or not isinstance(elements, list):
        raise ValidationError("JSON must contain a non-empty 'process' array")

    # Flatten the nested structure into elements + flows
    flat_elements, flows = _flatten_process(elements)

    if not flat_elements:
        raise ValidationError("Process produced no BPMN elements")

    _validate_elements(flat_elements)

    # Build XML tree
    root = _build_definitions()
    process_el = etree.SubElement(
        root,
        f"{{{BPMN_NS}}}process",
        attrib={"id": "Process_1", "isExecutable": "true"},
    )

    # Add flow nodes
    for elem in flat_elements:
        _add_element(process_el, elem)

    # Add sequence flows
    for flow in flows:
        _add_sequence_flow(process_el, flow)

    return etree.tostring(
        root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    ).decode("utf-8")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_input(
    process_json: BpmnProcessJson | dict[str, Any] | str,
) -> dict[str, Any]:
    """Parse JSON string, dict, or Pydantic model into a dict."""
    if isinstance(process_json, BpmnProcessJson):
        return process_json.model_dump()

    if isinstance(process_json, str):
        try:
            data = json.loads(process_json)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Invalid JSON: {exc}") from exc
    else:
        data = process_json

    if not isinstance(data, dict):
        raise ValidationError("Input must be a JSON object with a 'process' key")
    return data


def _validate_elements(elements: list[dict[str, str]]) -> None:
    """Check that elements have valid types and unique IDs."""
    ids: set[str] = set()
    has_start = False
    has_end = False

    for elem in elements:
        elem_type = elem.get("type", "")
        elem_id = elem.get("id", "")

        if elem_type not in _VALID_ELEMENT_TYPES:
            raise ValidationError(
                f"Unknown element type '{elem_type}'. "
                f"Valid types: {sorted(_VALID_ELEMENT_TYPES)}"
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


def _flatten_process(
    elements: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Flatten nested gateway branches into a flat element/flow list.

    Walks the ``process`` array sequentially.  When a gateway with
    ``branches`` is encountered, each branch's ``path`` is flattened
    and the appropriate sequence flows are created.  If ``has_join``
    is ``true``, a matching merge gateway is inserted after the
    branches.

    Returns:
        Tuple of (flat_elements, sequence_flows).
    """
    flat: list[dict[str, str]] = []
    flows: list[dict[str, str]] = []
    flow_counter = 0

    def next_flow_id() -> str:
        nonlocal flow_counter
        flow_counter += 1
        return f"Flow_{flow_counter}"

    prev_id: str | None = None

    for item in elements:
        elem_type = item.get("type", "")
        elem_id = item.get("id", "")
        label = item.get("label", "")
        branches = item.get("branches")

        if elem_type in _GATEWAY_TYPES and branches:
            prev_id = _flatten_gateway(item, flat, flows, prev_id, next_flow_id)
        else:
            flat.append({"type": elem_type, "id": elem_id, "label": label})
            if prev_id:
                flows.append(_flow(next_flow_id(), prev_id, elem_id))
            prev_id = elem_id

    return flat, flows


def _flatten_gateway(
    item: dict[str, Any],
    flat: list[dict[str, str]],
    flows: list[dict[str, str]],
    prev_id: str | None,
    next_flow_id: Any,
) -> str | None:
    """Flatten a gateway with branches into *flat* and *flows*.

    Returns:
        The ID of the merge gateway (if ``has_join``) or ``None``.
    """
    elem_type = item["type"]
    elem_id = item["id"]
    label = item.get("label", "")
    branches = item.get("branches", [])

    flat.append({"type": elem_type, "id": elem_id, "label": label})
    if prev_id:
        flows.append(_flow(next_flow_id(), prev_id, elem_id))

    has_join = item.get("has_join", False)
    join_id = f"{elem_id}_join" if has_join else None
    branch_end_ids = _flatten_branches(branches, elem_id, flat, flows, next_flow_id)

    if has_join and join_id:
        flat.append({"type": elem_type, "id": join_id, "label": ""})
        flows.extend(_flow(next_flow_id(), eid, join_id) for eid in branch_end_ids)
        return join_id

    return None


def _flatten_branches(
    branches: list[dict[str, Any]],
    gateway_id: str,
    flat: list[dict[str, str]],
    flows: list[dict[str, str]],
    next_flow_id: Any,
) -> list[str]:
    """Process gateway branches and return the last element ID of each."""
    branch_end_ids: list[str] = []

    for branch in branches:
        condition = branch.get("condition", "")
        path = branch.get("path", [])
        if not path:
            continue

        first_in_branch = path[0]
        flows.append(
            _flow(
                next_flow_id(),
                gateway_id,
                first_in_branch["id"],
                condition,
            )
        )

        branch_prev: str | None = None
        for step in path:
            flat.append(
                {
                    "type": step.get("type", "task"),
                    "id": step["id"],
                    "label": step.get("label", ""),
                }
            )
            if branch_prev:
                flows.append(_flow(next_flow_id(), branch_prev, step["id"]))
            branch_prev = step["id"]

        if branch_prev:
            branch_end_ids.append(branch_prev)

    return branch_end_ids


def _flow(
    flow_id: str,
    source: str,
    target: str,
    condition: str = "",
) -> dict[str, str]:
    """Create a sequence flow dict."""
    result: dict[str, str] = {
        "id": flow_id,
        "sourceRef": source,
        "targetRef": target,
    }
    if condition:
        result["condition"] = condition
    return result


def _build_definitions() -> etree._Element:
    """Create the ``<bpmn:definitions>`` root element."""
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


def _add_element(
    process: etree._Element,
    elem: dict[str, str],
) -> None:
    """Add a BPMN flow node to the process element."""
    tag = f"{{{BPMN_NS}}}{elem['type']}"
    attrib: dict[str, str] = {"id": elem["id"]}
    if elem.get("label"):
        attrib["name"] = elem["label"]
    etree.SubElement(process, tag, attrib=attrib)


def _add_sequence_flow(
    process: etree._Element,
    flow: dict[str, str],
) -> None:
    """Add a ``<bpmn:sequenceFlow>`` to the process element."""
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
