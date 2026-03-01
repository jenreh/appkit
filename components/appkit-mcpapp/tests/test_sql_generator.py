"""Tests for SQL generator service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from appkit_mcpapp.services.sql_generator import (
    SQLGenerationError,
    _clean_sql_response,
    generate_sql,
    get_safe_columns,
)
from appkit_mcpapp.services.sql_validator import (
    ADMIN_ONLY_COLUMNS,
    ALLOWED_COLUMNS,
)


class TestCleanSqlResponse:
    """Tests for _clean_sql_response helper."""

    def test_plain_sql(self) -> None:
        assert _clean_sql_response("SELECT * FROM auth_users") == (
            "SELECT * FROM auth_users"
        )

    def test_strips_sql_code_block(self) -> None:
        result = _clean_sql_response("```sql\nSELECT 1\n```")
        assert result == "SELECT 1"

    def test_strips_generic_code_block(self) -> None:
        result = _clean_sql_response("```\nSELECT 1\n```")
        assert result == "SELECT 1"

    def test_strips_whitespace(self) -> None:
        result = _clean_sql_response("  SELECT 1  ")
        assert result == "SELECT 1"


class TestGetSafeColumns:
    """Tests for get_safe_columns."""

    def test_admin_gets_all_columns(self) -> None:
        cols = get_safe_columns(is_admin=True)
        assert set(cols) == ALLOWED_COLUMNS

    def test_non_admin_excludes_restricted(self) -> None:
        cols = get_safe_columns(is_admin=False)
        for col in ADMIN_ONLY_COLUMNS:
            assert col not in cols

    def test_non_admin_includes_safe_columns(self) -> None:
        cols = get_safe_columns(is_admin=False)
        assert "id" in cols
        assert "is_active" in cols
        assert "roles" in cols

    def test_returns_sorted_list(self) -> None:
        cols = get_safe_columns(is_admin=True)
        assert cols == sorted(cols)


class TestGenerateSql:
    """Tests for generate_sql function."""

    @pytest.mark.asyncio
    async def test_no_client_raises(self) -> None:
        with pytest.raises(SQLGenerationError, match="not available"):
            await generate_sql("test question", client=None)

    @pytest.mark.asyncio
    async def test_empty_question_raises(self) -> None:
        client = AsyncMock()
        with pytest.raises(SQLGenerationError, match="empty"):
            await generate_sql("", client=client)

    @pytest.mark.asyncio
    async def test_successful_generation(self) -> None:
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "SELECT COUNT(*) as count FROM auth_users"
        mock_response.choices = [mock_choice]

        client = AsyncMock()
        client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await generate_sql(
            "How many users are there?",
            is_admin=True,
            client=client,
        )

        assert "SELECT" in result
        assert "auth_users" in result

    @pytest.mark.asyncio
    async def test_generated_sql_with_code_blocks(self) -> None:
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "```sql\nSELECT COUNT(*) FROM auth_users\n```"
        mock_response.choices = [mock_choice]

        client = AsyncMock()
        client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await generate_sql(
            "Count users",
            is_admin=True,
            client=client,
        )

        assert not result.startswith("```")
        assert "SELECT" in result

    @pytest.mark.asyncio
    async def test_unsafe_sql_raises(self) -> None:
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "DROP TABLE auth_users"
        mock_response.choices = [mock_choice]

        client = AsyncMock()
        client.chat.completions.create = AsyncMock(return_value=mock_response)

        with pytest.raises(SQLGenerationError, match="not safe"):
            await generate_sql(
                "Drop the users table",
                is_admin=True,
                client=client,
            )

    @pytest.mark.asyncio
    async def test_empty_llm_response_raises(self) -> None:
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = None
        mock_response.choices = [mock_choice]

        client = AsyncMock()
        client.chat.completions.create = AsyncMock(return_value=mock_response)

        with pytest.raises(SQLGenerationError, match="empty"):
            await generate_sql(
                "test",
                is_admin=True,
                client=client,
            )

    @pytest.mark.asyncio
    async def test_non_admin_restricted_columns(self) -> None:
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "SELECT email FROM auth_users"
        mock_response.choices = [mock_choice]

        client = AsyncMock()
        client.chat.completions.create = AsyncMock(return_value=mock_response)

        with pytest.raises(SQLGenerationError, match="not safe"):
            await generate_sql(
                "Show emails",
                is_admin=False,
                client=client,
            )

    @pytest.mark.asyncio
    async def test_client_error_raises(self) -> None:
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("API error")
        )

        with pytest.raises(SQLGenerationError, match="Failed"):
            await generate_sql(
                "Count users",
                is_admin=True,
                client=client,
            )
