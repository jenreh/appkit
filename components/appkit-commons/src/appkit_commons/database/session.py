import contextlib
import logging
from collections.abc import AsyncGenerator, Iterator
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from appkit_commons.database.configuration import DatabaseConfig
from appkit_commons.database.sessionmanager import (
    AsyncSessionManager,
    SessionManager,
)
from appkit_commons.registry import service_registry

logger = logging.getLogger(__name__)


def _get_db_config() -> DatabaseConfig:
    """Get database configuration from registry."""
    db_config = service_registry().get(DatabaseConfig)
    if db_config is None:
        logger.error("DatabaseConfig not found in registry")
        raise RuntimeError("DatabaseConfig not initialized in registry")
    return db_config


def _get_engine_kwargs() -> dict[str, Any]:
    """Get engine configuration kwargs."""
    db_config = _get_db_config()

    if db_config.type == "postgres":
        return {
            "pool_size": db_config.pool_size,
            "max_overflow": db_config.max_overflow,
            "echo": db_config.echo,
            "pool_pre_ping": True,
        }

    return {}


# if app_config.testing:
#     _engine_kwargs["poolclass"] = NullPool  # type: ignore
#     _engine_kwargs["echo"] = app_config.database.echo
#     _engine_kwargs.pop("pool_size")
#     _engine_kwargs.pop("max_overflow")


# Create a database engine
@lru_cache(maxsize=1)
def get_async_session_manager() -> AsyncSessionManager:
    db_config = _get_db_config()
    engine_kwargs = _get_engine_kwargs()
    return AsyncSessionManager(db_config.url, **engine_kwargs)


@lru_cache(maxsize=1)
def get_session_manager() -> SessionManager:
    db_config = _get_db_config()
    engine_kwargs = _get_engine_kwargs()
    return SessionManager(db_config.url, **engine_kwargs)


@contextlib.asynccontextmanager
async def get_asyncdb_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_async_session_manager().session() as session:
        yield session


def get_db_session() -> Iterator[Session]:
    with get_session_manager().session() as session:
        yield session


def get_db_engine() -> Engine:
    return get_session_manager().get_engine()  # type: ignore
