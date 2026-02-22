"""Tests for session module functions."""

import inspect
import logging
from collections.abc import Generator

import pytest
from sqlalchemy import Engine

from appkit_commons.database.configuration import DatabaseConfig
from appkit_commons.database.session import (
    _get_db_config,
    _get_engine_kwargs,
    get_async_session_manager,
    get_asyncdb_session,
    get_db_engine,
    get_db_session,
    get_session_manager,
)
from appkit_commons.registry import ServiceRegistry

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def clear_session_caches() -> Generator[None, None, None]:
    """Clear lru_cache for session manager functions."""
    get_async_session_manager.cache_clear()
    get_session_manager.cache_clear()
    yield
    # Clear after test as well
    get_async_session_manager.cache_clear()
    get_session_manager.cache_clear()


class TestGetDbConfig:
    """Test suite for _get_db_config function."""

    def test_get_db_config_returns_config_from_registry(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """_get_db_config returns DatabaseConfig from registry."""
        # Arrange
        db_config = DatabaseConfig(
            url="sqlite:///:memory:",
            type="sqlite",
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
        )
        clean_service_registry.register(db_config)

        # Act
        result = _get_db_config()

        # Assert
        assert result is db_config
        assert result.url == "sqlite:///:memory:"

    def test_get_db_config_raises_when_not_configured(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """_get_db_config raises RuntimeError when DatabaseConfig not in registry."""
        # Act & Assert
        with pytest.raises(RuntimeError, match="DatabaseConfig not initialized"):
            _get_db_config()


class TestGetEngineKwargs:
    """Test suite for _get_engine_kwargs function."""

    def test_get_engine_kwargs_postgresql_returns_pool_config(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """_get_engine_kwargs returns PostgreSQL pool configuration."""
        # Arrange
        db_config = DatabaseConfig(
            url="postgresql://user:pass@localhost/db",
            type="postgresql",
            echo=True,
            pool_size=20,
            max_overflow=30,
            pool_recycle=1800,
        )
        clean_service_registry.register(db_config)

        # Act
        kwargs = _get_engine_kwargs()

        # Assert
        assert kwargs["pool_size"] == 20
        assert kwargs["max_overflow"] == 30
        assert kwargs["echo"] is True
        assert kwargs["pool_pre_ping"] is True
        assert kwargs["pool_recycle"] == 1800
        assert "connect_args" in kwargs

    def test_get_engine_kwargs_sqlite_returns_empty(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """_get_engine_kwargs returns empty dict for SQLite."""
        # Arrange
        db_config = DatabaseConfig(
            url="sqlite:///:memory:",
            type="sqlite",
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
        )
        clean_service_registry.register(db_config)

        # Act
        kwargs = _get_engine_kwargs()

        # Assert
        assert kwargs == {}

    def test_get_engine_kwargs_postgresql_with_echo_false(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """_get_engine_kwargs respects echo=False for PostgreSQL."""
        # Arrange
        db_config = DatabaseConfig(
            url="postgresql://user:pass@localhost/db",
            type="postgresql",
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_recycle=1800,
        )
        clean_service_registry.register(db_config)

        # Act
        kwargs = _get_engine_kwargs()

        # Assert
        assert kwargs["echo"] is False


class TestGetAsyncSessionManager:
    """Test suite for get_async_session_manager function."""

    def test_get_async_session_manager_creates_manager(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """get_async_session_manager creates AsyncSessionManager instance."""
        # Arrange
        db_config = DatabaseConfig(
            url="sqlite+aiosqlite:///:memory:",
            type="sqlite",
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
        )
        clean_service_registry.register(db_config)

        # Act
        manager = get_async_session_manager()

        # Assert
        assert manager is not None

    def test_get_async_session_manager_caches_instance(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """get_async_session_manager caches the AsyncSessionManager instance."""
        # Arrange
        db_config = DatabaseConfig(
            url="sqlite+aiosqlite:///:memory:",
            type="sqlite",
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
        )
        clean_service_registry.register(db_config)

        # Act
        manager1 = get_async_session_manager()
        manager2 = get_async_session_manager()

        # Assert
        assert manager1 is manager2


class TestGetSessionManager:
    """Test suite for get_session_manager function."""

    def test_get_session_manager_creates_manager(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """get_session_manager creates SessionManager instance."""
        # Arrange
        db_config = DatabaseConfig(
            url="sqlite:///:memory:",
            type="sqlite",
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
        )
        clean_service_registry.register(db_config)

        # Act
        manager = get_session_manager()

        # Assert
        assert manager is not None

    def test_get_session_manager_caches_instance(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """get_session_manager caches the SessionManager instance."""
        # Arrange
        db_config = DatabaseConfig(
            url="sqlite:///:memory:",
            type="sqlite",
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
        )
        clean_service_registry.register(db_config)

        # Act
        manager1 = get_session_manager()
        manager2 = get_session_manager()

        # Assert
        assert manager1 is manager2


class TestGetAsyncdbSession:
    """Test suite for get_asyncdb_session context manager."""

    def test_get_asyncdb_session_is_context_manager(self) -> None:
        """get_asyncdb_session is a context manager function."""
        # Assert - just verify it's a callable that returns a context manager
        assert callable(get_asyncdb_session)


class TestGetDbSession:
    """Test suite for get_db_session generator function."""

    def test_get_db_session_function_signature(self) -> None:
        """get_db_session is a generator function."""
        # Assert
        assert inspect.isgeneratorfunction(get_db_session)

    def test_get_db_session_is_callable(self) -> None:
        """get_db_session is callable."""
        # Assert
        assert callable(get_db_session)


class TestGetDbEngine:
    """Test suite for get_db_engine function."""

    def test_get_db_engine_returns_engine(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """get_db_engine returns Engine instance."""
        # Arrange
        db_config = DatabaseConfig(
            url="sqlite:///:memory:",
            type="sqlite",
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
        )
        clean_service_registry.register(db_config)

        # Act
        engine = get_db_engine()

        # Assert
        assert engine is not None
        assert isinstance(engine, Engine)

    def test_get_db_engine_returns_same_engine(
        self, clean_service_registry: ServiceRegistry
    ) -> None:
        """get_db_engine returns the same engine instance (caching)."""
        # Arrange
        db_config = DatabaseConfig(
            url="sqlite:///:memory:",
            type="sqlite",
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
        )
        clean_service_registry.register(db_config)

        # Act
        engine1 = get_db_engine()
        engine2 = get_db_engine()

        # Assert
        assert engine1 is engine2
