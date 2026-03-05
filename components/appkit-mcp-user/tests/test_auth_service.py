"""Tests for authentication service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from appkit_mcp_commons.context import UserContext
from appkit_mcp_commons.exceptions import AuthenticationError
from appkit_mcp_user.authentication.service import (
    _is_expired,
    authenticate_user,
)

_SM_PATH = "appkit_mcp_user.authentication.service.get_session_manager"


def _mock_db_session(
    db_session_entity: MagicMock | None,
) -> MagicMock:
    """Create a mock session manager context."""
    mock_session = MagicMock()
    mock_session.execute.return_value.scalar_one_or_none.return_value = (  # noqa: E501
        db_session_entity
    )
    mock_sm = MagicMock()
    mock_sm.return_value.session.return_value.__enter__ = lambda _: mock_session
    mock_sm.return_value.session.return_value.__exit__ = MagicMock(return_value=False)
    return mock_sm


class TestIsExpired:
    """Tests for _is_expired helper."""

    def test_past_datetime_is_expired(self) -> None:
        past = datetime.now(UTC) - timedelta(hours=1)
        assert _is_expired(past) is True

    def test_future_datetime_not_expired(self) -> None:
        future = datetime.now(UTC) + timedelta(hours=1)
        assert _is_expired(future) is False

    def test_naive_datetime_treated_as_utc(self) -> None:
        past = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)
        assert _is_expired(past) is True


class TestAuthenticateUser:
    """Tests for authenticate_user."""

    def test_empty_session_id_raises(self) -> None:
        with pytest.raises(AuthenticationError, match="No session ID"):
            authenticate_user("")

    def test_none_session_id_raises(self) -> None:
        with pytest.raises(AuthenticationError, match="No session ID"):
            authenticate_user(None)

    @patch(_SM_PATH)
    def test_session_not_found_raises(self, mock_sm: MagicMock) -> None:
        sm = _mock_db_session(None)
        mock_sm.return_value = sm.return_value

        with pytest.raises(AuthenticationError, match="Invalid session"):
            authenticate_user("nonexistent-session")

    @patch(_SM_PATH)
    def test_expired_session_raises(self, mock_sm: MagicMock) -> None:
        entity = MagicMock()
        entity.expires_at = datetime.now(UTC) - timedelta(hours=1)
        entity.user_id = 1
        sm = _mock_db_session(entity)
        mock_sm.return_value = sm.return_value

        with pytest.raises(AuthenticationError, match="Session expired"):
            authenticate_user("expired-session")

    @patch(_SM_PATH)
    def test_no_user_raises(self, mock_sm: MagicMock) -> None:
        entity = MagicMock()
        entity.expires_at = datetime.now(UTC) + timedelta(hours=1)
        entity.user = None
        sm = _mock_db_session(entity)
        mock_sm.return_value = sm.return_value

        with pytest.raises(AuthenticationError, match="User not found"):
            authenticate_user("orphan-session")

    @patch(_SM_PATH)
    def test_inactive_user_raises(self, mock_sm: MagicMock) -> None:
        user = MagicMock()
        user.is_active = False
        entity = MagicMock()
        entity.expires_at = datetime.now(UTC) + timedelta(hours=1)
        entity.user = user
        sm = _mock_db_session(entity)
        mock_sm.return_value = sm.return_value

        with pytest.raises(AuthenticationError, match="inactive"):
            authenticate_user("inactive-user-session")

    @patch(_SM_PATH)
    def test_successful_auth_returns_context(self, mock_sm: MagicMock) -> None:
        user = MagicMock()
        user.id = 42
        user.is_admin = True
        user.roles = ["admin", "viewer"]
        user.is_active = True
        entity = MagicMock()
        entity.expires_at = datetime.now(UTC) + timedelta(hours=1)
        entity.user = user
        sm = _mock_db_session(entity)
        mock_sm.return_value = sm.return_value

        ctx = authenticate_user("valid-session")

        assert isinstance(ctx, UserContext)
        assert ctx.user_id == 42
        assert ctx.is_admin is True
        assert ctx.roles == ["admin", "viewer"]

    @patch(_SM_PATH)
    def test_null_roles_become_empty_list(self, mock_sm: MagicMock) -> None:
        user = MagicMock()
        user.id = 1
        user.is_admin = False
        user.roles = None
        user.is_active = True
        entity = MagicMock()
        entity.expires_at = datetime.now(UTC) + timedelta(hours=1)
        entity.user = user
        sm = _mock_db_session(entity)
        mock_sm.return_value = sm.return_value

        ctx = authenticate_user("valid-session")
        assert ctx.roles == []
