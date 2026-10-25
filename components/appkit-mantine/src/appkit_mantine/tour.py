"""Mantine Tour component (Mantine 9.7)."""

from typing import Any, Literal

import reflex as rx
from reflex.vars.base import Var

from appkit_mantine.base import MantineComponentBase, MantineLayoutComponentBase


class TourStep(MantineComponentBase):
    """Mantine Tour.Step — one step; must be a direct child of ``Tour``."""

    tag = "Tour.Step"

    target: Var[str] = None
    """CSS selector of the target element; omit for a centered step."""

    title: Var[Any] = None
    position: Var[str] = None
    spotlight_padding: Var[int] = None
    spotlight_radius: Var[int] = None
    with_beacon: Var[bool] = None
    with_overlay: Var[bool] = None

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_step_open": rx.event.no_args_event_spec,
            "on_step_close": rx.event.no_args_event_spec,
        }


class Tour(MantineLayoutComponentBase):
    """Mantine Tour — step-by-step onboarding with a spotlight overlay.

    https://mantine.dev/core/tour/
    """

    tag = "Tour"

    active: Var[bool] = None
    """Whether the tour is running."""

    step: Var[int] = None
    """Current step index (controlled)."""

    default_step: Var[int] = None
    """Initial step index; use ``-1`` in beacon mode."""

    mode: Var[Literal["guided", "beacon"]] = None
    close_on_escape: Var[bool] = None
    close_on_overlay_click: Var[bool] = None
    color: Var[str] = None
    labels: Var[dict] = None
    max_width: Var[int] = None
    overlay_color: Var[str] = None
    spotlight_padding: Var[int] = None
    spotlight_radius: Var[int] = None
    step_transition_duration: Var[int] = None
    tooltip_shadow: Var[str] = None
    with_close_button: Var[bool] = None
    with_keyboard_navigation: Var[bool] = None
    with_overlay: Var[bool] = None
    with_overlay_interaction: Var[bool] = None
    with_scroll_into_view: Var[bool] = None
    within_portal: Var[bool] = None
    z_index: Var[int | str] = None

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_close": rx.event.no_args_event_spec,
            "on_step_change": lambda step: [step],
            "on_step_open": lambda step: [step],
            "on_step_close": lambda step: [step],
        }


class TourNamespace(rx.ComponentNamespace):
    """Namespace for Tour components."""

    __call__ = staticmethod(Tour.create)
    step = staticmethod(TourStep.create)


tour = TourNamespace()
