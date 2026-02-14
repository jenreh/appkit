"""Examples demonstrating AutoScroll and AutoScrollWithControls usage.

This page shows both components with streaming/dynamic content scenarios
to demonstrate auto-scroll and manual scroll button behaviors.
"""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


class ChatStreamState(rx.State):
    """Demo state for streaming chat with auto-scroll."""

    scroll_position: dict = {"x": 0, "y": 0}
    at_top: bool = True
    at_bottom: bool = True

    messages: list[str] = [
        "User: Hello!",
        "Assistant: Hi there! How can I help?",
        "User: Tell me about Reflex.",
    ]

    @rx.event
    def add_message(self, msg: str) -> None:
        """Add a new message (simulates streaming)."""
        self.messages.append(msg)

    @rx.event
    def stream_response(self) -> None:
        """Simulate streaming response with multiple messages."""
        streaming_parts = [
            "Assistant: Reflex is a Python web framework",
            " that makes it easy to build full-stack apps.",
            " You define your UI and state in Python",
            " and it handles the rest.",
            " Pretty cool, right?",
        ]
        for part in streaming_parts:
            self.add_message(part)

    @rx.event
    def update_scroll_position(self, position: dict) -> None:
        """Update scroll tracking."""
        self.scroll_position = position
        y = position.get("y", 0)
        self.at_top = y == 0
        if y != 0:
            self.at_bottom = False


class DataStreamState(rx.State):
    """Demo state for data streaming with auto-scroll."""

    scroll_position: dict = {"x": 0, "y": 0}
    at_top: bool = True
    at_bottom: bool = True

    log_lines: list[str] = [
        "[INFO] Starting application...",
        "[INFO] Loading configuration...",
        "[DEBUG] Config loaded successfully",
    ]

    @rx.event
    def update_scroll_position(self, position: dict) -> None:
        """Update scroll tracking."""
        self.scroll_position = position
        y = position.get("y", 0)
        self.at_top = y == 0

    @rx.event
    def add_log(self, level: str, message: str) -> None:
        """Add a log line."""
        self.log_lines.append(f"[{level}] {message}")

    @rx.event
    def simulate_processing(self) -> None:
        """Simulate background processing with logs."""
        logs = [
            ("INFO", "Processing started"),
            ("DEBUG", "Initializing components"),
            ("DEBUG", "Components initialized"),
            ("INFO", "Processing complete"),
        ]
        for level, msg in logs:
            self.add_log(level, msg)


def auto_scroll_example() -> rx.Component:
    """Basic AutoScroll example - auto-scrolls to bottom."""
    return example_box(
        "AutoScroll Basic Example",
        mn.stack(
            mn.text(
                "Content automatically scrolls to bottom when new messages arrive. "
                "Try clicking 'Add Message' to see it in action.",
                size="sm",
                c="dimmed",
            ),
            mn.divider(),
            mn.scroll_area.autoscroll(
                mn.stack(
                    rx.foreach(
                        ChatStreamState.messages,
                        lambda msg: mn.paper(
                            mn.text(msg, size="sm"),
                            p="xs",
                            with_border=True,
                        ),
                    ),
                    gap="xs",
                ),
                height="250px",
                width="100%",
                border="1px solid",
                border_color=rx.color("gray", 4),
                border_radius="md",
            ),
            mn.divider(),
            mn.group(
                mn.button(
                    "Add Message",
                    on_click=ChatStreamState.add_message("New message added"),
                    variant="default",
                ),
                mn.button(
                    "Stream Response",
                    on_click=ChatStreamState.stream_response,
                ),
            ),
        ),
    )


def auto_scroll_with_controls_example() -> rx.Component:
    """AutoScroll example 2."""
    return example_box(
        "AutoScroll Example 2",
        mn.stack(
            mn.group(
                mn.text(
                    f"At bottom: {DataStreamState.at_bottom}, "
                    f"at top: {DataStreamState.at_top}",
                    size="sm",
                    c="dimmed",
                ),
                mn.text(
                    f"Pos: x={DataStreamState.scroll_position['x']}, "
                    f"y={DataStreamState.scroll_position['y']}",
                    size="xs",
                    c="dimmed",
                ),
                justify="space-between",
            ),
            mn.divider(),
            mn.scroll_area.autoscroll(
                mn.stack(
                    rx.foreach(
                        DataStreamState.log_lines,
                        lambda line: mn.text(line, size="xs", ff="monospace"),
                    ),
                    gap=0,
                ),
                height="300px",
                width="100%",
                border="1px solid",
                border_color=rx.color("gray", 4),
                border_radius="md",
                on_scroll_position_change=DataStreamState.update_scroll_position,
            ),
            mn.divider(),
            mn.group(
                mn.button(
                    "Add Log",
                    on_click=DataStreamState.add_log("INFO", "Manual log entry"),
                    variant="default",
                ),
                mn.button(
                    "Simulate Processing",
                    on_click=DataStreamState.simulate_processing,
                ),
            ),
        ),
    )


def stateful_autoscroll_example() -> rx.Component:
    """ScrollAreaWithState with autoscroll enabled."""
    return example_box(
        "ScrollArea.Stateful with AutoScroll",
        mn.stack(
            mn.text(
                "Combines state-based scroll tracking, top/bottom buttons, "
                "and autoscroll behavior.",
                size="sm",
                c="dimmed",
            ),
            mn.group(
                mn.button(
                    "Add Message",
                    on_click=ChatStreamState.add_message("User: New message here!"),
                    variant="default",
                ),
                mn.button(
                    "Stream Response",
                    on_click=ChatStreamState.stream_response,
                ),
            ),
            mn.stack(
                mn.scroll_area.stateful(
                    mn.stack(
                        rx.foreach(
                            ChatStreamState.messages,
                            lambda msg, idx: mn.card(
                                mn.text(msg, size="sm"),
                                p="xs",
                                bg=rx.cond(
                                    msg.contains("User:"),
                                    "var(--mantine-color-blue-1)",
                                    "var(--mantine-color-gray-1)",
                                ),
                                key=f"msg-{idx}",
                            ),
                        ),
                        gap="xs",
                    ),
                    autoscroll=True,
                    persist_key="stateful-autoscroll-demo",
                    height="300px",
                    show_controls=True,
                    controls="both",
                    scrollbars="y",
                    type="hover",
                ),
            ),
            mn.alert(
                "✨ New: autoscroll=True enables auto-scroll while "
                "preserving state tracking, scroll persistence, "
                "and navigation buttons.",
                icon=rx.icon("info"),
                variant="light",
                color="blue",
            ),
        ),
    )


@navbar_layout(
    route="/auto-scroll",
    title="AutoScroll Examples",
    description="AutoScroll Component Examples",
    navbar=app_navbar(),
    with_header=False,
)
def auto_scroll_examples() -> rx.Component:
    """Main auto-scroll examples page."""
    return mn.container(
        mn.stack(
            mn.title("AutoScroll Components", order=1),
            mn.text(
                "Demonstration of AutoScroll and AutoScrollWithControls components",
                size="md",
                c="dimmed",
            ),
            mn.divider(),
            auto_scroll_example(),
            auto_scroll_with_controls_example(),
            stateful_autoscroll_example(),
            gap="xl",
        ),
        size="lg",
    )
