import reflex as rx

from appkit_assistant.components.user_prompt_editor import user_prompt_editor
from appkit_assistant.state.user_prompt_state import UserPromptState
from appkit_ui.components.header import header
from appkit_user.authentication.templates import authenticated

from app.components.navbar import app_navbar


@authenticated(
    route="/prompts",
    title="Meine Prompts",
    navbar=app_navbar(),
    on_load=UserPromptState.load_user_prompts,
)
def prompts_page() -> rx.Component:
    """Page for managing user-defined system prompts."""
    return rx.vstack(
        header("Prompt Manager"),
        user_prompt_editor(),
        height="calc(100vh - 180px)",  # Adjust based on header height
        overflow="hidden",
        flex="1",
        width="100%",
        max_width="1200px",
        spacing="4",
    )
