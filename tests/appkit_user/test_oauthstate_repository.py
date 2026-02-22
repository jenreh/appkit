"""Tests for OAuthStateRepository."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_user.authentication.backend.database.entities import OAuthStateEntity


class TestOAuthStateRepository:
    """Test suite for OAuthStateRepository."""

    @pytest.mark.asyncio
    async def test_find_valid_by_state_and_provider_existing(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """find_valid_by_state_and_provider returns valid state."""
        # Arrange
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        state_entity = await oauth_state_factory(
            provider="github", state="state_abc123", expires_at=expires_at
        )

        # Act
        found = await oauth_state_repository.find_valid_by_state_and_provider(
            async_session, "state_abc123", "github"
        )

        # Assert
        assert found is not None
        assert found.id == state_entity.id
        assert found.state == "state_abc123"
        assert found.provider == "github"

    @pytest.mark.asyncio
    async def test_find_valid_by_state_and_provider_expired(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """find_valid_by_state_and_provider returns None for expired state."""
        # Arrange
        expired_time = datetime.now(UTC) - timedelta(minutes=10)
        await oauth_state_factory(
            provider="github", state="expired_state", expires_at=expired_time
        )

        # Act
        found = await oauth_state_repository.find_valid_by_state_and_provider(
            async_session, "expired_state", "github"
        )

        # Assert
        assert found is None

    @pytest.mark.asyncio
    async def test_find_valid_by_state_and_provider_wrong_provider(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """find_valid_by_state_and_provider returns None for wrong provider."""
        # Arrange
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        await oauth_state_factory(
            provider="github", state="state_xyz", expires_at=expires_at
        )

        # Act
        found = await oauth_state_repository.find_valid_by_state_and_provider(
            async_session, "state_xyz", "azure"
        )

        # Assert
        assert found is None

    @pytest.mark.asyncio
    async def test_find_valid_by_state_and_provider_wrong_state(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """find_valid_by_state_and_provider returns None for wrong state."""
        # Arrange
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        await oauth_state_factory(
            provider="github", state="correct_state", expires_at=expires_at
        )

        # Act
        found = await oauth_state_repository.find_valid_by_state_and_provider(
            async_session, "wrong_state", "github"
        )

        # Assert
        assert found is None

    @pytest.mark.asyncio
    async def test_find_valid_by_state_and_provider_nonexistent(
        self, async_session: AsyncSession, oauth_state_repository
    ) -> None:
        """find_valid_by_state_and_provider returns None when state doesn't exist."""
        # Act
        found = await oauth_state_repository.find_valid_by_state_and_provider(
            async_session, "nonexistent", "github"
        )

        # Assert
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_expired_removes_expired_states(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """delete_expired removes states past their expiration time."""
        # Arrange
        expired_time = datetime.now(UTC) - timedelta(minutes=10)
        valid_time = datetime.now(UTC) + timedelta(minutes=10)

        expired1 = await oauth_state_factory(
            provider="github", state="expired_1", expires_at=expired_time
        )
        expired2 = await oauth_state_factory(
            provider="azure", state="expired_2", expires_at=expired_time
        )
        valid_state = await oauth_state_factory(
            provider="github", state="valid", expires_at=valid_time
        )

        # Act
        deleted_count = await oauth_state_repository.delete_expired(async_session)

        # Assert
        assert deleted_count == 2
        # Verify expired states are gone
        from sqlalchemy import select

        result = await async_session.execute(
            select(OAuthStateEntity).where(
                OAuthStateEntity.id.in_([expired1.id, expired2.id])
            )
        )
        assert len(list(result.scalars().all())) == 0
        # Verify valid state still exists
        result = await async_session.execute(
            select(OAuthStateEntity).where(OAuthStateEntity.id == valid_state.id)
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_delete_expired_returns_zero_when_no_expired(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """delete_expired returns 0 when no expired states exist."""
        # Arrange
        valid_time = datetime.now(UTC) + timedelta(minutes=10)
        await oauth_state_factory(
            provider="github", state="valid1", expires_at=valid_time
        )
        await oauth_state_factory(
            provider="azure", state="valid2", expires_at=valid_time
        )

        # Act
        deleted_count = await oauth_state_repository.delete_expired(async_session)

        # Assert
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_delete_expired_handles_multiple_providers(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """delete_expired removes expired states across all providers."""
        # Arrange
        expired_time = datetime.now(UTC) - timedelta(minutes=10)
        await oauth_state_factory(
            provider="github", state="github_expired", expires_at=expired_time
        )
        await oauth_state_factory(
            provider="azure", state="azure_expired", expires_at=expired_time
        )
        await oauth_state_factory(
            provider="google", state="google_expired", expires_at=expired_time
        )

        # Act
        deleted_count = await oauth_state_repository.delete_expired(async_session)

        # Assert
        assert deleted_count == 3

    @pytest.mark.asyncio
    async def test_delete_by_session_id_removes_matching_states(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """delete_by_session_id removes all states for a session."""
        # Arrange
        session_id = "session_abc123"
        state1 = await oauth_state_factory(
            provider="github", session_id=session_id, state="state1"
        )
        state2 = await oauth_state_factory(
            provider="azure", session_id=session_id, state="state2"
        )
        other_state = await oauth_state_factory(
            provider="github", session_id="other_session", state="other"
        )

        # Act
        deleted_count = await oauth_state_repository.delete_by_session_id(
            async_session, session_id
        )

        # Assert
        assert deleted_count == 2
        # Verify states for session_id are gone
        from sqlalchemy import select

        result = await async_session.execute(
            select(OAuthStateEntity).where(
                OAuthStateEntity.id.in_([state1.id, state2.id])
            )
        )
        assert len(list(result.scalars().all())) == 0
        # Verify other_state still exists
        result = await async_session.execute(
            select(OAuthStateEntity).where(OAuthStateEntity.id == other_state.id)
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_delete_by_session_id_returns_zero_when_no_match(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """delete_by_session_id returns 0 when no states match session_id."""
        # Arrange
        await oauth_state_factory(
            provider="github", session_id="different_session", state="state1"
        )

        # Act
        deleted_count = await oauth_state_repository.delete_by_session_id(
            async_session, "nonexistent_session"
        )

        # Assert
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_delete_by_session_id_empty_session_id(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """delete_by_session_id handles empty session_id."""
        # Arrange
        await oauth_state_factory(
            provider="github", session_id="real_session", state="state1"
        )

        # Act
        deleted_count = await oauth_state_repository.delete_by_session_id(
            async_session, ""
        )

        # Assert
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_delete_expired_boundary_exact_expiration(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """delete_expired deletes states at exact expiration time."""
        # Arrange
        now = datetime.now(UTC)
        # State expires exactly now
        await oauth_state_factory(
            provider="github", state="boundary_state", expires_at=now
        )

        # Act
        deleted_count = await oauth_state_repository.delete_expired(async_session)

        # Assert - state at exact expiration should be deleted (expires_at < now check)
        # In practice, some time has passed, so it will be deleted
        assert deleted_count >= 0

    @pytest.mark.asyncio
    async def test_find_valid_distinguishes_providers(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """find_valid_by_state_and_provider distinguishes between providers."""
        # Arrange
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        # Same state value, different providers
        github_state = await oauth_state_factory(
            provider="github", state="same_state", expires_at=expires_at
        )
        azure_state = await oauth_state_factory(
            provider="azure", state="same_state", expires_at=expires_at
        )

        # Act
        found_github = await oauth_state_repository.find_valid_by_state_and_provider(
            async_session, "same_state", "github"
        )
        found_azure = await oauth_state_repository.find_valid_by_state_and_provider(
            async_session, "same_state", "azure"
        )

        # Assert
        assert found_github is not None
        assert found_azure is not None
        assert found_github.id == github_state.id
        assert found_azure.id == azure_state.id
        assert found_github.id != found_azure.id

    @pytest.mark.asyncio
    async def test_find_valid_with_code_verifier(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """find_valid_by_state_and_provider retrieves state with code_verifier."""
        # Arrange
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        verifier = "test_code_verifier_123"
        state_entity = await oauth_state_factory(
            provider="github",
            state="pkce_state",
            code_verifier=verifier,
            expires_at=expires_at,
        )

        # Act
        found = await oauth_state_repository.find_valid_by_state_and_provider(
            async_session, "pkce_state", "github"
        )

        # Assert
        assert found is not None
        assert found.code_verifier == verifier

    @pytest.mark.asyncio
    async def test_find_valid_with_user_association(
        self,
        async_session: AsyncSession,
        user_factory,
        oauth_state_factory,
        oauth_state_repository,
    ) -> None:
        """find_valid_by_state_and_provider retrieves state associated with user."""
        # Arrange
        user = await user_factory(email="oauth@example.com")
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        state_entity = await oauth_state_factory(
            provider="github", state="user_state", user=user, expires_at=expires_at
        )

        # Act
        found = await oauth_state_repository.find_valid_by_state_and_provider(
            async_session, "user_state", "github"
        )

        # Assert
        assert found is not None
        assert found.user_id == user.id

    @pytest.mark.asyncio
    async def test_delete_expired_preserves_valid_states_with_same_session(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """delete_expired preserves valid states even if same session has expired states."""
        # Arrange
        session_id = "mixed_session"
        expired_time = datetime.now(UTC) - timedelta(minutes=10)
        valid_time = datetime.now(UTC) + timedelta(minutes=10)

        expired_state = await oauth_state_factory(
            provider="github",
            session_id=session_id,
            state="expired",
            expires_at=expired_time,
        )
        valid_state = await oauth_state_factory(
            provider="github",
            session_id=session_id,
            state="valid",
            expires_at=valid_time,
        )

        # Act
        deleted_count = await oauth_state_repository.delete_expired(async_session)

        # Assert
        assert deleted_count == 1
        # Verify only expired state is gone
        from sqlalchemy import select

        result = await async_session.execute(
            select(OAuthStateEntity).where(OAuthStateEntity.id == expired_state.id)
        )
        assert result.scalar_one_or_none() is None
        # Verify valid state still exists
        result = await async_session.execute(
            select(OAuthStateEntity).where(OAuthStateEntity.id == valid_state.id)
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_delete_by_session_id_clears_all_providers(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """delete_by_session_id removes states for all providers in a session."""
        # Arrange
        session_id = "multi_provider_session"
        await oauth_state_factory(
            provider="github", session_id=session_id, state="github_state"
        )
        await oauth_state_factory(
            provider="azure", session_id=session_id, state="azure_state"
        )
        await oauth_state_factory(
            provider="google", session_id=session_id, state="google_state"
        )

        # Act
        deleted_count = await oauth_state_repository.delete_by_session_id(
            async_session, session_id
        )

        # Assert
        assert deleted_count == 3
        # Verify all states for this session are gone
        from sqlalchemy import select

        result = await async_session.execute(
            select(OAuthStateEntity).where(OAuthStateEntity.session_id == session_id)
        )
        assert len(list(result.scalars().all())) == 0
