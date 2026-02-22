"""MCP OAuth Authentication Service.

Handles OAuth 2.0 flows for MCP servers including:
- Discovery of OAuth metadata via RFC 8414
- Authorization URL construction with PKCE support
- Token exchange (authorization code for tokens)
- Token refresh
- Token storage and retrieval
"""

import base64
import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from urllib.parse import urlencode, urlparse

import httpx
from sqlmodel import Session, select

from appkit_assistant.backend.database.models import (
    AssistantMCPUserToken,
    MCPServer,
)
from appkit_assistant.backend.schemas import (
    MCPAuthType,
)
from appkit_user.authentication.backend.database.entities import OAuthStateEntity

logger = logging.getLogger(__name__)

# Discovery paths per RFC 8414
WELL_KNOWN_PATHS = [
    "/.well-known/oauth-authorization-server",
    "/.well-known/openid-configuration",
]


def _generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge (S256).

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    # Generate code verifier (43-128 characters)
    code_verifier = (
        base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")
    )

    # Generate code challenge (SHA256 hash of verifier)
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest())
        .decode("utf-8")
        .rstrip("=")
    )

    return code_verifier, code_challenge


@dataclass
class OAuthDiscoveryResult:
    """Result of OAuth metadata discovery."""

    issuer: str | None = None
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None
    registration_endpoint: str | None = None
    scopes_supported: list[str] | None = None
    error: str | None = None


@dataclass
class ClientRegistrationResult:
    """Result of OAuth Dynamic Client Registration (RFC 7591)."""

    client_id: str | None = None
    client_secret: str | None = None
    client_id_issued_at: int | None = None
    client_secret_expires_at: int | None = None
    error: str | None = None
    error_description: str | None = None


@dataclass
class TokenResult:
    """Result of token exchange or refresh."""

    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    token_type: str | None = None
    scope: str | None = None
    error: str | None = None
    error_description: str | None = None


class MCPAuthService:
    """Service for handling MCP OAuth authentication flows."""

    def __init__(self, redirect_uri: str) -> None:
        """Initialize the service.

        Args:
            redirect_uri: The OAuth redirect URI for the callback endpoint.
        """
        self.redirect_uri = redirect_uri
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def discover_oauth_config(self, server_url: str) -> OAuthDiscoveryResult:
        """Discover OAuth metadata from the server.

        Attempts to fetch OAuth metadata from well-known endpoints per RFC 8414.

        Args:
            server_url: The MCP server URL to discover OAuth config from.

        Returns:
            OAuthDiscoveryResult with discovered endpoints or error.
        """
        client = await self._get_client()
        parsed = urlparse(server_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        for path in WELL_KNOWN_PATHS:
            discovery_url = f"{base_url}{path}"
            logger.debug("Attempting OAuth discovery at: %s", discovery_url)

            try:
                response = await client.get(discovery_url)
                if response.status_code == HTTPStatus.OK:
                    data = response.json()
                    return OAuthDiscoveryResult(
                        issuer=data.get("issuer"),
                        authorization_endpoint=data.get("authorization_endpoint"),
                        token_endpoint=data.get("token_endpoint"),
                        registration_endpoint=data.get("registration_endpoint"),
                        scopes_supported=data.get("scopes_supported"),
                    )
            except httpx.RequestError as e:
                logger.debug("Discovery failed at %s: %s", discovery_url, str(e))
                continue
            except Exception as e:
                logger.warning("Unexpected error during discovery: %s", str(e))
                continue

        return OAuthDiscoveryResult(
            error="OAuth discovery failed: No valid metadata found at well-known paths"
        )

    async def register_client(
        self,
        registration_endpoint: str,
        client_name: str = "AppKit Assistant",
        additional_redirect_uris: list[str] | None = None,
    ) -> ClientRegistrationResult:
        """Register a new OAuth client via Dynamic Client Registration (RFC 7591).

        Some OAuth providers like Atlassian MCP require clients to register
        dynamically before they can authenticate.

        Args:
            registration_endpoint: The OAuth registration endpoint URL.
            client_name: The name to register the client with.
            additional_redirect_uris: Additional redirect URIs to register.

        Returns:
            ClientRegistrationResult with client_id and optionally client_secret.
        """
        client = await self._get_client()

        redirect_uris = [self.redirect_uri]
        if additional_redirect_uris:
            redirect_uris.extend(additional_redirect_uris)

        # Client metadata per RFC 7591
        client_metadata = {
            "client_name": client_name,
            "redirect_uris": redirect_uris,
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",  # Public client (no secret)
        }

        logger.debug(
            "Registering OAuth client at %s with metadata: %s",
            registration_endpoint,
            client_metadata,
        )

        try:
            response = await client.post(
                registration_endpoint,
                json=client_metadata,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
                data = response.json()
                logger.debug(
                    "Successfully registered OAuth client: %s",
                    data.get("client_id"),
                )
                return ClientRegistrationResult(
                    client_id=data.get("client_id"),
                    client_secret=data.get("client_secret"),
                    client_id_issued_at=data.get("client_id_issued_at"),
                    client_secret_expires_at=data.get("client_secret_expires_at"),
                )

            # Handle error response
            try:
                error_data = response.json()
                return ClientRegistrationResult(
                    error=error_data.get("error", "registration_failed"),
                    error_description=error_data.get(
                        "error_description",
                        f"HTTP {response.status_code}: {response.text}",
                    ),
                )
            except Exception:
                return ClientRegistrationResult(
                    error="registration_failed",
                    error_description=f"HTTP {response.status_code}: {response.text}",
                )

        except httpx.RequestError as e:
            logger.error("Client registration request failed: %s", str(e))
            return ClientRegistrationResult(
                error="request_failed",
                error_description=str(e),
            )

    async def build_authorization_url_with_registration(
        self,
        server: MCPServer,
        state: str | None = None,
        session: Session | None = None,
        user_id: int | None = None,
    ) -> tuple[str, str]:
        """Build the OAuth authorization URL, registering client via DCR if needed.

        This method will automatically discover OAuth config and perform Dynamic
        Client Registration (RFC 7591) if the server has no client_id configured
        and a registration_endpoint is available.

        Args:
            server: The MCP server configuration.
            state: Optional state parameter. If not provided, a random one is generated.
            session: DB Session for storing PKCE state and updating server config.
            user_id: User ID for binding state.

        Returns:
            Tuple of (authorization_url, state) where state should be stored
            for verification.
        """
        # Ensure we work with a session-attached object to avoid StateProxy issues
        # and to allow persisting changes if DCR happens.
        if session and server.id:
            db_server = session.get(MCPServer, server.id)
            if db_server:
                server = db_server

        # If no client_id, attempt Dynamic Client Registration
        if not server.oauth_client_id:
            logger.debug(
                "No client_id for server %s, attempting DCR",
                server.name,
            )

            # Discover OAuth config to find registration endpoint
            discovery_result = await self.discover_oauth_config(server.url)

            if discovery_result.error:
                msg = f"OAuth discovery failed: {discovery_result.error}"
                raise ValueError(msg)

            if not discovery_result.registration_endpoint:
                msg = "Server has no client ID and no registration endpoint available"
                raise ValueError(msg)

            # Perform Dynamic Client Registration
            reg_result = await self.register_client(
                registration_endpoint=discovery_result.registration_endpoint,
                client_name="AppKit Assistant",
            )

            if reg_result.error:
                msg = (
                    f"Client registration failed: "
                    f"{reg_result.error}: {reg_result.error_description}"
                )
                raise ValueError(msg)

            if not reg_result.client_id:
                msg = "Client registration succeeded but no client_id returned"
                raise ValueError(msg)

            # Update server with registered client_id
            server.oauth_client_id = reg_result.client_id
            if reg_result.client_secret:
                server.oauth_client_secret = reg_result.client_secret

            # Also update discovered endpoints if not already set
            auth_endpoint = discovery_result.authorization_endpoint
            if not server.oauth_authorize_url and auth_endpoint:
                server.oauth_authorize_url = auth_endpoint
            if not server.oauth_token_url and discovery_result.token_endpoint:
                server.oauth_token_url = discovery_result.token_endpoint

            # Persist updated server configuration
            if session:
                session.add(server)
                try:
                    session.commit()
                    logger.debug(
                        "Persisted DCR client_id %s for server %s",
                        reg_result.client_id,
                        server.name,
                    )
                except Exception as e:
                    logger.error("Failed to persist DCR client_id: %s", e)
                    session.rollback()

        # Now delegate to the synchronous URL builder
        return self.build_authorization_url(
            server=server,
            state=state,
            session=session,
            user_id=user_id,
        )

    def build_authorization_url(
        self,
        server: MCPServer,
        state: str | None = None,
        session: Session | None = None,
        user_id: int | None = None,
    ) -> tuple[str, str]:
        """Build the OAuth authorization URL for user login.

        Supports PKCE by generating code_verifier and storing it if a session is
        provided.

        Args:
            server: The MCP server configuration.
            state: Optional state parameter. If not provided, a random one is generated.
            session: DB Session for storing PKCE state.
            user_id: User ID for binding state.

        Returns:
            Tuple of (authorization_url, state) where state should be stored
            for verification.
        """
        if not server.oauth_authorize_url:
            msg = "Server has no authorization URL configured"
            raise ValueError(msg)

        if state is None:
            state = secrets.token_urlsafe(32)
            logger.info("Generated new OAuth state: %s", state)

        if not server.oauth_client_id:
            msg = "Server has no client ID configured"
            raise ValueError(msg)

        # Generate PKCE parameters (required by OAuth 2.1 / MCP servers)
        code_verifier, code_challenge = _generate_pkce_pair()

        params = {
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "state": state,
            "client_id": server.oauth_client_id,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        # Store state in DB for CSRF protection, server mapping, and PKCE verifier
        if session:
            provider_key = f"mcp:{server.id}" if server.id else "mcp:unknown"
            logger.info(
                "Saving OAuth state to DB: state=%s, provider=%s, user_id=%s",
                state,
                provider_key,
                user_id,
            )
            oauth_state = OAuthStateEntity(
                session_id="mcp_auth_flow",
                state=state,
                provider=provider_key,
                code_verifier=code_verifier,
                expires_at=datetime.now(UTC) + timedelta(minutes=10),
                user_id=user_id,
            )
            session.add(oauth_state)
            try:
                session.commit()
                logger.info("OAuth state committed successfully: %s", state)
            except Exception as e:
                logger.error("Failed to commit OAuth state: %s", e)
                session.rollback()
        else:
            logger.warning(
                "No DB session provided to build_authorization_url. "
                "PKCE and state check will fail."
            )

        if server.oauth_scopes:
            params["scope"] = server.oauth_scopes

        auth_url = f"{server.oauth_authorize_url}?{urlencode(params)}"
        logger.debug(
            "build_authorization_url: base=%s, result=%s",
            server.oauth_authorize_url,
            auth_url,
        )
        return auth_url, state

    async def exchange_code_for_tokens(  # noqa: PLR0911
        self,
        server: MCPServer,
        code: str,
        state: str | None = None,
        session: Session | None = None,
    ) -> TokenResult:
        """Exchange authorization code for access and refresh tokens.

        Args:
            server: The MCP server configuration.
            code: The authorization code received from the callback.
            state: The state parameter from the callback (required for PKCE).
            session: DB Session for retrieving PKCE verifier.

        Returns:
            TokenResult with tokens or error information.
        """
        if not server.oauth_token_url:
            return TokenResult(error="no_token_url", error_description="No token URL")

        client = await self._get_client()

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        if not server.oauth_client_id:
            logger.error("Missing client_id for server %s", server.name)
            return TokenResult(
                error="config_missing",
                error_description="Client ID missing in server configuration",
            )

        data["client_id"] = server.oauth_client_id

        # Helper to get session from manager if not provided
        # (Though arguments type hint says session is Optional,
        # we expect it for state check)

        # Check OAuth state (CSRF) and retrieve PKCE code_verifier
        code_verifier: str | None = None
        if state and session:
            provider_key = f"mcp:{server.id}" if server.id else "mcp:unknown"
            oauth_state = session.exec(
                select(OAuthStateEntity).where(
                    OAuthStateEntity.state == state,
                    OAuthStateEntity.provider == provider_key,
                )
            ).first()

            if oauth_state:
                if oauth_state.expires_at < datetime.now(UTC):
                    logger.warning("OAuth state expired for state %s", state)
                    return TokenResult(
                        error="invalid_grant",
                        error_description="OAuth state expired or invalid",
                    )

                # Retrieve PKCE code_verifier before cleanup
                code_verifier = oauth_state.code_verifier

                # Clean up used state
                session.delete(oauth_state)
                session.commit()
            else:
                logger.warning("No OAuth state found for state %s.", state)

        # Add PKCE code_verifier if available (required by providers like Atlassian)
        if code_verifier:
            data["code_verifier"] = code_verifier

        if server.oauth_client_secret:
            data["client_secret"] = server.oauth_client_secret

        try:
            response = await client.post(
                server.oauth_token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code == HTTPStatus.OK:
                token_data = response.json()
                return TokenResult(
                    access_token=token_data.get("access_token"),
                    refresh_token=token_data.get("refresh_token"),
                    expires_in=token_data.get("expires_in"),
                    token_type=token_data.get("token_type", "Bearer"),
                    scope=token_data.get("scope"),
                )

            # Handle error response
            try:
                error_data = response.json()
                return TokenResult(
                    error=error_data.get("error", "unknown_error"),
                    error_description=error_data.get(
                        "error_description",
                        f"HTTP {response.status_code}",
                    ),
                )
            except Exception:
                return TokenResult(
                    error="http_error",
                    error_description=f"HTTP {response.status_code}",
                )

        except httpx.RequestError as e:
            logger.error("Token exchange request failed: %s", str(e))
            return TokenResult(
                error="request_failed",
                error_description=str(e),
            )

    async def refresh_access_token(
        self,
        server: MCPServer,
        refresh_token: str,
    ) -> TokenResult:
        """Refresh an access token using a refresh token.

        Args:
            server: The MCP server configuration.
            refresh_token: The refresh token to use.

        Returns:
            TokenResult with new tokens or error information.
        """
        if not server.oauth_token_url:
            return TokenResult(error="no_token_url", error_description="No token URL")

        if not server.oauth_client_id:
            return TokenResult(error="no_client_id", error_description="No client ID")

        client = await self._get_client()

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": server.oauth_client_id,
        }

        if server.oauth_client_secret:
            data["client_secret"] = server.oauth_client_secret

        try:
            response = await client.post(
                server.oauth_token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code == HTTPStatus.OK:
                token_data = response.json()
                return TokenResult(
                    access_token=token_data.get("access_token"),
                    refresh_token=token_data.get("refresh_token", refresh_token),
                    expires_in=token_data.get("expires_in"),
                    token_type=token_data.get("token_type", "Bearer"),
                    scope=token_data.get("scope"),
                )

            try:
                error_data = response.json()
                return TokenResult(
                    error=error_data.get("error", "unknown_error"),
                    error_description=error_data.get(
                        "error_description",
                        f"HTTP {response.status_code}",
                    ),
                )
            except Exception:
                return TokenResult(
                    error="http_error",
                    error_description=f"HTTP {response.status_code}",
                )

        except httpx.RequestError as e:
            logger.error("Token refresh request failed: %s", str(e))
            return TokenResult(
                error="request_failed",
                error_description=str(e),
            )

    # Database operations

    def get_user_token(
        self,
        session: Session,
        user_id: int,
        mcp_server_id: int,
    ) -> AssistantMCPUserToken | None:
        """Get a user's token for an MCP server.

        Args:
            session: Database session.
            user_id: The user's ID.
            mcp_server_id: The MCP server's ID.

        Returns:
            The token record or None if not found.
        """
        statement = select(AssistantMCPUserToken).where(
            AssistantMCPUserToken.user_id == user_id,
            AssistantMCPUserToken.mcp_server_id == mcp_server_id,
        )
        return session.exec(statement).first()

    def save_user_token(
        self,
        session: Session,
        user_id: int,
        mcp_server_id: int,
        token_result: TokenResult,
    ) -> AssistantMCPUserToken:
        """Save or update a user's token for an MCP server.

        Args:
            session: Database session.
            user_id: The user's ID.
            mcp_server_id: The MCP server's ID.
            token_result: The token data from exchange or refresh.

        Returns:
            The saved token record.
        """
        # Calculate expiry
        expires_in = token_result.expires_in or 3600  # Default 1 hour
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

        # Check for existing token
        existing = self.get_user_token(session, user_id, mcp_server_id)

        if existing:
            existing.access_token = token_result.access_token or ""
            if token_result.refresh_token:
                existing.refresh_token = token_result.refresh_token
            existing.expires_at = expires_at
            existing.updated_at = datetime.now(UTC)
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing

        # Create new token
        new_token = AssistantMCPUserToken(
            user_id=user_id,
            mcp_server_id=mcp_server_id,
            access_token=token_result.access_token or "",
            refresh_token=token_result.refresh_token,
            expires_at=expires_at,
        )
        session.add(new_token)
        session.commit()
        session.refresh(new_token)
        return new_token

    def delete_user_token(
        self,
        session: Session,
        user_id: int,
        mcp_server_id: int,
    ) -> bool:
        """Delete a user's token for an MCP server.

        Args:
            session: Database session.
            user_id: The user's ID.
            mcp_server_id: The MCP server's ID.

        Returns:
            True if a token was deleted, False otherwise.
        """
        token = self.get_user_token(session, user_id, mcp_server_id)
        if token:
            session.delete(token)
            session.commit()
            return True
        return False

    def is_token_valid(self, token: AssistantMCPUserToken) -> bool:
        """Check if a token is still valid (not expired).

        Args:
            token: The token to check.

        Returns:
            True if the token is valid, False if expired.
        """
        # Add 30 second buffer for clock skew
        return token.expires_at > datetime.now(UTC) + timedelta(seconds=30)

    async def ensure_valid_token(
        self,
        session: Session,
        server: MCPServer,
        token: AssistantMCPUserToken,
    ) -> AssistantMCPUserToken | None:
        """Ensure a token is valid, refreshing if necessary.

        Args:
            session: Database session.
            server: The MCP server configuration.
            token: The token to validate/refresh.

        Returns:
            A valid token or None if refresh failed.
        """
        if self.is_token_valid(token):
            return token

        # Token expired, try to refresh
        if not token.refresh_token:
            logger.warning("Token expired and no refresh token available")
            return None

        logger.debug("Refreshing expired token for server %s", server.name)
        result = await self.refresh_access_token(server, token.refresh_token)

        if result.error:
            logger.error(
                "Token refresh failed: %s - %s",
                result.error,
                result.error_description,
            )
            return None

        # Save the refreshed token
        return self.save_user_token(
            session,
            token.user_id,
            token.mcp_server_id,
            result,
        )

    def update_server_oauth_config(
        self,
        session: Session,
        server: MCPServer,
        discovery_result: OAuthDiscoveryResult,
    ) -> MCPServer:
        """Update server with discovered OAuth configuration.

        Args:
            session: Database session.
            server: The MCP server to update.
            discovery_result: The discovery result with OAuth metadata.

        Returns:
            The updated server.
        """
        server.oauth_issuer = discovery_result.issuer
        server.oauth_authorize_url = discovery_result.authorization_endpoint
        server.oauth_token_url = discovery_result.token_endpoint
        if discovery_result.scopes_supported:
            server.oauth_scopes = " ".join(discovery_result.scopes_supported)
        server.oauth_discovered_at = datetime.now(UTC)
        server.auth_type = MCPAuthType.OAUTH_DISCOVERY

        session.add(server)
        session.commit()
        session.refresh(server)
        return server
