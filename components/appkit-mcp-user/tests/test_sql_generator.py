from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import AsyncOpenAI

from appkit_mcp_user.services.sql_generator import (
    SQLGenerationError,
    _clean_sql_response,
    generate_sql,
    get_safe_columns,
)
from appkit_mcp_user.services.sql_validator import (
    ADMIN_ONLY_COLUMNS,
    ALLOWED_COLUMNS,
    SQLValidationError,
)


@pytest.fixture
def mock_openai_client() -> AsyncOpenAI:
    """Mock OpenAI client."""
    client = AsyncMock(spec=AsyncOpenAI)
    client.chat = AsyncMock()
    client.chat.completions = AsyncMock()
    client.chat.completions.create = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_generate_sql_success(
    mock_openai_client: AsyncOpenAI,
) -> None:
    """Test successful SQL generation."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "SELECT count(*) FROM auth_users"

    mock_openai_client.chat.completions.create.return_value = mock_response

    with patch("appkit_mcp_user.services.sql_generator.validate_sql") as mock_validate:
        mock_validate.return_value = "SELECT count(*) FROM auth_users"

        sql = await generate_sql(
            "Count users",
            is_admin=True,
            client=mock_openai_client,
        )
        assert sql == "SELECT count(*) FROM auth_users"


@pytest.mark.asyncio
async def test_generate_sql_validation_failure(
    mock_openai_client: AsyncOpenAI,
) -> None:
    """Test SQL generation validation failure."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "DROP TABLE auth_users"

    mock_openai_client.chat.completions.create.return_value = mock_response

    with patch("appkit_mcp_user.services.sql_generator.validate_sql") as mock_validate:
        mock_validate.side_effect = SQLValidationError("Unsafe query")

        with pytest.raises(SQLGenerationError) as exc:
            await generate_sql(
                "Destroy everything",
                is_admin=True,
                client=mock_openai_client,
            )

        assert "Generated query is not safe" in str(exc.value)


@pytest.mark.asyncio
async def test_generate_sql_no_client() -> None:
    """Test error when no client provided."""
    with pytest.raises(SQLGenerationError, match="not available"):
        await generate_sql("Test", client=None)


@pytest.mark.asyncio
async def test_generate_sql_empty_question() -> None:
    """Test error when question is empty."""
    client = AsyncMock(spec=AsyncOpenAI)
    with pytest.raises(SQLGenerationError, match="cannot be empty"):
        await generate_sql("", client=client)


@pytest.mark.asyncio
async def test_generate_sql_whitespace_question() -> None:
    """Test error when question is whitespace only."""
    client = AsyncMock(spec=AsyncOpenAI)
    with pytest.raises(SQLGenerationError, match="cannot be empty"):
        await generate_sql("   ", client=client)


@pytest.mark.asyncio
async def test_generate_sql_empty_response(
    mock_openai_client: AsyncOpenAI,
) -> None:
    """Test error when LLM returns empty content."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None

    mock_openai_client.chat.completions.create.return_value = mock_response

    with pytest.raises(SQLGenerationError, match="empty response"):
        await generate_sql(
            "Count users",
            is_admin=True,
            client=mock_openai_client,
        )


@pytest.mark.asyncio
async def test_generate_sql_api_error(
    mock_openai_client: AsyncOpenAI,
) -> None:
    """Test error when API call fails."""
    mock_openai_client.chat.completions.create.side_effect = RuntimeError("API error")

    with pytest.raises(SQLGenerationError, match="Failed to generate"):
        await generate_sql(
            "Count users",
            is_admin=True,
            client=mock_openai_client,
        )


@pytest.mark.asyncio
async def test_generate_sql_strips_markdown(
    mock_openai_client: AsyncOpenAI,
) -> None:
    """Test that markdown code blocks are stripped."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "```sql\nSELECT id FROM auth_users\n```"

    mock_openai_client.chat.completions.create.return_value = mock_response

    with patch("appkit_mcp_user.services.sql_generator.validate_sql") as mock_validate:
        mock_validate.return_value = "SELECT id FROM auth_users"

        sql = await generate_sql(
            "Get user IDs",
            is_admin=True,
            client=mock_openai_client,
        )
        assert sql == "SELECT id FROM auth_users"


class TestCleanSqlResponse:
    """Tests for _clean_sql_response."""

    def test_strips_sql_block(self) -> None:
        result = _clean_sql_response("```sql\nSELECT 1\n```")
        assert result == "SELECT 1"

    def test_strips_generic_block(self) -> None:
        result = _clean_sql_response("```\nSELECT 1\n```")
        assert result == "SELECT 1"

    def test_no_block(self) -> None:
        result = _clean_sql_response("SELECT 1")
        assert result == "SELECT 1"

    def test_strips_whitespace(self) -> None:
        result = _clean_sql_response("  SELECT 1  ")
        assert result == "SELECT 1"


class TestGetSafeColumns:
    """Tests for get_safe_columns."""

    def test_admin_gets_all_columns(self) -> None:
        cols = get_safe_columns(is_admin=True)
        assert "email" in cols
        assert "name" in cols
        assert "id" in cols

    def test_non_admin_excludes_pii(self) -> None:
        cols = get_safe_columns(is_admin=False)
        assert "email" not in cols
        assert "name" not in cols
        assert "id" in cols

    def test_returns_sorted(self) -> None:
        cols = get_safe_columns(is_admin=True)
        assert cols == sorted(cols)


def test_constants() -> None:
    """Test constants are defined correctly."""
    assert len(ADMIN_ONLY_COLUMNS) > 0
    assert len(ALLOWED_COLUMNS) > 0
    assert "email" in ALLOWED_COLUMNS
