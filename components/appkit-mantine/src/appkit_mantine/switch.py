from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MantineComponentBase


class Switch(MantineComponentBase):
    """Mantine Switch component.

    Documentation: https://mantine.dev/core/switch/
    """

    tag = "Switch"

    checked: Var[bool] = None
    default_checked: Var[bool] = None
    label: Var[str] = None
    description: Var[str] = None
    error: Var[str] = None
    disabled: Var[bool] = None

    label_position: Var[Literal["left", "right"]] = None
    """Position of the label relative to the switch."""

    size: Var[Literal["xs", "sm", "md", "lg", "xl"]] = None
    radius: Var[Literal["xs", "sm", "md", "lg", "xl"]] = None
    color: Var[str] = None

    on_label: Var[str] = None
    off_label: Var[str] = None

    thumb_icon: Var[rx.Component] = None

    on_change: EventHandler[lambda e0: [e0.target.checked]] = None

    def get_event_triggers(self) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_change": lambda e0: [e0.target.checked],
        }


switch = Switch.create
