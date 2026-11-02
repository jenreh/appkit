"""Mantine Toggle and Toolbar components (Mantine 9.7)."""

from typing import Any, Literal

import reflex as rx
from reflex.vars.base import Var

from appkit_mantine.base import (
    MantineComponentBase,
    MantineLayoutComponentBase,
    MantineNumberSize,
    MantineSize,
)


class Toggle(MantineLayoutComponentBase):
    """Mantine Toggle — button switching between active and inactive states.

    https://mantine.dev/core/toggle/
    """

    tag = "Toggle"

    active: Var[bool] = None
    """Controlled active state."""

    default_active: Var[bool] = None
    """Initial active state (uncontrolled)."""

    auto_contrast: Var[bool] = None
    """Adjusts icon color on ``filled`` variant based on ``color``."""

    auto_width: Var[bool] = None
    """Width fits the content instead of staying square."""

    color: Var[str] = None
    disabled: Var[bool] = None
    radius: Var[MantineNumberSize] = None
    size: Var[MantineSize] = None
    variant: Var[str] = None

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_active_change": lambda active: [active],
        }


class ToolbarToggle(MantineComponentBase):
    """Mantine Toolbar.Toggle — stateless toggle, pass ``active``."""

    tag = "Toolbar.Toggle"

    active: Var[bool] = None
    auto_width: Var[bool] = None
    disabled: Var[bool] = None


class ToolbarToggleGroup(MantineComponentBase):
    """Mantine Toolbar.ToggleGroup — manages selection of its items."""

    tag = "Toolbar.ToggleGroup"

    type: Var[Literal["single", "multiple"]] = None
    """Selection mode (required)."""

    value: Var[str | list[str] | None] = None
    default_value: Var[str | list[str] | None] = None
    disabled: Var[bool] = None

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_change": lambda value: [value],
        }


class ToolbarToggleItem(MantineComponentBase):
    """Mantine Toolbar.ToggleItem — toggle reading state from its group."""

    tag = "Toolbar.ToggleItem"

    value: Var[str] = None
    auto_width: Var[bool] = None
    disabled: Var[bool] = None


class ToolbarGroup(MantineComponentBase):
    """Mantine Toolbar.Group."""

    tag = "Toolbar.Group"


class ToolbarDivider(MantineComponentBase):
    """Mantine Toolbar.Divider."""

    tag = "Toolbar.Divider"


class Toolbar(MantineLayoutComponentBase):
    """Mantine Toolbar — accessible toolbar with roving tabindex navigation.

    https://mantine.dev/core/toolbar/
    """

    tag = "Toolbar"

    auto_contrast: Var[bool] = None
    color: Var[str] = None
    loop: Var[bool] = None
    """Arrow navigation wraps from last to first item (default ``True``)."""

    orientation: Var[Literal["horizontal", "vertical"]] = None
    radius: Var[MantineNumberSize] = None
    size: Var[MantineSize] = None
    variant: Var[str] = None
    with_border: Var[bool] = None


class ToolbarNamespace(rx.ComponentNamespace):
    """Namespace for Toolbar components."""

    __call__ = staticmethod(Toolbar.create)
    toggle = staticmethod(ToolbarToggle.create)
    toggle_group = staticmethod(ToolbarToggleGroup.create)
    toggle_item = staticmethod(ToolbarToggleItem.create)
    group = staticmethod(ToolbarGroup.create)
    divider = staticmethod(ToolbarDivider.create)


toggle = Toggle.create
toolbar = ToolbarNamespace()
