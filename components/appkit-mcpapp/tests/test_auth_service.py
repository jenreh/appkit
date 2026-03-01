"""Tests for authentication service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from appkit_mcpapp.models.schemas import UserContext
from appkit_mcpapp.services.auth_service import (
    AuthenticationError,
    authenticate_user,
)


def _make_session_entity(
    *,
    session_id: str = "test-session",
    user_id: int = 1,
    expires_at: datetime | None = None,
    is_active: bool = True,
    is_admin: bool = False,
    roles: list[str] | None = None,
) -> MagicMock:
    """Create a mock UserSessionEntity with associated user."""
    if expires_at is None:
        expires_at = datetime.now(UTC) + timedelta(hours=1)

    user = MagicMock()
    user.id = user_id
    user.is_active = is_active
    user.is_admin = is_admin
    user.roles = roles or ["user"]

    session_entity = MagicMock()
    session_entity.session_id = session_id
    session_entity.user_id = user_id
    session_entity.expires_at = expires_at
    session_entity.user = user
    return session_entity


class TestAuthenticateUser:
    """Tests for authenticate_user function."""

    def test_empty_session_id_raises(self) -> None:
        with pytest.raises(AuthenticationError, match="No session"):
            authenticate_user("")

    @patch("appkit_mcpapp.services.auth_service.get_session_manager")
    def test_invalid_session_raises(self, mock_get_sm: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_get_sm.return_value.session.return_value.__enter__ = lambda _: mock_session
        mock_get_sm.return_value.session.return_value.__exit__ = MagicMock(
            return_value=False
        )

        with pytest.raises(AuthenticationError, match="Invalid session"):
            authenticate_user("nonexistent-session")

    @patch("appkit_mcpapp.services.auth_service.get_session_manager")
    def test_expired_session_raises(self, mock_get_sm: MagicMock) -> None:
        expired = datetime.now(UTC) - timedelta(hours=1)
        entity = _make_session_entity(expires_at=expired)

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = entity
        mock_get_sm.return_value.session.return_value.__enter__ = lambda _: mock_session
        mock_get_sm.return_value.session.return_value.__exit__ = MagicMock(
            return_value=False
        )

        with pytest.raises(AuthenticationError, match="expired"):
            authenticate_user("test-session")

    @patch("appkit_mcpapp.services.auth_service.get_session_manager")
    def test_inactive_user_raises(self, mock_get_sm: MagicMock) -> None:
        entity = _make_session_entity(is_active=False)

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = entity
        mock_get_sm.return_value.session.return_value.__enter__ = lambda _: mock_session
        mock_get_sm.return_value.session.return_value.__exit__ = MagicMock(
            return_value=False
        )

        with pytest.raises(AuthenticationError, match="inactive"):
            authenticate_user("test-session")

    @patch("appkit_mcpapp.services.auth_service.get_session_manager")
    def test_no_user_raises(self, mock_get_sm: MagicMock) -> None:
        entity = _make_session_entity()
        entity.user = None

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = entity
        mock_get_sm.return_value.session.return_value.__enter__ = lambda _: mock_session
        mock_get_sm.return_value.session.return_value.__exit__ = MagicMock(
            return_value=False
        )

        with pytest.raises(AuthenticationError, match="User not found"):
            authenticate_user("test-session")

    @patch("appkit_mcpapp.services.auth_service.get_session_manager")
    def test_successful_authentication(self, mock_get_sm: MagicMock) -> None:
        entity = _make_session_entity(
            user_id=42,
            is_admin=True,
            roles=["admin", "editor"],
        )

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = entity
        mock_get_sm.return_value.session.return_value.__enter__ = lambda _: mock_session
        mock_get_sm.return_value.session.return_value.__exit__ = MagicMock(
            return_value=False
        )

        result = authenticate_user("valid-session")

        assert isinstance(result, UserContext)
        assert result.user_id == 42
        assert result.is_admin is True
        assert result.roles == ["admin", "editor"]

    @patch("appkit_mcpapp.services.auth_service.get_session_manager")
    def test_regular_user_authentication(self, mock_get_sm: MagicMock) -> None:
        entity = _make_session_entity(
            user_id=10,
            is_admin=False,
            roles=["user"],
        )

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = entity
        mock_get_sm.return_value.session.return_value.__enter__ = lambda _: mock_session
        mock_get_sm.return_value.session.return_value.__exit__ = MagicMock(
            return_value=False
        )

        result = authenticate_user("user-session")

        assert result.user_id == 10
        assert result.is_admin is False
