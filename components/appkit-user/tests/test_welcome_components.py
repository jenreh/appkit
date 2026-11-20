"""Tests for the welcome page factory and the admin approval UI pieces."""

from collections.abc import Callable
from typing import Any

import pytest
import reflex as rx
from reflex.config import get_config

from appkit_user.authentication.backend.models import User
from appkit_user.authentication.components import logout_button, welcome_pending
from appkit_user.user_management.components.user import (
    approve_user_button,
    pending_badge,
    pending_only_switch,
    users_table,
)
from appkit_user.user_management.pages import create_welcome_page
from appkit_user.user_management.states.user_states import UserState


class _RecordingLayout:
    """Page layout double that records what the factory registers."""

    def __init__(self) -> None:
        self.kwargs: dict[str, Any] = {}

    def __call__(
        self, **kwargs: Any
    ) -> Callable[[Callable[[], rx.Component]], Callable[[], rx.Component]]:
        self.kwargs = kwargs
        return lambda page: page


def _render(page: Any) -> str:
    """Build a page the factory returned (typed as a component, it is a callable)."""
    return str(page())


def test_welcome_page_defaults_to_configured_route() -> None:
    layout = _RecordingLayout()

    page = create_welcome_page(layout)

    assert layout.kwargs["route"] == "/welcome"
    assert layout.kwargs["title"] == "Willkommen"
    assert "leave_welcome_if_approved" in str(layout.kwargs["on_load"])
    rendered = _render(page)
    assert "Freigabe ausstehend" in rendered
    assert "session-monitor-trigger" in rendered


def test_welcome_page_renders_app_content() -> None:
    layout = _RecordingLayout()

    page = create_welcome_page(
        layout,
        content=lambda: rx.text("Eigene Begruessung"),
        route="/hallo",
        title="Hallo",
    )

    assert layout.kwargs["route"] == "/hallo"
    rendered = _render(page)
    assert "Eigene Begruessung" in rendered
    assert "Freigabe ausstehend" not in rendered


def test_welcome_pending_logo_honors_frontend_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_config(), "frontend_path", "/knai")

    assert "/knai/img/appkit_logo.svg" in str(welcome_pending())


def test_logout_button_triggers_logout() -> None:
    assert "logout" in str(logout_button())


def test_admin_approval_pieces_render() -> None:
    user = rx.Var.create(User(user_id=3, name="Neu", is_verified=False))

    assert "Ausstehend" in str(pending_badge(user))  # type: ignore[arg-type]
    assert "approve_user" in str(approve_user_button(user))  # type: ignore[arg-type]
    switch = str(pending_only_switch())
    assert "Nur ausstehende" in switch
    assert UserState.set_show_pending_only.fn.__name__ in switch


def test_users_table_has_pending_filter() -> None:
    assert "Nur ausstehende" in str(users_table())
