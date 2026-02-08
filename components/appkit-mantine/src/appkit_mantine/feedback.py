"""Mantine feedback components."""

from typing import Any

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


class ProgressNamespace(rx.ComponentNamespace):
    """Namespace for Progress components."""

    root = staticmethod(ProgressRoot.create)
    section = staticmethod(ProgressSection.create)
    label = staticmethod(ProgressLabel.create)

    __call__ = staticmethod(Progress.create)


alert = Alert.create
notification = Notification.create
progress = ProgressNamespace()
skeleton = Skeleton.create
