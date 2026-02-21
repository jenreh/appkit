"""Root conftest.py – shared fixtures for all test packages.

IMPORTANT: The service_registry must be pre-populated with DatabaseConfig
and ReflexConfig BEFORE any entity/model modules are imported, because
they call service_registry().get(...) at module level.
"""

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# ── 1. Bootstrap registry BEFORE any other local imports ─────────────────────
from appkit_commons.registry import service_registry
from appkit_commons.database.configuration import DatabaseConfig
from appkit_commons.configuration.configuration import ReflexConfig

TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()


def _bootstrap_registry() -> None:
    """Register required services in the singleton service registry."""
    reg = service_registry()
    if not reg.has(DatabaseConfig):
        db_config = DatabaseConfig(
            type="sqlite",
            name=":memory:",
            encryption_key=SecretStr(TEST_ENCRYPTION_KEY),
        )
        reg.register_as(DatabaseConfig, db_config)
    if not reg.has(ReflexConfig):
        reg.register_as(ReflexConfig, ReflexConfig(deploy_url="http://localhost:3000"))


_bootstrap_registry()

# ── 2. Now safe to import entities ───────────────────────────────────────────
from appkit_commons.database.entities import Base  # noqa: E402


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """Create async SQLite in-memory engine for the test session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine):
    """Provide an AsyncSession for each test, rolling back after."""
    async_session_factory = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session
        await session.rollback()
