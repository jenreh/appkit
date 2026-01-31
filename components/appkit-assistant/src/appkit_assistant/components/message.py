import reflex as rx

import appkit_mantine as mn
from appkit_assistant.backend.models import (
    Message,
    MessageType,
    Thinking,
    ThinkingStatus,
    ThinkingType,
)
from appkit_assistant.state.thread_state import (
    ThreadState,
)
from appkit_ui.components.collabsible import collabsible
from appkit_ui.components.dialogs import delete_dialog

message_styles = {
    "spacing": "4",
    "width": "100%",
    "max_width": "880px",
    "margin_top": "24px",
    "margin_left": "auto",
    "margin_right": "auto",
}


class AuthCardComponent:
    """Component for displaying MCP OAuth authentication cards."""

    @staticmethod
    def render() -> rx.Component:
        """Render the auth required card when authentication is needed."""
        return rx.cond(
            ThreadState.show_auth_card,
            rx.hstack(
                rx.avatar(
                    fallback="🔐",
                    size="3",
                    variant="soft",
                    radius="full",
                    margin_top="16px",
                ),
                rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.text(
                                "Anmeldung erforderlich",
                                weight="bold",
                                size="3",
                            ),
                            spacing="2",
                        ),
                        rx.text(
                            rx.text.span(ThreadState.pending_auth_server_name),
                            " benötigt Ihre Anmeldung, um fortzufahren.",
                            size="2",
                            color=rx.color("gray", 11),
                        ),
                        rx.hstack(
                            rx.button(
                                "Anmelden",
                                on_click=ThreadState.start_mcp_oauth,
                                color_scheme="amber",
                                variant="solid",
                            ),
                            rx.button(
                                "Abbrechen",
                                on_click=ThreadState.dismiss_auth_card,
                                color_scheme="gray",
                                variant="solid",
                            ),
                            spacing="3",
                            margin_top="2",
                        ),
                        spacing="3",
                        padding="4",
                    ),
                    size="2",
                    variant="surface",
                    max_width="400px",
                    margin_top="16px",
                ),
                style=message_styles,
            ),
            rx.fragment(),
        )


class MessageActionsBar:
    """Component for message action buttons (copy, download, retry)."""

    @staticmethod
    def render(message: Message) -> rx.Component:
        return rx.hstack(
            rx.tooltip(
                rx.icon_button(
                    rx.icon("copy", size=14),
                    on_click=ThreadState.copy_message(message.text),
                    variant="ghost",
                    size="1",
                    color_scheme="gray",
                ),
                content="Kopieren",
            ),
            rx.tooltip(
                rx.icon_button(
                    rx.icon("download", size=14),
                    on_click=ThreadState.download_message(message.text, message.id),
                    variant="ghost",
                    size="1",
                    color_scheme="gray",
                ),
                content="Herunterladen",
            ),
            rx.tooltip(
                delete_dialog(
                    title="Nachricht löschen",
                    content="diese Nachricht",
                    on_click=ThreadState.delete_message(message.id),
                    icon_button=True,
                    variant="ghost",
                    size="1",
                    color_scheme="gray",
                ),
                content="Löschen",
            ),
            rx.cond(
                (message.type == MessageType.ASSISTANT)
                | (message.type == MessageType.ERROR),
                rx.tooltip(
                    rx.icon_button(
                        rx.cond(
                            ThreadState.processing,
                            rx.spinner(size="1"),
                            rx.icon("refresh-cw", size=14),
                        ),
                        on_click=ThreadState.retry_message(message.id),
                        variant="ghost",
                        size="1",
                        color_scheme="gray",
                        disabled=ThreadState.processing,
                    ),
                    content="Erneut generieren (folgende Nachrichten werden entfernt)",
                ),
                rx.fragment(),
            ),
            spacing="3",
            margin_top="-9px",
            margin_left="9px",
        )


class MessageComponent:
    @staticmethod
    def _file_badge(filename: str) -> rx.Component:
        """Render a single file attachment badge."""
        return rx.badge(
            rx.icon("paperclip", size=12),
            filename,
            variant="soft",
            color="gray",
            size="1",
            radius="small",
        )

    @staticmethod
    def _attachments_row(attachments: list[str]) -> rx.Component:
        """Render a row of file attachment badges."""
        return rx.cond(
            attachments.length() > 0,
            rx.hstack(
                rx.foreach(attachments, MessageComponent._file_badge),
                spacing="2",
                margin_top="8px",
                justify="end",
                width="90%",
                flex_wrap="wrap",
            ),
            rx.fragment(),
        )

    @staticmethod
    def human_message(message: Message) -> rx.Component:
        return rx.cond(
            ThreadState.editing_message_id == message.id,
            # Edit Mode
            rx.vstack(
                rx.text_area(
                    value=ThreadState.edited_message_content,
                    on_change=ThreadState.set_edited_message_content,
                    height="112px",
                    width="824px",
                    auto_focus=True,
                    bg=rx.color("gray", 3),
                    variant="soft",
                ),
                rx.hstack(
                    rx.button(
                        "Abbrechen",
                        on_click=ThreadState.cancel_edit,
                        variant="soft",
                        color_scheme="gray",
                    ),
                    rx.button("Senden", on_click=ThreadState.submit_edited_message),
                    justify="end",
                    width="100%",
                    spacing="2",
                ),
                style=message_styles,
                align="end",
            ),
            rx.vstack(
                rx.hstack(
                    rx.spacer(),
                    rx.vstack(
                        rx.box(
                            rx.text(
                                message.text,
                                padding="0.5em",
                                border_radius="10px",
                                white_space="pre-line",
                            ),
                            padding="4px",
                            max_width="800px",
                            background_color=rx.color_mode_cond(
                                light=rx.color("accent", 3),
                                dark=rx.color("accent", 3),
                            ),
                            border_radius="9px",
                        ),
                        MessageComponent._attachments_row(message.attachments),
                        align="end",
                        spacing="1",
                    ),
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.tooltip(
                        rx.icon_button(
                            rx.icon("pencil", size=14),
                            on_click=ThreadState.set_editing_mode(
                                message.id, message.text
                            ),
                            variant="ghost",
                            size="1",
                            color_scheme="gray",
                        ),
                        content="Bearbeiten",
                    ),
                    rx.tooltip(
                        delete_dialog(
                            title="Nachricht löschen",
                            content="diese Nachricht",
                            on_click=ThreadState.delete_message(message.id),
                            icon_button=True,
                            variant="ghost",
                            size="1",
                            color_scheme="gray",
                        ),
                        content="Löschen",
                    ),
                    rx.tooltip(
                        rx.icon_button(
                            rx.icon("copy", size=14),
                            on_click=ThreadState.copy_message(message.text),
                            variant="ghost",
                            size="1",
                            color_scheme="gray",
                        ),
                        content="Kopieren",
                    ),
                    spacing="3",
                    justify="end",
                    margin_right="9px",
                ),
                align="end",
                style=message_styles,
            ),
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
                rx.box(
                    mn.markdown_preview(
                        source=message.text,
                        enable_mermaid=message.done,
                        enable_katex=message.done,
                        security_level="standard",
                        class_name="markdown",
                    ),
                    padding="0.5em",
                    margin_top="18px",
                    max_width="90%",
                ),
            ),
            # Annotations/Sources
            rx.cond(
                message.annotations.length() > 0,
                rx.vstack(
                    rx.hstack(
                        rx.icon("file-text", size=13, color=rx.color("gray", 9)),
                        rx.text(
                            "Quellen:",
                            size="1",
                            color=rx.color("gray", 9),
                        ),
                        spacing="1",
                    ),
                    rx.hstack(
                        rx.foreach(
                            message.annotations,
                            lambda ann: rx.badge(
                                ann,
                                size="1",
                                variant="soft",
                                color_scheme="gray",
                            ),
                        ),
                        spacing="1",
                        align="start",
                        flex_wrap="wrap",
                    ),
                    padding="6px",
                    margin_top="6px",
                    margin_bottom="6px",
                    width="90%",
                    align="start",
                ),
                rx.fragment(),
            ),
            # Actions bar
            rx.cond(
                message.done,
                MessageActionsBar.render(message),
                rx.fragment(),
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
    def error_message(message: Message) -> rx.Component:
        return rx.hstack(
            rx.avatar(
                fallback="!",
                size="3",
                variant="soft",
                radius="full",
                margin_top="16px",
                color_scheme="red",
            ),
            rx.vstack(
                rx.callout(
                    message.text,
                    icon="triangle-alert",
                    color_scheme="red",
                    max_width="100%",
                    size="1",
                    padding="0.5em",
                    border_radius="9px",
                    margin_top="18px",
                ),
                MessageActionsBar.render(message),
                width="90%",
                spacing="2",
            ),
            style=message_styles,
        )

    @staticmethod
    def system_message(message: str) -> rx.Component:
        return rx.hstack(
            rx.avatar(
                fallback="⚙",
                size="3",
                variant="soft",
                radius="full",
                margin_top="16px",
                color_scheme="gray",
            ),
            rx.callout(
                message,
                icon="info",
                color_scheme="gray",
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
                    MessageComponent.human_message(message),
                ),
                (
                    MessageType.ASSISTANT,
                    MessageComponent.assistant_message(message),
                ),
                (
                    MessageType.ERROR,
                    MessageComponent.error_message(message),
                ),
                (
                    MessageType.SYSTEM,
                    MessageComponent.system_message(message.text),
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
            rx.cond(
                tool_item.type == ThinkingType.PROCESSING,
                ToolCallComponent._render_processing(tool_item),
                ToolCallComponent._render_tool_call(tool_item),
            ),
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
    def _render_processing(item: Thinking) -> rx.Component:
        """Render file processing progress."""
        return rx.hstack(
            rx.cond(
                item.status == ThinkingStatus.COMPLETED,
                rx.icon("circle-check", size=14, color=rx.color("green", 9)),
                rx.cond(
                    item.status == ThinkingStatus.ERROR,
                    rx.icon("circle-x", size=14, color=rx.color("red", 9)),
                    rx.icon("file-up", size=14, color=rx.color("blue", 9)),
                ),
            ),
            rx.text(
                item.text,
                size="1",
                color=rx.cond(
                    item.status == ThinkingStatus.ERROR,
                    rx.color("red", 9),
                    rx.color("gray", 10),
                ),
            ),
            spacing="2",
            padding="3px 6px",
            margin_bottom="3px",
            width="100%",
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
