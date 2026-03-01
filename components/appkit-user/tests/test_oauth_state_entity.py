"""Tests for OAuthStateEntity model."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_user.authentication.backend.database.entities import OAuthStateEntity


class TestOAuthStateEntity:
    """Test suite for OAuthStateEntity model."""

    @pytest.mark.asyncio
    async def test_create_oauth_state(self, oauth_state_factory) -> None:
        """Creating an OAuth state succeeds."""
        # Act
        state = await oauth_state_factory(provider="github")

        # Assert
        assert state.id is not None
        assert state.provider == "github"
        assert state.state is not None
        assert state.session_id is not None
        assert state.expires_at is not None

    @pytest.mark.asyncio
    async def test_oauth_state_with_user(
        self, user_factory, oauth_state_factory
    ) -> None:
        """OAuth state can be associated with a user."""
        # Arrange
        user = await user_factory(email="state@example.com")

        # Act
        state = await oauth_state_factory(provider="azure", user=user)

        # Assert
        assert state.user_id == user.id

    @pytest.mark.asyncio
    async def test_oauth_state_without_user(self, oauth_state_factory) -> None:
        """OAuth state can exist without a user (guest login)."""
        # Act
        state = await oauth_state_factory(provider="github", user=None)

        # Assert
        assert state.user_id is None

    @pytest.mark.asyncio
    async def test_oauth_state_pkce_code_verifier(self, oauth_state_factory) -> None:
        """OAuth state stores PKCE code_verifier."""
        # Arrange
        verifier = "test_code_verifier_abc123"

        # Act
        state = await oauth_state_factory(code_verifier=verifier)

        # Assert
        assert state.code_verifier == verifier

    @pytest.mark.asyncio
    async def test_oauth_state_nullable_code_verifier(
        self, oauth_state_factory
    ) -> None:
        """OAuth state code_verifier can be None (non-PKCE flow)."""
        # Act
        state = await oauth_state_factory(code_verifier=None)

        # Assert
        assert state.code_verifier is None

    @pytest.mark.asyncio
    async def test_oauth_state_expiration(self, oauth_state_factory) -> None:
        """OAuth state has expiration timestamp."""
        # Arrange
        expires_at = datetime.now(UTC) + timedelta(minutes=10)

        # Act
        state = await oauth_state_factory(expires_at=expires_at)

        # Assert
        assert state.expires_at is not None

        # Handle naive/aware timestamp comparison
        def get_ts(dt: datetime) -> float:
            return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).timestamp()

        assert abs(get_ts(state.expires_at) - get_ts(expires_at)) < 1

    @pytest.mark.asyncio
    async def test_oauth_state_different_providers(self, oauth_state_factory) -> None:
        """OAuth states can be created for different providers."""
        # Act
        github_state = await oauth_state_factory(provider="github")
        azure_state = await oauth_state_factory(provider="azure")

        # Assert
        assert github_state.provider == "github"
        assert azure_state.provider == "azure"
        assert github_state.state != azure_state.state

    @pytest.mark.asyncio
    async def test_oauth_state_user_relationship(
        self, async_session: AsyncSession, user_factory, oauth_state_factory
    ) -> None:
        """OAuth state has relationship to user."""
        # Arrange
        user = await user_factory(email="relationship@example.com")

        # Act
        state = await oauth_state_factory(user=user)
        await async_session.refresh(state, ["user"])

        # Assert
        assert state.user is not None
        assert state.user.id == user.id
        assert state.user.email == user.email

    @pytest.mark.asyncio
    async def test_oauth_state_cascade_on_user_delete(
        self, async_session: AsyncSession, user_factory, oauth_state_factory
    ) -> None:
        """Deleting user sets user_id to NULL (SET NULL cascade)."""
        # Arrange
        user = await user_factory(email="cascade@example.com")
        state = await oauth_state_factory(user=user)
        state_id = state.id

        # Act
        await async_session.delete(user)
        await async_session.flush()

        # Assert - state should still exist but user_id should be NULL
        result = await async_session.execute(
            select(OAuthStateEntity).where(OAuthStateEntity.id == state_id)
        )
        remaining_state = result.scalar_one_or_none()
        assert remaining_state is not None
        assert remaining_state.user_id is None

    @pytest.mark.asyncio
    async def test_oauth_state_index_on_expires_at(self, oauth_state_factory) -> None:
        """OAuth state table has index on expires_at for cleanup queries."""
        # This test verifies the index exists by checking table args
        # Arrange & Act
        state = await oauth_state_factory()

        # Assert - just verify state was created (index is in __table_args__)
        assert state.expires_at is not None
        # The actual index check is at the SQLAlchemy metadata level
        table_args = OAuthStateEntity.__table_args__
        index_names = [idx.name for idx in table_args if hasattr(idx, "name")]
        assert "ix_oauth_states_expires_at" in index_names

    @pytest.mark.asyncio
    async def test_oauth_state_unique_states(self, oauth_state_factory) -> None:
        """Each OAuth state should have a unique state value."""
        # Act
        state1 = await oauth_state_factory()
        state2 = await oauth_state_factory()
        state3 = await oauth_state_factory()

        # Assert
        assert state1.state != state2.state
        assert state2.state != state3.state
        assert state1.state != state3.state
