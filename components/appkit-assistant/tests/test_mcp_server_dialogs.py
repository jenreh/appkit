"""Tests for the MCP server dialog ValidationState.initialize.

The edit button passes a row of ``MCPServerState.servers`` to ``initialize``;
the frontend sends it as a plain dict, so the handler's type hint must be one
Reflex coerces (pydantic), not the SQLAlchemy entity.
"""

from types import MethodType, SimpleNamespace
from typing import get_type_hints

from reflex_base.event.processor.base_state_processor import (
    _transform_event_payload,
)

from appkit_assistant.backend.schemas import MCPServerConfigModel
from appkit_assistant.components.mcp_server_dialogs import (
    AUTH_TYPE_API_KEY,
    AUTH_TYPE_OAUTH,
    ValidationState,
)

_INITIALIZE = ValidationState.__dict__["initialize"].fn


def _run_initialize(payload: dict) -> SimpleNamespace:
    stub = SimpleNamespace()
    for name in ("_reset_errors", "_reset_fields", "_load_server_data"):
        setattr(stub, name, MethodType(ValidationState.__dict__[name], stub))
    args = _transform_event_payload(payload, get_type_hints(_INITIALIZE))
    _INITIALIZE(stub, **args)
    return stub


def test_initialize_accepts_serialized_row() -> None:
    row = MCPServerConfigModel(
        id=2,
        name="Docs",
        description="Docs server",
        url="https://mcp.example.com",
        oauth_client_id="cid",
        oauth_scopes="read",
        required_role="admin",
        inject_user_id=False,
    ).model_dump(mode="json")

    state = _run_initialize({"server": row})

    assert state.name == "Docs"
    assert state.url == "https://mcp.example.com"
    assert state.auth_type == AUTH_TYPE_OAUTH
    assert state.oauth_client_id == "cid"
    assert state.oauth_scopes == "read"
    assert state.required_role == "admin"
    assert state.inject_user_id is False


def test_initialize_none_resets_fields() -> None:
    state = _run_initialize({"server": None})

    assert state.name == ""
    assert state.auth_type == AUTH_TYPE_API_KEY
    assert state.url_error == ""
