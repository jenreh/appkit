"""Mantine-based AlertDialog component for Reflex.

Provides the same compound API as Radix UI's AlertDialog so existing
``rx.alert_dialog.*`` usages can be migrated to ``mn.alert_dialog.*``
with minimal changes while gaining full Mantine theming.

Compound components:
    Root        - context provider; holds open state
    Trigger     - wraps any child; opens dialog on click
    Content     - modal shell (overlay + content)
    Title       - sticky header with close button
    Description - scrollable body content
    Cancel      - closes dialog; default label "Abbrechen"
    Action      - fires callback then closes; default label "Löschen"
    Footer      - convenience Cancel + Action group

Example::

    import appkit_mantine as mn

    mn.alert_dialog.root(
        mn.alert_dialog.trigger(
            mn.action_icon(rx.icon("trash-2"), color="red"),
        ),
        mn.alert_dialog.content(
            mn.alert_dialog.title("Löschen bestätigen"),
            mn.alert_dialog.description(
                mn.text("Wirklich löschen?"),
            ),
            mn.alert_dialog.footer(
                on_action=State.delete_item,
            ),
        ),
    )
"""

from __future__ import annotations

import reflex as rx
from reflex.assets import asset
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MANTINE_LIBARY, MANTINE_VERSION

_WRAPPER_JS = asset(path="alert_dialog_wrapper.js", shared=True)
_WRAPPER_IMPORT = f"$/public/{_WRAPPER_JS}"

_LIB_DEPS: list[str] = [
    f"{MANTINE_LIBARY}@{MANTINE_VERSION}",
    f"@mantine/hooks@{MANTINE_VERSION}",
    "react@^19.2.0",
    "react-dom@^19.2.0",
]


class AlertDialogBase(rx.Component):
    """Shared base for all AlertDialog sub-components."""

    library = _WRAPPER_IMPORT
    lib_dependencies: list[str] = _LIB_DEPS

    def _get_custom_code(self) -> str:
        return """import '@mantine/core/styles.css';"""


# ─── Root ─────────────────────────────────────────────────────────────────────


class AlertDialogRoot(AlertDialogBase):
    """Context provider for the compound AlertDialog.

    Supports both controlled (``open`` + ``on_open_change``) and uncontrolled
    (internal state via ``default_open``) modes.
    """

    tag = "AlertDialogRoot"

    open: Var[bool] = None
    """Controlled open state."""

    default_open: Var[bool] = None
    """Initial open state when uncontrolled."""

    size: Var[str] = "sm"
    """Mantine modal size (xs, sm, md, lg, xl or CSS value)."""

    _rename_props = {
        "default_open": "defaultOpen",
        "on_open_change": "onOpenChange",
    }

    on_open_change: EventHandler[lambda value: [value]] = None
    """Fired when the open state changes."""


# ─── Trigger ──────────────────────────────────────────────────────────────────


class AlertDialogTrigger(AlertDialogBase):
    """Wraps any child element and opens the dialog when clicked.

    Uses a ``display:contents`` span so it never affects layout.
    """

    tag = "AlertDialogTrigger"


# ─── Content ──────────────────────────────────────────────────────────────────


class AlertDialogContent(AlertDialogBase):
    """Modal shell — renders ``Modal.Root``, ``Modal.Overlay``, and
    ``Modal.Content``.

    Accepts any ``Modal`` prop forwarded via ``**rest``.
    """

    tag = "AlertDialogContent"

    centered: Var[bool] = True
    """Vertically center the modal."""


# ─── Title ────────────────────────────────────────────────────────────────────


class AlertDialogTitle(AlertDialogBase):
    """Sticky header that renders ``Modal.Header`` + ``Modal.Title`` + close
    button.

    Pass plain text or components as children.
    """

    tag = "AlertDialogTitle"


# ─── Description ──────────────────────────────────────────────────────────────


class AlertDialogDescription(AlertDialogBase):
    """Body content wrapper (``Modal.Body``).

    Pass any components as children.
    """

    tag = "AlertDialogDescription"


# ─── Cancel ───────────────────────────────────────────────────────────────────


class AlertDialogCancel(AlertDialogBase):
    """Closes the dialog when clicked.

    Renders a Mantine ``Button`` with ``variant="default"`` by default.
    Override the label by passing children.
    """

    tag = "AlertDialogCancel"

    variant: Var[str] = "default"
    """Mantine button variant."""

    _rename_props = {"on_cancel": "onCancel"}

    on_cancel: EventHandler[rx.event.no_args_event_spec] = None
    """Optional extra callback fired before the dialog closes."""


# ─── Action ───────────────────────────────────────────────────────────────────


class AlertDialogAction(AlertDialogBase):
    """Fires ``on_action`` then closes the dialog.

    Renders a Mantine ``Button`` with ``color="red"`` by default.
    Override the label by passing children.
    """

    tag = "AlertDialogAction"

    color: Var[str] = "red"
    """Mantine color for the action button."""

    variant: Var[str] = "filled"
    """Mantine button variant."""

    loading: Var[bool] = None
    """Show loading spinner while the action is in progress."""

    close_on_action: Var[bool] = True
    """Close the dialog after ``on_action`` fires (default ``True``)."""

    _rename_props = {
        "on_action": "onAction",
        "close_on_action": "closeOnAction",
    }

    on_action: EventHandler[rx.event.no_args_event_spec] = None
    """Callback fired when the action button is clicked."""


# ─── Footer ───────────────────────────────────────────────────────────────────


class AlertDialogFooter(AlertDialogBase):
    """Convenience component that renders a ``Cancel`` + ``Action`` button group.

    Props:
        cancel_label    - label for the cancel button (default "Abbrechen")
        action_label    - label for the action button (default "Löschen")
        on_cancel       - extra callback on cancel
        on_action       - callback on confirm/action
        action_loading  - show spinner on action button
        cancel_props    - dict of extra props forwarded to Cancel button
        action_props    - dict of extra props forwarded to Action button
    """

    tag = "AlertDialogFooter"

    cancel_label: Var[str] = "Abbrechen"
    action_label: Var[str] = "OK"
    action_loading: Var[bool] = None
    cancel_props: Var[dict] = None
    action_props: Var[dict] = None

    _rename_props = {
        "cancel_label": "cancelLabel",
        "action_label": "actionLabel",
        "on_cancel": "onCancel",
        "on_action": "onAction",
        "action_loading": "actionLoading",
        "cancel_props": "cancelProps",
        "action_props": "actionProps",
    }

    on_cancel: EventHandler[rx.event.no_args_event_spec] = None
    on_action: EventHandler[rx.event.no_args_event_spec] = None


# ─── Namespace ────────────────────────────────────────────────────────────────


class AlertDialogNamespace(rx.ComponentNamespace):
    """Namespace for compound AlertDialog components.

    Usage::

        import appkit_mantine as mn

        mn.alert_dialog.root(
            mn.alert_dialog.trigger(mn.button("Delete")),
            mn.alert_dialog.content(
                mn.alert_dialog.title("Confirm deletion"),
                mn.alert_dialog.description(mn.text("Are you sure?")),
                mn.alert_dialog.footer(on_action=State.delete),
            ),
        )
    """

    __call__ = staticmethod(AlertDialogRoot.create)
    root = staticmethod(AlertDialogRoot.create)
    trigger = staticmethod(AlertDialogTrigger.create)
    content = staticmethod(AlertDialogContent.create)
    title = staticmethod(AlertDialogTitle.create)
    description = staticmethod(AlertDialogDescription.create)
    cancel = staticmethod(AlertDialogCancel.create)
    action = staticmethod(AlertDialogAction.create)
    footer = staticmethod(AlertDialogFooter.create)


alert_dialog = AlertDialogNamespace()
