"""Tests for UserRepository."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_user.authentication.backend.database import (
    DefaultUserRoles,
    OAuthAccountEntity,
    get_current_utc_time,
    get_expiration_time,
    get_name_from_email,
    normalize_scope,
)
from appkit_user.authentication.backend.models import UserCreate


class TestHelperFunctions:
    """Test suite for helper functions."""

    def test_get_current_utc_time(self) -> None:
        """get_current_utc_time returns UTC datetime."""
        # Act
        result = get_current_utc_time()

        # Assert
        assert result.tzinfo == UTC
        assert isinstance(result, datetime)

    def test_get_expiration_time(self) -> None:
        """get_expiration_time calculates correct expiration."""
        # Arrange
        duration_seconds = 3600  # 1 hour
        before = datetime.now(UTC)

        # Act
        result = get_expiration_time(duration_seconds)

        # Assert
        after = datetime.now(UTC)
        assert result.tzinfo == UTC
        # Should be roughly 1 hour from the calculation point
        # The function resets seconds/microseconds, so we check the result is in range
        time_diff_from_before = (result - before).total_seconds()
        time_diff_from_after = (result - after).total_seconds()
        # Should be between ~59:00 and ~60:59 seconds difference
        assert 3540 <= time_diff_from_before <= 3720  # 59-61 minutes
        assert 3540 <= time_diff_from_after <= 3720

    def test_normalize_scope_from_list(self) -> None:
        """normalize_scope converts list to space-separated string."""
        # Act
        result = normalize_scope(["read:user", "user:email", "repo"])

        # Assert
        assert result == "read:user user:email repo"

    def test_normalize_scope_from_string(self) -> None:
        """normalize_scope preserves string as-is."""
        # Act
        result = normalize_scope("read:user user:email")

        # Assert
        assert result == "read:user user:email"

    def test_normalize_scope_from_none(self) -> None:
        """normalize_scope returns None for None input."""
        # Act
        result = normalize_scope(None)

        # Assert
        assert result is None

    def test_get_name_from_email_with_fallback(self) -> None:
        """get_name_from_email returns fallback name when provided."""
        # Act
        result = get_name_from_email("user@example.com", "John Doe")

        # Assert
        assert result == "John Doe"

    def test_get_name_from_email_extract_from_email(self) -> None:
        """get_name_from_email extracts username from email when no fallback."""
        # Act
        result = get_name_from_email("john.doe@example.com", None)

        # Assert
        assert result == "john.doe"

    def test_get_name_from_email_with_empty_fallback(self) -> None:
        """get_name_from_email extracts from email when fallback is empty."""
        # Act
        result = get_name_from_email("alice@test.com", "")

        # Assert
        assert result == "alice"

    def test_get_name_from_email_with_whitespace_fallback(self) -> None:
        """get_name_from_email extracts from email when fallback is whitespace."""
        # Act
        result = get_name_from_email("bob@test.com", "   ")

        # Assert
        assert result == "bob"


class TestUserRepository:
    """Test suite for UserRepository."""

    @pytest.mark.asyncio
    async def test_find_by_email_existing_user(
        self, async_session: AsyncSession, user_factory, user_repository
    ) -> None:
        """find_by_email returns existing user."""
        # Arrange
        user = await user_factory(email="find@example.com")

        # Act
        found = await user_repository.find_by_email(async_session, "find@example.com")

        # Assert
        assert found is not None
        assert found.id == user.id
        assert found.email == "find@example.com"

    @pytest.mark.asyncio
    async def test_find_by_email_nonexistent_user(
        self, async_session: AsyncSession, user_repository
    ) -> None:
        """find_by_email returns None for nonexistent user."""
        # Act
        found = await user_repository.find_by_email(
            async_session, "nonexistent@example.com"
        )

        # Assert
        assert found is None

    @pytest.mark.asyncio
    async def test_find_by_email_and_password_success(
        self, async_session: AsyncSession, user_with_password_factory, user_repository
    ) -> None:
        """find_by_email_and_password returns user with correct credentials."""
        # Arrange
        password = "CorrectPassword123!"  # noqa: S105
        user = await user_with_password_factory(
            email="login@example.com", password=password
        )

        # Act
        found = await user_repository.find_by_email_and_password(
            async_session, "login@example.com", password
        )

        # Assert
        assert found is not None
        assert found.id == user.id

    @pytest.mark.asyncio
    async def test_find_by_email_and_password_wrong_password(
        self, async_session: AsyncSession, user_with_password_factory, user_repository
    ) -> None:
        """find_by_email_and_password returns None for wrong password."""
        # Arrange
        await user_with_password_factory(
            email="wrong@example.com", password="CorrectPass123!"
        )

        # Act
        found = await user_repository.find_by_email_and_password(
            async_session, "wrong@example.com", "WrongPassword"
        )

        # Assert
        assert found is None

    @pytest.mark.asyncio
    async def test_find_by_email_and_password_inactive_user(
        self, async_session: AsyncSession, user_with_password_factory, user_repository
    ) -> None:
        """find_by_email_and_password returns None for inactive user."""
        # Arrange
        await user_with_password_factory(
            email="inactive@example.com", password="Pass123!", is_active=False
        )

        # Act
        found = await user_repository.find_by_email_and_password(
            async_session, "inactive@example.com", "Pass123!"
        )

        # Assert
        assert found is None

    @pytest.mark.asyncio
    async def test_find_by_email_and_password_unverified_user(
        self, async_session: AsyncSession, user_with_password_factory, user_repository
    ) -> None:
        """find_by_email_and_password returns None for unverified user."""
        # Arrange
        await user_with_password_factory(
            email="unverified@example.com", password="Pass123!", is_verified=False
        )

        # Act
        found = await user_repository.find_by_email_and_password(
            async_session, "unverified@example.com", "Pass123!"
        )

        # Assert
        assert found is None

    @pytest.mark.asyncio
    async def test_get_login_status_by_credentials_success(
        self, async_session: AsyncSession, user_with_password_factory, user_repository
    ) -> None:
        """get_login_status_by_credentials returns user and success status."""
        # Arrange
        password = "ValidPass123!"  # noqa: S105
        user = await user_with_password_factory(
            email="status@example.com", password=password
        )

        # Act
        found_user, status = await user_repository.get_login_status_by_credentials(
            async_session, "status@example.com", password
        )

        # Assert
        assert found_user is not None
        assert found_user.id == user.id
        assert status == "success"

    @pytest.mark.asyncio
    async def test_get_login_status_by_credentials_invalid(
        self, async_session: AsyncSession, user_with_password_factory, user_repository
    ) -> None:
        """get_login_status_by_credentials returns invalid_credentials status."""
        # Arrange
        await user_with_password_factory(
            email="invalid@example.com", password="Pass123!"
        )

        # Act
        found_user, status = await user_repository.get_login_status_by_credentials(
            async_session, "invalid@example.com", "WrongPassword"
        )

        # Assert
        assert found_user is None
        assert status == "invalid_credentials"

    @pytest.mark.asyncio
    async def test_get_login_status_by_credentials_inactive(
        self, async_session: AsyncSession, user_with_password_factory, user_repository
    ) -> None:
        """get_login_status_by_credentials returns inactive status."""
        # Arrange
        await user_with_password_factory(
            email="inactive@example.com", password="Pass123!", is_active=False
        )

        # Act
        found_user, status = await user_repository.get_login_status_by_credentials(
            async_session, "inactive@example.com", "Pass123!"
        )

        # Assert
        assert found_user is None
        assert status == "inactive"

    @pytest.mark.asyncio
    async def test_get_login_status_by_credentials_not_verified(
        self, async_session: AsyncSession, user_with_password_factory, user_repository
    ) -> None:
        """get_login_status_by_credentials returns not_verified status."""
        # Arrange
        await user_with_password_factory(
            email="notverified@example.com", password="Pass123!", is_verified=False
        )

        # Act
        found_user, status = await user_repository.get_login_status_by_credentials(
            async_session, "notverified@example.com", "Pass123!"
        )

        # Assert
        assert found_user is None
        assert status == "not_verified"

    @pytest.mark.asyncio
    async def test_validate_user_for_login_success(
        self, user_factory, user_repository
    ) -> None:
        """validate_user_for_login returns success for valid user."""
        # Arrange
        user = await user_factory(is_active=True, is_verified=True)

        # Act
        can_login, status = user_repository.validate_user_for_login(user)

        # Assert
        assert can_login is True
        assert status == "success"

    @pytest.mark.asyncio
    async def test_validate_user_for_login_inactive(
        self, user_factory, user_repository
    ) -> None:
        """validate_user_for_login returns inactive status."""
        # Arrange
        user = await user_factory(is_active=False, is_verified=True)

        # Act
        can_login, status = user_repository.validate_user_for_login(user)

        # Assert
        assert can_login is False
        assert status == "inactive"

    @pytest.mark.asyncio
    async def test_validate_user_for_login_not_verified(
        self, user_factory, user_repository
    ) -> None:
        """validate_user_for_login returns not_verified status."""
        # Arrange
        user = await user_factory(is_active=True, is_verified=False)

        # Act
        can_login, status = user_repository.validate_user_for_login(user)

        # Assert
        assert can_login is False
        assert status == "not_verified"

    @pytest.mark.asyncio
    async def test_validate_and_raise_for_oauth_login_inactive_raises(
        self, user_factory, user_repository
    ) -> None:
        """_validate_and_raise_for_oauth_login raises ValueError for inactive user."""
        # Arrange
        user = await user_factory(is_active=False, is_verified=True)

        # Act & Assert
        with pytest.raises(ValueError, match="Your account has been deactivated"):
            await user_repository._validate_and_raise_for_oauth_login(user)  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_validate_and_raise_for_oauth_login_not_verified_raises(
        self, user_factory, user_repository
    ) -> None:
        """_validate_and_raise_for_oauth_login raises ValueError for unverified user."""
        # Arrange
        user = await user_factory(is_active=True, is_verified=False)

        # Act & Assert
        with pytest.raises(ValueError, match="Your account has not been verified"):
            await user_repository._validate_and_raise_for_oauth_login(user)  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_validate_and_raise_for_oauth_login_success(
        self, user_factory, user_repository
    ) -> None:
        """_validate_and_raise_for_oauth_login does not raise for valid user."""
        # Arrange
        user = await user_factory(is_active=True, is_verified=True)

        # Act & Assert - should not raise
        await user_repository._validate_and_raise_for_oauth_login(user)  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_create_new_user(
        self, async_session: AsyncSession, user_repository
    ) -> None:
        """create_new_user creates user with correct fields."""
        # Arrange
        user_create = UserCreate(
            email="new@example.com",
            name="New User",
            password="SecurePass123!",
            is_verified=True,
            is_admin=False,
            is_active=True,
        )

        # Act
        created = await user_repository.create_new_user(async_session, user_create)

        # Assert
        assert created.id is not None
        assert created.email == "new@example.com"
        assert created.name == "New User"
        assert created.is_verified is True
        assert created.is_admin is False
        assert created.is_active is True
        assert created.check_password("SecurePass123!") is True

    @pytest.mark.asyncio
    async def test_create_new_user_extracts_name_from_email(
        self, async_session: AsyncSession, user_repository
    ) -> None:
        """create_new_user extracts name from email when not provided."""
        # Arrange
        user_create = UserCreate(email="extracted@example.com", password="Pass123!")

        # Act
        created = await user_repository.create_new_user(async_session, user_create)

        # Assert
        assert created.name == "extracted"

    @pytest.mark.asyncio
    async def test_create_new_user_assigns_default_role(
        self, async_session: AsyncSession, user_repository
    ) -> None:
        """create_new_user assigns default USER role when not specified."""
        # Arrange
        user_create = UserCreate(email="role@example.com", password="Pass123!")

        # Act
        created = await user_repository.create_new_user(async_session, user_create)

        # Assert
        assert DefaultUserRoles.USER in created.roles

    @pytest.mark.asyncio
    async def test_update_from_model(
        self, async_session: AsyncSession, user_factory, user_repository
    ) -> None:
        """update_from_model updates existing user."""
        # Arrange
        user = await user_factory(email="old@example.com", name="Old Name")
        user_update = UserCreate(
            user_id=user.id,
            email="updated@example.com",
            name="Updated Name",
            is_verified=False,
        )

        # Act
        updated = await user_repository.update_from_model(async_session, user_update)

        # Assert
        assert updated is not None
        assert updated.id == user.id
        assert updated.email == "updated@example.com"
        assert updated.name == "Updated Name"
        assert updated.is_verified is False

    @pytest.mark.asyncio
    async def test_update_from_model_nonexistent_user(
        self, async_session: AsyncSession, user_repository
    ) -> None:
        """update_from_model returns None for nonexistent user."""
        # Arrange
        user_update = UserCreate(
            user_id=99999, email="nonexistent@example.com", password="Pass123!"
        )

        # Act
        result = await user_repository.update_from_model(async_session, user_update)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_from_model_updates_password(
        self, async_session: AsyncSession, user_with_password_factory, user_repository
    ) -> None:
        """update_from_model updates password when provided."""
        # Arrange
        user = await user_with_password_factory(
            email="pass@example.com", password="OldPass123!"
        )
        user_update = UserCreate(
            user_id=user.id, email="pass@example.com", password="NewPass456!"
        )

        # Act
        updated = await user_repository.update_from_model(async_session, user_update)

        # Assert
        assert updated is not None
        assert updated.check_password("NewPass456!") is True
        assert updated.check_password("OldPass123!") is False

    @pytest.mark.asyncio
    async def test_update_password_success(
        self, async_session: AsyncSession, user_with_password_factory, user_repository
    ) -> None:
        """update_password changes password successfully."""
        # Arrange
        old_password = "OldPassword123!"  # noqa: S105
        new_password = "NewPassword456!"  # noqa: S105
        user = await user_with_password_factory(password=old_password)

        # Act
        updated = await user_repository.update_password(
            async_session, user.id, new_password, old_password
        )

        # Assert
        assert updated is not None
        assert updated.check_password(new_password) is True
        assert updated.check_password(old_password) is False

    @pytest.mark.asyncio
    async def test_update_password_wrong_old_password_raises(
        self, async_session: AsyncSession, user_with_password_factory, user_repository
    ) -> None:
        """update_password raises ValueError for incorrect old password."""
        # Arrange
        user = await user_with_password_factory(password="CorrectPass123!")

        # Act & Assert
        with pytest.raises(ValueError, match="Old password is incorrect"):
            await user_repository.update_password(
                async_session, user.id, "NewPass456!", "WrongOldPass"
            )

    @pytest.mark.asyncio
    async def test_update_password_nonexistent_user(
        self, async_session: AsyncSession, user_repository
    ) -> None:
        """update_password returns None for nonexistent user."""
        # Act
        result = await user_repository.update_password(
            async_session, 99999, "NewPass", "OldPass"
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_find_all_paginated(
        self, async_session: AsyncSession, user_factory, user_repository
    ) -> None:
        """find_all_paginated returns paginated users."""
        # Arrange
        await user_factory(email="user1@example.com")
        await user_factory(email="user2@example.com")
        await user_factory(email="user3@example.com")

        # Act
        users = await user_repository.find_all_paginated(
            async_session, limit=2, offset=0
        )

        # Assert
        assert len(users) == 2

    @pytest.mark.asyncio
    async def test_find_all_paginated_offset(
        self, async_session: AsyncSession, user_factory, user_repository
    ) -> None:
        """find_all_paginated respects offset parameter."""
        # Arrange
        await user_factory(email="a@example.com")
        await user_factory(email="b@example.com")
        await user_factory(email="c@example.com")

        # Act
        users = await user_repository.find_all_paginated(
            async_session, limit=2, offset=1
        )

        # Assert
        assert len(users) == 2
        # Should skip first user alphabetically

    @pytest.mark.asyncio
    async def test_get_or_create_oauth_user_creates_new_user(
        self,
        async_session: AsyncSession,
        user_repository,
        mock_github_user_response,
        mock_github_token_response,
    ) -> None:
        """get_or_create_oauth_user creates new user when no existing OAuth account."""
        # Act
        user = await user_repository.get_or_create_oauth_user(
            async_session,
            mock_github_user_response,
            "github",
            mock_github_token_response,
        )

        # Assert
        assert user.id is not None
        assert user.email == mock_github_user_response["email"]
        assert user.is_verified is True
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_get_or_create_oauth_user_links_existing_user(
        self,
        async_session: AsyncSession,
        user_factory,
        user_repository,
        mock_github_user_response,
        mock_github_token_response,
    ) -> None:
        """get_or_create_oauth_user links to existing user with same email."""
        # Arrange
        existing_user = await user_factory(email=mock_github_user_response["email"])

        # Act
        user = await user_repository.get_or_create_oauth_user(
            async_session,
            mock_github_user_response,
            "github",
            mock_github_token_response,
        )

        # Assert
        assert user.id == existing_user.id
        # Verify OAuth account was created

        result = await async_session.execute(
            select(OAuthAccountEntity).where(OAuthAccountEntity.user_id == user.id)
        )
        oauth_account = result.scalars().first()
        assert oauth_account is not None
        assert oauth_account.provider == "github"

    @pytest.mark.asyncio
    async def test_get_or_create_oauth_user_updates_existing_oauth_user(
        self,
        async_session: AsyncSession,
        user_factory,
        oauth_account_factory,
        user_repository,
        mock_github_user_response,
        mock_github_token_response,
    ) -> None:
        """get_or_create_oauth_user updates existing OAuth account."""
        # Arrange
        user = await user_factory(email=mock_github_user_response["email"])
        oauth_account = await oauth_account_factory(
            user=user,
            provider="github",
            account_id=str(mock_github_user_response["id"]),
            access_token="old_token",
        )

        # Act
        updated_user = await user_repository.get_or_create_oauth_user(
            async_session,
            mock_github_user_response,
            "github",
            mock_github_token_response,
        )

        # Assert
        assert updated_user.id == user.id
        # Verify token was updated
        await async_session.refresh(oauth_account)
        assert oauth_account.access_token == mock_github_token_response["access_token"]

    @pytest.mark.asyncio
    async def test_get_or_create_oauth_user_inactive_user_raises(
        self,
        async_session: AsyncSession,
        user_factory,
        oauth_account_factory,
        user_repository,
        mock_github_user_response,
        mock_github_token_response,
    ) -> None:
        """get_or_create_oauth_user raises for inactive user."""
        # Arrange
        user = await user_factory(
            email=mock_github_user_response["email"], is_active=False
        )
        await oauth_account_factory(
            user=user,
            provider="github",
            account_id=str(mock_github_user_response["id"]),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="account has been deactivated"):
            await user_repository.get_or_create_oauth_user(
                async_session,
                mock_github_user_response,
                "github",
                mock_github_token_response,
            )

    @pytest.mark.asyncio
    async def test_get_or_create_oauth_user_unverified_user_raises(
        self,
        async_session: AsyncSession,
        user_factory,
        oauth_account_factory,
        user_repository,
        mock_github_user_response,
        mock_github_token_response,
    ) -> None:
        """get_or_create_oauth_user raises for unverified user."""
        # Arrange
        user = await user_factory(
            email=mock_github_user_response["email"], is_verified=False
        )
        await oauth_account_factory(
            user=user,
            provider="github",
            account_id=str(mock_github_user_response["id"]),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="account has not been verified"):
            await user_repository.get_or_create_oauth_user(
                async_session,
                mock_github_user_response,
                "github",
                mock_github_token_response,
            )

    @pytest.mark.asyncio
    async def test_get_or_create_oauth_user_normalizes_scope(
        self, async_session: AsyncSession, user_repository, mock_github_user_response
    ) -> None:
        """get_or_create_oauth_user normalizes scope from list to string."""
        # Arrange
        token_with_list_scope = {
            "access_token": "token123",
            "token_type": "Bearer",
            "scope": ["read:user", "user:email"],
            "expires_in": 3600,
        }

        # Act
        user = await user_repository.get_or_create_oauth_user(
            async_session, mock_github_user_response, "github", token_with_list_scope
        )

        # Assert
        result = await async_session.execute(
            select(OAuthAccountEntity).where(OAuthAccountEntity.user_id == user.id)
        )
        oauth_account = result.scalars().first()
        assert oauth_account.scope == "read:user user:email"

    @pytest.mark.asyncio
    async def test_get_or_create_oauth_user_handles_expires_in(
        self, async_session: AsyncSession, user_repository, mock_github_user_response
    ) -> None:
        """get_or_create_oauth_user sets expiration from expires_in."""
        # Arrange
        token_with_expiry = {
            "access_token": "token123",
            "token_type": "Bearer",
            "expires_in": 7200,  # 2 hours
        }

        # Act
        user = await user_repository.get_or_create_oauth_user(
            async_session, mock_github_user_response, "github", token_with_expiry
        )

        # Assert

        result = await async_session.execute(
            select(OAuthAccountEntity).where(OAuthAccountEntity.user_id == user.id)
        )
        oauth_account = result.scalars().first()
        assert oauth_account.expires_at is not None
        # Expiration should be roughly 2 hours from now
        # Handle both naive and aware datetimes (SQLite may return naive)
        now = datetime.now(UTC)
        expires_at = oauth_account.expires_at
        if expires_at.tzinfo:
            expires_ts = expires_at.timestamp()
        else:
            expires_ts = expires_at.replace(tzinfo=UTC).timestamp()
        now_ts = now.timestamp()
        time_diff = expires_ts - now_ts
        # Allow wider range due to base time truncation in get_expiration_time
        assert 7000 <= time_diff <= 7300
