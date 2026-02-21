from typing import Literal

from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MantineComponentBase, MantineInputComponentBase


class RadioGroup(MantineInputComponentBase):
    """Mantine Radio.Group component.

    Documentation: https://mantine.dev/core/radio/
    """

    tag = "Radio.Group"

    # Event handlers
    # Radio.Group onChange returns value string directly
    on_change: EventHandler[lambda value: [value]] = None


class Radio(MantineComponentBase):
    """Mantine Radio component.

    Documentation: https://mantine.dev/core/radio/
    """

    tag = "Radio"

    # Props
    value: Var[str] = None
    """Value of the radio button."""

    label: Var[str] = None
    """Label shown next to the radio."""

    description: Var[str] = None
    """Description shown below the label."""

    error: Var[str | bool] = None
    """Error state or message."""

    disabled: Var[bool] = None
    """Disabled state."""

    checked: Var[bool] = None
    """Checked state (controlled)."""

    default_checked: Var[bool] = None
    """Default checked state (uncontrolled)."""

    color: Var[str] = None
    """Key of theme.colors or any valid CSS color."""

    start_value: Var[str] = None
    """Value for uncontrolled component."""

    label_position: Var[Literal["left", "right"]] = None
    """Position of the label relative to the radio."""

    icon_color: Var[str] = None
    """Color of the check icon."""

    size: Var[Literal["xs", "sm", "md", "lg", "xl"]] = None
    """Size of the radio."""

    # Event handlers
    # Radio onChange returns event
    on_change: EventHandler[lambda e0: [e0.target.checked]] = None


radio = Radio.create
radio_group = RadioGroup.create
