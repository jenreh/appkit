"""Tests for SecretProvider secret management."""

import os
from unittest.mock import patch

import pytest

from appkit_commons.configuration.secret_provider import (
    SECRET,
    SecretNotFoundError,
    SecretProvider,
    _get_secret_from_env,
    get_secret,
)


class TestSecretProvider:
    """Test suite for SecretProvider."""

    def test_get_secret_from_env_direct_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Getting secret with exact key match succeeds."""
        # Arrange
        monkeypatch.setenv("my-secret-key", "secret-value")

        # Act
        value = _get_secret_from_env("my-secret-key")

        # Assert
        assert value == "secret-value"

    def test_get_secret_from_env_uppercase(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Getting secret falls back to uppercase key."""
        # Arrange
        monkeypatch.setenv("MY_SECRET_KEY", "uppercase-value")

        # Act
        value = _get_secret_from_env("my_secret_key")

        # Assert
        assert value == "uppercase-value"

    def test_get_secret_from_env_dash_to_underscore(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Getting secret converts dashes to underscores and uppercases."""
        # Arrange
        monkeypatch.setenv("MY_SECRET_KEY", "transformed-value")

        # Act
        value = _get_secret_from_env("my-secret-key")

        # Assert
        assert value == "transformed-value"

    def test_get_secret_from_env_dash_to_underscore_lowercase(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Getting secret tries lowercase dash-to-underscore transformation."""
        # Arrange
        monkeypatch.setenv("my_secret_key", "lowercase-transformed")

        # Act
        value = _get_secret_from_env("my-secret-key")

        # Assert
        assert value == "lowercase-transformed"

    def test_get_secret_from_env_not_found_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Getting non-existent secret raises SecretNotFoundError."""
        # Ensure the key doesn't exist
        monkeypatch.delenv("NONEXISTENT_KEY", raising=False)

        # Act & Assert
        with pytest.raises(SecretNotFoundError, match="not found in environment"):
            _get_secret_from_env("nonexistent-key")

    def test_get_secret_from_env_error_lists_attempts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Error message lists all attempted key variations."""
        # Arrange
        monkeypatch.delenv("MISSING_KEY", raising=False)

        # Act & Assert
        with pytest.raises(SecretNotFoundError) as exc_info:
            _get_secret_from_env("missing-key")

        error_msg = str(exc_info.value)
        assert "missing-key" in error_msg
        assert "MISSING-KEY" in error_msg
        assert "MISSING_KEY" in error_msg

    def test_get_secret_local_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_secret() uses local provider when SECRET_PROVIDER=local."""
        # Arrange
        monkeypatch.setenv("SECRET_PROVIDER", "local")
        monkeypatch.setenv("test-key", "test-value")

        # Act
        value = get_secret("test-key")

        # Assert
        assert value == "test-value"

    def test_get_secret_defaults_to_local(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret() defaults to local provider if not specified."""
        # Arrange
        monkeypatch.delenv("SECRET_PROVIDER", raising=False)
        monkeypatch.setenv("default-key", "default-value")

        # Act
        value = get_secret("default-key")

        # Assert
        assert value == "default-value"

    def test_secret_prefix_constant(self) -> None:
        """SECRET constant is defined correctly."""
        # Assert
        assert SECRET == "secret:"

    def test_secret_provider_enum_values(self) -> None:
        """SecretProvider enum has correct values."""
        # Assert
        assert SecretProvider.AZURE == "azure"
        assert SecretProvider.LOCAL == "local"

    def test_get_secret_from_env_empty_value_returns_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Getting secret with empty string value returns empty string."""
        # Arrange
        monkeypatch.setenv("empty-key", "")

        # Act
        value = _get_secret_from_env("empty-key")

        # Assert
        assert value == ""

    def test_get_secret_from_env_priority_order(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret_from_env tries keys in priority order."""
        # Arrange - set multiple variations, direct key should win
        monkeypatch.setenv("my-key", "direct-match")
        monkeypatch.setenv("MY-KEY", "uppercase-match")
        monkeypatch.setenv("MY_KEY", "transformed-match")

        # Act
        value = _get_secret_from_env("my-key")

        # Assert
        assert value == "direct-match"

    def test_get_secret_from_env_uppercase_priority(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If direct key not found, uppercase is tried next."""
        # Arrange - don't set direct key, only uppercase
        monkeypatch.delenv("my-key", raising=False)
        monkeypatch.setenv("MY-KEY", "uppercase-value")

        # Act
        value = _get_secret_from_env("my-key")

        # Assert
        assert value == "uppercase-value"

    def test_get_secret_case_insensitive_variations(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret handles various case combinations."""
        # Arrange
        test_cases = [
            ("lowercase-key", "lowercase_key", "value1"),
            ("UPPERCASE-KEY", "UPPERCASE_KEY", "value2"),
            ("Mixed-Case-Key", "MIXED_CASE_KEY", "value3"),
        ]

        for input_key, env_key, expected_value in test_cases:
            monkeypatch.setenv(env_key, expected_value)

            # Act
            value = _get_secret_from_env(input_key)

            # Assert
            assert value == expected_value

    def test_secret_not_found_error_is_exception(self) -> None:
        """SecretNotFoundError is a proper Exception subclass."""
        # Arrange
        error = SecretNotFoundError("test message")

        # Assert
        assert isinstance(error, Exception)
        assert str(error) == "test message"

    @pytest.mark.skipif(
        os.getenv("AZURE_KEY_VAULT_URL") is None,
        reason="Azure Key Vault not configured",
    )
    def test_get_secret_azure_provider_requires_vault_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret() with Azure provider requires AZURE_KEY_VAULT_URL."""
        # Arrange
        monkeypatch.setenv("SECRET_PROVIDER", "azure")
        monkeypatch.delenv("AZURE_KEY_VAULT_URL", raising=False)

        # Act & Assert
        with pytest.raises(RuntimeError, match="AZURE_KEY_VAULT_URL"):
            get_secret("any-key")

    def test_get_secret_preserves_special_characters(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret preserves special characters in secret values."""
        # Arrange
        special_value = "p@ssw0rd!#$%^&*()_+-=[]{}|;:',.<>?/~`"
        monkeypatch.setenv("special-key", special_value)

        # Act
        value = _get_secret_from_env("special-key")

        # Assert
        assert value == special_value

    def test_get_secret_whitespace_handling(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret preserves leading/trailing whitespace."""
        # Arrange
        whitespace_value = "  value with spaces  "
        monkeypatch.setenv("whitespace-key", whitespace_value)

        # Act
        value = _get_secret_from_env("whitespace-key")

        # Assert
        assert value == whitespace_value


class TestGetSecretAzureProvider:
    """Test suite for Azure provider internals (module-level tests)."""

    def test_get_secret_from_env_multiple_keys(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test getting secrets with multiple environment keys."""
        # Arrange
        monkeypatch.setenv("db-password", "secret123")

        # Act
        value = _get_secret_from_env("db-password")

        # Assert
        assert value == "secret123"

    def test_secret_provider_enum_has_correct_values(self) -> None:
        """Verify SecretProvider enum values."""
        # Assert
        assert hasattr(SecretProvider, "AZURE")
        assert hasattr(SecretProvider, "LOCAL")
        assert SecretProvider.AZURE.value == "azure"
        assert SecretProvider.LOCAL.value == "local"

    def test_get_secret_calls_correct_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret delegates to correct provider based on configuration."""
        # When SECRET_PROVIDER env var is not "azure", it uses local provider
        monkeypatch.delenv("SECRET_PROVIDER", raising=False)
        monkeypatch.setenv("test-password", "local-secret")

        # Act
        value = get_secret("test-password")

        # Assert
        assert value == "local-secret"

    def test_secret_error_details_transformation_keys(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Error from _get_secret_from_env includes all key variations."""
        # Arrange
        key = "complex-key-name"

        # Act & Assert
        with pytest.raises(SecretNotFoundError) as exc_info:
            _get_secret_from_env(key)

        error_msg = str(exc_info.value)
        # Should list all attempted keys
        assert "complex-key-name" in error_msg
        assert "COMPLEX" in error_msg or "COMPLEX_KEY_NAME" in error_msg

    def test_get_secret_with_numeric_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret preserves numeric string values."""
        # Arrange
        monkeypatch.setenv("port-number", "5432")

        # Act
        value = _get_secret_from_env("port-number")

        # Assert
        assert value == "5432"
        assert isinstance(value, str)

    def test_get_secret_with_json_like_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret preserves JSON-like values."""
        # Arrange
        json_value = '{"key":"value","nested":{"data":"here"}}'
        monkeypatch.setenv("config-json", json_value)

        # Act
        value = _get_secret_from_env("config-json")

        # Assert
        assert value == json_value
        assert '"key":"value"' in value

    def test_get_secret_hyphen_variations_comprehensive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test all hyphen-to-underscore transformation attempts."""
        # Arrange - set only the transformed lowercase version
        monkeypatch.delenv("my-db-user", raising=False)
        monkeypatch.delenv("MY-DB-USER", raising=False)
        monkeypatch.delenv("MY_DB_USER", raising=False)
        monkeypatch.setenv("my_db_user", "user_value")

        # Act
        value = _get_secret_from_env("my-db-user")

        # Assert
        assert value == "user_value"

    def test_get_azure_client_raises_on_missing_vault_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_get_azure_client raises RuntimeError when AZURE_KEY_VAULT_URL not set."""
        # Arrange
        monkeypatch.delenv("AZURE_KEY_VAULT_URL", raising=False)

        # Act & Assert
        with pytest.raises(RuntimeError, match="AZURE_KEY_VAULT_URL"):
            from appkit_commons.configuration.secret_provider import (
                _get_azure_client,
            )

            _get_azure_client.cache_clear()
            _get_azure_client()

    def test_get_secret_from_env_tries_all_variations(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_get_secret_from_env tries variations in correct order."""
        # Arrange - set varied keys to check priority
        monkeypatch.delenv("key", raising=False)
        monkeypatch.delenv("KEY", raising=False)
        monkeypatch.delenv("key_with_underscore", raising=False)
        monkeypatch.setenv("KEY_WITH_UNDERSCORE", "found-at-uppercase")

        # Act
        value = _get_secret_from_env("key-with-underscore")

        # Assert
        assert value == "found-at-uppercase"

    def test_get_secret_azure_missing_vault_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret raises RuntimeError when using Azure but VAULT_URL not set."""
        # Arrange - simulate Azure provider without vault URL
        monkeypatch.setenv("SECRET_PROVIDER", "azure")
        monkeypatch.delenv("AZURE_KEY_VAULT_URL", raising=False)

        # This should raise an error when trying to get the Azure client
        # We need to patch the import to test this
        def mock_get_azure_client():
            raise RuntimeError(
                "Environment variable 'AZURE_KEY_VAULT_URL' must be set to use "
                "SecretProvider.AZURE"
            )

        with patch(
            "appkit_commons.configuration.secret_provider._get_azure_client",
            side_effect=mock_get_azure_client,
        ):
            # Act & Assert
            with pytest.raises(RuntimeError, match="AZURE_KEY_VAULT_URL"):
                get_secret("any-key")

    def test_get_secret_with_empty_string_from_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_get_secret_from_env returns empty string value."""
        # Arrange
        monkeypatch.setenv("empty-secret", "")

        # Act
        value = _get_secret_from_env("empty-secret")

        # Assert
        assert value == ""
        assert isinstance(value, str)


class TestSecretProvider:
    """Test suite for SecretProvider."""

    def test_get_secret_from_env_direct_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Getting secret with exact key match succeeds."""
        # Arrange
        monkeypatch.setenv("my-secret-key", "secret-value")

        # Act
        value = _get_secret_from_env("my-secret-key")

        # Assert
        assert value == "secret-value"

    def test_get_secret_from_env_uppercase(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Getting secret falls back to uppercase key."""
        # Arrange
        monkeypatch.setenv("MY_SECRET_KEY", "uppercase-value")

        # Act
        value = _get_secret_from_env("my_secret_key")

        # Assert
        assert value == "uppercase-value"

    def test_get_secret_from_env_dash_to_underscore(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Getting secret converts dashes to underscores and uppercases."""
        # Arrange
        monkeypatch.setenv("MY_SECRET_KEY", "transformed-value")

        # Act
        value = _get_secret_from_env("my-secret-key")

        # Assert
        assert value == "transformed-value"

    def test_get_secret_from_env_dash_to_underscore_lowercase(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Getting secret tries lowercase dash-to-underscore transformation."""
        # Arrange
        monkeypatch.setenv("my_secret_key", "lowercase-transformed")

        # Act
        value = _get_secret_from_env("my-secret-key")

        # Assert
        assert value == "lowercase-transformed"

    def test_get_secret_from_env_not_found_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Getting non-existent secret raises SecretNotFoundError."""
        # Ensure the key doesn't exist
        monkeypatch.delenv("NONEXISTENT_KEY", raising=False)

        # Act & Assert
        with pytest.raises(SecretNotFoundError, match="not found in environment"):
            _get_secret_from_env("nonexistent-key")

    def test_get_secret_from_env_error_lists_attempts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Error message lists all attempted key variations."""
        # Arrange
        monkeypatch.delenv("MISSING_KEY", raising=False)

        # Act & Assert
        with pytest.raises(SecretNotFoundError) as exc_info:
            _get_secret_from_env("missing-key")

        error_msg = str(exc_info.value)
        assert "missing-key" in error_msg
        assert "MISSING-KEY" in error_msg
        assert "MISSING_KEY" in error_msg

    def test_get_secret_local_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_secret() uses local provider when SECRET_PROVIDER=local."""
        # Arrange
        monkeypatch.setenv("SECRET_PROVIDER", "local")
        monkeypatch.setenv("test-key", "test-value")

        # Act
        value = get_secret("test-key")

        # Assert
        assert value == "test-value"

    def test_get_secret_defaults_to_local(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret() defaults to local provider if not specified."""
        # Arrange
        monkeypatch.delenv("SECRET_PROVIDER", raising=False)
        monkeypatch.setenv("default-key", "default-value")

        # Act
        value = get_secret("default-key")

        # Assert
        assert value == "default-value"

    def test_secret_prefix_constant(self) -> None:
        """SECRET constant is defined correctly."""
        # Assert
        assert SECRET == "secret:"

    def test_secret_provider_enum_values(self) -> None:
        """SecretProvider enum has correct values."""
        # Assert
        assert SecretProvider.AZURE == "azure"
        assert SecretProvider.LOCAL == "local"

    def test_get_secret_from_env_empty_value_returns_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Getting secret with empty string value returns empty string."""
        # Arrange
        monkeypatch.setenv("empty-key", "")

        # Act
        value = _get_secret_from_env("empty-key")

        # Assert
        assert value == ""

    def test_get_secret_from_env_priority_order(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret_from_env tries keys in priority order."""
        # Arrange - set multiple variations, direct key should win
        monkeypatch.setenv("my-key", "direct-match")
        monkeypatch.setenv("MY-KEY", "uppercase-match")
        monkeypatch.setenv("MY_KEY", "transformed-match")

        # Act
        value = _get_secret_from_env("my-key")

        # Assert
        assert value == "direct-match"

    def test_get_secret_from_env_uppercase_priority(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If direct key not found, uppercase is tried next."""
        # Arrange - don't set direct key, only uppercase
        monkeypatch.delenv("my-key", raising=False)
        monkeypatch.setenv("MY-KEY", "uppercase-value")

        # Act
        value = _get_secret_from_env("my-key")

        # Assert
        assert value == "uppercase-value"

    def test_get_secret_case_insensitive_variations(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret handles various case combinations."""
        # Arrange
        test_cases = [
            ("lowercase-key", "lowercase_key", "value1"),
            ("UPPERCASE-KEY", "UPPERCASE_KEY", "value2"),
            ("Mixed-Case-Key", "MIXED_CASE_KEY", "value3"),
        ]

        for input_key, env_key, expected_value in test_cases:
            monkeypatch.setenv(env_key, expected_value)

            # Act
            value = _get_secret_from_env(input_key)

            # Assert
            assert value == expected_value

    def test_secret_not_found_error_is_exception(self) -> None:
        """SecretNotFoundError is a proper Exception subclass."""
        # Arrange
        error = SecretNotFoundError("test message")

        # Assert
        assert isinstance(error, Exception)
        assert str(error) == "test message"

    @pytest.mark.skipif(
        os.getenv("AZURE_KEY_VAULT_URL") is None,
        reason="Azure Key Vault not configured",
    )
    def test_get_secret_azure_provider_requires_vault_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret() with Azure provider requires AZURE_KEY_VAULT_URL."""
        # Arrange
        monkeypatch.setenv("SECRET_PROVIDER", "azure")
        monkeypatch.delenv("AZURE_KEY_VAULT_URL", raising=False)

        # Act & Assert
        with pytest.raises(RuntimeError, match="AZURE_KEY_VAULT_URL"):
            get_secret("any-key")

    def test_get_secret_preserves_special_characters(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret preserves special characters in secret values."""
        # Arrange
        special_value = "p@ssw0rd!#$%^&*()_+-=[]{}|;:',.<>?/~`"
        monkeypatch.setenv("special-key", special_value)

        # Act
        value = _get_secret_from_env("special-key")

        # Assert
        assert value == special_value

    def test_get_secret_whitespace_handling(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret preserves leading/trailing whitespace."""
        # Arrange
        whitespace_value = "  value with spaces  "
        monkeypatch.setenv("whitespace-key", whitespace_value)

        # Act
        value = _get_secret_from_env("whitespace-key")

        # Assert
        assert value == whitespace_value
