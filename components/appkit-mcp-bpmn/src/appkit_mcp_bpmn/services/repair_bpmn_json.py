"""Deterministic repair for LLM-generated BPMN JSON.

Enforces: every gateway branch has a NON-EMPTY path by inserting a NoOp task.

Usage:
    data = json.loads(raw_text)
    data = repair_bpmn_json(data)
    parsed = BpmnProcessJson.model_validate(data)
"""

from __future__ import annotations

import re
import uuid
from typing import Any

_NOOP_ID_SAFE = re.compile(r"[^A-Za-z0-9_]")


def _mk_noop_task(existing_ids: set[str], prefix: str = "Task_NoOp") -> dict[str, Any]:
    base = f"{prefix}_{uuid.uuid4().hex[:8]}"
    base = _NOOP_ID_SAFE.sub("_", base)
    while base in existing_ids:
        base = f"{prefix}_{uuid.uuid4().hex[:8]}"
        base = _NOOP_ID_SAFE.sub("_", base)

    existing_ids.add(base)
    return {
        "type": "task",
        "id": base,
        "label": "Continue",
        "branches": None,
        "has_join": False,
        "target_ref": None,
    }


def _collect_ids_from_raw_process(process: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()

    def walk_elements(elems: list[dict[str, Any]]) -> None:
        for el in elems:
            el_id = el.get("id")
            if isinstance(el_id, str):
                ids.add(el_id)
            branches = el.get("branches")
            if isinstance(branches, list):
                for br in branches:
                    path = br.get("path")
                    if isinstance(path, list):
                        walk_elements(path)

    walk_elements(process)
    return ids


def repair_bpmn_json(raw: dict[str, Any]) -> dict[str, Any]:
    if (
        not isinstance(raw, dict)
        or "process" not in raw
        or not isinstance(raw["process"], list)
    ):
        return raw

    process: list[dict[str, Any]] = raw["process"]
    existing_ids = _collect_ids_from_raw_process(process)

    def repair_elements(elems: list[dict[str, Any]]) -> None:
        for el in elems:
            branches = el.get("branches")
            if not isinstance(branches, list):
                continue

            for br in branches:
                path = br.get("path")
                if not isinstance(path, list):
                    path = []
                    br["path"] = path

                if len(path) == 0:
                    path.append(_mk_noop_task(existing_ids))

                repair_elements(path)

    repair_elements(process)
    return raw
