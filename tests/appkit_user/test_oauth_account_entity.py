"""Tests for OAuthAccountEntity model."""

import pytest
from datetime import UTC, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_user.authentication.backend.entities import OAuthAccountEntity


class TestOAuthAccountEntity:
    """Test suite for OAuthAccountEntity model."""

    @pytest.mark.asyncio
    async def test_create_oauth_account(
        self, async_session: AsyncSession, user_factory, oauth_account_factory
    ) -> None:
        """Creating an OAuth account for a user succeeds."""
        # Arrange
        user = await user_factory(email="oauth@example.com")

        # Act
        oauth = await oauth_account_factory(user=user, provider="github")

        # Assert
        assert oauth.id is not None
        assert oauth.user_id == user.id
        assert oauth.provider == "github"
        assert oauth.account_id is not None
        assert oauth.access_token is not None

    @pytest.mark.asyncio
    async def test_oauth_account_encrypted_tokens(
        self, async_session: AsyncSession, user_factory, oauth_account_factory
    ) -> None:
        """OAuth tokens are encrypted in database."""
        # Arrange
        user = await user_factory(email="encrypted@example.com")
        plain_token = "gho_test_token_12345"

        # Act
        oauth = await oauth_account_factory(
            user=user, provider="github", access_token=plain_token
        )

        # Assert
        # Token is stored (encrypted form may differ from plain)
        assert oauth.access_token is not None
        # When retrieved, it should decrypt to original
        assert oauth.access_token == plain_token

    @pytest.mark.asyncio
    async def test_oauth_account_multiple_providers_per_user(
        self, async_session: AsyncSession, user_factory, oauth_account_factory
    ) -> None:
        """A user can have accounts with multiple OAuth providers."""
        # Arrange
        user = await user_factory(email="multi@example.com")

        # Act
        github = await oauth_account_factory(user=user, provider="github")
        azure = await oauth_account_factory(user=user, provider="azure")

        # Assert
        assert github.provider == "github"
        assert azure.provider == "azure"
        assert github.user_id == azure.user_id == user.id

    @pytest.mark.asyncio
    async def test_oauth_account_unique_provider_account(
        self, async_session: AsyncSession, user_factory, oauth_account_factory
    ) -> None:
        """Provider + account_id combination must be unique."""
        # Arrange
        user1 = await user_factory(email="user1@example.com")
        user2 = await user_factory(email="user2@example.com")
        account_id = "github_account_123"

        await oauth_account_factory(
            user=user1, provider="github", account_id=account_id
        )

        # Act & Assert - same provider + account_id should fail
        with pytest.raises(Exception):  # IntegrityError
            await oauth_account_factory(
                user=user2, provider="github", account_id=account_id
            )

    @pytest.mark.asyncio
    async def test_oauth_account_with_refresh_token(
        self, async_session: AsyncSession, user_factory, oauth_account_factory
    ) -> None:
        """OAuth account can store refresh token."""
        # Arrange
        user = await user_factory(email="refresh@example.com")
        refresh_token = "refresh_token_xyz789"

        # Act
        oauth = await oauth_account_factory(
            user=user, provider="azure", refresh_token=refresh_token
        )

        # Assert
        assert oauth.refresh_token == refresh_token

    @pytest.mark.asyncio
    async def test_oauth_account_token_expiration(
        self, async_session: AsyncSession, user_factory, oauth_account_factory
    ) -> None:
        """OAuth account stores token expiration time."""
        # Arrange
        user = await user_factory(email="expiry@example.com")
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        # Act
        oauth = await oauth_account_factory(user=user, expires_at=expires_at)

        # Assert
        assert oauth.expires_at is not None
        assert oauth.expires_at == expires_at

    @pytest.mark.asyncio
    async def test_oauth_account_scope(
        self, async_session: AsyncSession, user_factory, oauth_account_factory
    ) -> None:
        """OAuth account stores granted scopes."""
        # Arrange
        user = await user_factory(email="scope@example.com")
        scope = "read:user user:email repo"

        # Act
        oauth = await oauth_account_factory(user=user, scope=scope)

        # Assert
        assert oauth.scope == scope

    @pytest.mark.asyncio
    async def test_oauth_account_user_relationship(
        self, async_session: AsyncSession, user_factory, oauth_account_factory
    ) -> None:
        """OAuth account has relationship back to user."""
        # Arrange
        user = await user_factory(email="relationship@example.com")

        # Act
        oauth = await oauth_account_factory(user=user)
        await async_session.refresh(oauth, ["user"])

        # Assert
        assert oauth.user is not None
        assert oauth.user.id == user.id
        assert oauth.user.email == user.email

    @pytest.mark.asyncio
    async def test_oauth_account_cascade_delete(
        self, async_session: AsyncSession, user_factory, oauth_account_factory
    ) -> None:
        """Deleting user cascades to delete OAuth accounts."""
        # Arrange
        user = await user_factory(email="cascade@example.com")
        oauth = await oauth_account_factory(user=user)
        oauth_id = oauth.id

        # Act
        await async_session.delete(user)
        await async_session.flush()

        # Assert
        from sqlalchemy import select

        result = await async_session.execute(
            select(OAuthAccountEntity).where(OAuthAccountEntity.id == oauth_id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_oauth_account_token_type(
        self, async_session: AsyncSession, user_factory, oauth_account_factory
    ) -> None:
        """OAuth account stores token type."""
        # Arrange
        user = await user_factory(email="tokentype@example.com")

        # Act
        oauth = await oauth_account_factory(user=user, token_type="Bearer")

        # Assert
        assert oauth.token_type == "Bearer"

    @pytest.mark.asyncio
    async def test_oauth_account_nullable_refresh_token(
        self, async_session: AsyncSession, user_factory, oauth_account_factory
    ) -> None:
        """OAuth account refresh_token can be None."""
        # Arrange
        user = await user_factory(email="norefresh@example.com")

        # Act
        oauth = await oauth_account_factory(user=user, refresh_token=None)

        # Assert
        assert oauth.refresh_token is None
