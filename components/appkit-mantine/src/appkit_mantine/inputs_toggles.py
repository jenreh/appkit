from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import (
    MantineComponentBase,
    MantineInputComponentBase,
    MantineNumberSize,
    MantineSize,
)


class MantineToggleComponentBase(MantineComponentBase):
    """Base class for toggle-like components (Checkbox, Radio, Switch)."""

    checked: Var[bool] = None
    """Checked state (controlled)."""

    default_checked: Var[bool] = None
    """Default checked state (uncontrolled)."""

    label: Var[str] = None
    """Label shown next to the component."""

    description: Var[str] = None
    """Description shown below the label."""

    error: Var[str | bool] = None
    """Error state or message."""

    disabled: Var[bool] = None
    """Disabled state."""

    color: Var[str] = None
    """Key of theme.colors or any valid CSS color."""

    size: Var[MantineSize] = None
    """Size of the component."""

    label_position: Var[Literal["left", "right"]] = None
    """Position of the label relative to the component."""

    wrapper_props: Var[dict[str, Any]] = None
    """Props to pass to the root element (div)."""

    radius: Var[MantineNumberSize] = None
    """Key of theme.radius or any valid CSS value to set border-radius."""

    name: Var[str] = None
    """Name attribute of the input element."""

    value: Var[str] = None
    """Value attribute of the input element."""

    id: Var[str] = None
    """Id attribute of the input element."""

    required: Var[bool] = None
    """Required attribute of the input element."""

    on_change: EventHandler[lambda e0: [e0.target.checked]] = None

    def get_event_triggers(self) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_change": lambda e0: [e0.target.checked],
        }


class MantineIndicatorBase(MantineComponentBase):
    """Base class for toggle indicators."""

    checked: Var[bool] = None
    """Checked state."""

    disabled: Var[bool] = None
    """Disabled state."""

    radius: Var[MantineNumberSize] = None
    """Key of theme.radius or any valid CSS value to set border-radius."""

    size: Var[MantineSize] = None
    """Size of the indicator."""

    color: Var[str] = None
    """Key of theme.colors or any valid CSS color."""

    icon_color: Var[str] = None
    """Color of the check icon."""


class MantineCardBase(MantineComponentBase):
    """Base class for toggle cards."""

    checked: Var[bool] = None
    """Checked state (controlled)."""

    default_checked: Var[bool] = None
    """Default checked state (uncontrolled)."""

    disabled: Var[bool] = None
    """Disabled state."""

    value: Var[str] = None
    """Value attribute of the input element."""

    name: Var[str] = None
    """Name attribute of the input element."""

    radius: Var[MantineNumberSize] = None
    """Key of theme.radius or any valid CSS value to set border-radius."""

    with_border: Var[bool] = None
    """Determines whether the card should have a border."""


class Switch(MantineToggleComponentBase):
    """Mantine Switch component.

    Documentation: https://mantine.dev/core/switch/
    """

    tag = "Switch"

    on_label: Var[str] = None
    """Label to be shown when switch is on."""

    off_label: Var[str] = None
    """Label to be shown when switch is off."""

    thumb_icon: Var[rx.Component] = None
    """Icon inside the thumb of the switch."""


class RadioGroup(MantineInputComponentBase):
    """Mantine Radio.Group component.

    Documentation: https://mantine.dev/core/radio/
    """

    tag = "Radio.Group"

    on_change: EventHandler[lambda value: [value]] = None


class Radio(MantineToggleComponentBase):
    """Mantine Radio component.

    Documentation: https://mantine.dev/core/radio/
    """

    tag = "Radio"

    icon_color: Var[str] = None
    """Color of the check icon."""


class RadioIndicator(MantineIndicatorBase):
    """Mantine Radio.Indicator component.

    Documentation: https://mantine.dev/core/radio/#radioindicator
    """

    tag = "Radio.Indicator"


class RadioCard(MantineCardBase):
    """Mantine Radio.Card component.

    Documentation: https://mantine.dev/core/radio/#radiocard-component
    """

    tag = "Radio.Card"


class RadioNamespace(rx.ComponentNamespace):
    __call__ = staticmethod(Radio.create)
    group = staticmethod(RadioGroup.create)
    indicator = staticmethod(RadioIndicator.create)
    card = staticmethod(RadioCard.create)


class CheckboxGroup(MantineInputComponentBase):
    """Mantine Checkbox.Group component.

    Documentation: https://mantine.dev/core/checkbox/
    """

    tag = "Checkbox.Group"

    value: Var[list[str]] = None
    """Value of the checkbox group (controlled)."""

    default_value: Var[list[str]] = None
    """Default value of the checkbox group (uncontrolled)."""

    on_change: EventHandler[lambda value: [value]] = None


class Checkbox(MantineToggleComponentBase):
    """Mantine Checkbox component.

    Documentation: https://mantine.dev/core/checkbox/
    """

    tag = "Checkbox"

    indeterminate: Var[bool] = None
    """Indeterminate state."""

    icon_color: Var[str] = None
    """Color of the check icon."""

    tab_index: Var[int] = None
    """Tab index."""


class CheckboxIndicator(MantineIndicatorBase):
    """Mantine Checkbox.Indicator component.

    Documentation: https://mantine.dev/core/checkbox/#checkboxindicator
    """

    tag = "Checkbox.Indicator"

    indeterminate: Var[bool] = None
    """Indeterminate state."""


class CheckboxCard(MantineCardBase):
    """Mantine Checkbox.Card component.

    Documentation: https://mantine.dev/core/checkbox/#checkboxcard-component
    """

    tag = "Checkbox.Card"


class CheckboxNamespace(rx.ComponentNamespace):
    __call__ = staticmethod(Checkbox.create)
    group = staticmethod(CheckboxGroup.create)
    indicator = staticmethod(CheckboxIndicator.create)
    card = staticmethod(CheckboxCard.create)


checkbox = CheckboxNamespace()
radio = RadioNamespace()
switch = Switch.create
