"""Tests for AIModelValidationState.initialize.

The edit button passes a row of ``AIModelAdminState.models`` to
``initialize``; the frontend sends it as a plain dict, so the handler's type
hint must be one Reflex coerces (pydantic), not the SQLAlchemy entity.
"""

from types import SimpleNamespace
from typing import get_type_hints

from reflex_base.event.processor.base_state_processor import (
    _transform_event_payload,
)

from appkit_assistant.backend.schemas import AssistantAIModelConfigModel
from appkit_assistant.components.ai_model_dialogs import AIModelValidationState

_INITIALIZE = AIModelValidationState.__dict__["initialize"].fn


def _run_initialize(payload: dict) -> SimpleNamespace:
    stub = SimpleNamespace()
    args = _transform_event_payload(payload, get_type_hints(_INITIALIZE))
    _INITIALIZE(stub, **args)
    return stub


def test_initialize_accepts_serialized_row() -> None:
    row = AssistantAIModelConfigModel(
        id=7,
        model_id="gpt-5",
        text="GPT-5",
        processor_type="openai",
        temperature=0.3,
        supports_tools=True,
        requires_role="admin",
        on_azure=True,
    ).model_dump(mode="json")

    state = _run_initialize({"record": row})

    assert state.model_id == "gpt-5"
    assert state.text == "GPT-5"
    assert state.temperature == "0.3"
    assert state.supports_tools is True
    assert state.requires_role == "admin"
    assert state.on_azure is True


def test_initialize_none_resets_fields() -> None:
    state = _run_initialize({"record": None})

    assert state.model_id == ""
    assert state.temperature == "0.05"
    assert state.on_azure is False
