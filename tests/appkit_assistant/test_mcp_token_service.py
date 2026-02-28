"""Tests for MCPTokenService.

Covers get_valid_token for cached, refreshed, and missing token scenarios.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.services.mcp_token_service import (
    MCPTokenService,
)


@pytest.fixture
def token_service() -> MCPTokenService:
    mock_auth_svc = MagicMock()
    return MCPTokenService(mcp_auth_service=mock_auth_svc)


class TestGetValidToken:
    @pytest.mark.asyncio
    async def test_no_existing_token(self, token_service: MCPTokenService) -> None:
        server = MagicMock()
        server.id = 1

        mock_session = MagicMock()
        token_service._mcp_auth_service.get_user_token.return_value = None  # noqa: SLF001

        with patch(
            "appkit_assistant.backend.services.mcp_token_service.rx.session"
        ) as mock_rx_session:
            mock_rx_session.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_rx_session.return_value.__exit__ = MagicMock(return_value=False)
            result = await token_service.get_valid_token(server, user_id=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_valid_token_returned(self, token_service: MCPTokenService) -> None:
        server = MagicMock()
        server.id = 1
        token = MagicMock()
        token.access_token = "valid-token"  # noqa: S105

        mock_session = MagicMock()
        token_service._mcp_auth_service.get_user_token.return_value = token  # noqa: SLF001
        token_service._mcp_auth_service.ensure_valid_token = AsyncMock(  # noqa: SLF001
            return_value=token
        )

        with patch(
            "appkit_assistant.backend.services.mcp_token_service.rx.session"
        ) as mock_rx_session:
            mock_rx_session.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_rx_session.return_value.__exit__ = MagicMock(return_value=False)
            result = await token_service.get_valid_token(server, user_id=1)

        assert result is token

    @pytest.mark.asyncio
    async def test_expired_token_refresh_fails(
        self, token_service: MCPTokenService
    ) -> None:
        server = MagicMock()
        server.id = 1
        token = MagicMock()
        token.access_token = "expired"  # noqa: S105

        mock_session = MagicMock()
        token_service._mcp_auth_service.get_user_token.return_value = token  # noqa: SLF001
        token_service._mcp_auth_service.ensure_valid_token = AsyncMock(  # noqa: SLF001
            return_value=None
        )

        with patch(
            "appkit_assistant.backend.services.mcp_token_service.rx.session"
        ) as mock_rx_session:
            mock_rx_session.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_rx_session.return_value.__exit__ = MagicMock(return_value=False)
            result = await token_service.get_valid_token(server, user_id=1)

        assert result is None
