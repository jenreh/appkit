"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import logging

import reflex as rx

from appkit_assistant.components import (
    Suggestion,
)
from appkit_assistant.components.thread import Assistant
from appkit_assistant.roles import (
    ASSISTANT_USER_ROLE,
)
from appkit_assistant.state.thread_list_state import ThreadListState
from appkit_assistant.state.thread_state import ThreadState
from appkit_mantine import mermaid_zoom_script
from appkit_ui.components.header import header
from appkit_user.authentication.components.components import (
    default_fallback,
    requires_role,
)
from appkit_user.authentication.templates import authenticated

from app.components.navbar import app_navbar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

suggestions = [
    Suggestion(prompt="Wie ist das Wetter in Gütersloh?", icon="cloud-sun"),
    Suggestion(prompt="Was ist die Hauptstadt von Frankreich?", icon="map-pin-house"),
    Suggestion(
        prompt="Was ist die Antwort auf das Leben, das Universum und den ganzen Rest?"
    ),
    Suggestion(prompt="Was ist der Sinn des Lebens?"),
]


@authenticated(
    route="/assistant",
    title="Assistant",
    description="A demo page for the Assistant UI.",
    navbar=app_navbar(),
    on_load=[
        ThreadState.set_suggestions(suggestions),
        ThreadState.initialize(),
        ThreadListState.initialize(),
    ],
)
def assistant_page() -> rx.Component:
    assistant_styles = {
        "height": "calc(100vh - 76px)",
        "margin_bottom": "18px",
    }

    return requires_role(
        header("Assistent"),
        mermaid_zoom_script(),  # Enable image/diagram zooming
        rx.flex(
            rx.vstack(
                Assistant.thread_list(
                    width="100%",
                    margin_top="6px",
                    **assistant_styles,  # type: ignore
                ),
                flex_shrink=0,
                width="248px",
                padding="0px 12px",
                border_right=f"1px solid {rx.color('gray', 5)}",
                background_color=rx.color("gray", 1),
            ),
            rx.vstack(
                rx.center(
                    Assistant.thread(
                        welcome_message=("👋 Hallo, wie kann ich Dir heute helfen?"),
                        with_attachments=True,
                        with_scroll_to_bottom=False,
                        with_thread_list=True,
                        with_tools=True,
                        # styling
                        padding="12px",
                        border_radius="10px",
                        direction="column",
                        width="100%",
                        **assistant_styles,
                    ),
                    width="100%",
                ),
                width="100%",
                flex_shrink=1,
            ),
            display="column",
            **assistant_styles,
        ),
        role=ASSISTANT_USER_ROLE.name,
        fallback=default_fallback(),
    )
