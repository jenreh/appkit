"""Table component for displaying and managing AI model configurations."""

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.backend.database.models import AssistantAIModel
from appkit_assistant.components.ai_model_dialogs import (
    AIModelValidationState,
    add_ai_model_button,
    add_ai_model_modal,
    delete_ai_model_dialog,
    edit_ai_model_modal,
)
from appkit_assistant.state.ai_model_admin_state import AIModelAdminState
from appkit_ui.styles import sticky_header_style


def _processor_short_label(processor_type: str) -> rx.Component:
    """Render a short badge for the processor type."""
    # Use rx.match for reactive rendering
    return rx.match(
        processor_type,
        ("openai", rx.badge("OpenAI", color_scheme="blue")),
        ("claude", rx.badge("Claude", color_scheme="orange")),
        ("perplexity", rx.badge("Perplexity", color_scheme="teal")),
        ("gemini", rx.badge("Gemini", color_scheme="green")),
        ("lorem_ipsum", rx.badge("Test", color_scheme="gray")),
        rx.badge(processor_type, color_scheme="gray", variant="outline"),
    )


def ai_model_table_row(record: AssistantAIModel) -> rx.Component:
    """Render a single AI model as a table row."""
    return mn.table.tr(
        # Display name
        mn.table.td(
            mn.text(
                record.text,
                size="sm",
                fw="500",
                style={"whiteSpace": "nowrap"},
            ),
            min_width="160px",
        ),
        # Unique model_id
        mn.table.td(
            mn.text(
                record.model_id,
                size="sm",
                c="dimmed",
                style={"whiteSpace": "nowrap"},
            ),
            width="1%",
            style={"whiteSpace": "nowrap"},
        ),
        # Processor type badge
        mn.table.td(
            _processor_short_label(record.processor_type),
            width="1%",
            style={"whiteSpace": "nowrap"},
        ),
        # Required role — inline select with spinner
        mn.table.td(
            mn.group(
                mn.select(
                    value=record.requires_role,
                    data=AIModelAdminState.available_roles,
                    placeholder="nicht eingeschränkt",
                    size="xs",
                    clearable=True,
                    check_icon_position="right",
                    on_change=lambda val: AIModelAdminState.update_model_role(
                        record.id, val
                    ),
                    w="180px",
                ),
                mn.box(
                    rx.cond(
                        AIModelAdminState.updating_role_model_id == record.id,
                        rx.spinner(size="1"),
                    ),
                    width="16px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex_shrink="0",
                ),
                align="center",
                gap="xs",
                wrap="nowrap",
            ),
            width="1%",
            style={"whiteSpace": "nowrap"},
        ),
        # Active toggle — inline switch with spinner
        mn.table.td(
            mn.group(
                mn.switch(
                    checked=record.active,
                    on_change=lambda checked: AIModelAdminState.toggle_model_active(
                        record.id, checked
                    ),
                    size="sm",
                ),
                mn.box(
                    rx.cond(
                        AIModelAdminState.updating_active_model_id == record.id,
                        rx.spinner(size="1"),
                    ),
                    width="16px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex_shrink="0",
                ),
                align="center",
                gap="xs",
                wrap="nowrap",
            ),
            width="1%",
            style={"whiteSpace": "nowrap"},
        ),
        # Actions
        mn.table.td(
            mn.group(
                rx.icon_button(
                    rx.icon("square-pen", size=19),
                    variant="ghost",
                    on_click=[
                        lambda: AIModelAdminState.get_model(record.id),
                        AIModelValidationState.initialize(record),
                        AIModelAdminState.open_edit_modal,
                    ],
                    margin="0",
                ),
                delete_ai_model_dialog(record),
                align="center",
                gap="xs",
                wrap="nowrap",
            ),
            width="1%",
            style={"whiteSpace": "nowrap"},
        ),
    )


def ai_models_table(
    available_roles: list[dict[str, str]] | None = None,
    role_labels: dict[str, str] | None = None,
) -> rx.Component:
    """Admin table for managing AI model configurations."""
    if available_roles is None:
        available_roles = []
    if role_labels is None:
        role_labels = {}

    return mn.stack(
        add_ai_model_modal(),
        edit_ai_model_modal(),
        rx.flex(
            add_ai_model_button(),
            mn.text_input(
                placeholder="Modell filtern...",
                left_section=rx.icon("search", size=16),
                left_section_pointer_events="none",
                value=AIModelAdminState.search_filter,
                on_change=AIModelAdminState.set_search_filter,
                size="sm",
                w="18rem",
            ),
            rx.spacer(),
            width="100%",
            margin_bottom="md",
            gap="12px",
            align="center",
        ),
        mn.table(
            mn.table.thead(
                mn.table.tr(
                    mn.table.th(mn.text("Name", size="sm", fw="700")),
                    mn.table.th(mn.text("Modell-ID", size="sm", fw="700")),
                    mn.table.th(mn.text("Prozessor", size="sm", fw="700")),
                    mn.table.th(mn.text("Rolle", size="sm", fw="700")),
                    mn.table.th(mn.text("Aktiv", size="sm", fw="700")),
                    mn.table.th(mn.text("", size="sm")),
                    style=sticky_header_style,
                ),
            ),
            mn.table.tbody(
                rx.foreach(
                    AIModelAdminState.filtered_models,
                    ai_model_table_row,
                )
            ),
            sticky_header=True,
            sticky_header_offset="0px",
            striped=False,
            highlight_on_hover=True,
            highlight_on_hover_color=rx.color_mode_cond(
                light="gray.0",
                dark="dark.8",
            ),
            w="100%",
        ),
        w="100%",
        on_mount=[
            AIModelAdminState.set_available_roles(available_roles, role_labels),
            AIModelAdminState.load_models_with_toast,
        ],
    )
