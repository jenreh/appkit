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
from appkit_assistant.roles import ASSISTANT_USER_ROLE
from appkit_assistant.state.mcp_server_state import MCPServerState
from appkit_ui.components.dialogs import (
    delete_dialog,
)
from appkit_ui.components.form_inputs import form_field

logger = logging.getLogger(__name__)

AUTH_TYPE_API_KEY = "api_key"
AUTH_TYPE_OAUTH = "oauth"

# Validation constants
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 200
MAX_PROMPT_LENGTH = 2000
MIN_NAME_LENGTH = 3


class ValidationState(rx.State):
    """State for validating MCP server form inputs."""

    url: str = ""
    name: str = ""
    description: str = ""
    prompt: str = ""
    required_role: str = ASSISTANT_USER_ROLE.name
    active: bool = False

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

    # Validation errors
    url_error: str = ""
    name_error: str = ""
    description_error: str = ""
    prompt_error: str = ""
    oauth_client_id_error: str = ""
    oauth_client_secret_error: str = ""

    @rx.event
    def initialize(self, server: MCPServer | None = None) -> None:
        """Reset validation state with optional server data."""
        logger.debug("Initializing ValidationState")
        self._reset_errors()

        if server is None:
            self._reset_fields()
        else:
            self._load_server_data(server)

    def _reset_errors(self) -> None:
        """Clear all validation errors."""
        self.url_error = ""
        self.name_error = ""
        self.description_error = ""
        self.prompt_error = ""
        self.oauth_client_id_error = ""
        self.oauth_client_secret_error = ""

    def _reset_fields(self) -> None:
        """Reset all form fields to default values."""
        self.url = ""
        self.name = ""
        self.description = ""
        self.prompt = ""
        self.required_role = ASSISTANT_USER_ROLE.name
        self.auth_type = AUTH_TYPE_API_KEY
        self.oauth_client_id = ""
        self.oauth_client_secret = ""
        self.oauth_issuer = ""
        self.oauth_authorize_url = ""
        self.oauth_token_url = ""
        self.oauth_scopes = ""

    def _load_server_data(self, server: MCPServer) -> None:
        """Load data from an existing server."""
        self.url = server.url
        self.name = server.name
        self.description = server.description
        self.prompt = server.prompt or ""
        self.active = server.active
        self.required_role = server.required_role or ASSISTANT_USER_ROLE.name

        # Load OAuth configuration
        if server.oauth_client_id:
            self.auth_type = AUTH_TYPE_OAUTH
            self.oauth_client_id = server.oauth_client_id
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

    @rx.event
    async def set_auth_type(self, auth_type: str) -> AsyncGenerator[Any, Any]:
        """Set the authentication type and trigger discovery if needed."""
        self.auth_type = auth_type

        if auth_type == AUTH_TYPE_API_KEY:
            self.oauth_client_id_error = ""
            self.oauth_client_secret_error = ""
        elif auth_type == AUTH_TYPE_OAUTH:
            async for event in self.check_discovery():
                yield event

    @rx.event
    def validate_url(self) -> None:
        """Validate the URL field."""
        if not self.url or not self.url.strip():
            self.url_error = "Die URL darf nicht leer sein."
        elif not self.url.startswith(("http://", "https://")):
            self.url_error = "Die URL muss mit http:// oder https:// beginnen."
        else:
            self.url_error = ""

    @rx.event
    def validate_name(self) -> None:
        """Validate the name field."""
        if not self.name or not self.name.strip():
            self.name_error = "Der Name darf nicht leer sein."
        elif len(self.name) < MIN_NAME_LENGTH:
            self.name_error = (
                f"Der Name muss mindestens {MIN_NAME_LENGTH} Zeichen lang sein."
            )
        else:
            self.name_error = ""

    @rx.event
    def validate_description(self) -> None:
        """Validate the description field."""
        if not self.description or not self.description.strip():
            self.description_error = "Die Beschreibung darf nicht leer sein."
        elif len(self.description) > MAX_DESCRIPTION_LENGTH:
            self.description_error = (
                f"Die Beschreibung darf maximal {MAX_DESCRIPTION_LENGTH}"
                " Zeichen lang sein."
            )
        else:
            self.description_error = ""

    @rx.event
    def validate_prompt(self) -> None:
        """Validate the prompt field."""
        if self.prompt and len(self.prompt) > MAX_PROMPT_LENGTH:
            self.prompt_error = (
                f"Die Anweisung darf maximal {MAX_PROMPT_LENGTH} Zeichen lang sein."
            )
        else:
            self.prompt_error = ""

    @rx.event
    def validate_oauth_client_id(self) -> None:
        """Validate the OAuth client ID field."""
        self.oauth_client_id_error = ""

    @rx.event
    def validate_oauth_client_secret(self) -> None:
        """Validate the OAuth client secret field."""
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
        return 2000 - len(self.prompt or "")  # noqa: PLR2004

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
        self.description = description
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

    def set_required_role(self, role: str) -> None:
        """Set the required role for accessing this MCP server."""
        self.required_role = role

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
    return mn.radio.group(
        mn.group(
            mn.radio(value=AUTH_TYPE_API_KEY, label="HTTP Headers"),
            mn.radio(value=AUTH_TYPE_OAUTH, label="OAuth 2.0"),
        ),
        value=ValidationState.auth_type,
        on_change=ValidationState.set_auth_type,
        name="auth_type",
        mb="12px",
    )


def _api_key_auth_fields(server: MCPServer | None = None) -> rx.Component:
    """Fields for API key / HTTP headers authentication."""
    headers_default = json(server.headers) if server is not None else "{}"

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
            default_value=headers_default,
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
                autocomplete="one-time-code",
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
                autocomplete="new-password",
            ),
            rx.heading("OAuth Endpunkte & Scopes", size="3", margin_top="12px"),
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
            width="100%",
        ),
        # Hidden field for non-OAuth mode
        rx.el.input(
            type="hidden",
            name="auth_type",
            value=MCPAuthType.API_KEY,
        ),
    )


def _role_select() -> rx.Component:
    """Role selection dropdown for MCP server access control."""
    return mn.select(
        label="Erforderliche Rolle",
        description="Nur Benutzer mit dieser Rolle können den MCP Server verwenden.",
        data=MCPServerState.available_roles,
        value=ValidationState.required_role,
        on_change=ValidationState.set_required_role,
        placeholder="Rolle auswählen",
        name="required_role",
        width="100%",
        mb="12px",
    )


def _prompt_field(server: MCPServer | None = None) -> rx.Component:
    """Reusable prompt textarea with character count."""
    is_edit_mode = server is not None
    return rx.flex(
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
                mn.text(
                    f"{ValidationState.prompt_remaining}/2000",
                    size="xs",
                    c="dimmed",
                ),
                mn.text(
                    f"{ValidationState.prompt_remaining}/2000",
                    size="xs",
                    c="red",
                    fw="bold",
                ),
            ),
            justify="end",
            width="100%",
            margin_top="4px",
        ),
        direction="column",
        spacing="0",
        width="100%",
        my="3px",
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
            max_length=MAX_NAME_LENGTH,
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
            max_length=MAX_DESCRIPTION_LENGTH,
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
        _prompt_field(server),
        mn.divider(label="Berechtigung", my="md"),
        _role_select(),
        mn.divider(label="Authentifizierung", my="md"),
        _auth_type_selector(),
        _api_key_auth_fields(server),
        _oauth_auth_fields(server),
    ]

    return rx.flex(
        *fields,
        direction="column",
    )


def _modal_footer(
    submit_label: str,
    on_cancel: rx.EventHandler,
) -> rx.Component:
    """Footer buttons for add/edit modals."""
    return rx.flex(
        mn.button(
            "Abbrechen",
            variant="subtle",
            on_click=on_cancel,
        ),
        mn.button(
            submit_label,
            type="submit",
            disabled=ValidationState.has_errors,
            loading=MCPServerState.loading,
        ),
        direction="row",
        gap="9px",
        justify_content="end",
        padding="16px",
        border_top="1px solid var(--mantine-color-default-border)",
        background="var(--mantine-color-body)",
        width="100%",
    )


def _mcp_server_modal(
    title: str,
    opened: bool | rx.Var,
    on_close: rx.EventHandler,
    on_submit: rx.EventHandler,
    submit_label: str,
    fields: rx.Component,
) -> rx.Component:
    """Shared modal structure for add/edit MCP server."""
    return mn.modal(
        rx.form.root(
            rx.flex(
                mn.scroll_area.autosize(
                    fields,
                    max_height="60vh",
                    width="100%",
                    type="always",
                    offset_scrollbars=True,
                ),
                _modal_footer(submit_label, on_close),
                direction="column",
            ),
            on_submit=on_submit,
            reset_on_submit=False,
            height="100%",
        ),
        title=title,
        opened=opened,
        on_close=on_close,
        size="lg",
        centered=True,
        overlay_props={"backgroundOpacity": 0.5, "blur": 4},
    )


def add_mcp_server_button() -> rx.Component:
    """Button to open the add MCP server modal."""
    return mn.button(
        "Neuen MCP Server anlegen",
        left_section=rx.icon("plus", size=16),
        size="sm",
        loading=MCPServerState.opening_add_modal,
        on_click=[
            ValidationState.initialize(None),
            MCPServerState.open_add_modal,
        ],
    )


def add_mcp_server_modal() -> rx.Component:
    """Modal for adding a new MCP server."""
    return _mcp_server_modal(
        title="Neuen MCP Server anlegen",
        opened=MCPServerState.add_modal_open,
        on_close=MCPServerState.close_add_modal,
        on_submit=MCPServerState.add_server,
        submit_label="MCP Server anlegen",
        fields=mcp_server_form_fields(),
    )


def edit_mcp_server_modal() -> rx.Component:
    """Modal for editing an existing MCP server."""
    return _mcp_server_modal(
        title="MCP Server aktualisieren",
        opened=MCPServerState.edit_modal_open,
        on_close=MCPServerState.close_edit_modal,
        on_submit=MCPServerState.modify_server,
        submit_label="MCP Server aktualisieren",
        fields=mcp_server_form_fields(MCPServerState.current_server),
    )


def delete_mcp_server_dialog(server: MCPServer) -> rx.Component:
    """Use the generic delete dialog component for MCP servers."""
    return delete_dialog(
        title="MCP Server löschen",
        content=server.name,
        on_click=lambda: MCPServerState.delete_server(server.id),
        icon_button=True,
        variant="subtle",
        color="red",
    )


def update_mcp_server_dialog(server: MCPServer) -> rx.Component:
    """Dialog trigger button for updating an existing MCP server."""
    return mn.action_icon(
        rx.icon("square-pen", size=19),
        variant="subtle",
        color="gray",
        loading=MCPServerState.opening_edit_server_id == server.id,
        on_click=[
            ValidationState.initialize(server),
            MCPServerState.open_edit_modal(server.id),
        ],
        margin="0",
    )
