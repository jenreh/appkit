"""Dialog components for MCP server management."""

import logging
from typing import Any

import reflex as rx
from reflex.vars import var_operation, var_operation_return
from reflex.vars.base import RETURN, CustomVarOperationReturn

import appkit_mantine as mn
from appkit_assistant.backend.models import MCPServer
from appkit_assistant.state.mcp_server_state import MCPServerState
from appkit_ui.components.dialogs import (
    delete_dialog,
    dialog_buttons,
    dialog_header,
)
from appkit_ui.components.form_inputs import form_field

logger = logging.getLogger(__name__)


class ValidationState(rx.State):
    url: str = ""
    name: str = ""
    desciption: str = ""
    prompt: str = ""

    url_error: str = ""
    name_error: str = ""
    description_error: str = ""
    prompt_error: str = ""

    @rx.event
    def initialize(self, server: MCPServer | None = None) -> None:
        """Reset validation state."""
        logger.debug("Initializing ValidationState")
        if server is None:
            self.url = ""
            self.name = ""
            self.desciption = ""
            self.prompt = ""
        else:
            self.url = server.url
            self.name = server.name
            self.desciption = server.description
            self.prompt = server.prompt or ""

        self.url_error = ""
        self.name_error = ""
        self.description_error = ""
        self.prompt_error = ""

    @rx.event
    def validate_url(self) -> None:
        """Validate the URL field."""
        if not self.url or self.url.strip() == "":
            self.url_error = "Die URL darf nicht leer sein."
        elif not self.url.startswith("http://") and not self.url.startswith("https://"):
            self.url_error = "Die URL muss mit http:// oder https:// beginnen."
        else:
            self.url_error = ""

    @rx.event
    def validate_name(self) -> None:
        """Validate the name field."""
        if not self.name or self.name.strip() == "":
            self.name_error = "Der Name darf nicht leer sein."
        elif len(self.name) < 3:  # noqa: PLR2004
            self.name_error = "Der Name muss mindestens 3 Zeichen lang sein."
        else:
            self.name_error = ""

    @rx.event
    def validate_description(self) -> None:
        """Validate the description field."""
        if self.desciption and len(self.desciption) > 200:  # noqa: PLR2004
            self.description_error = (
                "Die Beschreibung darf maximal 200 Zeichen lang sein."
            )
        elif not self.desciption or self.desciption.strip() == "":
            self.description_error = "Die Beschreibung darf nicht leer sein."
        else:
            self.description_error = ""

    @rx.event
    def validate_prompt(self) -> None:
        """Validate the prompt field."""
        if self.prompt and len(self.prompt) > 2000:  # noqa: PLR2004
            self.prompt_error = "Die Anweisung darf maximal 2000 Zeichen lang sein."
        else:
            self.prompt_error = ""

    @rx.var
    def has_errors(self) -> bool:
        """Check if the form can be submitted."""
        return bool(
            self.url_error
            or self.name_error
            or self.description_error
            or self.prompt_error
        )

    @rx.var
    def prompt_remaining(self) -> int:
        """Calculate remaining characters for prompt field."""
        return 2000 - len(self.prompt or "")

    def set_url(self, url: str) -> None:
        """Set the URL and validate it."""
        self.url = url
        self.validate_url()

    def set_name(self, name: str) -> None:
        """Set the name and validate it."""
        self.name = name
        self.validate_name()

    def set_description(self, description: str) -> None:
        """Set the description and validate it."""
        self.desciption = description
        self.validate_description()

    def set_prompt(self, prompt: str) -> None:
        """Set the prompt and validate it."""
        self.prompt = prompt
        self.validate_prompt()


@var_operation
def json(obj: rx.Var, indent: int = 4) -> CustomVarOperationReturn[RETURN]:
    return var_operation_return(
        js_expression=f"JSON.stringify(JSON.parse({obj}), null, {indent})",
        var_type=Any,
    )


def mcp_server_form_fields(server: MCPServer | None = None) -> rx.Component:
    """Reusable form fields for MCP server add/update dialogs."""
    is_edit_mode = server is not None

    fields = [
        form_field(
            name="name",
            icon="server",
            label="Name",
            hint="Eindeutiger Name des MCP-Servers",
            type="text",
            placeholder="MCP-Server Name",
            default_value=server.name if is_edit_mode else "",
            required=True,
            max_length=64,
            on_change=ValidationState.set_name,
            on_blur=ValidationState.validate_name,
            validation_error=ValidationState.name_error,
        ),
        form_field(
            name="description",
            icon="text",
            label="Beschreibung",
            hint=(
                "Kurze Beschreibung zur besseren Identifikation und Auswahl "
                "durch den Nutzer"
            ),
            type="text",
            placeholder="Beschreibung...",
            max_length=200,
            default_value=server.description if is_edit_mode else "",
            required=True,
            on_change=ValidationState.set_description,
            on_blur=ValidationState.validate_description,
            validation_error=ValidationState.description_error,
        ),
        form_field(
            name="url",
            icon="link",
            label="URL",
            hint="Vollständige URL des MCP-Servers (z. B. https://example.com/mcp/v1/sse)",
            type="text",
            placeholder="https://example.com/mcp/v1/sse",
            default_value=server.url if is_edit_mode else "",
            required=True,
            on_change=ValidationState.set_url,
            on_blur=ValidationState.validate_url,
            validation_error=ValidationState.url_error,
        ),
        rx.flex(
            mn.textarea(
                name="prompt",
                label="Prompt",
                description=(
                    "Beschreiben Sie, wie das MCP-Tool verwendet werden soll. "
                    "Dies wird als Ergänzung des Systemprompts im Chat genutzt."
                ),
                placeholder=("Anweidungen an das Modell..."),
                default_value=server.prompt if is_edit_mode else "",
                on_change=ValidationState.set_prompt,
                on_blur=ValidationState.validate_prompt,
                validation_error=ValidationState.prompt_error,
                autosize=True,
                min_rows=3,
                max_rows=8,
                width="100%",
            ),
            rx.flex(
                rx.cond(
                    ValidationState.prompt_remaining >= 0,
                    rx.text(
                        f"{ValidationState.prompt_remaining}/2000",
                        size="1",
                        color="gray",
                    ),
                    rx.text(
                        f"{ValidationState.prompt_remaining}/2000",
                        size="1",
                        color="red",
                        weight="bold",
                    ),
                ),
                justify="end",
                width="100%",
                margin_top="4px",
            ),
            direction="column",
            spacing="0",
            width="100%",
        ),
        mn.form.json(
            name="headers_json",
            label="HTTP Headers",
            description=(
                "Geben Sie die HTTP-Header im JSON-Format ein. "
                'Beispiel: {"Content-Type": "application/json", '
                '"Authorization": "Bearer token"}'
            ),
            placeholder="{}",
            validation_error="Ungültiges JSON",
            default_value=json(server.headers) if is_edit_mode else "{}",
            format_on_blur=True,
            autosize=True,
            min_rows=4,
            max_rows=6,
            width="100%",
        ),
    ]

    return rx.flex(
        *fields,
        direction="column",
        spacing="1",
    )


def add_mcp_server_button() -> rx.Component:
    """Button and dialog for adding a new MCP server."""
    ValidationState.initialize()
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus"),
                rx.text(
                    "Neuen MCP Server anlegen",
                    display=["none", "none", "block"],
                    size="2",
                ),
                size="2",
                variant="solid",
                on_click=[ValidationState.initialize(server=None)],
                margin_bottom="15px",
            ),
        ),
        rx.dialog.content(
            dialog_header(
                icon="server",
                title="Neuen MCP Server anlegen",
                description="Geben Sie die Details des neuen MCP Servers ein",
            ),
            rx.flex(
                rx.form.root(
                    mcp_server_form_fields(),
                    dialog_buttons(
                        "MCP Server anlegen",
                        has_errors=ValidationState.has_errors,
                    ),
                    on_submit=MCPServerState.add_server,
                    reset_on_submit=False,
                ),
                width="100%",
                direction="column",
                spacing="4",
            ),
            class_name="dialog",
        ),
    )


def delete_mcp_server_dialog(server: MCPServer) -> rx.Component:
    """Use the generic delete dialog component for MCP servers."""
    return delete_dialog(
        title="MCP Server löschen",
        content=server.name,
        on_click=lambda: MCPServerState.delete_server(server.id),
        icon_button=True,
        size="2",
        variant="ghost",
        color_scheme="crimson",
    )


def update_mcp_server_dialog(server: MCPServer) -> rx.Component:
    """Dialog for updating an existing MCP server."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.icon_button(
                rx.icon("square-pen", size=20),
                size="2",
                variant="ghost",
                on_click=[
                    lambda: MCPServerState.get_server(server.id),
                    ValidationState.initialize(server),
                ],
            ),
        ),
        rx.dialog.content(
            dialog_header(
                icon="server",
                title="MCP Server aktualisieren",
                description="Aktualisieren Sie die Details des MCP Servers",
            ),
            rx.flex(
                rx.form.root(
                    mcp_server_form_fields(server),
                    dialog_buttons(
                        "MCP Server aktualisieren",
                        has_errors=ValidationState.has_errors,
                    ),
                    on_submit=MCPServerState.modify_server,
                    reset_on_submit=False,
                ),
                width="100%",
                direction="column",
                spacing="4",
            ),
            class_name="dialog",
        ),
    )
