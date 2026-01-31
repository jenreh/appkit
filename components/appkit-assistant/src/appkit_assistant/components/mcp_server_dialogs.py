"""Dialog components for MCP server management."""

import logging
from collections.abc import AsyncGenerator
from typing import Any

import reflex as rx
from reflex.vars import var_operation, var_operation_return
from reflex.vars.base import RETURN, CustomVarOperationReturn

import appkit_mantine as mn
from appkit_assistant.backend.database.models import MCPAuthType, MCPServer
from appkit_assistant.backend.services.mcp_auth_service import MCPAuthService
from appkit_assistant.state.mcp_server_state import MCPServerState
from appkit_ui.components.dialogs import (
    delete_dialog,
    dialog_buttons,
    dialog_header,
)
from appkit_ui.components.form_inputs import form_field

logger = logging.getLogger(__name__)

AUTH_TYPE_API_KEY = "api_key"
AUTH_TYPE_OAUTH = "oauth"


class ValidationState(rx.State):
    url: str = ""
    name: str = ""
    desciption: str = ""
    prompt: str = ""

    # Authentication type selection
    auth_type: str = AUTH_TYPE_API_KEY

    # OAuth fields
    oauth_client_id: str = ""
    oauth_client_secret: str = ""

    # Discovered metadata
    oauth_issuer: str = ""
    oauth_authorize_url: str = ""
    oauth_token_url: str = ""
    oauth_scopes: str = ""

    url_error: str = ""
    name_error: str = ""
    description_error: str = ""
    prompt_error: str = ""
    oauth_client_id_error: str = ""
    oauth_client_secret_error: str = ""

    @rx.event
    def initialize(self, server: MCPServer | None = None) -> None:
        """Reset validation state."""
        logger.debug("Initializing ValidationState")
        if server is None:
            self.url = ""
            self.name = ""
            self.desciption = ""
            self.prompt = ""
            self.auth_type = AUTH_TYPE_API_KEY
            self.oauth_client_id = ""
            self.oauth_client_secret = ""
            self.oauth_issuer = ""
            self.oauth_authorize_url = ""
            self.oauth_token_url = ""
            self.oauth_scopes = ""
        else:
            self.url = server.url
            self.name = server.name
            self.desciption = server.description
            self.prompt = server.prompt or ""
            # Determine auth type from server
            if server.oauth_client_id:
                self.auth_type = AUTH_TYPE_OAUTH
                self.oauth_client_id = server.oauth_client_id or ""
                self.oauth_client_secret = server.oauth_client_secret or ""
            else:
                self.auth_type = AUTH_TYPE_API_KEY
                self.oauth_client_id = ""
                self.oauth_client_secret = ""

            # Load discovered metadata
            self.oauth_issuer = server.oauth_issuer or ""
            self.oauth_authorize_url = server.oauth_authorize_url or ""
            self.oauth_token_url = server.oauth_token_url or ""
            self.oauth_scopes = server.oauth_scopes or ""

        self.url_error = ""
        self.name_error = ""
        self.description_error = ""
        self.prompt_error = ""
        self.oauth_client_id_error = ""
        self.oauth_client_secret_error = ""

    @rx.event
    async def set_auth_type(self, auth_type: str) -> AsyncGenerator[Any, Any]:
        """Set the authentication type."""
        self.auth_type = auth_type
        # Clear OAuth errors when switching to API key mode
        if auth_type == AUTH_TYPE_API_KEY:
            self.oauth_client_id_error = ""
            self.oauth_client_secret_error = ""
        elif auth_type == AUTH_TYPE_OAUTH:
            # Trigger discovery
            async for event in self.check_discovery():
                yield event

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

    @rx.event
    def validate_oauth_client_id(self) -> None:
        """Validate the OAuth client ID field."""
        # Client ID might be optional for some public clients or implicit flows
        # so we don't enforce it strictly here, but warn if missing for standard flows
        self.oauth_client_id_error = ""

    @rx.event
    def validate_oauth_client_secret(self) -> None:
        """Validate the OAuth client secret field."""
        # Client Secret is optional for Public Clients (PKCE)
        self.oauth_client_secret_error = ""

    @rx.var
    def has_errors(self) -> bool:
        """Check if the form can be submitted."""
        base_errors = bool(
            self.url_error
            or self.name_error
            or self.description_error
            or self.prompt_error
        )
        if self.auth_type == AUTH_TYPE_OAUTH:
            return base_errors or bool(
                self.oauth_client_id_error or self.oauth_client_secret_error
            )
        return base_errors

    @rx.var
    def prompt_remaining(self) -> int:
        """Calculate remaining characters for prompt field."""
        return 2000 - len(self.prompt or "")

    @rx.var
    def is_oauth_mode(self) -> bool:
        """Check if OAuth mode is selected."""
        return self.auth_type == AUTH_TYPE_OAUTH

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

    def set_oauth_client_id(self, client_id: str) -> None:
        """Set the OAuth client ID and validate it."""
        self.oauth_client_id = client_id
        self.validate_oauth_client_id()

    def set_oauth_client_secret(self, client_secret: str) -> None:
        """Set the OAuth client secret and validate it."""
        self.oauth_client_secret = client_secret
        self.validate_oauth_client_secret()

    def set_oauth_issuer(self, value: str) -> None:
        """Set the OAuth issuer."""
        self.oauth_issuer = value

    def set_oauth_authorize_url(self, value: str) -> None:
        """Set the OAuth authorization URL."""
        self.oauth_authorize_url = value

    def set_oauth_token_url(self, value: str) -> None:
        """Set the OAuth token URL."""
        self.oauth_token_url = value

    def set_oauth_scopes(self, value: str) -> None:
        """Set the OAuth scopes."""
        self.oauth_scopes = value

    async def check_discovery(self) -> AsyncGenerator[Any, Any]:
        """Check for OAuth configuration at the given URL."""
        if not self.url or self.url_error:
            return

        try:
            # Create a throwaway service just for discovery
            service = MCPAuthService(redirect_uri="")
            result = await service.discover_oauth_config(self.url)
            await service.close()

            if result.error:
                # No OAuth or error - stick to current settings or do nothing
                logger.debug("OAuth discovery failed: %s", result.error)
                return

            # OAuth found! Update state
            self.oauth_issuer = result.issuer or ""
            self.oauth_authorize_url = result.authorization_endpoint or ""
            self.oauth_token_url = result.token_endpoint or ""
            self.oauth_scopes = " ".join(result.scopes_supported or [])

            # Switch to OAuth mode and notify user
            self.auth_type = AUTH_TYPE_OAUTH
            yield rx.toast.success(
                f"OAuth 2.0 Konfiguration gefunden: {self.oauth_issuer}",
                position="top-right",
            )
            # Clear OAuth errors as we just switched and fields are empty
            # (user needs to fill them)
            self.oauth_client_id_error = ""
            self.oauth_client_secret_error = ""

        except Exception as e:
            logger.error("Error during OAuth discovery: %s", e)


@var_operation
def json(obj: rx.Var, indent: int = 4) -> CustomVarOperationReturn[RETURN]:
    return var_operation_return(
        js_expression=f"JSON.stringify(JSON.parse({obj} || '{{}}'), null, {indent})",
        var_type=Any,
    )


def _auth_type_selector() -> rx.Component:
    """Radio for selecting authentication type."""
    return rx.box(
        rx.text("Authentifizierung", size="2", weight="medium", mb="2"),
        rx.radio_group.root(
            rx.flex(
                rx.flex(
                    rx.radio_group.item(value=AUTH_TYPE_API_KEY),
                    rx.text("HTTP Headers", size="2"),
                    align="center",
                    spacing="2",
                ),
                rx.flex(
                    rx.radio_group.item(value=AUTH_TYPE_OAUTH),
                    rx.text("OAuth 2.0", size="2"),
                    align="center",
                    spacing="2",
                ),
                spacing="4",
            ),
            value=ValidationState.auth_type,
            on_change=ValidationState.set_auth_type,
            name="auth_type",
        ),
        width="100%",
        mb="3",
    )


def _api_key_auth_fields(server: MCPServer | None = None) -> rx.Component:
    """Fields for API key / HTTP headers authentication."""
    is_edit_mode = server is not None
    return rx.cond(
        ~ValidationState.is_oauth_mode,
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
        rx.fragment(),
    )


def _oauth_auth_fields(server: MCPServer | None = None) -> rx.Component:
    """Fields for OAuth 2.0 authentication."""
    is_edit_mode = server is not None
    return rx.cond(
        ValidationState.is_oauth_mode,
        rx.flex(
            rx.box(
                rx.callout(
                    "OAuth 2.0 ermöglicht eine sichere Anmeldung über den "
                    "Identitätsanbieter des MCP-Servers. Die OAuth-Endpunkte "
                    "können automatisch ermittelt oder manuell konfiguriert werden.",
                    icon="info",
                    size="1",
                    color="blue",
                ),
                width="100%",
                mb="3",
            ),
            # Primary Fields (Client ID / Secret)
            form_field(
                name="oauth_client_id",
                icon="key",
                label="Client-ID",
                hint="Die OAuth Client-ID (optional für Public Clients)",
                type="text",
                placeholder="client-id-xxx",
                default_value=server.oauth_client_id if is_edit_mode else "",
                value=ValidationState.oauth_client_id,
                required=False,
                on_change=ValidationState.set_oauth_client_id,
                on_blur=ValidationState.validate_oauth_client_id,
                validation_error=ValidationState.oauth_client_id_error,
                autocomplete="off",
            ),
            form_field(
                name="oauth_client_secret",
                icon="lock",
                label="Client-Secret",
                hint="Das OAuth Client-Secret (optional für Public Clients)",
                type="password",
                placeholder="••••••••",
                default_value=server.oauth_client_secret if is_edit_mode else "",
                value=ValidationState.oauth_client_secret,
                required=False,
                on_change=ValidationState.set_oauth_client_secret,
                on_blur=ValidationState.validate_oauth_client_secret,
                validation_error=ValidationState.oauth_client_secret_error,
                autocomplete="off",
            ),
            rx.text("OAuth Endpunkte & Scopes", size="2", weight="medium", mb="1"),
            # Additional Discovery Fields (Editable)
            form_field(
                name="oauth_issuer",
                icon="globe",
                label="Issuer (Aussteller)",
                hint="Die URL des OAuth Identity Providers",
                type="text",
                placeholder="https://auth.example.com",
                default_value=server.oauth_issuer if is_edit_mode else "",
                value=ValidationState.oauth_issuer,
                required=False,
                on_change=ValidationState.set_oauth_issuer,
            ),
            form_field(
                name="oauth_authorize_url",
                icon="arrow-right-left",
                label="Authorization URL",
                hint="Endpoint für den Login-Dialog",
                type="text",
                placeholder="https://auth.example.com/authorize",
                default_value=server.oauth_authorize_url if is_edit_mode else "",
                value=ValidationState.oauth_authorize_url,
                required=False,
                on_change=ValidationState.set_oauth_authorize_url,
            ),
            form_field(
                name="oauth_token_url",
                icon="key-round",
                label="Token URL",
                hint="Endpoint zum Tausch von Code gegen Token",
                type="text",
                placeholder="https://auth.example.com/token",
                default_value=server.oauth_token_url if is_edit_mode else "",
                value=ValidationState.oauth_token_url,
                required=False,
                on_change=ValidationState.set_oauth_token_url,
            ),
            form_field(
                name="oauth_scopes",
                icon="list-checks",
                label="Scopes",
                hint="Berechtigungen (Scopes), durch Leerzeichen getrennt",
                type="text",
                placeholder="openid profile email",
                default_value=server.oauth_scopes if is_edit_mode else "",
                value=ValidationState.oauth_scopes,
                required=False,
                on_change=ValidationState.set_oauth_scopes,
            ),
            # Hidden field to pass auth_type to form submission
            rx.el.input(
                type="hidden",
                name="auth_type",
                value=MCPAuthType.OAUTH_DISCOVERY,
            ),
            direction="column",
            spacing="1",
            width="100%",
        ),
        # Hidden field for non-OAuth mode
        rx.el.input(
            type="hidden",
            name="auth_type",
            value=MCPAuthType.API_KEY,
        ),
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
            on_blur=[ValidationState.validate_url, ValidationState.check_discovery],
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
        # Authentication type selector and conditional fields
        _auth_type_selector(),
        _api_key_auth_fields(server),
        _oauth_auth_fields(server),
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
                    mn.scroll_area(
                        mcp_server_form_fields(server),
                        height="60vh",
                        width="100%",
                    ),
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
