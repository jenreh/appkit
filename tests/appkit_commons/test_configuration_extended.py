"""Tests for configuration modules."""

import os
from unittest.mock import MagicMock, patch

import pytest

from appkit_commons.configuration.base import (
    BaseConfig,
    _replace_value_if_secret,
    _starts_with_secret,
)
from appkit_commons.configuration.secret_provider import (
    SECRET,
    SecretNotFoundError,
    _get_secret_from_azure,
    _get_secret_from_env,
)


class TestStartsWithSecret:
    """Test suite for _starts_with_secret function."""

    def test_string_starting_with_secret(self) -> None:
        """_starts_with_secret returns True for secret: prefix."""
        # Act & Assert
        assert _starts_with_secret("secret:my_secret") is True

    def test_string_with_uppercase_secret(self) -> None:
        """_starts_with_secret handles uppercase SECRET prefix."""
        # Act & Assert
        assert _starts_with_secret("SECRET:my_secret") is True

    def test_string_without_secret(self) -> None:
        """_starts_with_secret returns False for regular strings."""
        # Act & Assert
        assert _starts_with_secret("regular_value") is False

    def test_empty_string(self) -> None:
        """_starts_with_secret returns False for empty string."""
        # Act & Assert
        assert _starts_with_secret("") is False

    def test_mixed_case_secret(self) -> None:
        """_starts_with_secret handles mixed case."""
        # Act & Assert
        assert _starts_with_secret("SeCreT:value") is True


class TestReplaceValueIfSecret:
    """Test suite for _replace_value_if_secret function."""

    def test_replace_secret_value(self) -> None:
        """_replace_value_if_secret replaces secret: prefix values."""
        # Arrange
        mock_secret_func = MagicMock(return_value="actual_secret_value")

        # Act
        result = _replace_value_if_secret("key", "secret:my_key", mock_secret_func)

        # Assert
        assert result == "actual_secret_value"
        mock_secret_func.assert_called_once_with("my_key")

    def test_replace_secret_uses_value_as_key(self) -> None:
        """_replace_value_if_secret uses the text after secret: as key."""
        # Arrange
        mock_secret_func = MagicMock(return_value="retrieved_value")

        # Act
        result = _replace_value_if_secret(
            "param_key",
            "secret:specific_secret_name",
            mock_secret_func,
        )

        # Assert
        assert result == "retrieved_value"
        mock_secret_func.assert_called_once_with("specific_secret_name")

    def test_replace_secret_with_empty_value_uses_key_name(self) -> None:
        """_replace_value_if_secret uses field name when secret value is empty."""
        # Arrange
        mock_secret_func = MagicMock(return_value="from_key")

        # Act
        result = _replace_value_if_secret("field_name", "secret:", mock_secret_func)

        # Assert
        assert result == "from_key"
        mock_secret_func.assert_called_once_with("field_name")

    def test_non_secret_value_unchanged(self) -> None:
        """_replace_value_if_secret returns non-secret values unchanged."""
        # Arrange
        mock_secret_func = MagicMock()

        # Act
        result = _replace_value_if_secret("key", "normal_value", mock_secret_func)

        # Assert
        assert result == "normal_value"
        mock_secret_func.assert_not_called()

    def test_replace_value_in_list(self) -> None:
        """_replace_value_if_secret processes lists recursively."""
        # Arrange
        mock_secret_func = MagicMock(side_effect=lambda x: f"secret_{x}")

        # Act
        result = _replace_value_if_secret(
            "key",
            ["secret:one", "normal", "secret:two"],
            mock_secret_func,
        )

        # Assert
        assert result == ["secret_one", "normal", "secret_two"]
        assert mock_secret_func.call_count == 2

    def test_replace_non_string_value(self) -> None:
        """_replace_value_if_secret returns non-string values unchanged."""
        # Arrange
        mock_secret_func = MagicMock()

        # Act
        result = _replace_value_if_secret("key", 42, mock_secret_func)

        # Assert
        assert result == 42
        mock_secret_func.assert_not_called()

    def test_replace_none_value(self) -> None:
        """_replace_value_if_secret handles None values."""
        # Arrange
        mock_secret_func = MagicMock()

        # Act
        result = _replace_value_if_secret("key", None, mock_secret_func)

        # Assert
        assert result is None
        mock_secret_func.assert_not_called()

    def test_replace_boolean_value(self) -> None:
        """_replace_value_if_secret handles boolean values."""
        # Arrange
        mock_secret_func = MagicMock()

        # Act
        result_true = _replace_value_if_secret("key", True, mock_secret_func)
        result_false = _replace_value_if_secret("key", False, mock_secret_func)

        # Assert
        assert result_true is True
        assert result_false is False
        mock_secret_func.assert_not_called()


class TestGetSecretFromEnv:
    """Test suite for _get_secret_from_env function."""

    def test_get_secret_direct_key(self) -> None:
        """_get_secret_from_env retrieves secret with direct key lookup."""
        # Arrange
        with patch.dict(os.environ, {"my_secret": "secret_value"}):
            # Act
            result = _get_secret_from_env("my_secret")

            # Assert
            assert result == "secret_value"

    def test_get_secret_uppercase_key(self) -> None:
        """_get_secret_from_env tries uppercase key when direct lookup fails."""
        # Arrange
        with patch.dict(os.environ, {"MY_SECRET": "value"}, clear=True):
            # Act
            result = _get_secret_from_env("my_secret")

            # Assert
            assert result == "value"

    def test_get_secret_dash_to_underscore(self) -> None:
        """_get_secret_from_env converts dashes to underscores."""
        # Arrange
        with patch.dict(os.environ, {"MY_DB_USER": "dbuser"}, clear=True):
            # Act
            result = _get_secret_from_env("my-db-user")

            # Assert
            assert result == "dbuser"

    def test_get_secret_dash_to_underscore_lowercase(self) -> None:
        """_get_secret_from_env tries lowercase after dash conversion."""
        # Arrange
        with patch.dict(os.environ, {"my_db_password": "dbpass"}, clear=True):
            # Act
            result = _get_secret_from_env("my-db-password")

            # Assert
            assert result == "dbpass"

    def test_get_secret_not_found_raises_error(self) -> None:
        """_get_secret_from_env raises SecretNotFoundError when not found."""
        # Arrange
        # Act & Assert
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(
                SecretNotFoundError,
                match="Secret 'nonexistent' not found in environment variables",
            ),
        ):
            _get_secret_from_env("nonexistent")

    def test_get_secret_prefers_direct_lookup(self) -> None:
        """_get_secret_from_env prefers direct key over transformations."""
        # Arrange
        with patch.dict(
            os.environ,
            {
                "my_key": "direct_value",
                "MY_KEY": "uppercase_value",
            },
        ):
            # Act
            result = _get_secret_from_env("my_key")

            # Assert
            assert result == "direct_value"

    def test_get_secret_fallback_chain(self) -> None:
        """_get_secret_from_env tries multiple fallback strategies."""
        # Arrange
        # Only provide the uppercase+dash version
        with patch.dict(os.environ, {"APP_DB_PORT": "5432"}, clear=True):
            # Act
            result = _get_secret_from_env("app-db-port")

            # Assert
            assert result == "5432"

    def test_get_secret_error_message_helpful(self) -> None:
        """_get_secret_from_env provides helpful error message."""
        # Arrange
        with patch.dict(os.environ, {}, clear=True):
            # Act & Assert
            with pytest.raises(SecretNotFoundError) as exc_info:
                _get_secret_from_env("test-key")

            error_msg = str(exc_info.value)
            assert "test-key" in error_msg
            assert "TEST_KEY" in error_msg or "test_key" in error_msg


class TestSecretProvider:
    """Test suite for SecretProvider enum."""

    def test_secret_constant_value(self) -> None:
        """SECRET constant is properly defined."""
        # Assert - verify constant value matches expected
        assert SECRET == "secret:"  # noqa: S105


class TestBaseConfig:
    """Test suite for BaseConfig."""

    def test_base_config_extra_ignore(self) -> None:
        """BaseConfig ignores extra fields."""

        # Arrange
        class TestConfig(BaseConfig):
            name: str = "default"

        # Act & Assert - extra field should not raise error
        config = TestConfig(name="test", extra_field="ignored")
        assert config.name == "test"
        assert not hasattr(config, "extra_field")

    def test_base_config_nested_delimiter(self) -> None:
        """BaseConfig supports nested delimiter."""

        # Arrange
        class NestedConfig(BaseConfig):
            class DatabaseSettings(BaseConfig):
                host: str = "localhost"
                port: int = 5432

            database: DatabaseSettings = DatabaseSettings()

        # Act - nested values can be set via env with __ delimiter
        with patch.dict(os.environ, {"database__host": "remote.host"}):
            config = NestedConfig()

            # Assert
            assert config.database.host == "remote.host"


class TestAzureSecretProvider:
    """Test suite for Azure secret provider functionality."""

    def test_get_secret_from_azure_success(self) -> None:
        """_get_secret_from_azure retrieves secret from Azure."""
        # Arrange

        mock_secret = MagicMock()
        mock_secret.value = "secret_value"
        mock_client = MagicMock()
        mock_client.get_secret.return_value = mock_secret

        # Act & Assert
        with patch(
            "appkit_commons.configuration.secret_provider._get_azure_client"
        ) as mock_get_client:
            mock_get_client.return_value = mock_client
            result = _get_secret_from_azure("my_key")
            assert result == "secret_value"
            mock_client.get_secret.assert_called_once_with("my_key")

    def test_get_secret_from_azure_empty_value(self) -> None:
        """_get_secret_from_azure raises error for empty secret."""
        # Arrange

        mock_secret = MagicMock()
        mock_secret.value = ""
        mock_client = MagicMock()
        mock_client.get_secret.return_value = mock_secret

        # Act & Assert
        with patch(
            "appkit_commons.configuration.secret_provider._get_azure_client"
        ) as mock_get_client:
            mock_get_client.return_value = mock_client
            with pytest.raises(
                SecretNotFoundError,
                match="Secret 'my_key' not found in Azure Key Vault",
            ):
                _get_secret_from_azure("my_key")

    def test_get_secret_from_azure_lowercase_key(self) -> None:
        """_get_secret_from_azure converts key to lowercase."""
        # Arrange

        mock_secret = MagicMock()
        mock_secret.value = "found"
        mock_client = MagicMock()
        mock_client.get_secret.return_value = mock_secret

        # Act
        with patch(
            "appkit_commons.configuration.secret_provider._get_azure_client"
        ) as mock_get_client:
            mock_get_client.return_value = mock_client
            result = _get_secret_from_azure("MY_KEY_NAME")

        # Assert
        assert result == "found"
        mock_client.get_secret.assert_called_once_with("my_key_name")
