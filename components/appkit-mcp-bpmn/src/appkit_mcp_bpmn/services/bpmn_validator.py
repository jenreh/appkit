"""BPMN XML validator using lxml for schema-aware parsing."""

import logging

from lxml import etree

from appkit_mcp_commons.exceptions import ValidationError

logger = logging.getLogger(__name__)

BPMN_NAMESPACES = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmn2": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "dc": "http://www.omg.org/spec/DD/20100524/DC",
    "di": "http://www.omg.org/spec/DD/20100524/DI",
}

_DEFINITIONS_TAGS = {
    "{http://www.omg.org/spec/BPMN/20100524/MODEL}definitions",
    "definitions",
}


def validate_bpmn_xml(xml: str) -> str:
    """Parse and validate a BPMN 2.0 XML string.

    Checks:
    1. Well-formed XML.
    2. Root element is ``<bpmn:definitions>`` (or ``<definitions>``).
    3. At least one ``<process>`` element exists.
    4. At least one start-event and one end-event exist.

    Args:
        xml: Raw BPMN 2.0 XML string.

    Returns:
        Normalised XML string (pretty-printed, UTF-8).

    Raises:
        ValidationError: If XML is malformed or structurally invalid.
    """
    if not xml or not xml.strip():
        raise ValidationError("Empty XML input")

    xml_bytes = xml.strip().encode("utf-8")

    # Remove XML declaration BOM/encoding issues
    if xml_bytes.startswith(b"\xef\xbb\xbf"):
        xml_bytes = xml_bytes[3:]

    try:
        root = etree.fromstring(xml_bytes)  # noqa: S320
    except etree.XMLSyntaxError as exc:
        raise ValidationError(f"Malformed XML: {exc}") from exc

    # Validate root element
    if root.tag not in _DEFINITIONS_TAGS:
        # Check with namespace
        local = etree.QName(root.tag).localname
        if local != "definitions":
            raise ValidationError(f"Root element must be <definitions>, got <{local}>")

    # Find process elements (any namespace)
    bpmn_ns = BPMN_NAMESPACES["bpmn"]
    processes = root.findall(f".//{{{bpmn_ns}}}process")
    if not processes:
        # Try without namespace
        processes = root.findall(".//process")
    if not processes:
        raise ValidationError("BPMN XML must contain at least one <process> element")

    # Validate start/end events exist
    start_events = root.findall(f".//{{{bpmn_ns}}}startEvent") or root.findall(
        ".//startEvent"
    )
    end_events = root.findall(f".//{{{bpmn_ns}}}endEvent") or root.findall(
        ".//endEvent"
    )

    if not start_events:
        raise ValidationError("BPMN process must contain at least one <startEvent>")
    if not end_events:
        raise ValidationError("BPMN process must contain at least one <endEvent>")

    logger.info(
        "BPMN XML validated: %d process(es), %d start event(s), %d end event(s)",
        len(processes),
        len(start_events),
        len(end_events),
    )

    # Return normalised XML
    return etree.tostring(
        root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    ).decode("utf-8")
