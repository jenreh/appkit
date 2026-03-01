"""Tests for query_users tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_mcpapp.models.schemas import QueryResult, UserContext
from appkit_mcpapp.services.sql_generator import SQLGenerationError
from appkit_mcpapp.tools.query_users import query_users_table


@pytest.fixture
def admin_user() -> UserContext:
    """Admin user context fixture."""
    return UserContext(user_id=1, is_admin=True, roles=["admin"])


@pytest.fixture
def regular_user() -> UserContext:
    """Regular (non-admin) user context fixture."""
    return UserContext(user_id=2, is_admin=False, roles=["user"])


class TestQueryUsersTable:
    """Tests for query_users_table tool."""

    @pytest.mark.asyncio
    @patch("appkit_mcpapp.tools.query_users.generate_sql")
    @patch("appkit_mcpapp.tools.query_users.get_session_manager")
    async def test_successful_query(
        self,
        mock_get_sm: MagicMock,
        mock_gen_sql: AsyncMock,
        admin_user: UserContext,
    ) -> None:
        mock_gen_sql.return_value = (
            "SELECT is_active, COUNT(*) as count FROM auth_users GROUP BY is_active"
        )

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (True, 10),
            (False, 3),
        ]
        mock_result.keys.return_value = ["is_active", "count"]

        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result

        mock_get_sm.return_value.session.return_value.__enter__ = lambda _: mock_session
        mock_get_sm.return_value.session.return_value.__exit__ = MagicMock(
            return_value=False
        )

        result = await query_users_table(
            "How many active vs inactive users?",
            admin_user,
            openai_client=AsyncMock(),
        )

        assert isinstance(result, QueryResult)
        assert result.success is True
        assert result.row_count == 2
        assert len(result.data) == 2
        assert result.columns == ["is_active", "count"]

    @pytest.mark.asyncio
    @patch("appkit_mcpapp.tools.query_users.generate_sql")
    async def test_sql_generation_failure(
        self,
        mock_gen_sql: AsyncMock,
        regular_user: UserContext,
    ) -> None:
        mock_gen_sql.side_effect = SQLGenerationError("Test error")

        result = await query_users_table(
            "Invalid question",
            regular_user,
            openai_client=AsyncMock(),
        )

        assert result.success is False
        assert result.error is not None
        assert "generate" in result.error.lower()

    @pytest.mark.asyncio
    @patch("appkit_mcpapp.tools.query_users.generate_sql")
    @patch("appkit_mcpapp.tools.query_users.get_session_manager")
    async def test_db_execution_failure(
        self,
        mock_get_sm: MagicMock,
        mock_gen_sql: AsyncMock,
        admin_user: UserContext,
    ) -> None:
        mock_gen_sql.return_value = "SELECT 1 FROM auth_users"

        mock_session = MagicMock()
        mock_session.execute.side_effect = RuntimeError("DB error")

        mock_get_sm.return_value.session.return_value.__enter__ = lambda _: mock_session
        mock_get_sm.return_value.session.return_value.__exit__ = MagicMock(
            return_value=False
        )

        result = await query_users_table(
            "Count users",
            admin_user,
            openai_client=AsyncMock(),
        )

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    @patch("appkit_mcpapp.tools.query_users.generate_sql")
    @patch("appkit_mcpapp.tools.query_users.get_session_manager")
    async def test_non_admin_columns_filtered(
        self,
        mock_get_sm: MagicMock,
        mock_gen_sql: AsyncMock,
        regular_user: UserContext,
    ) -> None:
        mock_gen_sql.return_value = "SELECT id, is_active FROM auth_users"

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, True),
            (2, False),
        ]
        mock_result.keys.return_value = ["id", "is_active"]

        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result

        mock_get_sm.return_value.session.return_value.__enter__ = lambda _: mock_session
        mock_get_sm.return_value.session.return_value.__exit__ = MagicMock(
            return_value=False
        )

        result = await query_users_table(
            "List users",
            regular_user,
            openai_client=AsyncMock(),
        )

        assert result.success is True
        # Non-admin should not see email or name columns
        for row in result.data:
            assert "email" not in row
            assert "name" not in row
