"""Dialog components for OpenAI Agent management."""

import logging

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.backend.models import OpenAIAgent
from appkit_assistant.state.openai_agent_state import OpenAIAgentState
from appkit_ui.components.dialogs import (
    delete_dialog,
    dialog_buttons,
    dialog_header,
)
from appkit_ui.components.form_inputs import form_field

logger = logging.getLogger(__name__)


class OpenAIAgentValidationState(rx.State):
    endpoint: str = ""
    name: str = ""
    description: str = ""
    api_key: str = ""

    endpoint_error: str = ""
    name_error: str = ""
    description_error: str = ""
    api_key_error: str = ""

    @rx.event
    def initialize(self, agent: OpenAIAgent | None = None) -> None:
        """Reset validation state."""
        if agent:
            self.endpoint = agent.endpoint
            self.name = agent.name
            self.description = agent.description
            self.api_key = agent.api_key
        else:
            self.endpoint = ""
            self.name = ""
            self.description = ""
            self.api_key = ""

        self.endpoint_error = ""
        self.name_error = ""
        self.description_error = ""
        self.api_key_error = ""

    @rx.event
    def validate_endpoint(self) -> None:
        if not self.endpoint:
            self.endpoint_error = "Endpoint ist erforderlich."
        else:
            self.endpoint_error = ""

    @rx.event
    def validate_name(self) -> None:
        if not self.name:
            self.name_error = "Name ist erforderlich."
        else:
            self.name_error = ""

    @rx.event
    def validate_description(self) -> None:
        self.description_error = ""

    @rx.event
    def validate_api_key(self) -> None:
        if not self.api_key:
            self.api_key_error = "API Key ist erforderlich."
        else:
            self.api_key_error = ""

    @rx.var
    def has_errors(self) -> bool:
        return bool(
            self.endpoint_error
            or self.name_error
            or self.description_error
            or self.api_key_error
        )

    def set_endpoint(self, endpoint: str) -> None:
        self.endpoint = endpoint
        self.validate_endpoint()

    def set_name(self, name: str) -> None:
        self.name = name
        self.validate_name()

    def set_description(self, description: str) -> None:
        self.description = description
        self.validate_description()

    def set_api_key(self, api_key: str) -> None:
        self.api_key = api_key
        self.validate_api_key()


def openai_agent_form_fields(agent: OpenAIAgent | None = None) -> rx.Component:
    """Reusable form fields for OpenAI Agent add/update dialogs."""
    is_edit_mode = agent is not None

    fields = [
        form_field(
            name="name",
            icon="bot",
            label="Name",
            hint="Eindeutiger Name des OpenAI Agents",
            type="text",
            placeholder="Agent Name",
            default_value=agent.name if is_edit_mode else "",
            required=True,
            max_length=64,
            on_change=OpenAIAgentValidationState.set_name,
            on_blur=OpenAIAgentValidationState.validate_name,
            validation_error=OpenAIAgentValidationState.name_error,
        ),
        form_field(
            name="description",
            icon="text",
            label="Beschreibung",
            hint="Kurze Beschreibung des Agents",
            type="text",
            placeholder="Beschreibung...",
            max_length=200,
            default_value=agent.description if is_edit_mode else "",
            required=False,
            on_change=OpenAIAgentValidationState.set_description,
            on_blur=OpenAIAgentValidationState.validate_description,
            validation_error=OpenAIAgentValidationState.description_error,
        ),
        form_field(
            name="endpoint",
            icon="link-2",
            label="Endpoint",
            hint="Vollständige URL des Agent Endpoints",
            type="text",
            placeholder="https://...",
            default_value=agent.endpoint if is_edit_mode else "",
            required=True,
            on_change=OpenAIAgentValidationState.set_endpoint,
            on_blur=OpenAIAgentValidationState.validate_endpoint,
            validation_error=OpenAIAgentValidationState.endpoint_error,
        ),
        mn.password_input(
            name="api_key",
            icon="key",
            label="API Key",
            description="API Key für den Zugriff auf den Agent",
            placeholder="sk-...",
            default_value=agent.api_key if is_edit_mode else "",
            required=True,
            with_asterisk=True,
            on_change=OpenAIAgentValidationState.set_api_key,
            on_blur=OpenAIAgentValidationState.validate_api_key,
            error=OpenAIAgentValidationState.api_key_error,
            width="100%",
        ),
        rx.hstack(
            rx.switch(
                name="is_active",
                default_checked=agent.is_active if is_edit_mode else True,
            ),
            rx.text("Aktiv", size="2"),
            margin_top="15px",
        ),
    ]

    return rx.flex(
        *fields,
        direction="column",
        spacing="1",
    )


def add_openai_agent_button() -> rx.Component:
    """Button and dialog for adding a new OpenAI Agent."""
    OpenAIAgentValidationState.initialize()
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus"),
                rx.text(
                    "Neuen Agent anlegen", display=["none", "none", "block"], size="2"
                ),
                size="2",
                variant="solid",
                on_click=[OpenAIAgentValidationState.initialize(agent=None)],
                margin_bottom="15px",
            ),
        ),
        rx.dialog.content(
            dialog_header(
                icon="bot",
                title="Neuen Azure Agent anlegen",
                description="Geben Sie die Details des neuen Agents ein",
            ),
            rx.flex(
                rx.form.root(
                    openai_agent_form_fields(),
                    dialog_buttons(
                        "Agent anlegen",
                        has_errors=OpenAIAgentValidationState.has_errors,
                    ),
                    on_submit=OpenAIAgentState.add_agent,
                    reset_on_submit=False,
                ),
                width="100%",
                direction="column",
                spacing="4",
            ),
            class_name="dialog",
        ),
    )


def delete_openai_agent_dialog(agent: OpenAIAgent) -> rx.Component:
    """Use the generic delete dialog component for OpenAI Agents."""
    return delete_dialog(
        title="Azure Agent löschen",
        content=agent.name,
        on_click=lambda: OpenAIAgentState.delete_agent(agent.id),
        icon_button=True,
        size="2",
        variant="ghost",
        color_scheme="crimson",
    )


def update_openai_agent_dialog(agent: OpenAIAgent) -> rx.Component:
    """Dialog for updating an existing OpenAI Agent."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.icon_button(
                rx.icon("square-pen", size=20),
                size="2",
                variant="ghost",
                on_click=[
                    lambda: OpenAIAgentState.get_agent(agent.id),
                    OpenAIAgentValidationState.initialize(agent),
                ],
            ),
        ),
        rx.dialog.content(
            dialog_header(
                icon="bot",
                title="OpenAI Agent aktualisieren",
                description="Aktualisieren Sie die Details des Agents",
            ),
            rx.flex(
                rx.form.root(
                    openai_agent_form_fields(agent),
                    dialog_buttons(
                        "Agent aktualisieren",
                        has_errors=OpenAIAgentValidationState.has_errors,
                    ),
                    on_submit=OpenAIAgentState.modify_agent,
                    reset_on_submit=False,
                ),
                width="100%",
                direction="column",
                spacing="4",
            ),
            class_name="dialog",
        ),
    )
