"""Table component for displaying Azure Agents."""

import reflex as rx
from reflex.components.radix.themes.components.table import TableRow

from appkit_assistant.backend.models import OpenAIAgent
from appkit_assistant.components.openai_agent_dialogs import (
    add_openai_agent_button,
    delete_openai_agent_dialog,
    update_openai_agent_dialog,
)
from appkit_assistant.state.openai_agent_state import OpenAIAgentState


def openai_agent_table_row(agent: OpenAIAgent) -> TableRow:
    """Show an Azure Agent in a table row."""
    return rx.table.row(
        rx.table.cell(
            agent.name,
            white_space="nowrap",
        ),
        rx.table.cell(
            rx.text(
                agent.endpoint,
                title=agent.endpoint,
                style={
                    "display": "block",
                    "overflow": "hidden",
                    "text_overflow": "ellipsis",
                    "white_space": "nowrap",
                },
            ),
            white_space="nowrap",
            style={
                "max_width": "0",
                "width": "100%",
            },
        ),
        rx.table.cell(
            rx.cond(
                agent.is_active,
                rx.icon("user-check", color="green", size=21),
                rx.icon("user-x", color="crimson", size=21),
            ),
            text_align="center",
            white_space="nowrap",
        ),
        rx.table.cell(
            rx.hstack(
                update_openai_agent_dialog(agent),
                delete_openai_agent_dialog(agent),
                spacing="2",
                align_items="center",
            ),
            white_space="nowrap",
        ),
        justify="center",
        vertical_align="middle",
        style={"_hover": {"bg": rx.color("gray", 2)}},
    )


def openai_agents_table() -> rx.Fragment:
    return rx.fragment(
        rx.flex(
            add_openai_agent_button(),
            rx.spacer(),
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Name", width="20%"),
                    rx.table.column_header_cell("Endpoint", width="calc(80% - 190px)"),
                    rx.table.column_header_cell("Aktiv", width="50px"),
                    rx.table.column_header_cell("", width="140px"),
                ),
            ),
            rx.table.body(rx.foreach(OpenAIAgentState.agents, openai_agent_table_row)),
            size="3",
            width="100%",
            table_layout="fixed",
            on_mount=OpenAIAgentState.load_agents_with_toast,
        ),
    )
