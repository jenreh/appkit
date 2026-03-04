"""Pydantic models for BPMN MCP tool results and structured output.

Optimized for robustness:
- Strict JSON (extra fields forbidden)
- Gateways: branches only on gateways, at least 2 branches
- Branches: path MUST be non-empty (pass-through uses a NoOp task)
- Process: exactly one startEvent (first), at least one endEvent
- target_ref must reference an existing id (enabled)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from appkit_mcp_commons.models import BaseResult

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

_GATEWAY_TYPES: set[str] = {
    "exclusiveGateway",
    "parallelGateway",
    "inclusiveGateway",
    "eventBasedGateway",
}

MIN_GATEWAY_BRANCHES = 2


class _StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BpmnBranch(_StrictBaseModel):
    condition: str = Field(
        default="", description="Guard condition label (e.g. 'Approved')."
    )
    path: list[BpmnElement] = Field(description="Ordered elements inside this branch.")
    target_ref: str | None = Field(
        default=None,
        description="ID of an existing element to connect to (for loops/jumps).",
    )

    @model_validator(mode="after")
    def validate_branch_shape(self) -> BpmnBranch:
        if len(self.path) == 0:
            raise ValueError(
                "Invalid branch: path must be non-empty. "
                "Fix: add a minimal NoOp task (type='task', label='Continue') "
                "or add the real branch steps."
            )
        return self


class BpmnElement(_StrictBaseModel):
    type: _ELEMENT_TYPES = Field(description="BPMN element type.")
    id: str = Field(description="Unique element identifier (e.g. 'task_1').")
    label: str = Field(
        default="", description="Human-readable name shown on the element."
    )
    branches: list[BpmnBranch] | None = Field(
        default=None, description="Gateway branches (gateways only)."
    )
    has_join: bool = Field(
        default=False, description="Auto-merge after branches (gateways only)."
    )
    target_ref: str | None = Field(
        default=None, description="Override next connection."
    )

    @model_validator(mode="after")
    def validate_gateway_rules(self) -> BpmnElement:
        is_gateway = self.type in _GATEWAY_TYPES

        if not is_gateway:
            if self.branches is not None:
                raise ValueError(
                    f"Element '{self.id}' is not a gateway, so branches must be null."
                )
            if self.has_join:
                raise ValueError(
                    f"Element '{self.id}' is not a gateway, so has_join must be false."
                )
            return self

        if self.branches is None or len(self.branches) < MIN_GATEWAY_BRANCHES:
            raise ValueError(
                f"Gateway '{self.id}' must have at least "
                f"{MIN_GATEWAY_BRANCHES} branches."
            )

        def branch_signature(b: BpmnBranch) -> tuple:
            path_sig = tuple((e.type, e.id, e.label, e.target_ref) for e in b.path)
            return (b.target_ref, path_sig)

        sigs = [branch_signature(b) for b in self.branches]
        if len(set(sigs)) == 1:
            raise ValueError(
                f"Gateway '{self.id}' is redundant: all branches are identical."
            )

        return self


BpmnBranch.model_rebuild()
BpmnElement.model_rebuild()


def _collect_all_elements(
    elements: list[BpmnElement], depth: int = 0
) -> list[tuple[BpmnElement, int]]:
    result: list[tuple[BpmnElement, int]] = []
    for elem in elements:
        result.append((elem, depth))
        if elem.branches:
            for br in elem.branches:
                result.extend(_collect_all_elements(br.path, depth + 1))
    return result


class BpmnProcessJson(_StrictBaseModel):
    process: list[BpmnElement] = Field(
        description="Ordered list of BPMN elements describing the workflow."
    )

    @model_validator(mode="after")
    def validate_process(self) -> BpmnProcessJson:
        if not self.process:
            raise ValueError("Process must contain at least one element.")
        if self.process[0].type != "startEvent":
            raise ValueError(
                f"First element must be a startEvent, got '{self.process[0].type}'."
            )

        all_elements = _collect_all_elements(self.process)

        start_events = [e for e, _ in all_elements if e.type == "startEvent"]
        if len(start_events) != 1:
            raise ValueError(
                f"Exactly one startEvent required, found {len(start_events)}."
            )

        end_events = [e for e, _ in all_elements if e.type == "endEvent"]
        if not end_events:
            raise ValueError("At least one endEvent is required.")

        ids = {e.id for e, _ in all_elements}
        for e, _ in all_elements:
            if e.target_ref is not None and e.target_ref not in ids:
                raise ValueError(
                    f"Element target_ref '{e.target_ref}' does not reference an "
                    "existing id."
                )
            if e.branches:
                for b in e.branches:
                    if b.target_ref is not None and b.target_ref not in ids:
                        raise ValueError(
                            f"Branch target_ref '{b.target_ref}' does not reference an "
                            "existing id."
                        )

        return self


class DiagramResult(BaseResult, _StrictBaseModel):
    id: str | None = Field(default=None, description="Unique diagram ID")
    download_url: str | None = Field(default=None, description="URL for .bpmn download")
    view_url: str | None = Field(default=None, description="URL for HTML viewer")
