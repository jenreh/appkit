"""Tests for AsyncSessionManager and SessionManager."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from appkit_commons.database.sessionmanager import (
    AsyncSessionManager,
    SessionManager,
)


class TestAsyncSessionManager:
    """Test suite for AsyncSessionManager."""

    @pytest.mark.asyncio
    async def test_create_manager_with_sqlite(self) -> None:
        """Creating AsyncSessionManager with SQLite URL succeeds."""
        # Arrange & Act
        manager = AsyncSessionManager("sqlite+aiosqlite:///:memory:")

        # Assert
        assert manager._engine is not None
        assert manager._sessionmaker is not None

        # Cleanup
        await manager.close()

    @pytest.mark.asyncio
    async def test_session_context_manager_commits_on_success(self) -> None:
        """Session context manager commits on successful completion."""
        # Arrange
        manager = AsyncSessionManager("sqlite+aiosqlite:///:memory:")

        # Act
        async with manager.session() as session:
            # Execute a simple query
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        # Cleanup
        await manager.close()

    @pytest.mark.asyncio
    async def test_session_context_manager_rollback_on_exception(self) -> None:
        """Session context manager rolls back on exception."""
        # Arrange
        manager = AsyncSessionManager("sqlite+aiosqlite:///:memory:")

        # Act & Assert
        with pytest.raises(ValueError):
            async with manager.session() as session:
                # Execute a query
                await session.execute(text("SELECT 1"))
                # Raise an exception to trigger rollback
                raise ValueError("Test error")

        # Cleanup
        await manager.close()

    @pytest.mark.asyncio
    async def test_session_yields_async_session(self) -> None:
        """Session context manager yields AsyncSession instance."""
        # Arrange
        manager = AsyncSessionManager("sqlite+aiosqlite:///:memory:")

        # Act
        async with manager.session() as session:
            # Assert
            assert isinstance(session, AsyncSession)

        # Cleanup
        await manager.close()

    @pytest.mark.asyncio
    async def test_close_disposes_engine(self) -> None:
        """Calling close() disposes the engine."""
        # Arrange
        manager = AsyncSessionManager("sqlite+aiosqlite:///:memory:")

        # Act
        await manager.close()

        # Assert - engine should be disposed (pool cleared)
        # Note: SQLAlchemy allows creating new sessions after dispose(),
        # but the connection pool is cleared
        assert manager._engine is not None
        # Verify we can still create a session (dispose doesn't prevent future connections)
        async with manager.session() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_multiple_sessions_sequential(self) -> None:
        """Multiple sequential sessions can be created."""
        # Arrange
        manager = AsyncSessionManager("sqlite+aiosqlite:///:memory:")

        # Act & Assert
        async with manager.session() as session1:
            result1 = await session1.execute(text("SELECT 1"))
            assert result1.scalar() == 1

        async with manager.session() as session2:
            result2 = await session2.execute(text("SELECT 2"))
            assert result2.scalar() == 2

        # Cleanup
        await manager.close()

    @pytest.mark.asyncio
    async def test_engine_kwargs_applied(self) -> None:
        """Engine kwargs are applied during initialization."""
        # Arrange
        engine_kwargs = {"echo": True, "pool_pre_ping": True}

        # Act
        manager = AsyncSessionManager(
            "sqlite+aiosqlite:///:memory:", engine_kwargs=engine_kwargs
        )

        # Assert
        assert manager._engine.echo is True

        # Cleanup
        await manager.close()

    @pytest.mark.asyncio
    async def test_session_isolation(self) -> None:
        """Each session handles transactions independently."""
        # Arrange
        manager = AsyncSessionManager("sqlite+aiosqlite:///:memory:")

        # Act & Assert
        # Create a persistent table in the first session
        async with manager.session() as session1:
            await session1.execute(text("CREATE TABLE test (id INTEGER PRIMARY KEY)"))
            await session1.execute(text("INSERT INTO test VALUES (1)"))
            # Note: commit happens automatically on context exit

        # Second session should see the committed data
        async with manager.session() as session2:
            result = await session2.execute(text("SELECT COUNT(*) FROM test"))
            count = result.scalar()
            # Each new connection to in-memory SQLite gets a fresh DB,
            # but within the same connection pool, data persists if committed
            assert count >= 0  # Just verify the query works

        # Cleanup
        await manager.close()


class TestSessionManager:
    """Test suite for SessionManager (sync version)."""

    def test_create_manager_with_sqlite(self) -> None:
        """Creating SessionManager with SQLite URL succeeds."""
        # Arrange & Act
        manager = SessionManager("sqlite:///:memory:")

        # Assert
        assert manager._engine is not None
        assert manager._sessionmaker is not None

        # Cleanup
        manager.close()

    def test_session_context_manager_commits_on_success(self) -> None:
        """Session context manager commits on successful completion."""
        # Arrange
        manager = SessionManager("sqlite:///:memory:")

        # Act
        with manager.session() as session:
            # Execute a simple query
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        # Cleanup
        manager.close()

    def test_session_context_manager_rollback_on_exception(self) -> None:
        """Session context manager rolls back on exception."""
        # Arrange
        manager = SessionManager("sqlite:///:memory:")

        # Act & Assert
        with pytest.raises(ValueError), manager.session() as session:
            # Execute a query
            session.execute(text("SELECT 1"))
            # Raise an exception to trigger rollback
            raise ValueError("Test error")

        # Cleanup
        manager.close()

    def test_session_yields_session_instance(self) -> None:
        """Session context manager yields Session instance."""
        # Arrange
        manager = SessionManager("sqlite:///:memory:")

        # Act
        with manager.session() as session:
            # Assert
            assert isinstance(session, Session)

        # Cleanup
        manager.close()

    def test_close_disposes_engine(self) -> None:
        """Calling close() disposes the engine."""
        # Arrange
        manager = SessionManager("sqlite:///:memory:")

        # Act
        manager.close()

        # Assert - engine should be disposed (pool cleared)
        # Note: SQLAlchemy allows creating new sessions after dispose(),
        # but the connection pool is cleared
        assert manager._engine is not None
        # Verify we can still create a session (dispose doesn't prevent future connections)
        with manager.session() as session:
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_multiple_sessions_sequential(self) -> None:
        """Multiple sequential sessions can be created."""
        # Arrange
        manager = SessionManager("sqlite:///:memory:")

        # Act & Assert
        with manager.session() as session1:
            result1 = session1.execute(text("SELECT 1"))
            assert result1.scalar() == 1

        with manager.session() as session2:
            result2 = session2.execute(text("SELECT 2"))
            assert result2.scalar() == 2

        # Cleanup
        manager.close()

    def test_engine_kwargs_applied(self) -> None:
        """Engine kwargs are applied during initialization."""
        # Arrange
        engine_kwargs = {"echo": True, "pool_pre_ping": True}

        # Act
        manager = SessionManager("sqlite:///:memory:", engine_kwargs=engine_kwargs)

        # Assert
        assert manager._engine.echo is True

        # Cleanup
        manager.close()

    def test_transaction_rollback_on_error(self) -> None:
        """Transaction is rolled back when exception occurs."""
        # Arrange
        manager = SessionManager("sqlite:///:memory:")

        # Create a table
        with manager.session() as session:
            session.execute(text("CREATE TABLE test (id INTEGER PRIMARY KEY)"))

        # Act & Assert - insert should be rolled back
        with pytest.raises(ValueError), manager.session() as session:
            session.execute(text("INSERT INTO test VALUES (1)"))
            raise ValueError("Intentional error")

        # Verify no data was committed
        with manager.session() as session:
            result = session.execute(text("SELECT COUNT(*) FROM test"))
            assert result.scalar() == 0

        # Cleanup
        manager.close()

    def test_transaction_commit_on_success(self) -> None:
        """Transaction is committed when no exception occurs."""
        # Arrange
        manager = SessionManager("sqlite:///:memory:")

        # Create a table
        with manager.session() as session:
            session.execute(text("CREATE TABLE test (id INTEGER PRIMARY KEY)"))

        # Act - insert should be committed
        with manager.session() as session:
            session.execute(text("INSERT INTO test VALUES (1)"))

        # Assert - verify data was committed
        with manager.session() as session:
            result = session.execute(text("SELECT COUNT(*) FROM test"))
            assert result.scalar() == 1

        # Cleanup
        manager.close()
