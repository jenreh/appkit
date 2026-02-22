"""Tests for database configuration."""

import pytest
from pydantic import SecretStr

from appkit_commons.database.configuration import DatabaseConfig


class TestDatabaseConfig:
    """Test suite for DatabaseConfig."""

    def test_database_config_defaults(self) -> None:
        """DatabaseConfig uses sensible defaults."""
        # Act
        config = DatabaseConfig(
            password=SecretStr("test_pass"),
            encryption_key=SecretStr("test_key"),
        )

        # Assert
        assert config.type == "postgresql"
        assert config.username == "postgres"
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.name == "postgres"
        assert config.pool_size == 10
        assert config.max_overflow == 30
        assert config.pool_recycle == 1800
        assert config.echo is False
        assert config.testing is False
        assert config.ssl_mode == "disable"

    def test_sqlite_url_generation(self) -> None:
        """DatabaseConfig generates correct SQLite URL."""
        # Act
        config = DatabaseConfig(
            type="sqlite",
            name="test.db",
            password=SecretStr(""),
            encryption_key=SecretStr(""),
        )

        # Assert
        assert config.url == "sqlite:///test.db"

    def test_postgresql_url_generation_basic(self) -> None:
        """DatabaseConfig generates correct PostgreSQL URL."""
        # Act
        config = DatabaseConfig(
            type="postgresql",
            username="testuser",
            password=SecretStr("testpass"),
            host="localhost",
            port=5432,
            name="testdb",
            encryption_key=SecretStr(""),
        )

        # Assert
        assert config.url == (
            "postgresql+psycopg://testuser:testpass@localhost:5432/testdb"
        )

    def test_postgresql_url_with_special_char_password(self) -> None:
        """DatabaseConfig properly escapes special characters in password."""
        # Act
        config = DatabaseConfig(
            type="postgresql",
            username="testuser",
            password=SecretStr("pass@word#123"),
            host="localhost",
            port=5432,
            name="testdb",
            encryption_key=SecretStr(""),
        )

        # Assert
        # @ and # should be URL encoded
        assert "pass%40word%23123" in config.url

    def test_postgresql_url_with_ssl_mode_require(self) -> None:
        """DatabaseConfig includes SSL mode in PostgreSQL URL when specified."""
        # Act
        config = DatabaseConfig(
            type="postgresql",
            username="testuser",
            password=SecretStr("testpass"),
            host="localhost",
            port=5432,
            name="testdb",
            encryption_key=SecretStr(""),
            ssl_mode="require",
        )

        # Assert
        assert config.url == (
            "postgresql+psycopg://testuser:testpass@localhost:5432/testdb?sslmode=require"  # noqa: E501
        )

    def test_postgresql_url_with_ssl_mode_verify_full(self) -> None:
        """DatabaseConfig includes verify-full SSL mode in URL."""
        # Act
        config = DatabaseConfig(
            type="postgresql",
            username="testuser",
            password=SecretStr("testpass"),
            host="pg.example.com",
            port=5432,
            name="mydb",
            encryption_key=SecretStr(""),
            ssl_mode="verify-full",
        )

        # Assert
        assert config.url == (
            "postgresql+psycopg://testuser:testpass@pg.example.com:5432/mydb?sslmode=verify-full"  # noqa: E501
        )

    def test_postgresql_url_with_ssl_mode_disable(self) -> None:
        """DatabaseConfig does not include SSL mode when disabled."""
        # Act
        config = DatabaseConfig(
            type="postgresql",
            username="testuser",
            password=SecretStr("testpass"),
            host="localhost",
            port=5432,
            name="testdb",
            encryption_key=SecretStr(""),
            ssl_mode="disable",
        )

        # Assert
        assert "sslmode" not in config.url

    def test_postgresql_url_with_custom_port(self) -> None:
        """DatabaseConfig uses custom port in URL."""
        # Act
        config = DatabaseConfig(
            type="postgresql",
            username="testuser",
            password=SecretStr("testpass"),
            host="db.example.com",
            port=5433,
            name="mydb",
            encryption_key=SecretStr(""),
        )

        # Assert
        assert "5433" in config.url

    def test_unsupported_database_type_raises_error(self) -> None:
        """DatabaseConfig raises ValueError for unsupported database type."""
        # Act & Assert
        config = DatabaseConfig(
            type="mysql",
            password=SecretStr(""),
            encryption_key=SecretStr(""),
        )
        with pytest.raises(ValueError, match="Unsupported database type"):
            _ = config.url

    def test_password_encapsulation(self) -> None:
        """DatabaseConfig stores password as SecretStr."""
        # Act
        config = DatabaseConfig(
            password=SecretStr("secret_password"),
            encryption_key=SecretStr(""),
        )

        # Assert
        assert config.password.get_secret_value() == "secret_password"

    def test_encryption_key_encapsulation(self) -> None:
        """DatabaseConfig stores encryption_key as SecretStr."""
        # Act
        key_value = "encryption_secret"
        config = DatabaseConfig(
            password=SecretStr(""),
            encryption_key=SecretStr(key_value),
        )

        # Assert
        assert config.encryption_key.get_secret_value() == key_value

    def test_database_config_custom_values(self) -> None:
        """DatabaseConfig accepts custom configuration values."""
        # Act
        config = DatabaseConfig(
            type="postgresql",
            username="custom_user",
            password=SecretStr("custom_pass"),
            host="custom.host",
            port=5433,
            name="custom_db",
            encryption_key=SecretStr("custom_key"),
            pool_size=20,
            max_overflow=50,
            pool_recycle=3600,
            echo=True,
            testing=True,
            ssl_mode="require",
        )

        # Assert
        assert config.username == "custom_user"
        assert config.host == "custom.host"
        assert config.port == 5433
        assert config.name == "custom_db"
        assert config.pool_size == 20
        assert config.max_overflow == 50
        assert config.pool_recycle == 3600
        assert config.echo is True
        assert config.testing is True
        assert config.ssl_mode == "require"

    def test_postgresql_url_with_special_username(self) -> None:
        """DatabaseConfig handles special characters in username."""
        # Act
        config = DatabaseConfig(
            type="postgresql",
            username="user@domain",
            password=SecretStr("pass"),
            host="localhost",
            port=5432,
            name="testdb",
            encryption_key=SecretStr(""),
        )

        # Assert - The URL should be properly formed
        assert "postgresql+psycopg://" in config.url

    def test_postgresql_url_with_empty_password(self) -> None:
        """DatabaseConfig handles empty password correctly."""
        # Act
        config = DatabaseConfig(
            type="postgresql",
            username="testuser",
            password=SecretStr(""),
            host="localhost",
            port=5432,
            name="testdb",
            encryption_key=SecretStr(""),
        )

        # Assert
        assert "testuser:@localhost" in config.url

    def test_sqlite_url_with_path(self, tmp_path) -> None:
        """DatabaseConfig handles SQLite with path."""
        # Act
        db_path = str(tmp_path / "database.db")
        config = DatabaseConfig(
            type="sqlite",
            name=db_path,
            password=SecretStr(""),
            encryption_key=SecretStr(""),
        )

        # Assert
        assert config.url == f"sqlite:///{db_path}"
