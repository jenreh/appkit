"""Flat sequential BPMN process model for LLM structured output.

All steps live in a single flat list.  Flow is sequential (step N → step N+1)
unless overridden by ``next`` (explicit jump) or ``branches`` (gateway fan-out).
No nested branch paths, no ``has_join`` — merge points are modelled as explicit
``merge`` steps.

OpenAI strict-mode compatible: every field is always present (null when unused).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from appkit_mcp_commons.models import BaseResult

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

type StepType = Literal[
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
    "intermediateCatchEvent",
    "intermediateThrowEvent",
    "exclusive",
    "parallel",
    "inclusive",
    "eventBased",
    "merge",
]

ElementId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        pattern=r"^[A-Za-z0-9_]+$",
    ),
]

GATEWAY_TYPES: frozenset[str] = frozenset(
    {"exclusive", "parallel", "inclusive", "eventBased"}
)

BPMN_TYPE_MAP: dict[str, str] = {
    "exclusive": "exclusiveGateway",
    "parallel": "parallelGateway",
    "inclusive": "inclusiveGateway",
    "eventBased": "eventBasedGateway",
    "merge": "parallelGateway",
}

MIN_GATEWAY_BRANCHES = 2

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class _StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BpmnBranch(_StrictBase):
    condition: str = Field(
        default="",
        description="Guard label, e.g. 'Approved'.",
    )
    target: ElementId = Field(
        description="Target step id this branch jumps to.",
    )


class BpmnStep(_StrictBase):
    id: ElementId = Field(description="Unique step identifier.")
    type: StepType = Field(description="BPMN element type.")
    label: str = Field(default="", description="Human-readable label.")
    branches: list[BpmnBranch] | None = Field(
        default=None,
        description=(
            "Outgoing branches. Required for gateways (>=2). "
            "Optional for tasks/events with multiple outgoing flows."
        ),
    )
    next: ElementId | None = Field(
        default=None,
        description=(
            "Explicit jump target overriding sequential flow. "
            "null = continue to next step in list."
        ),
    )


class BpmnLane(_StrictBase):
    name: str = Field(description="Lane display name.")
    steps: list[ElementId] = Field(description="Step ids assigned to this lane.")


class BpmnProcess(_StrictBase):
    steps: list[BpmnStep] = Field(
        description="Flat ordered list of process steps.",
    )
    lanes: list[BpmnLane] | None = Field(
        default=None,
        description="Optional swimlane assignments.",
    )

    @model_validator(mode="after")
    def validate_process(self) -> Self:
        if not self.steps:
            raise ValueError("Process must contain at least one step.")

        _validate_structure(self.steps)
        ids = {s.id for s in self.steps}
        _validate_step_shapes(self.steps, ids)
        if self.lanes:
            _validate_lanes(self.lanes, ids)
        graph = _build_flow_graph(self.steps)
        _validate_reachability(self.steps, graph)
        return self


# ---------------------------------------------------------------------------
class DiagramResult(BaseResult, _StrictBase):
    id: str | None = Field(default=None, description="Unique diagram ID")
    name: str | None = Field(default=None, description="Diagram display name")
    download_url: str | None = Field(default=None, description="URL for .bpmn download")
    view_url: str | None = Field(default=None, description="URL for HTML viewer")


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_structure(steps: list[BpmnStep]) -> None:
    """Check startEvent/endEvent counts and unique IDs."""
    id_counts = Counter(s.id for s in steps)
    dups = sorted(k for k, v in id_counts.items() if v > 1)
    if dups:
        raise ValueError("Duplicate step ids: " + ", ".join(dups))

    if steps[0].type != "startEvent":
        raise ValueError("First step must be a startEvent.")

    starts = [s for s in steps if s.type == "startEvent"]
    if len(starts) != 1:
        raise ValueError(f"Exactly one startEvent required, found {len(starts)}.")

    if not any(s.type == "endEvent" for s in steps):
        raise ValueError("At least one endEvent is required.")


def _validate_step_shapes(steps: list[BpmnStep], ids: set[str]) -> None:
    """Validate per-step constraints and reference integrity."""
    for step in steps:
        is_gw = step.type in GATEWAY_TYPES

        if is_gw:
            if not step.branches or len(step.branches) < MIN_GATEWAY_BRANCHES:
                raise ValueError(
                    f"Gateway '{step.id}' needs at least "
                    f"{MIN_GATEWAY_BRANCHES} branches."
                )
        elif step.branches is not None and len(step.branches) == 0:
            raise ValueError(f"Step '{step.id}' has empty branches list.")

        if step.branches and step.next is not None:
            raise ValueError(
                f"Step '{step.id}' must not set next "
                "when branches are present (flow goes through branches)."
            )

        if step.type == "endEvent" and step.next is not None:
            raise ValueError(f"endEvent '{step.id}' must not set next.")

        if step.next is not None and step.next not in ids:
            raise ValueError(f"Step '{step.id}' references unknown next '{step.next}'.")

        if step.branches:
            for br in step.branches:
                if br.target not in ids:
                    raise ValueError(
                        f"Branch in '{step.id}' references unknown "
                        f"target '{br.target}'."
                    )


def _validate_lanes(lanes: list[BpmnLane], ids: set[str]) -> None:
    """Validate lane step references."""
    for lane in lanes:
        for sid in lane.steps:
            if sid not in ids:
                raise ValueError(f"Lane '{lane.name}' references unknown step '{sid}'.")


def _build_flow_graph(steps: list[BpmnStep]) -> dict[str, set[str]]:
    """Build the control-flow graph from the flat step list.

    Flow rules:
    1. step.branches set → each branch.target
    2. endEvent → no outgoing flow
    3. step.next is set → flow to next target
    4. Otherwise → flow to steps[idx + 1]
    """
    graph: dict[str, set[str]] = defaultdict(set)
    for idx, step in enumerate(steps):
        graph.setdefault(step.id, set())

        if step.type == "endEvent":
            continue

        if step.branches:
            for br in step.branches:
                graph[step.id].add(br.target)
        elif step.next is not None:
            graph[step.id].add(step.next)
        elif idx + 1 < len(steps):
            graph[step.id].add(steps[idx + 1].id)

    return graph


def _dfs(graph: dict[str, set[str]], starts: list[str]) -> set[str]:
    visited: set[str] = set()
    stack = list(starts)
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        stack.extend(graph.get(node, set()) - visited)
    return visited


def _reverse_graph(graph: dict[str, set[str]]) -> dict[str, set[str]]:
    rev: dict[str, set[str]] = defaultdict(set)
    for src, targets in graph.items():
        rev.setdefault(src, set())
        for tgt in targets:
            rev[tgt].add(src)
    return rev


def _validate_reachability(
    steps: list[BpmnStep],
    graph: dict[str, set[str]],
) -> None:
    """Validate all steps are reachable and can reach an endEvent."""
    ids = {s.id for s in steps}
    start_id = steps[0].id

    reachable = _dfs(graph, [start_id])
    unreachable = sorted(ids - reachable)
    if unreachable:
        raise ValueError("Unreachable steps: " + ", ".join(unreachable))

    end_ids = [s.id for s in steps if s.type == "endEvent"]
    can_reach_end = _dfs(_reverse_graph(graph), end_ids)
    non_terminating = sorted(
        s.id for s in steps if s.id in reachable and s.id not in can_reach_end
    )
    if non_terminating:
        raise ValueError(
            "Steps that cannot reach any endEvent: " + ", ".join(non_terminating)
        )
