"""Mantine Carousel extension components."""

from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MANTINE_VERSION, MantineLayoutComponentBase

CAROUSEL_LIBRARY = f"@mantine/carousel@{MANTINE_VERSION}"
EMBLA_LIBRARY = "embla-carousel-react@^8.3.0"


class MantineCarouselBase(MantineLayoutComponentBase):
    """Base class for Carousel components."""

    library = CAROUSEL_LIBRARY
    lib_dependencies: list[str] = [EMBLA_LIBRARY]

    def _get_custom_code(self) -> str:
        return """import '@mantine/core/styles.css';
import '@mantine/carousel/styles.css';"""


class CarouselRoot(MantineCarouselBase):
    """Mantine Carousel — slide show with navigation controls.

    https://mantine.dev/x/carousel/
    """

    tag = "Carousel"

    _rename_props = {
        "control_size": "controlSize",
        "controls_offset": "controlsOffset",
        "embla_options": "emblaOptions",
        "get_embla_api": "getEmblaApi",
        "get_indicator_props": "getIndicatorProps",
        "include_gap_in_size": "includeGapInSize",
        "initial_slide": "initialSlide",
        "next_control_icon": "nextControlIcon",
        "next_control_props": "nextControlProps",
        "on_next_slide": "onNextSlide",
        "on_previous_slide": "onPreviousSlide",
        "on_slide_change": "onSlideChange",
        "previous_control_icon": "previousControlIcon",
        "previous_control_props": "previousControlProps",
        "slide_gap": "slideGap",
        "slide_size": "slideSize",
        "with_controls": "withControls",
        "with_indicators": "withIndicators",
        "with_keyboard_events": "withKeyboardEvents",
    }

    height: Var[str | int] = None
    initial_slide: Var[int] = None
    orientation: Var[Literal["horizontal", "vertical"]] = None
    slide_size: Var[str | int] = None
    slide_gap: Var[str | int] = None
    with_controls: Var[bool] = None
    with_indicators: Var[bool] = None
    with_keyboard_events: Var[bool] = None
    control_size: Var[str | int] = None
    controls_offset: Var[str | int] = None
    include_gap_in_size: Var[bool] = None
    embla_options: Var[dict] = None
    next_control_icon: Var[Any] = None
    previous_control_icon: Var[Any] = None

    on_slide_change: EventHandler[lambda index: [index]] = None
    on_next_slide: EventHandler[rx.event.no_args_event_spec] = None
    on_previous_slide: EventHandler[rx.event.no_args_event_spec] = None


class CarouselSlide(MantineCarouselBase):
    """Mantine Carousel.Slide — individual slide wrapper."""

    tag = "Carousel.Slide"


class CarouselNamespace(rx.ComponentNamespace):
    """Namespace for Carousel components."""

    __call__ = staticmethod(CarouselRoot.create)
    slide = staticmethod(CarouselSlide.create)


carousel = CarouselNamespace()
