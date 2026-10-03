"""Tests for ImageGeneratorValidationState.initialize.

The edit button passes a row of ``ImageGeneratorAdminState.generators`` to
``initialize``; the frontend sends it as a plain dict, so the handler's type
hint must be one Reflex coerces (pydantic), not the SQLAlchemy entity.
"""

from types import SimpleNamespace
from typing import get_type_hints

from reflex_base.event.processor.base_state_processor import (
    _transform_event_payload,
)

from appkit_imagecreator.backend.models import ImageGeneratorConfigModel
from appkit_imagecreator.components.image_generator_dialogs import (
    ImageGeneratorValidationState,
)

_INITIALIZE = ImageGeneratorValidationState.__dict__["initialize"].fn


def _run_initialize(payload: dict) -> SimpleNamespace:
    stub = SimpleNamespace()
    args = _transform_event_payload(payload, get_type_hints(_INITIALIZE))
    _INITIALIZE(stub, **args)
    return stub


def test_initialize_accepts_serialized_row() -> None:
    row = ImageGeneratorConfigModel(
        id=3,
        model_id="dall-e-3",
        model="dall-e-3",
        label="DALL-E 3",
        processor_type="openai",
        api_key="k",
        extra_config={"size": "1024x1024"},
        required_role="admin",
    ).model_dump(mode="json")

    state = _run_initialize({"generator": row})

    assert state.model_id == "dall-e-3"
    assert state.label == "DALL-E 3"
    assert state.processor_type == "openai"
    assert state.required_role == "admin"
    assert '"size": "1024x1024"' in state.extra_config
    assert state.model_id_error == ""


def test_initialize_none_resets_fields() -> None:
    state = _run_initialize({"generator": None})

    assert state.model_id == ""
    assert state.extra_config == ""
    assert state.required_role == ""
