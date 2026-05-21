"""Mantine feedback components."""

from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MantineLayoutComponentBase


class Alert(MantineLayoutComponentBase):
    """Mantine Alert component."""

    tag = "Alert"

    title: Var[str]
    color: Var[str]
    variant: Var[str]  # filled, light, outline, transparent, white, default
    radius: Var[str | int]
    with_close_button: Var[bool]
    close_button_label: Var[str]
    icon: Var[Any]

    on_close: EventHandler[list]


class Notification(MantineLayoutComponentBase):
    """Mantine Notification component."""

    tag = "Notification"

    title: Var[str]
    color: Var[str]
    radius: Var[str | int]
    icon: Var[Any]
    with_close_button: Var[bool]
    with_border: Var[bool]
    loading: Var[bool]

    on_close: EventHandler[list]


class ProgressRoot(MantineLayoutComponentBase):
    """Mantine Progress.Root component."""

    tag = "Progress.Root"

    size: Var[str | int]
    radius: Var[str | int]
    transition_duration: Var[int]
    auto_contrast: Var[bool]


class ProgressSection(MantineLayoutComponentBase):
    """Mantine Progress.Section component."""

    tag = "Progress.Section"

    value: Var[int | float]
    color: Var[str]
    striped: Var[bool]
    animated: Var[bool]


class ProgressLabel(MantineLayoutComponentBase):
    """Mantine Progress.Label component."""

    tag = "Progress.Label"


class Progress(MantineLayoutComponentBase):
    """Mantine Progress component (Simple usage)."""

    tag = "Progress"

    value: Var[int | float]
    color: Var[str]
    size: Var[str | int]
    radius: Var[str | int]
    striped: Var[bool]
    animated: Var[bool]
    transition_duration: Var[int]
    auto_contrast: Var[bool]


class Skeleton(MantineLayoutComponentBase):
    """Mantine Skeleton component."""

    tag = "Skeleton"

    visible: Var[bool]
    height: Var[str | int]
    width: Var[str | int]
    circle: Var[bool]
    radius: Var[str | int]
    animate: Var[bool]


class Loader(MantineLayoutComponentBase):
    """Mantine Loader component — animated loading indicator.

    https://mantine.dev/core/loader/
    """

    tag = "Loader"

    color: Var[str] = None
    size: Var[str | int] = None
    type: Var[Literal["bars", "dots", "oval"]] = None


class RingProgress(MantineLayoutComponentBase):
    """Mantine RingProgress component — circular progress ring.

    https://mantine.dev/core/ring-progress/
    """

    tag = "RingProgress"

    _rename_props = {
        "root_color": "rootColor",
        "round_caps": "roundCaps",
        "section_gap": "sectionGap",
        "start_angle": "startAngle",
        "transition_duration": "transitionDuration",
    }

    sections: Var[list[dict[str, Any]]] = None
    """List of sections: [{value: number, color: str, tooltip?: str}]"""

    size: Var[int] = None
    thickness: Var[int] = None
    label: Var[Any] = None
    root_color: Var[str] = None
    round_caps: Var[bool] = None
    section_gap: Var[int] = None
    start_angle: Var[int] = None
    transition_duration: Var[int] = None


class SemiCircleProgress(MantineLayoutComponentBase):
    """Mantine SemiCircleProgress component — half-circle progress indicator.

    https://mantine.dev/core/semi-circle-progress/
    """

    tag = "SemiCircleProgress"

    _rename_props = {
        "empty_segment_color": "emptySegmentColor",
        "fill_direction": "fillDirection",
        "filled_segment_color": "filledSegmentColor",
        "label_position": "labelPosition",
        "transition_duration": "transitionDuration",
    }

    value: Var[int | float] = None
    size: Var[int] = None
    thickness: Var[int] = None
    label: Var[Any] = None
    label_position: Var[Literal["center", "bottom"]] = None
    orientation: Var[Literal["up", "down"]] = None
    fill_direction: Var[Literal["right-to-left", "left-to-right"]] = None
    filled_segment_color: Var[str] = None
    empty_segment_color: Var[str] = None
    transition_duration: Var[int] = None


class ProgressNamespace(rx.ComponentNamespace):
    """Namespace for Progress components."""

    root = staticmethod(ProgressRoot.create)
    section = staticmethod(ProgressSection.create)
    label = staticmethod(ProgressLabel.create)

    __call__ = staticmethod(Progress.create)


alert = Alert.create
loader = Loader.create
notification = Notification.create
progress = ProgressNamespace()
ring_progress = RingProgress.create
semi_circle_progress = SemiCircleProgress.create
skeleton = Skeleton.create
