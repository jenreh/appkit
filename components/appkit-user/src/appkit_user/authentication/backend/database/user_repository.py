from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from appkit_commons.database.base_repository import BaseRepository
from appkit_user.authentication.backend.database.entities import (
    OAuthAccountEntity,
    UserEntity,
)
from appkit_user.authentication.backend.models import UserCreate


# Helper functions for cleaner code
def get_current_utc_time() -> datetime:
    """Get current UTC time."""
    return datetime.now(UTC)


def get_expiration_time(seconds: int) -> datetime:
    """Calculate expiration time from seconds."""
    base_time = get_current_utc_time().replace(second=0, microsecond=0)
    return base_time + timedelta(seconds=seconds)


def normalize_scope(scope_data: Any) -> str | None:
    """Normalize scope data to string format."""
    if isinstance(scope_data, list):
        return " ".join(scope_data)
    if scope_data is not None:
        return str(scope_data)
    return None


def get_name_from_email(
    email: str | None, fallback_name: str | None = None
) -> str | None:
    """Extract name from email address if name is empty or None."""
    if fallback_name and fallback_name.strip():
        return fallback_name
    if email and "@" in email:
        return email.split("@")[0]
    return fallback_name


class DefaultUserRoles(StrEnum):
    """Default user roles."""

    USER = "user"
    ADMIN = "admin"
    GUEST = "guest"


class UserRepository(BaseRepository[UserEntity, AsyncSession]):
    @property
    def model_class(self) -> type[UserEntity]:
        return UserEntity

    async def get_or_create_oauth_user(
        self, session: AsyncSession, user_info: dict, provider: str, token: dict
    ) -> UserEntity:
        """Get or create user from OAuth info, with async-safe relationship loading."""

        stmt = (
            select(OAuthAccountEntity)
            .where(
                OAuthAccountEntity.provider == provider,
                OAuthAccountEntity.account_id == str(user_info["id"]),
            )
            .options(selectinload(OAuthAccountEntity.user))
        )
        result = await session.execute(stmt)
        oauth_account = result.scalars().first()

        if oauth_account:
            return await self._update_existing_oauth_user(
                session, oauth_account, user_info, token
            )

        email_from_provider = user_info.get("email")
        target_user: UserEntity | None = None

        if email_from_provider:
            target_user = await self.find_by_email(session, email_from_provider)

        if target_user:
            # Check if existing user is allowed to login
            await self._validate_and_raise_for_oauth_login(target_user)

            target_user.name = get_name_from_email(
                email_from_provider, user_info.get("name")
            )
            target_user.avatar_url = user_info.get("avatar_url", target_user.avatar_url)
            target_user.is_verified = True
            target_user.last_login = get_current_utc_time()
        else:
            target_user = UserEntity(
                email=email_from_provider,
                name=get_name_from_email(email_from_provider, user_info.get("name")),
                avatar_url=user_info.get("avatar_url"),
                is_verified=True,
                is_active=True,
                roles=[DefaultUserRoles.USER],
                last_login=get_current_utc_time(),
            )
            session.add(target_user)
            await session.flush()
            await session.refresh(target_user)

        if target_user is None:
            raise ValueError(
                "User could not be determined or created for OAuth association."
            )

        await self._create_oauth_account(
            session, target_user, provider, user_info, token
        )

        await session.refresh(target_user)
        return target_user

    async def _update_existing_oauth_user(
        self,
        session: AsyncSession,
        oauth_account: OAuthAccountEntity,
        user_info: dict,
        token: dict,
    ) -> UserEntity:
        """Update an existing user from OAuth account."""
        user = oauth_account.user

        # Check if existing user is allowed to login
        await self._validate_and_raise_for_oauth_login(user)

        user.name = get_name_from_email(user_info.get("email"), user_info.get("name"))
        if user_info.get("email") is not None:
            user.email = user_info.get("email")
        user.avatar_url = user_info.get("avatar_url", user.avatar_url)
        user.last_login = get_current_utc_time()
        user.is_verified = True

        oauth_account.access_token = token.get(
            "access_token", oauth_account.access_token
        )
        oauth_account.refresh_token = token.get("refresh_token")
        oauth_account.account_email = user_info.get(
            "email", oauth_account.account_email
        )

        new_scope_data = token.get("scope")
        oauth_account.scope = normalize_scope(new_scope_data)

        if "expires_in" in token and token.get("expires_in") is not None:
            oauth_account.expires_at = get_expiration_time(token["expires_in"])
        elif "expires_in" in token and token.get("expires_in") is None:
            oauth_account.expires_at = None

        await session.flush()
        await session.refresh(user)
        return oauth_account.user

    async def _create_oauth_account(
        self,
        session: AsyncSession,
        target_user: UserEntity,
        provider: str,
        user_info: dict,
        token: dict,
    ) -> OAuthAccountEntity:
        """Create a new OAuth account for a user."""
        email_from_provider = user_info.get("email")

        new_oauth_account = OAuthAccountEntity(
            user_id=target_user.id,
            provider=provider,
            account_id=str(user_info["id"]),
            account_email=email_from_provider,
            access_token=token.get("access_token", ""),
            refresh_token=token.get("refresh_token"),
            token_type=token.get("token_type", "Bearer"),
            scope=normalize_scope(token.get("scope")),
        )

        if "expires_in" in token and token.get("expires_in") is not None:
            new_oauth_account.expires_at = get_expiration_time(token["expires_in"])

        session.add(new_oauth_account)
        await session.flush()
        await session.refresh(new_oauth_account)
        return new_oauth_account

    async def find_by_email(
        self, session: AsyncSession, email: str
    ) -> UserEntity | None:
        """Find a user by email."""
        stmt = select(UserEntity).where(UserEntity.email == email)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def find_by_email_and_password(
        self, session: AsyncSession, email: str, password: str
    ) -> UserEntity | None:
        """Get user by email and password."""
        stmt = select(UserEntity).where(
            UserEntity.email == email,
            UserEntity.is_active.is_(True),
            UserEntity.is_verified.is_(True),
        )
        result = await session.execute(stmt)
        user = result.scalars().first()

        if user and user.check_password(password):
            return user
        return None

    async def get_login_status_by_credentials(
        self, session: AsyncSession, email: str, password: str
    ) -> tuple[UserEntity | None, str]:
        """Get user by email and password, return user and status message.

        Returns:
            Tuple of (user_entity, status_message)
            - If login successful: (user_entity, "success")
            - If user not found or wrong password: (None, "invalid_credentials")
            - If user exists but inactive: (None, "inactive")
            - If user exists but not verified: (None, "not_verified")
        """
        # First check if user exists with correct password
        stmt = select(UserEntity).where(UserEntity.email == email)
        result = await session.execute(stmt)
        user = result.scalars().first()

        if not user or not user.check_password(password):
            return None, "invalid_credentials"

        # User exists and password is correct, now check status
        if not user.is_active:
            return None, "inactive"

        if not user.is_verified:
            return None, "not_verified"

        return user, "success"

    def validate_user_for_login(self, user: UserEntity) -> tuple[bool, str]:
        """Validate if a user can login.

        Returns:
            Tuple of (can_login, status_message)
            - If user can login: (True, "success")
            - If user is inactive: (False, "inactive")
            - If user is not verified: (False, "not_verified")
        """
        if not user.is_active:
            return False, "inactive"

        if not user.is_verified:
            return False, "not_verified"

        return True, "success"

    async def _validate_and_raise_for_oauth_login(self, user: UserEntity) -> None:
        """Validate user status for OAuth login and raise appropriate exceptions.

        Args:
            user: The user entity to validate

        Raises:
            ValueError: If user is inactive or not verified, with appropriate message
        """
        can_login, status = self.validate_user_for_login(user)
        if not can_login:
            if status == "inactive":
                raise ValueError(
                    "Your account has been deactivated. "
                    "Please contact an administrator."
                )
            if status == "not_verified":
                raise ValueError(
                    "Your account has not been verified. "
                    "Please contact an administrator."
                )

    async def create_new_user(
        self, session: AsyncSession, user: UserCreate
    ) -> UserEntity:
        """Create a new user."""
        new_user = UserEntity(
            email=user.email,
            name=get_name_from_email(user.email, user.name),
            password=user.password,  # Password will be hashed in UserEntity
            avatar_url=user.avatar_url,
            is_verified=user.is_verified,
            is_admin=user.is_admin,
            is_active=user.is_active,
            needs_password_reset=user.needs_password_reset,
            roles=user.roles or [DefaultUserRoles.USER],
            last_login=get_current_utc_time(),
        )

        session.add(new_user)
        await session.flush()
        await session.refresh(new_user)
        return new_user

    async def update_from_model(
        self, session: AsyncSession, user: UserCreate
    ) -> UserEntity | None:
        """Update user information from UserCreate model."""
        user_entity = await self.find_by_id(session, user.user_id)
        if not user_entity:
            return None

        user_entity.name = get_name_from_email(user.email, user.name)
        user_entity.email = user.email
        user_entity.avatar_url = user.avatar_url
        user_entity.is_verified = user.is_verified
        user_entity.is_admin = user.is_admin
        user_entity.is_active = user.is_active
        user_entity.needs_password_reset = user.needs_password_reset
        user_entity.roles = user.roles or [DefaultUserRoles.USER]
        user_entity.last_login = get_current_utc_time()

        if user.password:
            # Password will be hashed in UserEntity
            user_entity.password = user.password

        await session.flush()
        await session.refresh(user_entity)
        return user_entity

    async def update_password(
        self, session: AsyncSession, user_id: int, new_password: str, old_password: str
    ) -> UserEntity | None:
        """Update user password."""
        user = await self.find_by_id(session, user_id)
        if not user:
            return None

        if not user.check_password(old_password):
            raise ValueError("Old password is incorrect")

        user.password = new_password  # This will hash the new password
        await session.flush()
        await session.refresh(user)
        return user

    async def find_all_paginated(
        self, session: AsyncSession, limit: int = 200, offset: int = 0
    ) -> list[UserEntity]:
        """Find all users with pagination."""
        stmt = select(UserEntity).order_by(UserEntity.email).offset(offset).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())


user_repo = UserRepository()
