"""Mantine Splitter components wrapper for Reflex.

Wraps the ``@mantine/core`` Splitter (added in Mantine 9.3) — a declarative,
resizable split-pane layout built on the ``use-splitter`` hook.

Docs: https://mantine.dev/core/splitter/
"""

from __future__ import annotations

from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MantineLayoutComponentBase


class Splitter(MantineLayoutComponentBase):
    """Mantine Splitter — resizable split-pane container.

    https://mantine.dev/core/splitter/
    """

    tag = "Splitter"

    orientation: Var[Literal["horizontal", "vertical"]] = None
    """Panes layout direction (default ``"horizontal"``)."""

    sizes: Var[list[Any]] = None
    """Controlled sizes of the panes."""

    line_size: Var[str | int] = None
    """Thickness of the resizer line."""

    with_handle: Var[bool] = None
    """Show the grip handle on the resizer."""

    handle_color: Var[str] = None
    """Color of the resizer line."""

    handle_icon: Var[Any] = None
    """Custom grip icon rendered on the handle."""

    redistribute: Var[Literal["nearest", "equal"]] = None
    """Strategy used to reallocate space when a pane is resized."""

    reset_on_double_click: Var[bool] = None
    """Restore the default pane ratio on double-click (Mantine 9.4)."""

    on_size_change: EventHandler[lambda sizes: [sizes]] = None
    """Called with the new pane sizes while resizing."""


class SplitterPane(MantineLayoutComponentBase):
    """Mantine Splitter.Pane — a single pane inside a Splitter.

    https://mantine.dev/core/splitter/
    """

    tag = "Splitter.Pane"

    default_size: Var[str | int] = None
    """Initial pane size — number (flex) or CSS unit string (px/rem/%)."""

    min: Var[str | int] = None
    """Minimum pane size — number or CSS unit string (Mantine 9.4)."""

    max: Var[str | int] = None
    """Maximum pane size — number or CSS unit string (Mantine 9.4)."""

    collapsible: Var[bool] = None
    """Allow the pane to collapse below its minimum size."""


class SplitterNamespace(rx.ComponentNamespace):
    """Namespace exposing ``splitter`` and ``splitter.pane``."""

    __call__ = staticmethod(Splitter.create)
    pane = staticmethod(SplitterPane.create)


splitter = SplitterNamespace()
