"""Tests for BPMN XML validator."""

import pytest

from appkit_mcp_bpmn.services.bpmn_validator import validate_bpmn_xml
from appkit_mcp_commons.exceptions import ValidationError

VALID_BPMN = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="Event_Start" name="Start" />
    <bpmn:task id="Activity_1" name="Do Something" />
    <bpmn:endEvent id="Event_End" name="End" />
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Event_Start" targetRef="Activity_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Activity_1" targetRef="Event_End" />
  </bpmn:process>
</bpmn:definitions>
"""


def test_validate_valid_bpmn() -> None:
    """Valid BPMN XML passes validation and returns normalised output."""
    result = validate_bpmn_xml(VALID_BPMN)
    assert "definitions" in result
    assert "process" in result
    assert "startEvent" in result
    assert "endEvent" in result


def test_validate_empty_input() -> None:
    """Empty string raises ValidationError."""
    with pytest.raises(ValidationError, match="Empty XML input"):
        validate_bpmn_xml("")


def test_validate_whitespace_only() -> None:
    """Whitespace-only string raises ValidationError."""
    with pytest.raises(ValidationError, match="Empty XML input"):
        validate_bpmn_xml("   \n\t  ")


def test_validate_malformed_xml() -> None:
    """Malformed XML raises ValidationError."""
    with pytest.raises(ValidationError, match="Malformed XML"):
        validate_bpmn_xml("<not-closed>")


def test_validate_wrong_root_element() -> None:
    """Non-definitions root element raises ValidationError."""
    xml = '<html xmlns="http://www.w3.org/1999/xhtml"><body/></html>'
    with pytest.raises(ValidationError, match="Root element must be"):
        validate_bpmn_xml(xml)


def test_validate_missing_process() -> None:
    """Definitions without a process raises ValidationError."""
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_1">
</bpmn:definitions>
"""
    with pytest.raises(ValidationError, match="at least one <process>"):
        validate_bpmn_xml(xml)


def test_validate_missing_start_event() -> None:
    """Process without startEvent raises ValidationError."""
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_1">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:task id="Activity_1" name="Do Something" />
    <bpmn:endEvent id="Event_End" name="End" />
  </bpmn:process>
</bpmn:definitions>
"""
    with pytest.raises(ValidationError, match="startEvent"):
        validate_bpmn_xml(xml)


def test_validate_missing_end_event() -> None:
    """Process without endEvent raises ValidationError."""
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_1">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="Event_Start" name="Start" />
    <bpmn:task id="Activity_1" name="Do Something" />
  </bpmn:process>
</bpmn:definitions>
"""
    with pytest.raises(ValidationError, match="endEvent"):
        validate_bpmn_xml(xml)


def test_validate_returns_normalised_xml() -> None:
    """Validated XML is returned as normalised, pretty-printed UTF-8."""
    result = validate_bpmn_xml(VALID_BPMN)
    assert result.startswith("<?xml")
    assert "UTF-8" in result.split("\n")[0]


def test_validate_bpmn_with_bom() -> None:
    """XML with UTF-8 BOM is handled correctly."""
    bom_xml = "\ufeff" + VALID_BPMN
    result = validate_bpmn_xml(bom_xml)
    assert "definitions" in result


def test_validate_plain_definitions_tag() -> None:
    """XML using plain <definitions> (no namespace prefix) is accepted."""
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             id="Definitions_1">
  <process id="Process_1" isExecutable="true">
    <startEvent id="Event_Start" name="Start" />
    <endEvent id="Event_End" name="End" />
  </process>
</definitions>
"""
    result = validate_bpmn_xml(xml)
    assert "definitions" in result
