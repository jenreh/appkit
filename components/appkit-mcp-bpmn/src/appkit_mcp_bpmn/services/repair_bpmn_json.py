"""Deterministic repair for LLM-generated flat BPMN JSON.

Normalises common LLM mistakes so the data can pass
``BpmnProcess.model_validate()`` without a full retry cycle.

Repairs applied:
- Accepts ``process`` key as alias for ``steps``.
- Ensures every step has all required keys with safe defaults.
- Ensures every branch has ``condition`` and ``target`` keys.
- Strips unknown top-level keys.

Usage:
    data = json.loads(raw_text)
    data = repair_bpmn_json(data)
    parsed = BpmnProcess.model_validate(data)
"""

from __future__ import annotations

import uuid
from typing import Any

_REQUIRED_STEP_KEYS: dict[str, Any] = {
    "id": "",
    "type": "task",
    "label": "",
    "branches": None,
    "next": None,
}


def _ensure_step_keys(step: dict[str, Any]) -> dict[str, Any]:
    """Fill in missing keys with safe defaults."""
    for key, default in _REQUIRED_STEP_KEYS.items():
        if key not in step:
            if key == "id":
                step["id"] = f"step_{uuid.uuid4().hex[:8]}"
            elif key == "label":
                step["label"] = step.get("id", "Unnamed")
            else:
                step[key] = default
    return step


def _repair_branches(branches: Any) -> list[dict[str, str]] | None:
    """Normalise branches to the expected shape or return None."""
    if not isinstance(branches, list):
        return None
    repaired: list[dict[str, str]] = []
    for br in branches:
        if not isinstance(br, dict):
            continue
        entry: dict[str, str] = {
            "condition": str(br.get("condition", "")),
            "target": str(br.get("target") or br.get("target_ref", "")),
        }
        repaired.append(entry)
    return repaired if repaired else None


def repair_bpmn_json(raw: dict[str, Any]) -> dict[str, Any]:
    """Apply best-effort repairs to raw LLM JSON."""
    if not isinstance(raw, dict):
        return raw

    # Accept "process" as alias for "steps"
    if "process" in raw and "steps" not in raw:
        raw["steps"] = raw.pop("process")

    steps = raw.get("steps")
    if not isinstance(steps, list):
        return raw

    for step in steps:
        if not isinstance(step, dict):
            continue
        _ensure_step_keys(step)
        step["branches"] = _repair_branches(step.get("branches"))

    # Ensure lanes is present
    if "lanes" not in raw:
        raw["lanes"] = None

    # Strip unknown top-level keys
    allowed = {"steps", "lanes"}
    for key in list(raw.keys()):
        if key not in allowed:
            del raw[key]

    return raw
