import reflex as rx

import appkit_mantine as mn
from appkit_assistant.backend.models import (
    Message,
    MessageType,
)
from appkit_assistant.state.thread_state import (
    Thinking,
    ThinkingStatus,
    ThinkingType,
    ThreadState,
)
from appkit_ui.components.collabsible import collabsible

message_styles = {
    "spacing": "4",
    "width": "100%",
    "max_width": "880px",
    "margin_top": "24px",
    "margin_left": "auto",
    "margin_right": "auto",
}


class MessageComponent:
    @staticmethod
    def human_message(message: str) -> rx.Component:
        return rx.hstack(
            rx.spacer(),
            rx.box(
                rx.text(
                    message,
                    padding="0.5em",
                    border_radius="10px",
                    white_space="pre-line",
                ),
                padding="4px",
                max_width="80%",
                margin_top="24px",
                # margin_right="14px",
                background_color=rx.color_mode_cond(
                    light=rx.color("accent", 3),
                    dark=rx.color("accent", 3),
                ),
                border_radius="9px",
            ),
            style=message_styles,
        )

    @staticmethod
    def assistant_message(message: Message) -> rx.Component:
        """Display an assistant message with thinking content when items exist."""

        # Show thinking content only for the last assistant message
        should_show_thinking = (
            message.text == ThreadState.get_last_assistant_message_text
        ) & ThreadState.has_thinking_content

        # Main content area with all components
        content_area = rx.vstack(
            # Always rendered with conditional styling for smooth animations
            collabsible(
                rx.scroll_area(
                    rx.foreach(
                        ThreadState.thinking_items,
                        lambda item: ToolCallComponent.render(item),
                    ),
                    spacing="3",
                    max_height="180px",
                    padding="9px 12px",
                    width="100%",
                    scrollbars="vertical",
                ),
                title="Denkprozess & Werkzeuge",
                info_text=(
                    f"{ThreadState.get_unique_reasoning_sessions.length()} "
                    f"Nachdenken, "
                    f"{ThreadState.get_unique_tool_calls.length()} Werkzeuge"
                ),
                show_condition=should_show_thinking,
                expanded=ThreadState.thinking_expanded,
                on_toggle=ThreadState.toggle_thinking_expanded,
            ),
            # Main message content
            rx.cond(
                message.text == "",
                rx.hstack(
                    rx.text(
                        rx.cond(
                            ThreadState.current_activity != "",
                            ThreadState.current_activity,
                            "Denke nach",
                        ),
                        color=rx.color("gray", 8),
                        margin_right="9px",
                    ),
                    rx.hstack(
                        rx.el.span(""),
                        rx.el.span(""),
                        rx.el.span(""),
                        rx.el.span(""),
                    ),
                    class_name="loading",
                    height="40px",
                    color=rx.color("gray", 8),
                    background_color=rx.color("gray", 2),
                    padding="0.5em",
                    border_radius="9px",
                    margin_top="16px",
                    padding_right="18px",
                ),
                # Actual message content
                mn.markdown_preview(
                    source=message.text,
                    enable_mermaid=message.done,
                    enable_katex=message.done,
                    security_level="standard",
                    padding="0.5em",
                    border_radius="9px",
                    max_width="90%",
                    class_name="markdown",
                ),
                # rx.markdown(
                #     message.text,
                #     padding="0.5em",
                #     border_radius="9px",
                #     max_width="90%",
                #     class_name="markdown",
                # ),
            ),
            spacing="3",
            width="100%",
        )

        return rx.hstack(
            rx.avatar(
                fallback="AI",
                size="3",
                variant="soft",
                radius="full",
                margin_top="16px",
            ),
            content_area,
            style=message_styles,
        )

    @staticmethod
    def info_message(message: str) -> rx.Component:
        return rx.hstack(
            rx.avatar(
                fallback="AI",
                size="3",
                variant="soft",
                radius="full",
                margin_top="16px",
            ),
            rx.callout(
                message,
                icon="info",
                max_width="90%",
                size="1",
                padding="0.5em",
                border_radius="9px",
                margin_top="18px",
            ),
            style=message_styles,
        )

    @staticmethod
    def render_message(
        message: Message,
    ) -> rx.Component:
        """Render message with optional enhanced chunk-based components."""
        return rx.fragment(
            rx.match(
                message.type,
                (
                    MessageType.HUMAN,
                    MessageComponent.human_message(message.text),
                ),
                (
                    MessageType.ASSISTANT,
                    MessageComponent.assistant_message(message),
                ),
                MessageComponent.info_message(message.text),
            )
        )


class ToolCallComponent:
    """Component for displaying individual tool calls with green styling."""

    @staticmethod
    def render(tool_item: Thinking) -> rx.Component:
        return rx.cond(
            tool_item.type == ThinkingType.REASONING,
            ToolCallComponent._render_reasoning(tool_item),
            ToolCallComponent._render_tool_call(tool_item),
        )

    @staticmethod
    def _render_reasoning(item: Thinking) -> rx.Component:
        return rx.vstack(
            rx.text(item.text, size="1"),
            border_left=f"3px solid {rx.color('gray', 4)}",
            padding="3px 6px",
            margin_bottom="9px",
        )

    @staticmethod
    def _render_tool_call(item: Thinking) -> rx.Component:
        return rx.vstack(
            rx.hstack(
                rx.icon("wrench", size=14, color=rx.color("green", 8)),
                rx.text(
                    f"Werkzeug: {item.tool_name}",
                    size="1",
                    font_weight="bold",
                    color=rx.color("blue", 9),
                ),
                rx.spacer(),
                rx.text(
                    item.id,
                    size="1",
                    color=rx.color("gray", 6),
                ),
                spacing="1",
                margin_bottom="3px",
                width="100%",
            ),
            rx.cond(
                item.text,
                rx.vstack(
                    rx.text(
                        item.text,
                        size="1",
                        color=rx.color("gray", 10),
                    ),
                    align="start",
                    width="100%",
                ),
            ),
            rx.cond(
                item.parameters,
                rx.vstack(
                    rx.text(
                        item.parameters,
                        size="1",
                        color=rx.color("blue", 9),
                        white_space="pre-wrap",
                    ),
                    align="start",
                    width="100%",
                    spacing="1",
                ),
            ),
            rx.cond(
                item.status == ThinkingStatus.COMPLETED,
                rx.scroll_area(
                    rx.text(
                        item.result,
                        size="1",
                        color=rx.color("gray", 8),
                    ),
                    max_height="60px",
                    width="95%",
                    scrollbars="vertical",
                ),
            ),
            rx.cond(
                item.status == ThinkingStatus.ERROR,
                rx.vstack(
                    rx.hstack(
                        rx.icon("shield-alert", size=14, color=rx.color("red", 10)),
                        rx.text(
                            "Fehler",
                            size="1",
                            font_weight="bold",
                            color=rx.color("red", 10),
                        ),
                        spacing="1",
                    ),
                    rx.text(
                        item.error,
                        size="1",
                        color=rx.color("red", 9),
                    ),
                    align="start",
                    width="100%",
                    spacing="1",
                ),
            ),
            padding="3px 6px",
            border_left=f"3px solid {rx.color('gray', 5)}",
            margin_bottom="9px",
            width="100%",
            spacing="2",
        )
