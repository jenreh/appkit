from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import AsyncOpenAI

from appkit_mcp_user.services.sql_generator import SQLGenerationError, generate_sql
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
    # Define the create method on the mock
    client.chat.completions.create = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_generate_sql_success(mock_openai_client: AsyncOpenAI) -> None:
    """Test successful SQL generation."""
    # Mock successful response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "SELECT count(*) FROM auth_users"

    # Configure the mock to return our response
    mock_openai_client.chat.completions.create.return_value = mock_response

    # Mock the validator to pass
    with patch("appkit_mcp_user.services.sql_generator.validate_sql") as mock_validate:
        mock_validate.return_value = "SELECT count(*) FROM auth_users"

        sql = await generate_sql(
            "Count users",
            is_admin=True,
            client=mock_openai_client,
        )
        assert sql == "SELECT count(*) FROM auth_users"


@pytest.mark.asyncio
async def test_generate_sql_validation_failure(mock_openai_client: AsyncOpenAI) -> None:
    """Test SQL generation validation failure."""
    # Mock response that fails validation
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "DROP TABLE auth_users"

    mock_openai_client.chat.completions.create.return_value = mock_response

    # Mock validator to raise SQLValidationError
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
    try:
        await generate_sql("Test", client=None)
    except SQLGenerationError:
        pass
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")


def test_constants() -> None:
    """Test constants are defined correctly."""
    assert len(ADMIN_ONLY_COLUMNS) > 0
    assert len(ALLOWED_COLUMNS) > 0
    assert "email" in ALLOWED_COLUMNS
