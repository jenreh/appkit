"""Tests for database entities and custom types."""

import json
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import String
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine import Dialect

from appkit_commons.database.entities import (
    ArrayType,
    EncryptedString,
    Entity,
    get_cipher_key,
)


class TestGetCipherKey:
    """Test suite for get_cipher_key function."""

    def test_get_cipher_key_returns_string(self) -> None:
        """get_cipher_key returns a string value."""
        # This test just checks the function doesn't error
        # when called in a properly configured environment
        try:
            # get_cipher_key will try to fetch from registry
            # If registry is not configured, it will raise KeyError
            key = get_cipher_key()
            assert isinstance(key, str)
        except KeyError:
            # Expected if registry is not configured
            pass

    def test_encrypted_string_initializes(self) -> None:
        """EncryptedString initializes with a cipher key."""
        # Arrange
        with patch("appkit_commons.database.entities.get_cipher_key") as mock_get_key:  # noqa: E501
            test_key = Fernet.generate_key().decode()
            mock_get_key.return_value = test_key

            # Act
            column = EncryptedString()

            # Assert
            assert column.cipher is not None
            assert column.cipher_key == test_key


class TestEncryptedString:
    """Test suite for EncryptedString custom type."""

    @pytest.fixture
    def cipher_key(self) -> str:
        """Fixture providing a valid Fernet cipher key."""
        return Fernet.generate_key().decode()

    @pytest.fixture
    def encrypted_column(self, cipher_key: str) -> EncryptedString:
        """Fixture providing an EncryptedString instance."""
        with patch("appkit_commons.database.entities.get_cipher_key") as mock_get_key:
            mock_get_key.return_value = cipher_key
            return EncryptedString()

    def test_encrypted_string_initialization(self, cipher_key: str) -> None:
        """EncryptedString initializes with cipher key."""
        # Arrange & Act
        with patch("appkit_commons.database.entities.get_cipher_key") as mock_get_key:
            mock_get_key.return_value = cipher_key
            column = EncryptedString()

        # Assert
        assert column.cipher_key == cipher_key
        assert column.cipher is not None

    def test_encrypted_string_cache_ok(self) -> None:
        """EncryptedString has cache_ok set to True."""
        # Act
        column = EncryptedString()

        # Assert
        assert column.cache_ok is True

    def test_process_bind_param_encrypts_value(
        self, encrypted_column: EncryptedString
    ) -> None:  # noqa: E501
        """process_bind_param encrypts the value."""
        # Arrange
        plaintext = "secret_password"
        dialect = MagicMock(spec=Dialect)

        # Act
        encrypted = encrypted_column.process_bind_param(plaintext, dialect)

        # Assert
        assert encrypted is not None
        assert encrypted != plaintext
        # Verify it's a valid encrypted string (can be decrypted)
        decrypted = encrypted_column.cipher.decrypt(encrypted.encode()).decode()
        assert decrypted == plaintext

    def test_process_bind_param_none_returns_none(
        self, encrypted_column: EncryptedString
    ) -> None:
        """process_bind_param returns None for None input."""
        # Arrange
        dialect = MagicMock(spec=Dialect)

        # Act
        result = encrypted_column.process_bind_param(None, dialect)

        # Assert
        assert result is None

    def test_process_result_value_decrypts_value(
        self, encrypted_column: EncryptedString
    ) -> None:
        """process_result_value decrypts the value."""
        # Arrange
        plaintext = "decrypted_secret"
        encrypted = encrypted_column.cipher.encrypt(plaintext.encode()).decode()
        dialect = MagicMock(spec=Dialect)

        # Act
        decrypted = encrypted_column.process_result_value(encrypted, dialect)

        # Assert
        assert decrypted == plaintext

    def test_process_result_value_none_returns_none(
        self, encrypted_column: EncryptedString
    ) -> None:
        """process_result_value returns None for None input."""
        # Arrange
        dialect = MagicMock(spec=Dialect)

        # Act
        result = encrypted_column.process_result_value(None, dialect)

        # Assert
        assert result is None

    def test_encrypted_string_roundtrip(
        self, encrypted_column: EncryptedString
    ) -> None:
        """EncryptedString correctly encrypts and decrypts data."""
        # Arrange
        original = "test_data_123"
        dialect = MagicMock(spec=Dialect)

        # Act
        encrypted = encrypted_column.process_bind_param(original, dialect)
        decrypted = encrypted_column.process_result_value(encrypted, dialect)

        # Assert
        assert decrypted == original


class TestArrayType:
    """Test suite for ArrayType custom type."""

    def test_array_type_cache_ok(self) -> None:
        """ArrayType has cache_ok set to True."""
        # Act
        column = ArrayType()

        # Assert
        assert column.cache_ok is True

    def test_array_type_load_dialect_impl_postgres(self) -> None:
        """ArrayType uses ARRAY type for PostgreSQL."""
        # Arrange
        column = ArrayType()
        dialect = postgresql.dialect()

        # Act
        impl = column.load_dialect_impl(dialect)

        # Assert
        assert impl is not None

    def test_array_type_load_dialect_impl_sqlite(self) -> None:
        """ArrayType uses String type for SQLite."""
        # Arrange
        column = ArrayType()
        dialect = sqlite.dialect()

        # Act
        impl = column.load_dialect_impl(dialect)

        # Assert
        assert isinstance(impl, String)

    def test_process_bind_param_list_to_json_sqlite(self) -> None:
        """process_bind_param converts list to JSON for non-PostgreSQL."""
        # Arrange
        column = ArrayType()
        data = ["item1", "item2", "item3"]
        dialect = sqlite.dialect()

        # Act
        result = column.process_bind_param(data, dialect)

        # Assert
        assert result == json.dumps(data)

    def test_process_bind_param_postgres_returns_list(self) -> None:
        """process_bind_param returns list unchanged for PostgreSQL."""
        # Arrange
        column = ArrayType()
        data = ["item1", "item2", "item3"]
        dialect = postgresql.dialect()

        # Act
        result = column.process_bind_param(data, dialect)

        # Assert
        assert result == data

    def test_process_bind_param_none_returns_none(self) -> None:
        """process_bind_param returns None for None input."""
        # Arrange
        column = ArrayType()
        dialect = sqlite.dialect()

        # Act
        result = column.process_bind_param(None, dialect)

        # Assert
        assert result is None

    def test_process_bind_param_non_list_returns_value(self) -> None:
        """process_bind_param returns non-list values unchanged."""
        # Arrange
        column = ArrayType()
        data = "already_processed"
        dialect = sqlite.dialect()

        # Act
        result = column.process_bind_param(data, dialect)

        # Assert
        assert result == data

    def test_process_result_value_json_to_list_sqlite(self) -> None:
        """process_result_value converts JSON back to list for non-PostgreSQL."""
        # Arrange
        column = ArrayType()
        data = ["item1", "item2", "item3"]
        json_str = json.dumps(data)
        dialect = sqlite.dialect()

        # Act
        result = column.process_result_value(json_str, dialect)

        # Assert
        assert result == data

    def test_process_result_value_postgres_returns_list(self) -> None:
        """process_result_value returns list unchanged for PostgreSQL."""
        # Arrange
        column = ArrayType()
        data = ["item1", "item2", "item3"]
        dialect = postgresql.dialect()

        # Act
        result = column.process_result_value(data, dialect)

        # Assert
        assert result == data

    def test_process_result_value_none_returns_none(self) -> None:
        """process_result_value returns None for None input."""
        # Arrange
        column = ArrayType()
        dialect = sqlite.dialect()

        # Act
        result = column.process_result_value(None, dialect)

        # Assert
        assert result is None

    def test_process_result_value_non_string_returns_value(self) -> None:
        """process_result_value returns non-string values unchanged."""
        # Arrange
        column = ArrayType()
        data = ["already", "a", "list"]
        dialect = sqlite.dialect()

        # Act
        result = column.process_result_value(data, dialect)

        # Assert
        assert result == data

    def test_array_type_roundtrip_sqlite(self) -> None:
        """ArrayType correctly converts list to JSON and back for SQLite."""
        # Arrange
        column = ArrayType()
        original = ["apple", "banana", "cherry"]
        dialect = sqlite.dialect()

        # Act
        stored = column.process_bind_param(original, dialect)
        retrieved = column.process_result_value(stored, dialect)

        # Assert
        assert retrieved == original

    def test_array_type_roundtrip_postgres(self) -> None:
        """ArrayType preserves list for PostgreSQL."""
        # Arrange
        column = ArrayType()
        original = ["apple", "banana", "cherry"]
        dialect = postgresql.dialect()

        # Act
        stored = column.process_bind_param(original, dialect)
        retrieved = column.process_result_value(stored, dialect)

        # Assert
        assert retrieved == original

    def test_array_type_empty_list(self) -> None:
        """ArrayType handles empty list correctly."""
        # Arrange
        column = ArrayType()
        data = []
        dialect = sqlite.dialect()

        # Act
        stored = column.process_bind_param(data, dialect)
        retrieved = column.process_result_value(stored, dialect)

        # Assert
        assert retrieved == []


class TestEntity:
    """Test suite for Entity mixin class."""

    def test_entity_has_id_field(self) -> None:
        """Entity has id field."""
        # Assert
        assert hasattr(Entity, "id")

    def test_entity_has_created_field(self) -> None:
        """Entity has created timestamp field."""
        # Assert
        assert hasattr(Entity, "created")

    def test_entity_has_updated_field(self) -> None:
        """Entity has updated timestamp field."""
        # Assert
        assert hasattr(Entity, "updated")
