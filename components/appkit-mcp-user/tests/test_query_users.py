"""Tests for query_users tool module."""

from unittest.mock import MagicMock, patch

import pytest

from appkit_mcp_commons.context import UserContext
from appkit_mcp_user.services.sql_generator import SQLGenerationError
from appkit_mcp_user.tools.query_users import _execute_query, query_users_table


@pytest.fixture
def admin_ctx() -> UserContext:
    """Admin user context."""
    return UserContext(user_id=1, is_admin=True, roles=["admin"])


@pytest.fixture
def regular_ctx() -> UserContext:
    """Regular (non-admin) user context."""
    return UserContext(user_id=42, is_admin=False, roles=[])


# ---------------------------------------------------------------------------
# query_users_table tests
# ---------------------------------------------------------------------------


class TestQueryUsersTable:
    async def test_success(self, admin_ctx: UserContext) -> None:
        """Successful SQL generation and execution returns result."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "alice@example.com"),
            (2, "bob@example.com"),
        ]
        mock_result.keys.return_value = ["id", "email"]
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value = mock_result

        mock_sm = MagicMock()
        mock_sm.session.return_value = mock_session

        with (
            patch(
                "appkit_mcp_user.tools.query_users.generate_sql",
                return_value="SELECT id, email FROM auth_users",
            ),
            patch(
                "appkit_mcp_user.tools.query_users.get_session_manager",
                return_value=mock_sm,
            ),
        ):
            result = await query_users_table(
                "Show all users", admin_ctx, openai_client=MagicMock()
            )

        assert result.success is True
        assert result.row_count == 2
        assert result.columns == ["id", "email"]
        assert result.data[0]["email"] == "alice@example.com"

    async def test_sql_generation_error(self, regular_ctx: UserContext) -> None:
        """SQL generation failure returns error result."""
        with patch(
            "appkit_mcp_user.tools.query_users.generate_sql",
            side_effect=SQLGenerationError("LLM unavailable"),
        ):
            result = await query_users_table(
                "bad question", regular_ctx, openai_client=None
            )

        assert result.success is False
        assert "Could not generate query" in result.error
        assert "LLM unavailable" in result.error

    async def test_custom_model(self, admin_ctx: UserContext) -> None:
        """Custom model parameter is forwarded to generate_sql."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_result.keys.return_value = []
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value = mock_result

        mock_sm = MagicMock()
        mock_sm.session.return_value = mock_session

        with (
            patch(
                "appkit_mcp_user.tools.query_users.generate_sql",
                return_value="SELECT 1",
            ) as mock_gen,
            patch(
                "appkit_mcp_user.tools.query_users.get_session_manager",
                return_value=mock_sm,
            ),
        ):
            await query_users_table(
                "count",
                admin_ctx,
                openai_client=MagicMock(),
                model="gpt-custom",
            )

        mock_gen.assert_called_once()
        assert mock_gen.call_args.kwargs["model"] == "gpt-custom"


# ---------------------------------------------------------------------------
# _execute_query tests
# ---------------------------------------------------------------------------


class TestExecuteQuery:
    def test_success(self, admin_ctx: UserContext) -> None:
        """Successful query execution returns data."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(10, "user@example.com")]
        mock_result.keys.return_value = ["id", "email"]
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value = mock_result

        mock_sm = MagicMock()
        mock_sm.session.return_value = mock_session

        with patch(
            "appkit_mcp_user.tools.query_users.get_session_manager",
            return_value=mock_sm,
        ):
            result = _execute_query("SELECT id, email FROM auth_users", admin_ctx)

        assert result.success is True
        assert result.row_count == 1
        assert result.data[0] == {"id": 10, "email": "user@example.com"}

    def test_empty_result(self, regular_ctx: UserContext) -> None:
        """Empty result set returns success with empty data."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_result.keys.return_value = ["count"]
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value = mock_result

        mock_sm = MagicMock()
        mock_sm.session.return_value = mock_session

        with patch(
            "appkit_mcp_user.tools.query_users.get_session_manager",
            return_value=mock_sm,
        ):
            result = _execute_query(
                "SELECT COUNT(*) AS count FROM auth_users",
                regular_ctx,
            )

        assert result.success is True
        assert result.row_count == 0
        assert result.data == []

    def test_database_error(self, admin_ctx: UserContext) -> None:
        """Database execution error returns error result."""
        mock_sm = MagicMock()
        mock_sm.session.side_effect = RuntimeError("connection refused")

        with patch(
            "appkit_mcp_user.tools.query_users.get_session_manager",
            return_value=mock_sm,
        ):
            result = _execute_query("SELECT 1", admin_ctx)

        assert result.success is False
        assert "Query execution failed" in result.error

    def test_multiple_rows(self, admin_ctx: UserContext) -> None:
        """Multiple rows are correctly mapped to dicts."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("admin",),
            ("user",),
            ("viewer",),
        ]
        mock_result.keys.return_value = ["role"]
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value = mock_result

        mock_sm = MagicMock()
        mock_sm.session.return_value = mock_session

        with patch(
            "appkit_mcp_user.tools.query_users.get_session_manager",
            return_value=mock_sm,
        ):
            result = _execute_query("SELECT role FROM auth_users", admin_ctx)

        assert result.success is True
        assert result.row_count == 3
        assert result.data[2]["role"] == "viewer"
