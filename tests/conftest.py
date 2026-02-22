"""Root-level test fixtures shared across all test modules.

This conftest provides the foundational test infrastructure:
- Async SQLAlchemy engine and session management (SQLite in-memory)
- HTTP client mocking capabilities
- Service registry cleanup
- Test data generation utilities

Individual package tests extend these fixtures with specialized factories.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
import reflex as rx
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from appkit_commons.configuration.configuration import ReflexConfig
from appkit_commons.database.configuration import DatabaseConfig
from appkit_commons.database.entities import Base
from appkit_commons.registry import ServiceRegistry, service_registry

logger = logging.getLogger(__name__)

# ============================================================================
# Module-level registry bootstrapping
# ============================================================================
# Several model modules (appkit_assistant, appkit_user, appkit_imagecreator)
# call service_registry().get(...) at module level during import.
# We must register configs BEFORE importing model modules.

_registry = service_registry()
if not _registry.has(DatabaseConfig):
    _registry.register(
        DatabaseConfig(
            type="sqlite",
            name=":memory:",
            encryption_key="x6wrrHmIwfEZacK9sOBq5wJOykTDNhYlTdI_lLmmtJw=",
            testing=True,
        )
    )
if not _registry.has(ReflexConfig):
    _registry.register(
        ReflexConfig(
            deploy_url="http://localhost",
            frontend_port=3000,
            backend_port=3031,
        )
    )

# Import all model modules to register tables with Base.metadata
# This must happen AFTER registry bootstrapping
import appkit_assistant.backend.database.models  # noqa: F401
import appkit_imagecreator.backend.models  # noqa: F401
import appkit_user.authentication.backend.entities  # noqa: F401

# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config: Any) -> None:
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")


@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    """Set the event loop policy for the test session."""
    return asyncio.get_event_loop_policy()


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures (SQLite In-Memory)
# ============================================================================


@pytest_asyncio.fixture
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an async SQLite in-memory engine for testing.

    Uses StaticPool to ensure the same connection is reused,
    preventing SQLite from losing in-memory data between transactions.

    Creates tables from both appkit_commons.Base and rx.Model.metadata
    to support all model types in the test suite. ArrayType custom type
    handles both PostgreSQL ARRAY and SQLite JSON compatibility.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Create all tables from both metadata sources
    async with engine.begin() as conn:
        # Create appkit_commons.Base tables (appkit_user models)
        await conn.run_sync(Base.metadata.create_all)
        # Create rx.Model tables (appkit_imagecreator, appkit_assistant models)
        # ArrayType custom type handles both PostgreSQL ARRAY and SQLite JSON
        await conn.run_sync(rx.Model.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture
def async_session_factory(
    async_engine: AsyncEngine,
) -> sessionmaker[AsyncSession]:
    """Create an async session factory for the test engine.

    Configures explicit binds for both Base and rx.Model metadata
    to ensure the session can locate the correct engine for any model.
    """
    return sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
        binds={
            Base: async_engine,
            rx.Model: async_engine,
        },
    )


@pytest_asyncio.fixture
async def async_session(
    async_session_factory: sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async session for each test.

    Each test gets a fresh session that's automatically rolled back
    after the test completes, ensuring test isolation.
    """
    async with async_session_factory() as session, session.begin():
        # Start a transaction, automatic rollback on exit
        yield session


# ============================================================================
# Service Registry Fixtures
# ============================================================================


@pytest.fixture
def clean_service_registry() -> Generator[ServiceRegistry, None, None]:
    """Provide a clean service registry for each test.

    Clears the global singleton registry before and after each test
    to prevent state leakage between tests.
    """
    registry = service_registry()
    registry.clear()
    yield registry
    registry.clear()


# ============================================================================
# Secret Provider Fixtures
# ============================================================================


@pytest.fixture
def mock_secret_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock secret provider to always use local environment variables."""
    monkeypatch.setenv("SECRET_PROVIDER", "local")


@pytest.fixture
def mock_secrets(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Provide mock secrets in environment variables.

    Returns a dict that tests can populate with key-value pairs.
    The fixture automatically sets these as environment variables.
    """
    secrets = {
        "test-api-key": "test-key-12345",
        "test-db-user": "test_user",
        "test-db-password": "test_password",
        "OPENAI_API_KEY": "sk-test-key",
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
        "GOOGLE_API_KEY": "google-test-key",
        "PERPLEXITY_API_KEY": "pplx-test-key",
    }

    for key, value in secrets.items():
        monkeypatch.setenv(key, value)
        # Also set uppercase and underscore variations
        monkeypatch.setenv(key.upper(), value)
        monkeypatch.setenv(key.replace("-", "_").upper(), value)

    return secrets


# ============================================================================
# Test Data Generation Fixtures
# ============================================================================


@pytest.fixture
def faker_instance() -> Faker:
    """Provide a Faker instance for generating test data."""
    Faker.seed(42)  # Reproducible test data
    return Faker()


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for test files."""
    return tmp_path


# ============================================================================
# Logging Fixtures
# ============================================================================


@pytest.fixture
def captured_logs(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    """Capture log output for assertions."""
    caplog.set_level(logging.DEBUG)
    return caplog
