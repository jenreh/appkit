"""Pydantic models for BPMN MCP tool results and structured output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from appkit_mcp_commons.models import BaseResult

# ---------------------------------------------------------------------------
# Structured-output models — used with OpenAI ``response_format``
# ---------------------------------------------------------------------------

_ELEMENT_TYPES = Literal[
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
]


class BpmnBranch(BaseModel):
    """A branch inside a gateway element."""

    condition: str = Field(
        default="",
        description="Guard condition label (e.g. 'Approved', 'Rejected').",
    )
    path: list[BpmnElement] = Field(
        description="Ordered elements inside this branch.",
    )
    target_ref: str | None = Field(
        default=None,
        description="ID of an existing element to connect to (for loops/jumps).",
    )


class BpmnElement(BaseModel):
    """A single BPMN element in the process."""

    type: _ELEMENT_TYPES = Field(description="BPMN element type.")
    id: str = Field(description="Unique element identifier (e.g. 'task_1').")
    label: str = Field(
        default="",
        description="Human-readable name shown on the element.",
    )
    branches: list[BpmnBranch] | None = Field(
        default=None,
        description="Gateway branches. Only set for gateway types.",
    )
    has_join: bool = Field(
        default=False,
        description="Whether a merge gateway is auto-inserted after branches.",
    )
    target_ref: str | None = Field(
        default=None,
        description="ID of the next element to connect to. Overrides default flow.",
    )


# Resolve the forward reference BpmnBranch -> BpmnElement.
BpmnBranch.model_rebuild()
BpmnElement.model_rebuild()


def _collect_all_elements(
    elements: list[BpmnElement],
    depth: int = 0,
) -> list[tuple[BpmnElement, int]]:
    """Recursively collect all elements with their nesting depth."""
    result: list[tuple[BpmnElement, int]] = []
    for elem in elements:
        result.append((elem, depth))
        if elem.branches:
            for branch in elem.branches:
                result.extend(_collect_all_elements(branch.path, depth + 1))
    return result


class BpmnProcessJson(BaseModel):
    """Root model for the BPMN process JSON produced by the LLM.

    Use as ``response_format`` with ``client.beta.chat.completions.parse()``
    to guarantee the LLM returns valid, schema-conformant JSON.
    """

    process: list[BpmnElement] = Field(
        description="Ordered list of BPMN elements describing the workflow.",
    )

    @model_validator(mode="after")
    def validate_no_dangling_events(self) -> BpmnProcessJson:
        """Ensure exactly one startEvent (first) and at least one endEvent."""
        if not self.process:
            raise ValueError("Process must contain at least one element.")

        # --- startEvent checks ---
        if self.process[0].type != "startEvent":
            raise ValueError(
                f"First element must be a startEvent, got '{self.process[0].type}'.",
            )

        all_elements = _collect_all_elements(self.process)

        start_events = [e for e, depth in all_elements if e.type == "startEvent"]
        if len(start_events) != 1:
            raise ValueError(
                f"Exactly one startEvent required, found {len(start_events)}.",
            )

        # --- endEvent checks ---
        end_events = [e for e, depth in all_elements if e.type == "endEvent"]
        if not end_events:
            raise ValueError("At least one endEvent is required.")

        return self


# ---------------------------------------------------------------------------
# Tool-result models
# ---------------------------------------------------------------------------


class DiagramResult(BaseResult):
    """Result of a BPMN diagram operation.

    Attributes:
        id: Unique diagram identifier (UUID).
        download_url: URL to download the raw ``.bpmn`` file.
        view_url: URL for the interactive HTML viewer.
    """

    id: str | None = Field(default=None, description="Unique diagram ID")
    download_url: str | None = Field(default=None, description="URL for .bpmn download")
    view_url: str | None = Field(default=None, description="URL for HTML viewer")
