"""Mantine ActionBar component (Mantine 9.6)."""

from typing import Any

import reflex as rx
from reflex.vars.base import Var

from appkit_mantine.base import MantineComponentBase, MantineLayoutComponentBase


class ActionBarDivider(MantineComponentBase):
    """Mantine ActionBar.Divider — vertical separator between actions."""

    tag = "ActionBar.Divider"


class ActionBarCloseButton(MantineComponentBase):
    """Mantine ActionBar.CloseButton — calls the parent ``on_close``."""

    tag = "ActionBar.CloseButton"

    aria_label: Var[str] = None
    icon: Var[Any] = None
    icon_size: Var[str | int] = None
    size: Var[str | int] = None
    variant: Var[str] = None


class ActionBar(MantineLayoutComponentBase):
    """Mantine ActionBar — fixed bottom bar for bulk selection actions.

    https://mantine.dev/core/action-bar/
    """

    tag = "ActionBar"

    opened: Var[bool] = None
    """Whether the bar is visible (required)."""

    close_on_escape: Var[bool] = None
    keep_mounted: Var[bool] = None
    aria_label: Var[str] = None
    position: Var[dict] = None
    """Affix position, e.g. ``{"bottom": 20, "left": 20}``."""

    radius: Var[str | int] = None
    shadow: Var[str] = None
    with_border: Var[bool] = None
    within_portal: Var[bool] = None
    portal_props: Var[dict] = None
    transition_props: Var[dict] = None
    z_index: Var[int | str] = None

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_close": rx.event.no_args_event_spec,
        }


class ActionBarNamespace(rx.ComponentNamespace):
    """Namespace for ActionBar components."""

    __call__ = staticmethod(ActionBar.create)
    divider = staticmethod(ActionBarDivider.create)
    close_button = staticmethod(ActionBarCloseButton.create)


action_bar = ActionBarNamespace()
