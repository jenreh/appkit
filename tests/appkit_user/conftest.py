"""Package-specific fixtures for appkit-user tests."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import pytest_asyncio
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_user.authentication.backend.entities import (
    OAuthAccountEntity,
    OAuthStateEntity,
    UserEntity,
    UserSessionEntity,
)


# ============================================================================
# User Entity Factories
# ============================================================================


@pytest_asyncio.fixture
async def user_factory(async_session: AsyncSession, faker_instance: Faker):
    """Factory for creating test users."""

    async def _create_user(**kwargs: Any) -> UserEntity:
        """Create a user with optional field overrides."""
        defaults = {
            "email": faker_instance.email(),
            "name": faker_instance.name(),
            "avatar_url": faker_instance.image_url(),
            "is_verified": True,
            "is_active": True,
            "is_admin": False,
            "needs_password_reset": False,
            "roles": ["user"],
        }
        defaults.update(kwargs)

        user = UserEntity(**defaults)
        async_session.add(user)
        await async_session.flush()
        await async_session.refresh(user)
        return user

    return _create_user


@pytest_asyncio.fixture
async def user_with_password_factory(
    async_session: AsyncSession, faker_instance: Faker
):
    """Factory for creating users with passwords."""

    async def _create_user(password: str = "TestPassword123!", **kwargs: Any) -> UserEntity:
        """Create a user with a password."""
        defaults = {
            "email": faker_instance.email(),
            "name": faker_instance.name(),
            "is_verified": True,
            "is_active": True,
        }
        defaults.update(kwargs)

        user = UserEntity(**defaults)
        user.password = password  # Use the setter to hash the password
        async_session.add(user)
        await async_session.flush()
        await async_session.refresh(user)
        return user

    return _create_user


# ============================================================================
# Session Entity Factories
# ============================================================================


@pytest_asyncio.fixture
async def session_factory(async_session: AsyncSession):
    """Factory for creating test user sessions."""

    async def _create_session(
        user: UserEntity,
        session_id: str | None = None,
        expires_at: datetime | None = None,
        **kwargs: Any,
    ) -> UserSessionEntity:
        """Create a session for a user."""
        import secrets

        defaults = {
            "user_id": user.id,
            "session_id": session_id or secrets.token_urlsafe(32),
            "expires_at": expires_at
            or (datetime.now(UTC) + timedelta(hours=24)),
        }
        defaults.update(kwargs)

        session = UserSessionEntity(**defaults)
        async_session.add(session)
        await async_session.flush()
        await async_session.refresh(session)
        return session

    return _create_session


# ============================================================================
# OAuth Entity Factories
# ============================================================================


@pytest_asyncio.fixture
async def oauth_account_factory(async_session: AsyncSession, faker_instance: Faker):
    """Factory for creating OAuth accounts."""

    async def _create_oauth_account(
        user: UserEntity, provider: str = "github", **kwargs: Any
    ) -> OAuthAccountEntity:
        """Create an OAuth account for a user."""
        defaults = {
            "user_id": user.id,
            "provider": provider,
            "account_id": str(faker_instance.random_int(min=1000000, max=9999999)),
            "account_email": faker_instance.email(),
            "access_token": f"gho_{faker_instance.sha256()[:40]}",
            "refresh_token": None,
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
            "token_type": "Bearer",
            "scope": "read:user user:email",
        }
        defaults.update(kwargs)

        oauth_account = OAuthAccountEntity(**defaults)
        async_session.add(oauth_account)
        await async_session.flush()
        await async_session.refresh(oauth_account)
        return oauth_account

    return _create_oauth_account


@pytest_asyncio.fixture
async def oauth_state_factory(async_session: AsyncSession):
    """Factory for creating OAuth states."""

    async def _create_oauth_state(
        provider: str = "github",
        user: UserEntity | None = None,
        **kwargs: Any,
    ) -> OAuthStateEntity:
        """Create an OAuth state for CSRF protection."""
        import secrets

        defaults = {
            "user_id": user.id if user else None,
            "session_id": secrets.token_urlsafe(16),
            "state": secrets.token_urlsafe(32),
            "provider": provider,
            "code_verifier": secrets.token_urlsafe(32),
            "expires_at": datetime.now(UTC) + timedelta(minutes=10),
        }
        defaults.update(kwargs)

        oauth_state = OAuthStateEntity(**defaults)
        async_session.add(oauth_state)
        await async_session.flush()
        await async_session.refresh(oauth_state)
        return oauth_state

    return _create_oauth_state


# ============================================================================
# Repository Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def user_repository(async_session: AsyncSession):
    """Provide UserRepository instance."""
    from appkit_user.authentication.backend.user_repository import UserRepository

    return UserRepository()


@pytest_asyncio.fixture
async def user_session_repository(async_session: AsyncSession):
    """Provide UserSessionRepository instance."""
    from appkit_user.authentication.backend.user_session_repository import (
        UserSessionRepository,
    )

    return UserSessionRepository()


@pytest_asyncio.fixture
async def oauth_state_repository(async_session: AsyncSession):
    """Provide OAuthStateRepository instance."""
    from appkit_user.authentication.backend.oauthstate_repository import (
        OAuthStateRepository,
    )

    return OAuthStateRepository()


# ============================================================================
# Mock OAuth Provider Responses
# ============================================================================


@pytest.fixture
def mock_github_user_response() -> dict[str, Any]:
    """Mock GitHub user API response."""
    return {
        "id": 12345678,
        "login": "testuser",
        "email": "test@example.com",
        "name": "Test User",
        "avatar_url": "https://avatars.githubusercontent.com/u/12345678",
        "bio": "Test bio",
        "company": "Test Company",
    }


@pytest.fixture
def mock_github_token_response() -> dict[str, Any]:
    """Mock GitHub OAuth token response."""
    return {
        "access_token": "gho_test_access_token_1234567890",
        "token_type": "bearer",
        "scope": "read:user,user:email",
    }


@pytest.fixture
def mock_azure_user_response() -> dict[str, Any]:
    """Mock Azure AD user API response."""
    return {
        "id": "azure-user-id-123",
        "userPrincipalName": "test@example.com",
        "displayName": "Test User",
        "mail": "test@example.com",
        "jobTitle": "Developer",
    }


@pytest.fixture
def mock_azure_token_response() -> dict[str, Any]:
    """Mock Azure AD OAuth token response."""
    return {
        "access_token": "azure_access_token_test",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "azure_refresh_token_test",
        "scope": "User.Read",
    }
