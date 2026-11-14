"""Examples demonstrating Mantine ScrollArea usage in Reflex.

This page shows ScrollArea and ScrollArea.Autosize components with different
configurations: scrollbar types, scroll position tracking, programmatic scrolling,
and overflow detection.
"""

from __future__ import annotations

from typing import Any

import reflex as rx

import appkit_mantine as mn

from app.components.navbar import app_navbar
from app.components.templates import navbar_layout

SCROLL_VIEWPORT_ID = "custom-scroll-viewport"


class ScrollAreaState(rx.State):
    scroll_position: dict = {"x": 0, "y": 0}
    overflow_state: bool = False
    # track whether viewport is at top / bottom to disable buttons
    at_top: bool = True
    at_bottom: bool = False

    # Scroll metrics for buffer-based detection
    scroll_y: float = 0
    scroll_height: float = 0
    client_height: float = 0

    def is_at_bottom(self, buffer: float = 0) -> bool:
        """Check if scroll position is within buffer distance of bottom."""
        if self.scroll_height == 0 or self.client_height == 0:
            return False
        max_scroll = self.scroll_height - self.client_height
        return self.scroll_y >= (max_scroll - buffer)

    def is_at_top(self, buffer: float = 0) -> bool:
        """Check if scroll position is within buffer distance of top."""
        return self.scroll_y <= buffer

    @rx.event
    def update_scroll_metrics(self, data: dict) -> None:
        """Update scroll metrics for buffer-based position detection."""
        self.scroll_y = data.get("scrollY", 0)
        self.scroll_height = data.get("scrollHeight", 0)
        self.client_height = data.get("clientHeight", 0)

    @rx.event
    def update_scroll_position(self, position: dict) -> None:
        # position is expected as {'x': number, 'y': number}
        self.scroll_position = position
        y = position.get("y", 0)
        # at top when y == 0
        self.at_top = y == 0
        # clear at_bottom when user scrolls (onBottomReached will set it)
        if y != 0:
            self.at_bottom = False

    @rx.event
    def update_overflow(self, overflow: bool) -> None:
        self.overflow_state = overflow

    @rx.event
    def scroll_to_bottom(self) -> Any:
        return rx.call_script(
            f"""
            const viewport = document.getElementById('{SCROLL_VIEWPORT_ID}');
            if (viewport) {{
                viewport.scrollTo({{
                    top: viewport.scrollHeight,
                    behavior: 'smooth'
                }});
            }}
            """
        )

    @rx.event
    def scroll_to_top(self) -> Any:
        return rx.call_script(
            f"""
            const viewport = document.getElementById('{SCROLL_VIEWPORT_ID}');
            if (viewport) {{
                viewport.scrollTo({{
                    top: 0,
                    behavior: 'smooth'
                }});
            }}
            """
        )

    @rx.event
    def set_at_top(self) -> None:
        """Called when ScrollArea reports top reached."""
        self.at_top = True
        self.at_bottom = False

    @rx.event
    def set_at_bottom(self) -> None:
        """Called when ScrollArea reports bottom reached."""
        self.at_bottom = True
        self.at_top = False


@navbar_layout(
    route="/examples/scroll-area",
    title="Rich Select Examples",
    navbar=app_navbar(),
    with_header=False,
)
def scroll_area_examples() -> rx.Component:
    # Sample content for scrolling
    lorem_content = rx.vstack(
        rx.text(
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod "
            "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim "
            "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea "
            "commodo consequat."
        ),
        rx.text(
            "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum "
            "dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non "
            "proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
        ),
        rx.text(
            "Sed ut perspiciatis unde omnis iste natus error sit voluptatem "
            "accusantium ",
            "doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo "
            "inventore veritatis et quasi architecto beatae vitae dicta\
                sunt explicabo.",
        ),
        rx.text(
            "Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit "
            "aut fugit, ",
            "sed quia consequuntur magni dolores eos qui ratione "
            "voluptatem sequi nesciunt.",
        ),
        rx.text(
            "Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, "
            "consectetur, adipisci velit, sed quia non numquam eius modi tempora "
            "incidunt ut labore et dolore magnam aliquam quaerat voluptatem."
        ),
        spacing="4",
        width="100%",
    )

    return rx.container(
        rx.color_mode.button(position="top-right"),
        rx.vstack(
            rx.heading("ScrollArea Examples", size="8"),
            rx.text(
                "Demonstration of ScrollArea and ScrollArea.Autosize components",
                size="3",
                color="gray",
            ),
            rx.link("← Back to Home", href="/", size="3"),
            rx.grid(
                # ScrollArea with position tracking
                rx.card(
                    rx.vstack(
                        rx.heading("Scroll Position Tracking", size="4"),
                        mn.scroll_area(
                            rx.box(
                                lorem_content,
                                width="600px",  # Content wider than container
                            ),
                            height="150px",
                            width="100%",
                            type="hover",
                            on_scroll_position_change=ScrollAreaState.update_scroll_position,
                        ),
                        rx.text(
                            f"Position: x={ScrollAreaState.scroll_position['x']}, "
                            f"y={ScrollAreaState.scroll_position['y']}",
                            size="2",
                            font_family="mono",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    padding="4",
                    border_radius="md",
                ),
                # ScrollArea with vertical only scrollbars
                rx.card(
                    rx.vstack(
                        rx.heading("Vertical Only Scrollbars with State", size="4"),
                        mn.scroll_area.stateful(
                            rx.box(
                                lorem_content,
                                width="600px",  # Content wider than container
                            ),
                            height="150px",
                            width="100%",
                            scrollbars="y",
                            type="always",
                            show_controls=False,
                        ),
                        rx.text(
                            "Only vertical scrollbar visible", size="2", color="gray"
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    padding="4",
                    border_radius="md",
                ),
                # ScrollArea.Autosize
                rx.card(
                    rx.vstack(
                        rx.heading("ScrollArea.Autosize", size="4"),
                        mn.scroll_area.autosize(
                            rx.text(
                                "Sed ut perspiciatis unde omnis iste natus error sit"
                                " voluptatem accusantium ",
                                (
                                    "doloremque laudantium, totam rem aperiam,"
                                    " eaque ipsa quae ab illo inventore veritatis"
                                    " et quasi architecto beatae vitae dicta sunt"
                                    " explicabo."
                                ),
                            ),
                            max_height="150px",
                            max_width="100%",
                            type="always",
                            on_overflow_change=ScrollAreaState.update_overflow,
                        ),
                        rx.text(
                            f"Overflow: {ScrollAreaState.overflow_state}",
                            size="2",
                            font_family="mono",
                        ),
                        rx.text(
                            "Scrollbars appear only when needed", size="2", color="gray"
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    padding="4",
                    border_radius="md",
                ),
                # ScrollArea with vertical scrollbar pinned to the left
                rx.card(
                    rx.vstack(
                        rx.heading("Left Scrollbar Position", size="4"),
                        mn.scroll_area(
                            lorem_content,
                            height="150px",
                            width="100%",
                            type="always",
                            scrollbars="y",
                            vertical_scrollbar_position="left",
                        ),
                        rx.text(
                            "Vertical scrollbar pinned to the left side",
                            size="2",
                            color="gray",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    padding="4",
                    border_radius="md",
                ),
                # ScrollArea with custom scrollbar size
                rx.card(
                    rx.vstack(
                        rx.heading("Custom Scrollbar Size", size="4"),
                        mn.scroll_area(
                            lorem_content,
                            height="150px",
                            width="100%",
                            type="always",
                            scrollbar_size=20,
                        ),
                        rx.text("Thicker scrollbars (20px)", size="2", color="gray"),
                        spacing="3",
                        width="100%",
                    ),
                    padding="4",
                    border_radius="md",
                ),
                # ScrollArea with bottom control only
                rx.card(
                    rx.vstack(
                        rx.heading("Bottom Control Only", size="4"),
                        mn.scroll_area.stateful(
                            lorem_content,
                            height="150px",
                            type="hover",
                            offset_scrollbars=False,
                            controls="bottom",
                            controls_position="top",
                            bottom_button_text="↓ Bottom",
                        ),
                        rx.text(
                            "Only scroll-to-bottom button is shown",
                            size="2",
                            color="gray",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    padding="4",
                    border_radius="md",
                ),
                # ScrollArea with both controls right
                rx.card(
                    rx.vstack(
                        rx.heading("Both Controls (Default)", size="4"),
                        mn.scroll_area.stateful(
                            lorem_content,
                            height="150px",
                            controls="top-bottom",
                            type="hover",
                            offset_scrollbars=False,
                            controls_position="bottom",
                            top_button_text="↑",
                            bottom_button_text="↓",
                            button_align="right",
                            button_props={"style": {"background": "#ff9090"}},
                        ),
                        rx.text(
                            "Both scroll buttons are shown (default behavior)",
                            size="2",
                            color="gray",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    padding="4",
                    border_radius="md",
                ),
                columns="2",
                spacing="4",
                width="100%",
            ),
            spacing="6",
            width="100%",
            max_width="1200px",
            margin="0 auto",
            padding="6",
        ),
        spacint="3",
        width="100%",
    )
