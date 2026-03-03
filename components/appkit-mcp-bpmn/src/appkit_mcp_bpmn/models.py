"""Pydantic models for BPMN MCP tool results and structured output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

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


# Resolve the forward reference BpmnBranch -> BpmnElement.
BpmnBranch.model_rebuild()


class BpmnProcessJson(BaseModel):
    """Root model for the BPMN process JSON produced by the LLM.

    Use as ``response_format`` with ``client.beta.chat.completions.parse()``
    to guarantee the LLM returns valid, schema-conformant JSON.
    """

    process: list[BpmnElement] = Field(
        description="Ordered list of BPMN elements describing the workflow.",
    )


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
