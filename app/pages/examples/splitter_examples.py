"""Splitter component examples (Mantine 9.4, ``@mantine/core``)."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


class SplitterExampleState(rx.State):
    """Tracks live pane sizes so the examples can show the handle position."""

    # Sizes are percentages that must sum to 100 (Mantine ``use-splitter``).
    h_sizes: list[float] = [40.0, 60.0]
    v_sizes: list[float] = [40.0, 30.0, 30.0]

    @rx.event
    def on_h_resize(self, sizes: list[float]) -> None:
        """Store the new horizontal pane sizes reported while dragging."""
        self.h_sizes = sizes

    @rx.event
    def on_v_resize(self, sizes: list[float]) -> None:
        """Store the new vertical pane sizes reported while dragging."""
        self.v_sizes = sizes

    @rx.var
    def h_labels(self) -> list[str]:
        """Per-pane percentage labels for the horizontal splitter."""
        return [f"{size:.0f}%" for size in self.h_sizes]

    @rx.var
    def v_labels(self) -> list[str]:
        """Per-pane percentage labels for the vertical splitter."""
        return [f"{size:.0f}%" for size in self.v_sizes]

    @rx.var
    def h_summary(self) -> str:
        """Combined ``40% / 60%`` caption for the horizontal splitter."""
        return " / ".join(f"{size:.0f}%" for size in self.h_sizes)

    @rx.var
    def v_summary(self) -> str:
        """Combined ``40% / 30% / 30%`` caption for the vertical splitter."""
        return " / ".join(f"{size:.0f}%" for size in self.v_sizes)


def _pane(label: str, bg: str, pct: rx.Var) -> rx.Component:
    return mn.center(
        mn.stack(
            mn.text(label, fw="bold", ta="center"),
            mn.text(pct, size="sm", c="dark.5", ta="center"),
            gap=2,
            align="center",
        ),
        h="100%",
        bg=bg,
        p="md",
    )


def _caption(summary: rx.Var) -> rx.Component:
    return mn.text(
        "Current split: ",
        mn.text(summary, span=True, fw="bold"),
        size="sm",
        c="dimmed",
        mb="xs",
    )


# Mantine theme color keys (``<color>.<shade>``) — valid string values for ``bg``.
_BLUE = "blue.1"
_TEAL = "teal.1"
_GRAPE = "grape.1"
_ORANGE = "orange.1"
_LIME = "lime.1"


@navbar_layout(
    route="/splitter",
    title="Splitter",
    navbar=app_navbar(),
    with_header=False,
)
def splitter_examples() -> rx.Component:
    """Page demonstrating the Mantine Splitter component."""
    return mn.container(
        mn.stack(
            mn.title("Splitter", order=1),
            mn.text(
                "Resizable split-pane layout (Mantine 9.4). Drag the resizer to "
                "resize panes; double-click to reset when reset_on_double_click "
                "is set. Every pane needs an explicit default_size (summing to "
                "100) or the drag math resolves to NaN and the handle won't move.",
                size="md",
                c="dimmed",
            ),
            rx.link("← Back to Home", href="/", size="3"),
            example_box(
                "Horizontal (with handle, reset on double-click)",
                mn.stack(
                    _caption(SplitterExampleState.h_summary),
                    mn.splitter(
                        mn.splitter.pane(
                            _pane("Left", _BLUE, SplitterExampleState.h_labels[0]),
                            default_size=40,
                            min=20,
                        ),
                        mn.splitter.pane(
                            _pane("Right", _TEAL, SplitterExampleState.h_labels[1]),
                            default_size=60,
                            min=20,
                        ),
                        with_handle=True,
                        reset_on_double_click=True,
                        on_size_change=SplitterExampleState.on_h_resize,
                        h="220px",
                    ),
                    gap=0,
                ),
            ),
            example_box(
                "Vertical, three collapsible panes",
                mn.stack(
                    _caption(SplitterExampleState.v_summary),
                    mn.splitter(
                        mn.splitter.pane(
                            _pane("Top", _GRAPE, SplitterExampleState.v_labels[0]),
                            default_size=40,
                            collapsible=True,
                        ),
                        mn.splitter.pane(
                            _pane("Middle", _ORANGE, SplitterExampleState.v_labels[1]),
                            default_size=30,
                            collapsible=True,
                        ),
                        mn.splitter.pane(
                            _pane("Bottom", _LIME, SplitterExampleState.v_labels[2]),
                            default_size=30,
                            collapsible=True,
                        ),
                        orientation="vertical",
                        with_handle=True,
                        on_size_change=SplitterExampleState.on_v_resize,
                        h="320px",
                    ),
                    gap=0,
                ),
            ),
            w="100%",
            mb="6rem",
            gap="sm",
        ),
        size="lg",
        w="100%",
    )
