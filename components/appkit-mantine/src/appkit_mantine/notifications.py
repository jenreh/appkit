"""Mantine Notifications (``@mantine/notifications``).

Mount ``mn.notifications_provider()`` once per page or layout, then trigger
notifications from event handlers with the imperative helpers on
``mn.notifications`` (``show``, ``update``, ``hide``, ``clean``,
``clean_queue``, ``promise``). Each helper returns an event spec that runs
``notifications.*`` in the browser, so return it from a handler::

    @rx.event
    def save(self):
        return mn.notifications.show(
            message="Saved", title="Done", color="teal", with_auto_close_progress=True
        )

https://mantine.dev/x/notifications/
"""

from __future__ import annotations

import json
from typing import Any, Literal

import reflex as rx
from reflex.event import EventSpec
from reflex.vars.base import Var

from appkit_mantine.base import MANTINE_VERSION, MantineLayoutComponentBase

NOTIFICATIONS_LIBRARY = f"@mantine/notifications@{MANTINE_VERSION}"

NotificationPosition = Literal[
    "top-left",
    "top-right",
    "top-center",
    "bottom-left",
    "bottom-right",
    "bottom-center",
]

_GLOBAL = "window.mantineNotifications"


def _camel(name: str) -> str:
    head, *tail = name.split("_")
    return head + "".join(part.title() for part in tail)


def _payload(**data: Any) -> str:
    """Serialize keyword arguments to a JS object literal with camelCase keys."""
    return json.dumps({_camel(k): v for k, v in data.items() if v is not None})


def _call(expression: str) -> EventSpec:
    return rx.call_script(f"{_GLOBAL}.{expression}")


class Notifications(MantineLayoutComponentBase):
    """Mantine Notifications — container rendering the notification stack."""

    library = NOTIFICATIONS_LIBRARY
    tag = "Notifications"

    position: Var[NotificationPosition] = None
    auto_close: Var[int | bool] = None
    """Auto close timeout in ms, ``False`` disables auto close."""

    transition_duration: Var[int] = None
    allow_drag_dismiss: Var[bool] = None
    allow_scroll_dismiss: Var[bool] = None
    container_width: Var[int | str] = None
    notification_max_height: Var[int | str] = None
    limit: Var[int] = None
    z_index: Var[int | str] = None
    within_portal: Var[bool] = None
    pause_reset_on_hover: Var[Literal["all", "notification"]] = None
    layout: Var[Literal["default", "stacked"]] = None
    with_auto_close_progress: Var[bool] = None
    """Shows a progress line until the notification closes (Mantine 9.7)."""

    render_notification: Var[Any] = None
    """JS function ``(notification) => ReactNode`` replacing the default
    notification body for every notification; animations and drag dismiss
    are kept (Mantine 9.6). Pass a ``rx.Var`` holding a JS arrow function."""

    def _get_custom_code(self) -> str:
        return (
            "import '@mantine/core/styles.css';\n"
            "import '@mantine/notifications/styles.css';\n"
            "import { notifications } from '@mantine/notifications';\n"
            "if (typeof window !== 'undefined') {\n"
            "  window.mantineNotifications = notifications;\n"
            "}"
        )


class NotificationsApi:
    """Imperative ``notifications.*`` API returning Reflex event specs."""

    @staticmethod
    def show(
        message: str,
        *,
        id: str | None = None,  # noqa: A002
        title: str | None = None,
        color: str | None = None,
        position: NotificationPosition | None = None,
        auto_close: int | bool | None = None,
        with_auto_close_progress: bool | None = None,
        with_close_button: bool | None = None,
        with_border: bool | None = None,
        loading: bool | None = None,
        allow_close: bool | None = None,
        priority: int | None = None,
        radius: str | int | None = None,
    ) -> EventSpec:
        """Show a notification (``notifications.show``)."""
        return _call(
            "show("
            + _payload(
                message=message,
                id=id,
                title=title,
                color=color,
                position=position,
                auto_close=auto_close,
                with_auto_close_progress=with_auto_close_progress,
                with_close_button=with_close_button,
                with_border=with_border,
                loading=loading,
                allow_close=allow_close,
                priority=priority,
                radius=radius,
            )
            + ")"
        )

    @staticmethod
    def update(
        id: str,  # noqa: A002
        *,
        message: str | None = None,
        title: str | None = None,
        color: str | None = None,
        auto_close: int | bool | None = None,
        with_auto_close_progress: bool | None = None,
        with_close_button: bool | None = None,
        with_border: bool | None = None,
        loading: bool | None = None,
        allow_close: bool | None = None,
    ) -> EventSpec:
        """Update an open notification by id (``notifications.update``)."""
        return _call(
            "update("
            + _payload(
                id=id,
                message=message if message is not None else "",
                title=title,
                color=color,
                auto_close=auto_close,
                with_auto_close_progress=with_auto_close_progress,
                with_close_button=with_close_button,
                with_border=with_border,
                loading=loading,
                allow_close=allow_close,
            )
            + ")"
        )

    @staticmethod
    def hide(id: str) -> EventSpec:  # noqa: A002
        """Hide a notification by id (``notifications.hide``)."""
        return _call(f"hide({json.dumps(id)})")

    @staticmethod
    def clean() -> EventSpec:
        """Remove all notifications and the queue (``notifications.clean``)."""
        return _call("clean()")

    @staticmethod
    def clean_queue() -> EventSpec:
        """Remove queued notifications only (``notifications.cleanQueue``)."""
        return _call("cleanQueue()")

    @staticmethod
    def promise(
        promise_js: str,
        *,
        loading: dict[str, Any],
        success: dict[str, Any],
        error: dict[str, Any],
        id: str | None = None,  # noqa: A002
    ) -> EventSpec:
        """Track a browser-side promise (``notifications.promise``).

        Shows ``loading`` while the promise is pending, then ``success`` or
        ``error``. ``promise_js`` is a JavaScript expression evaluating to a
        promise, e.g. ``"fetch('/api/ping')"``. State dicts take camelCase
        Mantine keys (``title``, ``message``, ``color``, ...).
        """
        options = json.dumps(
            {"id": id, "loading": loading, "success": success, "error": error}
        )
        return _call(f"promise(({promise_js}), {options})")


notifications_provider = Notifications.create
notifications = NotificationsApi()
