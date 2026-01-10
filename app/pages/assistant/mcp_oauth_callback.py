"""MCP OAuth callback page and state.

Handles OAuth redirects from MCP server identity providers.
"""

import contextlib
import logging
from collections.abc import AsyncGenerator

import reflex as rx
from sqlmodel import Session, select

from appkit_assistant.backend.mcp_auth_service import MCPAuthService
from appkit_assistant.backend.models import MCPServer
from appkit_commons.configuration.configuration import ReflexConfig
from appkit_commons.database.session import get_session_manager
from appkit_commons.registry import service_registry
from appkit_user.authentication.backend.entities import OAuthStateEntity
from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)

# OAuth callback path - must match registered redirect URIs
MCP_OAUTH_CALLBACK_PATH = "/assistant/mcp/callback"


def build_mcp_oauth_redirect_uri() -> str:
    """Build the MCP OAuth redirect URI from configuration."""
    reflex_config: ReflexConfig | None = service_registry().get(ReflexConfig)
    if reflex_config:
        base_url = reflex_config.deploy_url
        port = reflex_config.frontend_port
        # Only add port if not standard (80 for http, 443 for https)
        if port and port not in (80, 443):
            return f"{base_url}:{port}{MCP_OAUTH_CALLBACK_PATH}"
        return f"{base_url}{MCP_OAUTH_CALLBACK_PATH}"
    # Fallback for development
    return f"http://localhost:8080{MCP_OAUTH_CALLBACK_PATH}"


class MCPOAuthState(rx.State):
    """State for handling MCP OAuth callbacks."""

    # UI state
    status: str = "processing"  # processing, success, error
    message: str = "Verarbeite Anmeldung..."
    server_name: str = ""

    # Stored from URL params
    _code: str = ""
    _state: str = ""
    _server_id: int | None = None

    @rx.event
    async def handle_mcp_oauth_callback(self) -> AsyncGenerator:
        """Handle the OAuth callback from an MCP server's identity provider."""
        # Get query params from router (using new router.url API)
        params = self.router.url.query_parameters
        code = params.get("code", "")
        state = params.get("state", "")
        server_id_str = params.get("server_id", "")

        logger.info(
            "MCP OAuth callback - params: %s, code: '%s', state: '%s', server_id: '%s'",
            params,
            code[:20] if code else "None",
            state,
            server_id_str,
        )

        if not code:
            self.status = "error"
            self.message = "Kein Autorisierungscode erhalten."
            yield
            return

        # If server_id is missing, try to recover it from state
        if not server_id_str and state:
            with get_session_manager().session() as session:
                oauth_state = (
                    session.execute(
                        select(OAuthStateEntity).where(OAuthStateEntity.state == state)
                    )
                    .scalars()
                    .first()
                )
                logger.info(
                    "OAuth state lookup - found: %s, provider: %s",
                    oauth_state is not None,
                    oauth_state.provider if oauth_state else "N/A",
                )
                if oauth_state and oauth_state.provider.startswith("mcp:"):
                    with contextlib.suppress(IndexError):
                        server_id_str = oauth_state.provider.split(":")[1]
                        logger.debug(
                            "Recovered server_id from state: %s", server_id_str
                        )

        if not server_id_str:
            self.status = "error"
            self.message = "Server-ID fehlt."
            yield
            return

        try:
            server_id = int(server_id_str)
        except ValueError:
            self.status = "error"
            self.message = "Ungültige Server-ID."
            yield
            return

        self._code = code
        self._state = state
        self._server_id = server_id

        # Get the server configuration
        with rx.session() as session:
            server = session.exec(
                select(MCPServer).where(MCPServer.id == server_id)
            ).first()

            if not server:
                self.status = "error"
                self.message = "Server nicht gefunden."
                yield
                return

            self.server_name = server.name

            # Get user ID from auth state
            user_id = await self._get_current_user_id()
            if not user_id:
                self.status = "error"
                self.message = "Nicht angemeldet."
                yield
                return

            # Exchange code for tokens - inline the logic to avoid yield from
            async for result in self._do_token_exchange(
                session, server, user_id, code, self._state
            ):
                yield result

    async def _do_token_exchange(
        self,
        session: Session,
        server: MCPServer,
        user_id: int,
        code: str,
        state: str,
    ) -> AsyncGenerator:
        """Exchange the authorization code for tokens."""
        redirect_uri = self._build_redirect_uri()
        auth_service = MCPAuthService(redirect_uri=redirect_uri)

        try:
            result = await auth_service.exchange_code_for_tokens(
                server, code, state=state, session=session
            )

            if result.error:
                self.status = "error"
                self.message = (
                    f"Token-Austausch fehlgeschlagen: {result.error_description}"
                )
                yield
                return

            # Save the token
            auth_service.save_user_token(
                session,
                user_id,
                server.id,  # type: ignore
                result,
            )

            self.status = "success"
            self.message = f"Erfolgreich mit {server.name} verbunden!"
            yield

            # Notify parent window via localStorage (works across windows)
            # Include user_id for security - prevents cross-user leakage
            server_id_str = str(server.id)
            logger.debug(
                "OAuth success - notifying via localStorage: "
                "server_id=%s, name=%s, user_id=%s",
                server_id_str,
                server.name,
                user_id,
            )
            script = f"""
                console.log('[OAuth] Setting localStorage for cross-window sync');
                var data = JSON.stringify({{
                    type: 'mcp-oauth-success',
                    serverId: '{server_id_str}',
                    serverName: '{server.name}',
                    userId: '{user_id}',
                    timestamp: Date.now()
                }});
                localStorage.setItem('mcp-oauth-result', data);
                console.log('[OAuth] localStorage set:', data);
                // Also try postMessage for same-origin popups
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'mcp-oauth-success',
                        serverId: '{server_id_str}',
                        serverName: '{server.name}',
                        userId: '{user_id}'
                    }}, '*');
                }}
                setTimeout(function() {{ window.close(); }}, 500);
            """
            yield rx.call_script(script)

        except Exception as e:
            logger.exception("Token exchange failed")
            self.status = "error"
            self.message = f"Fehler: {e!s}"
            yield

        finally:
            await auth_service.close()

    async def _get_current_user_id(self) -> int | None:
        """Get the current user's ID from auth state."""
        auth_state = await self.get_state(UserSession)
        # Verify authentication status to ensure user_id is populated from session token
        await auth_state.authenticated_user
        if auth_state.user_id and auth_state.user_id > 0:
            return auth_state.user_id
        return None

    def _build_redirect_uri(self) -> str:
        """Build the OAuth redirect URI from configuration.

        Uses the same configuration-based URL as the authorization request
        to ensure redirect_uri matches exactly.
        """
        return build_mcp_oauth_redirect_uri()


def mcp_oauth_callback_content() -> rx.Component:
    """Content for the MCP OAuth callback page."""
    return rx.center(
        rx.card(
            rx.vstack(
                rx.cond(
                    MCPOAuthState.status == "processing",
                    rx.fragment(
                        rx.spinner(size="3"),
                        rx.text(MCPOAuthState.message, size="3"),
                    ),
                    rx.cond(
                        MCPOAuthState.status == "success",
                        rx.fragment(
                            rx.icon("circle-check", size=48, color="green"),
                            rx.text(MCPOAuthState.message, size="3", weight="medium"),
                            rx.text(
                                "Dieses Fenster wird automatisch geschlossen.",
                                size="2",
                                color="gray",
                            ),
                        ),
                        rx.fragment(
                            rx.icon("circle-alert", size=48, color="red"),
                            rx.text(MCPOAuthState.message, size="3", weight="medium"),
                            rx.button(
                                "Fenster schließen",
                                on_click=rx.call_script("window.close()"),
                                variant="soft",
                            ),
                        ),
                    ),
                ),
                align="center",
                spacing="4",
                padding="6",
            ),
            size="3",
        ),
        height="100vh",
    )


@rx.page(
    route="/assistant/mcp/callback",
    title="MCP Verbindung",
    on_load=MCPOAuthState.handle_mcp_oauth_callback,
)
def mcp_oauth_callback_page() -> rx.Component:
    """MCP OAuth callback page."""
    return rx.theme(
        mcp_oauth_callback_content(),
        has_background=True,
    )
