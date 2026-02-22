"""Tests for OAuthStateRepository."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_user.authentication.backend.database.entities import OAuthStateEntity


class TestOAuthStateRepository:
    """Test suite for OAuthStateRepository."""

    @pytest.mark.asyncio
    async def test_find_valid_by_state_and_provider(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """find_valid_by_state_and_provider returns valid state."""
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        state_entity = await oauth_state_factory(
            provider="github", state="state_abc123", expires_at=expires_at
        )

        found = await oauth_state_repository.find_valid_by_state_and_provider(
            async_session, "state_abc123", "github"
        )

        assert found is not None
        assert found.id == state_entity.id
        assert found.state == "state_abc123"
        assert found.provider == "github"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("provider", "state", "search_provider", "search_state", "is_expired"),
        [
            ("github", "expired_state", "github", "expired_state", True),
            ("github", "state_xyz", "azure", "state_xyz", False),
            ("github", "correct_state", "github", "wrong_state", False),
            (None, None, "github", "nonexistent", False),
        ],
    )
    async def test_find_valid_by_state_and_provider_returns_none(
        self,
        async_session: AsyncSession,
        oauth_state_factory,
        oauth_state_repository,
        provider: str | None,
        state: str | None,
        search_provider: str,
        search_state: str,
        is_expired: bool,
    ) -> None:
        """find_valid_by_state_and_provider returns None for invalid cases."""
        if provider and state:
            expiry = datetime.now(UTC) + timedelta(
                minutes=10 if not is_expired else -10
            )
            await oauth_state_factory(provider=provider, state=state, expires_at=expiry)

        found = await oauth_state_repository.find_valid_by_state_and_provider(
            async_session, search_state, search_provider
        )

        assert found is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("verifier", [None, "test_code_verifier_123"])
    async def test_find_valid_with_properties(
        self,
        async_session: AsyncSession,
        oauth_state_factory,
        oauth_state_repository,
        user_factory,
        verifier: str | None,
    ) -> None:
        """find_valid_by_state_and_provider retrieves state with correct properties."""
        user = await user_factory(email="oauth@example.com")
        expires_at = datetime.now(UTC) + timedelta(minutes=10)

        await oauth_state_factory(
            provider="github",
            state="prop_state",
            code_verifier=verifier,
            user=user,
            expires_at=expires_at,
        )

        found = await oauth_state_repository.find_valid_by_state_and_provider(
            async_session, "prop_state", "github"
        )

        assert found is not None
        assert found.user_id == user.id
        assert found.code_verifier == verifier

    @pytest.mark.asyncio
    async def test_find_valid_distinguishes_providers(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """find_valid_by_state_and_provider distinguishes between providers."""
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        # Same state value, different providers
        github_state = await oauth_state_factory(
            provider="github", state="same_state", expires_at=expires_at
        )
        azure_state = await oauth_state_factory(
            provider="azure", state="same_state", expires_at=expires_at
        )

        found_github = await oauth_state_repository.find_valid_by_state_and_provider(
            async_session, "same_state", "github"
        )
        found_azure = await oauth_state_repository.find_valid_by_state_and_provider(
            async_session, "same_state", "azure"
        )

        assert found_github is not None
        assert found_azure is not None
        assert found_github.id == github_state.id
        assert found_azure.id == azure_state.id
        assert found_github.id != found_azure.id

    @pytest.mark.asyncio
    async def test_delete_expired_logic(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """delete_expired removes only expired states."""
        expired_time = datetime.now(UTC) - timedelta(minutes=10)
        valid_time = datetime.now(UTC) + timedelta(minutes=10)

        # Create mix of expired and valid states
        expired1 = await oauth_state_factory(
            provider="github", state="expired_1", expires_at=expired_time
        )
        expired2 = await oauth_state_factory(
            provider="azure", state="expired_2", expires_at=expired_time
        )
        valid_state = await oauth_state_factory(
            provider="github", state="valid", expires_at=valid_time
        )

        # Test boundary condition (expired exactly now or slightly in past)
        boundary_state = await oauth_state_factory(
            provider="github", state="boundary", expires_at=datetime.now(UTC)
        )

        deleted_count = await oauth_state_repository.delete_expired(async_session)

        # Expect 2 definitely expired + 1 boundary state (likely expired by execution time)
        assert deleted_count >= 2

        # Verify expired states are gone
        result = await async_session.execute(
            select(OAuthStateEntity).where(
                OAuthStateEntity.id.in_([expired1.id, expired2.id, boundary_state.id])
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
        valid_time = datetime.now(UTC) + timedelta(minutes=10)
        await oauth_state_factory(
            provider="github", state="valid1", expires_at=valid_time
        )

        deleted_count = await oauth_state_repository.delete_expired(async_session)

        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_delete_by_session_id(
        self, async_session: AsyncSession, oauth_state_factory, oauth_state_repository
    ) -> None:
        """delete_by_session_id removes all states for a session."""
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

        deleted_count = await oauth_state_repository.delete_by_session_id(
            async_session, session_id
        )

        assert deleted_count == 2

        # Verify states for session_id are gone
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
    @pytest.mark.parametrize("session_id", ["nonexistent_session", ""])
    async def test_delete_by_session_id_no_match(
        self,
        async_session: AsyncSession,
        oauth_state_factory,
        oauth_state_repository,
        session_id: str,
    ) -> None:
        """delete_by_session_id returns 0 when no states match session_id."""
        await oauth_state_factory(
            provider="github", session_id="real_session", state="state1"
        )

        deleted_count = await oauth_state_repository.delete_by_session_id(
            async_session, session_id
        )

        assert deleted_count == 0
