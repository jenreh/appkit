"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import logging

import reflex as rx

from appkit_assistant.backend.model_manager import ModelManager
from appkit_assistant.backend.models import (
    CLAUDE_HAIKU_4_5,
    GEMINI_3_FLASH,
    GEMINI_3_PRO,
    GPT_5_1,
    GPT_5_2,
    GPT_5_MINI,
    SONAR,
    SONAR_DEEP_RESEARCH,
    AIModel,
)
from appkit_assistant.backend.processors import (
    ClaudeResponsesProcessor,
    GeminiResponsesProcessor,
    LoremIpsumProcessor,
    OpenAIResponsesProcessor,
    PerplexityProcessor,
)
from appkit_assistant.components import (
    Suggestion,
)
from appkit_assistant.components.thread import Assistant
from appkit_assistant.configuration import AssistantConfig
from appkit_assistant.roles import (
    ASSISTANT_USER_ROLE,
)
from appkit_assistant.state.thread_list_state import ThreadListState
from appkit_assistant.state.thread_state import ThreadState
from appkit_commons.registry import service_registry
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


def initialize_model_manager() -> list[AIModel]:
    """Initialize the service manager and register all processors.

    Returns:
        List of available AI models.
    """
    model_manager = ModelManager()
    model_manager.register_processor("lorem_ipsum", LoremIpsumProcessor())
    config = service_registry().get(AssistantConfig)

    if config.perplexity_api_key is not None:
        model_manager.register_processor(
            "perplexity",
            PerplexityProcessor(
                api_key=config.perplexity_api_key.get_secret_value(),
                models={SONAR.id: SONAR, SONAR_DEEP_RESEARCH.id: SONAR_DEEP_RESEARCH},
            ),
        )

    models = {
        GPT_5_1.id: GPT_5_1,
        GPT_5_MINI.id: GPT_5_MINI,
        GPT_5_2.id: GPT_5_2,
    }

    model_manager.register_processor(
        "openai",
        OpenAIResponsesProcessor(
            api_key=config.openai_api_key.get_secret_value()
            if config.openai_api_key
            else None,
            base_url=config.openai_base_url,
            models=models,
            is_azure=config.openai_is_azure,
        ),
    )

    if config.claude_api_key is not None:
        claude_models = {
            CLAUDE_HAIKU_4_5.id: CLAUDE_HAIKU_4_5,
            # CLAUDE_SONNET_4_5.id: CLAUDE_SONNET_4_5,
        }
        model_manager.register_processor(
            "claude",
            ClaudeResponsesProcessor(
                api_key=config.claude_api_key.get_secret_value(),
                base_url=config.claude_base_url,
                models=claude_models,
            ),
        )

    if config.google_api_key is not None:
        gemini_models = {
            GEMINI_3_PRO.id: GEMINI_3_PRO,
            GEMINI_3_FLASH.id: GEMINI_3_FLASH,
        }
        model_manager.register_processor(
            "gemini",
            GeminiResponsesProcessor(
                api_key=config.google_api_key.get_secret_value(),
                models=gemini_models,
            ),
        )

    model_manager.set_default_model(GPT_5_MINI.id)
    return model_manager.get_all_models()


initialize_model_manager()


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
