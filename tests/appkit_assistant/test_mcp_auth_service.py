"""Tests for MCPAuthService.

Covers OAuth discovery, dynamic client registration, authorization URL
building with PKCE, token exchange, token refresh, and DB operations.
"""

from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from appkit_assistant.backend.services.mcp_auth_service import (
    ClientRegistrationResult,
    MCPAuthService,
    OAuthDiscoveryResult,
    TokenResult,
    _generate_pkce_pair,
)

# ============================================================================
# _generate_pkce_pair
# ============================================================================


class TestGeneratePkcePair:
    def test_returns_two_strings(self) -> None:
        verifier, challenge = _generate_pkce_pair()
        assert isinstance(verifier, str)
        assert isinstance(challenge, str)

    def test_verifier_sufficient_length(self) -> None:
        verifier, _ = _generate_pkce_pair()
        assert len(verifier) >= 43

    def test_different_each_call(self) -> None:
        v1, _ = _generate_pkce_pair()
        v2, _ = _generate_pkce_pair()
        assert v1 != v2


# ============================================================================
# Dataclasses
# ============================================================================


class TestOAuthDiscoveryResult:
    def test_defaults(self) -> None:
        r = OAuthDiscoveryResult()
        assert r.issuer is None
        assert r.authorization_endpoint is None
        assert r.token_endpoint is None
        assert r.error is None

    def test_with_values(self) -> None:
        r = OAuthDiscoveryResult(
            issuer="https://auth.example.com",
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
        )
        assert r.issuer == "https://auth.example.com"


class TestClientRegistrationResult:
    def test_defaults(self) -> None:
        r = ClientRegistrationResult()
        assert r.client_id is None
        assert r.error is None

    def test_with_values(self) -> None:
        r = ClientRegistrationResult(client_id="abc", client_secret="secret")
        assert r.client_id == "abc"
        assert r.client_secret == "secret"


class TestTokenResult:
    def test_defaults(self) -> None:
        r = TokenResult()
        assert r.access_token is None
        assert r.refresh_token is None
        assert r.error is None

    def test_with_values(self) -> None:
        r = TokenResult(access_token="token", expires_in=3600, token_type="Bearer")
        assert r.access_token == "token"
        assert r.expires_in == 3600


# ============================================================================
# MCPAuthService - initialization
# ============================================================================


class TestMCPAuthServiceInit:
    def test_init(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.example.com/callback")
        assert svc.redirect_uri == "https://app.example.com/callback"

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.example.com/callback")
        await svc._get_client()  # noqa: SLF001
        assert svc._http_client is not None  # noqa: SLF001
        await svc.close()
        assert svc._http_client is None  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_close_when_no_client(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.example.com/callback")
        await svc.close()  # Should not raise


# ============================================================================
# discover_oauth_config
# ============================================================================


class TestDiscoverOAuthConfig:
    @pytest.mark.asyncio
    async def test_success_first_path(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.json.return_value = {
            "issuer": "https://auth.test",
            "authorization_endpoint": "https://auth.test/authorize",
            "token_endpoint": "https://auth.test/token",
            "registration_endpoint": "https://auth.test/register",
            "scopes_supported": ["openid", "profile"],
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        svc._http_client = mock_client  # noqa: SLF001

        result = await svc.discover_oauth_config("https://mcp.test")
        assert result.issuer == "https://auth.test"
        assert result.authorization_endpoint == "https://auth.test/authorize"
        assert result.token_endpoint == "https://auth.test/token"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_not_found_all_paths(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.NOT_FOUND

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        svc._http_client = mock_client  # noqa: SLF001

        result = await svc.discover_oauth_config("https://mcp.test")
        assert result.error is not None
        assert "failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_request_error(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.RequestError("timeout"))
        svc._http_client = mock_client  # noqa: SLF001

        result = await svc.discover_oauth_config("https://mcp.test")
        assert result.error is not None


# ============================================================================
# register_client
# ============================================================================


class TestRegisterClient:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.CREATED
        mock_response.json.return_value = {
            "client_id": "client-123",
            "client_secret": "secret-456",
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._http_client = mock_client  # noqa: SLF001

        result = await svc.register_client("https://auth.test/register")
        assert result.client_id == "client-123"
        assert result.client_secret == "secret-456"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_error_response(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.BAD_REQUEST
        mock_response.json.return_value = {
            "error": "invalid_request",
            "error_description": "Bad redirect URI",
        }
        mock_response.text = "Bad Request"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._http_client = mock_client  # noqa: SLF001

        result = await svc.register_client("https://auth.test/register")
        assert result.error == "invalid_request"

    @pytest.mark.asyncio
    async def test_request_error(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.RequestError("fail"))
        svc._http_client = mock_client  # noqa: SLF001

        result = await svc.register_client("https://auth.test/register")
        assert result.error == "request_failed"


# ============================================================================
# build_authorization_url
# ============================================================================


class TestBuildAuthorizationUrl:
    def test_basic_url(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        server = MagicMock()
        server.oauth_authorize_url = "https://auth.test/authorize"
        server.oauth_client_id = "client-123"
        server.oauth_scopes = None
        server.id = 1

        url, state = svc.build_authorization_url(server, state="test-state")
        assert "https://auth.test/authorize?" in url
        assert "client_id=client-123" in url
        assert "state=test-state" in url
        assert "response_type=code" in url
        assert "code_challenge=" in url
        assert state == "test-state"

    def test_auto_state_generation(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        server = MagicMock()
        server.oauth_authorize_url = "https://auth.test/authorize"
        server.oauth_client_id = "client-123"
        server.oauth_scopes = None
        server.id = 1

        _url, state = svc.build_authorization_url(server)
        assert state is not None
        assert len(state) > 10

    def test_no_authorize_url_raises(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        server = MagicMock()
        server.oauth_authorize_url = None

        with pytest.raises(ValueError, match="authorization URL"):
            svc.build_authorization_url(server)

    def test_no_client_id_raises(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        server = MagicMock()
        server.oauth_authorize_url = "https://auth.test/authorize"
        server.oauth_client_id = None

        with pytest.raises(ValueError, match="client ID"):
            svc.build_authorization_url(server)

    def test_with_scopes(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        server = MagicMock()
        server.oauth_authorize_url = "https://auth.test/authorize"
        server.oauth_client_id = "client-123"
        server.oauth_scopes = "openid profile"
        server.id = 1

        url, _ = svc.build_authorization_url(server)
        assert "scope=openid+profile" in url


# ============================================================================
# exchange_code_for_tokens
# ============================================================================


class TestExchangeCodeForTokens:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        server = MagicMock()
        server.oauth_token_url = "https://auth.test/token"
        server.oauth_client_id = "client-123"
        server.oauth_client_secret = None
        server.id = 1

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.json.return_value = {
            "access_token": "at-123",
            "refresh_token": "rt-456",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._http_client = mock_client  # noqa: SLF001

        result = await svc.exchange_code_for_tokens(server, "auth-code")
        assert result.access_token == "at-123"
        assert result.refresh_token == "rt-456"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_no_token_url(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        server = MagicMock()
        server.oauth_token_url = None

        result = await svc.exchange_code_for_tokens(server, "code")
        assert result.error == "no_token_url"

    @pytest.mark.asyncio
    async def test_no_client_id(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        server = MagicMock()
        server.oauth_token_url = "https://auth.test/token"
        server.oauth_client_id = None
        server.name = "Test"

        result = await svc.exchange_code_for_tokens(server, "code")
        assert result.error == "config_missing"

    @pytest.mark.asyncio
    async def test_error_response(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        server = MagicMock()
        server.oauth_token_url = "https://auth.test/token"
        server.oauth_client_id = "client-123"
        server.oauth_client_secret = None
        server.id = 1

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.BAD_REQUEST
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Code expired",
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._http_client = mock_client  # noqa: SLF001

        result = await svc.exchange_code_for_tokens(server, "code")
        assert result.error == "invalid_grant"

    @pytest.mark.asyncio
    async def test_request_error(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        server = MagicMock()
        server.oauth_token_url = "https://auth.test/token"
        server.oauth_client_id = "client-123"
        server.oauth_client_secret = None
        server.id = 1
        server.name = "Test"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.RequestError("timeout"))
        svc._http_client = mock_client  # noqa: SLF001

        result = await svc.exchange_code_for_tokens(server, "code")
        assert result.error == "request_failed"


# ============================================================================
# refresh_access_token
# ============================================================================


class TestRefreshAccessToken:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        server = MagicMock()
        server.oauth_token_url = "https://auth.test/token"
        server.oauth_client_id = "client-123"
        server.oauth_client_secret = None
        server.name = "Test"

        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.json.return_value = {
            "access_token": "new-at-123",
            "expires_in": 3600,
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._http_client = mock_client  # noqa: SLF001

        result = await svc.refresh_access_token(server, "old-rt")
        assert result.access_token == "new-at-123"
        # refresh_token preserved when not in response
        assert result.refresh_token == "old-rt"

    @pytest.mark.asyncio
    async def test_no_token_url(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        server = MagicMock()
        server.oauth_token_url = None

        result = await svc.refresh_access_token(server, "rt")
        assert result.error == "no_token_url"

    @pytest.mark.asyncio
    async def test_no_client_id(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        server = MagicMock()
        server.oauth_token_url = "https://auth.test/token"
        server.oauth_client_id = None

        result = await svc.refresh_access_token(server, "rt")
        assert result.error == "no_client_id"


# ============================================================================
# is_token_valid
# ============================================================================


class TestIsTokenValid:
    def test_valid_token(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        token = MagicMock()
        token.expires_at = datetime.now(UTC) + timedelta(hours=1)
        assert svc.is_token_valid(token) is True

    def test_expired_token(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        token = MagicMock()
        token.expires_at = datetime.now(UTC) - timedelta(minutes=5)
        assert svc.is_token_valid(token) is False

    def test_token_within_buffer(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        token = MagicMock()
        # Expires in 10 seconds but 30 second buffer
        token.expires_at = datetime.now(UTC) + timedelta(seconds=10)
        assert svc.is_token_valid(token) is False


# ============================================================================
# ensure_valid_token
# ============================================================================


class TestEnsureValidToken:
    @pytest.mark.asyncio
    async def test_valid_token_returned_as_is(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        token = MagicMock()
        token.expires_at = datetime.now(UTC) + timedelta(hours=1)
        session = MagicMock()
        server = MagicMock()

        result = await svc.ensure_valid_token(session, server, token)
        assert result is token

    @pytest.mark.asyncio
    async def test_expired_no_refresh_token(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        token = MagicMock()
        token.expires_at = datetime.now(UTC) - timedelta(hours=1)
        token.refresh_token = None
        session = MagicMock()
        server = MagicMock()

        result = await svc.ensure_valid_token(session, server, token)
        assert result is None

    @pytest.mark.asyncio
    async def test_expired_refresh_success(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        token = MagicMock()
        token.expires_at = datetime.now(UTC) - timedelta(hours=1)
        token.refresh_token = "rt-123"
        token.user_id = 1
        token.mcp_server_id = 1
        session = MagicMock()
        server = MagicMock()
        server.name = "Test"

        new_token_result = TokenResult(
            access_token="new-at", refresh_token="new-rt", expires_in=3600
        )
        new_token = MagicMock()

        with (
            patch.object(
                svc,
                "refresh_access_token",
                new_callable=AsyncMock,
                return_value=new_token_result,
            ),
            patch.object(svc, "save_user_token", return_value=new_token),
        ):
            result = await svc.ensure_valid_token(session, server, token)
        assert result is new_token

    @pytest.mark.asyncio
    async def test_expired_refresh_failure(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        token = MagicMock()
        token.expires_at = datetime.now(UTC) - timedelta(hours=1)
        token.refresh_token = "rt-123"
        session = MagicMock()
        server = MagicMock()
        server.name = "Test"

        with patch.object(
            svc,
            "refresh_access_token",
            new_callable=AsyncMock,
            return_value=TokenResult(error="invalid_grant"),
        ):
            result = await svc.ensure_valid_token(session, server, token)
        assert result is None


# ============================================================================
# get_user_token, save_user_token, delete_user_token
# ============================================================================


class TestDBOperations:
    def test_get_user_token(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        session = MagicMock()
        mock_token = MagicMock()
        session.exec.return_value.first.return_value = mock_token

        result = svc.get_user_token(session, user_id=1, mcp_server_id=1)
        assert result is mock_token

    def test_get_user_token_not_found(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        session = MagicMock()
        session.exec.return_value.first.return_value = None

        result = svc.get_user_token(session, user_id=1, mcp_server_id=1)
        assert result is None

    def test_save_user_token_new(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        session = MagicMock()
        session.exec.return_value.first.return_value = None

        token_result = TokenResult(
            access_token="at-123", refresh_token="rt-456", expires_in=3600
        )
        svc.save_user_token(session, 1, 1, token_result)
        session.add.assert_called_once()
        session.commit.assert_called_once()

    def test_save_user_token_update_existing(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        session = MagicMock()
        existing = MagicMock()
        existing.access_token = "old-at"
        session.exec.return_value.first.return_value = existing

        token_result = TokenResult(
            access_token="new-at", refresh_token="new-rt", expires_in=3600
        )
        svc.save_user_token(session, 1, 1, token_result)
        assert existing.access_token == "new-at"
        assert existing.refresh_token == "new-rt"

    def test_delete_user_token_exists(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        session = MagicMock()
        token = MagicMock()
        session.exec.return_value.first.return_value = token

        result = svc.delete_user_token(session, 1, 1)
        assert result is True
        session.delete.assert_called_once_with(token)

    def test_delete_user_token_not_found(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        session = MagicMock()
        session.exec.return_value.first.return_value = None

        result = svc.delete_user_token(session, 1, 1)
        assert result is False


# ============================================================================
# update_server_oauth_config
# ============================================================================


class TestUpdateServerOAuthConfig:
    def test_updates_server(self) -> None:
        svc = MCPAuthService(redirect_uri="https://app.test/callback")
        session = MagicMock()
        server = MagicMock()
        discovery = OAuthDiscoveryResult(
            issuer="https://auth.test",
            authorization_endpoint="https://auth.test/authorize",
            token_endpoint="https://auth.test/token",
            scopes_supported=["openid", "profile"],
        )

        result = svc.update_server_oauth_config(session, server, discovery)
        assert result.oauth_issuer == "https://auth.test"
        assert result.oauth_authorize_url == "https://auth.test/authorize"
        assert result.oauth_token_url == "https://auth.test/token"
        assert result.oauth_scopes == "openid profile"
        session.add.assert_called_once()
        session.commit.assert_called_once()
