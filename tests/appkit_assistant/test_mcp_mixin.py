"""Tests for MCPCapabilities mixin.

Covers OAuth token management, header parsing, auth chunks,
server configuration, and pending auth server lifecycle.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.processors.mcp_mixin import MCPCapabilities
from appkit_assistant.backend.schemas import ChunkType, MCPAuthType

# ============================================================================
# Helpers
# ============================================================================


def _make_server(
    server_id: int = 1,
    server_name: str = "TestServer",
    headers: str | None = None,
    auth_type: str | None = None,
    url: str = "https://mcp.test",
    prompt: str | None = None,
) -> MagicMock:
    server = MagicMock()
    server.id = server_id
    server.name = server_name
    server.headers = headers
    server.auth_type = auth_type
    server.url = url
    server.prompt = prompt
    return server


# ============================================================================
# Initialization
# ============================================================================


class TestInit:
    def test_defaults(self) -> None:
        with patch(
            "appkit_assistant.backend.processors.mcp_mixin.mcp_oauth_redirect_uri",
            return_value="https://app.test/callback",
        ):
            mcp = MCPCapabilities()
        assert mcp.mcp_processor_name == "unknown"
        assert mcp.current_user_id is None
        assert mcp.pending_auth_servers == []

    def test_custom_params(self) -> None:
        mcp = MCPCapabilities(
            oauth_redirect_uri="https://custom.test/cb",
            processor_name="openai",
        )
        assert mcp.mcp_processor_name == "openai"

    def test_user_id_setter(self) -> None:
        with patch(
            "appkit_assistant.backend.processors.mcp_mixin.mcp_oauth_redirect_uri",
            return_value="https://app.test/callback",
        ):
            mcp = MCPCapabilities()
        mcp.current_user_id = 42
        assert mcp.current_user_id == 42
        mcp.current_user_id = None
        assert mcp.current_user_id is None


# ============================================================================
# Pending auth servers
# ============================================================================


class TestPendingAuthServers:
    def test_add_server(self) -> None:
        with patch(
            "appkit_assistant.backend.processors.mcp_mixin.mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ):
            mcp = MCPCapabilities()
        server = _make_server()
        mcp.add_pending_auth_server(server)
        assert len(mcp.pending_auth_servers) == 1

    def test_add_duplicate_server(self) -> None:
        with patch(
            "appkit_assistant.backend.processors.mcp_mixin.mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ):
            mcp = MCPCapabilities()
        server = _make_server()
        mcp.add_pending_auth_server(server)
        mcp.add_pending_auth_server(server)
        assert len(mcp.pending_auth_servers) == 1

    def test_clear_servers(self) -> None:
        with patch(
            "appkit_assistant.backend.processors.mcp_mixin.mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ):
            mcp = MCPCapabilities()
        mcp.add_pending_auth_server(_make_server(1))
        mcp.add_pending_auth_server(_make_server(2))
        mcp.clear_pending_auth_servers()
        assert mcp.pending_auth_servers == []


# ============================================================================
# parse_mcp_headers
# ============================================================================


class TestParseMcpHeaders:
    def test_no_headers(self) -> None:
        with patch(
            "appkit_assistant.backend.processors.mcp_mixin.mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ):
            mcp = MCPCapabilities()
        server = _make_server(headers=None)
        assert mcp.parse_mcp_headers(server) == {}

    def test_empty_json_headers(self) -> None:
        with patch(
            "appkit_assistant.backend.processors.mcp_mixin.mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ):
            mcp = MCPCapabilities()
        server = _make_server(headers="{}")
        assert mcp.parse_mcp_headers(server) == {}

    def test_valid_headers(self) -> None:
        with patch(
            "appkit_assistant.backend.processors.mcp_mixin.mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ):
            mcp = MCPCapabilities()
        headers = json.dumps({"X-API-Key": "test123", "Accept": "application/json"})
        server = _make_server(headers=headers)
        result = mcp.parse_mcp_headers(server)
        assert result["X-API-Key"] == "test123"
        assert result["Accept"] == "application/json"

    def test_invalid_json(self) -> None:
        with patch(
            "appkit_assistant.backend.processors.mcp_mixin.mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ):
            mcp = MCPCapabilities()
        server = _make_server(headers="not-json{")
        result = mcp.parse_mcp_headers(server)
        assert result == {}


# ============================================================================
# parse_mcp_headers_with_auth
# ============================================================================


class TestParseMcpHeadersWithAuth:
    def test_no_auth_header(self) -> None:
        with patch(
            "appkit_assistant.backend.processors.mcp_mixin.mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ):
            mcp = MCPCapabilities()
        headers = json.dumps({"X-API-Key": "test"})
        server = _make_server(headers=headers)
        h, token = mcp.parse_mcp_headers_with_auth(server)
        assert h == {"X-API-Key": "test"}
        assert token is None

    def test_bearer_token(self) -> None:
        with patch(
            "appkit_assistant.backend.processors.mcp_mixin.mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ):
            mcp = MCPCapabilities()
        headers = json.dumps({"Authorization": "Bearer my-token"})
        server = _make_server(headers=headers)
        h, token = mcp.parse_mcp_headers_with_auth(server)
        assert "Authorization" not in h
        assert token == "my-token"  # noqa: S105

    def test_non_bearer_auth(self) -> None:
        with patch(
            "appkit_assistant.backend.processors.mcp_mixin.mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ):
            mcp = MCPCapabilities()
        headers = json.dumps({"Authorization": "Basic abc123"})
        server = _make_server(headers=headers)
        _h, token = mcp.parse_mcp_headers_with_auth(server)
        assert token == "Basic abc123"  # noqa: S105


# ============================================================================
# get_valid_token
# ============================================================================


class TestGetValidToken:
    @pytest.mark.asyncio
    async def test_delegates_to_token_service(self) -> None:
        with patch(
            "appkit_assistant.backend.processors.mcp_mixin.mcp_oauth_redirect_uri",
            return_value="https://test/cb",
        ):
            mcp = MCPCapabilities()
        mock_token = MagicMock()
        mcp._mcp_token_service.get_valid_token = AsyncMock(  # noqa: SLF001
            return_value=mock_token
        )
        server = _make_server()
        result = await mcp.get_valid_token(server, user_id=1)
        assert result is mock_token


# ============================================================================
# create_auth_required_chunk
# ============================================================================


class TestCreateAuthRequiredChunk:
    @pytest.mark.asyncio
    async def test_creates_chunk(self) -> None:
        mcp = MCPCapabilities(
            oauth_redirect_uri="https://app.test/cb",
            processor_name="openai",
        )
        server = _make_server(server_id=5, server_name="GitHub")
        mcp.current_user_id = 1

        with patch(
            "appkit_assistant.backend.processors.mcp_mixin.get_session_manager"
        ) as mock_sm:
            mock_session = MagicMock()
            mock_sm.return_value.session.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_sm.return_value.session.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mcp._mcp_auth_service.build_authorization_url_with_registration = (  # noqa: SLF001
                AsyncMock(return_value=("https://auth.example.com/login", "state123"))
            )

            chunk = await mcp.create_auth_required_chunk(server)

        assert chunk.type == ChunkType.AUTH_REQUIRED
        assert chunk.chunk_metadata["server_id"] == "5"
        assert chunk.chunk_metadata["server_name"] == "GitHub"
        assert chunk.chunk_metadata["auth_url"] == "https://auth.example.com/login"
        assert chunk.chunk_metadata["state"] == "state123"

    @pytest.mark.asyncio
    async def test_handles_error(self) -> None:
        mcp = MCPCapabilities(
            oauth_redirect_uri="https://app.test/cb",
            processor_name="openai",
        )
        server = _make_server()

        with patch(
            "appkit_assistant.backend.processors.mcp_mixin.get_session_manager",
            side_effect=RuntimeError("db error"),
        ):
            chunk = await mcp.create_auth_required_chunk(server)

        assert chunk.type == ChunkType.AUTH_REQUIRED
        assert chunk.chunk_metadata["auth_url"] == ""


# ============================================================================
# yield_pending_auth_chunks
# ============================================================================


class TestYieldPendingAuthChunks:
    @pytest.mark.asyncio
    async def test_yields_for_each_server(self) -> None:
        mcp = MCPCapabilities(
            oauth_redirect_uri="https://app.test/cb",
            processor_name="openai",
        )
        mcp.add_pending_auth_server(_make_server(1, "Server1"))
        mcp.add_pending_auth_server(_make_server(2, "Server2"))

        with patch.object(
            mcp,
            "create_auth_required_chunk",
            new_callable=AsyncMock,
            side_effect=[
                MagicMock(type=ChunkType.AUTH_REQUIRED),
                MagicMock(type=ChunkType.AUTH_REQUIRED),
            ],
        ):
            chunks = [c async for c in mcp.yield_pending_auth_chunks()]

        assert len(chunks) == 2

    @pytest.mark.asyncio
    async def test_empty_pending(self) -> None:
        mcp = MCPCapabilities(
            oauth_redirect_uri="https://app.test/cb",
            processor_name="openai",
        )
        chunks = [c async for c in mcp.yield_pending_auth_chunks()]
        assert chunks == []


# ============================================================================
# configure_mcp_servers_with_tokens
# ============================================================================


class TestConfigureMcpServersWithTokens:
    @pytest.mark.asyncio
    async def test_empty_servers(self) -> None:
        mcp = MCPCapabilities(
            oauth_redirect_uri="https://app.test/cb",
            processor_name="test",
        )
        configs, prompt = await mcp.configure_mcp_servers_with_tokens(None, None)
        assert configs == []
        assert prompt == ""

    @pytest.mark.asyncio
    async def test_server_without_oauth(self) -> None:
        mcp = MCPCapabilities(
            oauth_redirect_uri="https://app.test/cb",
            processor_name="test",
        )
        headers = json.dumps({"X-API-Key": "key"})
        server = _make_server(headers=headers, auth_type=None, prompt="Use search")
        configs, prompt = await mcp.configure_mcp_servers_with_tokens([server], 1)
        assert len(configs) == 1
        assert configs[0]["name"] == "TestServer"
        assert configs[0]["url"] == "https://mcp.test"
        assert configs[0]["headers"]["X-API-Key"] == "key"
        assert "Use search" in prompt

    @pytest.mark.asyncio
    async def test_oauth_with_valid_token(self) -> None:
        mcp = MCPCapabilities(
            oauth_redirect_uri="https://app.test/cb",
            processor_name="test",
        )
        server = _make_server(
            auth_type=MCPAuthType.OAUTH_DISCOVERY,
            headers="{}",
        )
        mock_token = MagicMock()
        mock_token.access_token = "oauth-token"  # noqa: S105
        mcp._mcp_token_service.get_valid_token = AsyncMock(  # noqa: SLF001
            return_value=mock_token
        )

        configs, _ = await mcp.configure_mcp_servers_with_tokens([server], 1)
        assert configs[0]["headers"]["Authorization"] == "Bearer oauth-token"
        assert len(mcp.pending_auth_servers) == 0

    @pytest.mark.asyncio
    async def test_oauth_no_token_adds_pending(self) -> None:
        mcp = MCPCapabilities(
            oauth_redirect_uri="https://app.test/cb",
            processor_name="test",
        )
        server = _make_server(
            auth_type=MCPAuthType.OAUTH_DISCOVERY,
            headers="{}",
        )
        mcp._mcp_token_service.get_valid_token = AsyncMock(  # noqa: SLF001
            return_value=None
        )

        configs, _ = await mcp.configure_mcp_servers_with_tokens([server], 1)
        assert len(mcp.pending_auth_servers) == 1
        assert "Authorization" not in configs[0]["headers"]

    @pytest.mark.asyncio
    async def test_multiple_prompts_joined(self) -> None:
        mcp = MCPCapabilities(
            oauth_redirect_uri="https://app.test/cb",
            processor_name="test",
        )
        s1 = _make_server(1, "S1", headers="{}", prompt="prompt1")
        s2 = _make_server(2, "S2", headers="{}", prompt="prompt2")
        _, prompt = await mcp.configure_mcp_servers_with_tokens([s1, s2], None)
        assert "- prompt1" in prompt
        assert "- prompt2" in prompt

    @pytest.mark.asyncio
    async def test_no_prompts(self) -> None:
        mcp = MCPCapabilities(
            oauth_redirect_uri="https://app.test/cb",
            processor_name="test",
        )
        server = _make_server(headers="{}", prompt=None)
        _, prompt = await mcp.configure_mcp_servers_with_tokens([server], None)
        assert prompt == ""
