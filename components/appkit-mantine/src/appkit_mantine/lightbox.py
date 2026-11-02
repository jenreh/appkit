"""Mantine Lightbox (``@mantine/lightbox``, Mantine 9.6).

Full-screen media lightbox with carousel navigation, zoom and thumbnails.
Use it controlled (``mn.lightbox(opened=..., on_close=...)``) or mount
``mn.lightbox.provider()`` once and open it from event handlers with the
store helpers on ``mn.lightbox_api``::

    @rx.event
    def open_gallery(self):
        return mn.lightbox_api.open(self.slides, start_index=2)

Slides are dicts: ``{"src", "alt", "caption", "thumbSrc"}`` for images or
``{"type": "video", "src", "poster", "autoPlay"}`` for videos.

https://mantine.dev/x/lightbox/
"""

from __future__ import annotations

import json
from typing import Any

import reflex as rx
from reflex.event import EventSpec
from reflex.vars.base import Var

from appkit_mantine.base import MANTINE_VERSION, MantineLayoutComponentBase

LIGHTBOX_LIBRARY = f"@mantine/lightbox@{MANTINE_VERSION}"
EMBLA_CAROUSEL_LIBRARY = "embla-carousel@^8.5.2"
EMBLA_CAROUSEL_REACT_LIBRARY = "embla-carousel-react@^8.5.2"

_GLOBAL = "window.mantineLightbox"


class MantineLightboxBase(MantineLayoutComponentBase):
    """Props shared by ``Lightbox`` and ``Lightbox.Provider``."""

    library = LIGHTBOX_LIBRARY
    lib_dependencies: list[str] = [
        EMBLA_CAROUSEL_LIBRARY,
        EMBLA_CAROUSEL_REACT_LIBRARY,
    ]

    close_on_click_outside: Var[bool] = None
    close_on_swipe_down: Var[bool] = None
    embla_options: Var[dict] = None
    labels: Var[dict] = None
    """Localized strings for every toolbar button and aria label."""

    loop: Var[bool] = None
    return_focus: Var[bool] = None
    toolbar_items: Var[Any] = None
    transition_duration: Var[int] = None
    transition_props: Var[dict] = None
    with_download: Var[bool] = None
    with_fullscreen: Var[bool] = None
    with_initial_focus_placeholder: Var[bool] = None
    with_keyboard_events: Var[bool] = None
    """Arrow keys and ``F``/``T``/``Z`` shortcuts; ``Escape`` always closes."""

    with_navigation: Var[bool] = None
    with_slide_transition: Var[bool] = None
    with_thumbnails: Var[bool] = None
    with_zoom: Var[bool] = None
    within_portal: Var[bool] = None
    z_index: Var[int | str] = None
    zoom_max_scale: Var[float] = None

    def _get_custom_code(self) -> str:
        return (
            "import '@mantine/core/styles.css';\n"
            "import '@mantine/lightbox/styles.css';\n"
            "import { Lightbox as MantineLightboxStore } from '@mantine/lightbox';\n"
            "if (typeof window !== 'undefined') {\n"
            "  window.mantineLightbox = MantineLightboxStore;\n"
            "}"
        )


class Lightbox(MantineLightboxBase):
    """Mantine Lightbox — controlled full-screen media viewer."""

    tag = "Lightbox"

    opened: Var[bool] = None
    slides: Var[list[dict[str, Any]]] = None
    current_index: Var[int] = None
    """Controlled slide index; pair with ``on_index_change``."""

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_close": rx.event.no_args_event_spec,
            "on_index_change": lambda index: [index],
        }


class LightboxProvider(MantineLightboxBase):
    """Mantine Lightbox.Provider — store-driven lightbox, mount once."""

    tag = "Lightbox.Provider"


class LightboxApi:
    """Imperative store API (``Lightbox.open`` etc.) returning event specs."""

    @staticmethod
    def open(slides: list[dict[str, Any]], *, start_index: int = 0) -> EventSpec:
        """Open the provider lightbox with ``slides`` at ``start_index``."""
        payload = json.dumps({"slides": slides, "startIndex": start_index})
        return rx.call_script(f"{_GLOBAL}.open({payload})")

    @staticmethod
    def close() -> EventSpec:
        """Close the provider lightbox."""
        return rx.call_script(f"{_GLOBAL}.close()")

    @staticmethod
    def next() -> EventSpec:
        """Go to the next slide."""
        return rx.call_script(f"{_GLOBAL}.next()")

    @staticmethod
    def prev() -> EventSpec:
        """Go to the previous slide."""
        return rx.call_script(f"{_GLOBAL}.prev()")

    @staticmethod
    def set_index(index: int) -> EventSpec:
        """Jump to the slide at ``index``."""
        return rx.call_script(f"{_GLOBAL}.setIndex({int(index)})")


class LightboxNamespace(rx.ComponentNamespace):
    """Namespace for Lightbox components."""

    __call__ = staticmethod(Lightbox.create)
    provider = staticmethod(LightboxProvider.create)


lightbox = LightboxNamespace()
lightbox_api = LightboxApi()
