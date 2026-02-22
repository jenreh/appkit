"""Tests for UserEntity model."""

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_user.authentication.backend.database import UserEntity


class TestUserEntity:
    """Test suite for UserEntity model."""

    @pytest.mark.asyncio
    async def test_create_user_basic(
        self,
        async_session: AsyncSession,
        user_factory,  # noqa: ARG002
    ) -> None:
        """Creating a basic user succeeds."""
        # Act
        user = await user_factory(email="test@example.com", name="Test User")

        # Assert
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.is_verified is True
        assert user.is_active is True
        assert user.is_admin is False

    @pytest.mark.asyncio
    async def test_create_user_with_roles(
        self,
        async_session: AsyncSession,
        user_factory,  # noqa: ARG002
    ) -> None:
        """Creating a user with roles stores roles correctly."""
        # Act
        user = await user_factory(
            email="admin@example.com", roles=["user", "admin", "moderator"]
        )

        # Assert
        assert "user" in user.roles
        assert "admin" in user.roles
        assert "moderator" in user.roles
        assert len(user.roles) == 3

    @pytest.mark.asyncio
    async def test_user_password_setter_hashes(
        self, async_session: AsyncSession, user_factory
    ) -> None:
        """Setting password hashes it automatically."""
        # Arrange
        user = await user_factory(email="user@example.com")

        # Act
        user.password = "MySecretPassword123!"  # noqa: S105
        await async_session.flush()

        # Assert
        assert user._password is not None  # noqa: SLF001
        assert user._password != "MySecretPassword123!"  # noqa: S105, SLF001
        assert user._password.startswith("scrypt:")  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_user_password_getter_raises(
        self,
        async_session: AsyncSession,
        user_factory,  # noqa: ARG002
    ) -> None:
        """Reading password directly raises AttributeError."""
        # Arrange
        user = await user_factory(email="user@example.com")
        user.password = "test123"  # noqa: S105

        # Act & Assert
        with pytest.raises(
            AttributeError, match="password is not a readable attribute"
        ):
            _ = user.password

    @pytest.mark.asyncio
    async def test_check_password_correct(
        self,
        async_session: AsyncSession,
        user_with_password_factory,  # noqa: ARG002
    ) -> None:
        """check_password returns True for correct password."""
        # Arrange
        password = "CorrectPassword123!"  # noqa: S105
        user = await user_with_password_factory(password=password)

        # Act
        result = user.check_password(password)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_check_password_incorrect(
        self,
        async_session: AsyncSession,
        user_with_password_factory,  # noqa: ARG002
    ) -> None:
        """check_password returns False for incorrect password."""
        # Arrange
        user = await user_with_password_factory(password="CorrectPassword123!")

        # Act
        result = user.check_password("WrongPassword!")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_user_unique_email_constraint(
        self,
        async_session: AsyncSession,
        user_factory,  # noqa: ARG002
    ) -> None:
        """Creating users with duplicate email raises integrity error."""
        # Arrange
        await user_factory(email="duplicate@example.com")

        # Act & Assert
        with pytest.raises(Exception):  # IntegrityError or similar  # noqa: B017
            await user_factory(email="duplicate@example.com")

    @pytest.mark.asyncio
    async def test_user_to_dict(
        self,
        async_session: AsyncSession,
        user_factory,  # noqa: ARG002
    ) -> None:
        """to_dict returns correct dictionary representation."""
        # Arrange
        user = await user_factory(
            email="dict@example.com",
            name="Dict User",
            is_admin=True,
            roles=["admin", "user"],
        )

        # Act
        user_dict = user.to_dict()

        # Assert
        assert user_dict["user_id"] == user.id
        assert user_dict["email"] == "dict@example.com"
        assert user_dict["name"] == "Dict User"
        assert user_dict["is_admin"] is True
        assert user_dict["roles"] == ["admin", "user"]
        assert "last_login" in user_dict

    @pytest.mark.asyncio
    async def test_user_default_values(self, async_session: AsyncSession) -> None:
        """User entity has correct default values."""
        # Arrange & Act
        user = UserEntity(email="defaults@example.com")
        async_session.add(user)
        await async_session.flush()
        await async_session.refresh(user)

        # Assert
        assert user.is_verified is False
        assert user.is_admin is False
        assert user.is_active is True
        assert user.needs_password_reset is False
        assert user.roles == []

    @pytest.mark.asyncio
    async def test_user_last_login_timestamp(
        self,
        async_session: AsyncSession,
        user_factory,  # noqa: ARG002
    ) -> None:
        """User last_login is set automatically."""
        # Arrange & Act
        user = await user_factory(email="timestamp@example.com")

        # Assert
        assert user.last_login is not None
        assert isinstance(user.last_login, datetime)

    @pytest.mark.asyncio
    async def test_user_inactive_flag(
        self,
        async_session: AsyncSession,
        user_factory,  # noqa: ARG002
    ) -> None:
        """User can be marked as inactive."""
        # Arrange & Act
        user = await user_factory(email="inactive@example.com", is_active=False)

        # Assert
        assert user.is_active is False

    @pytest.mark.asyncio
    async def test_user_needs_password_reset_flag(
        self,
        async_session: AsyncSession,
        user_factory,  # noqa: ARG002
    ) -> None:
        """User can be marked as needing password reset."""
        # Arrange & Act
        user = await user_factory(email="reset@example.com", needs_password_reset=True)

        # Assert
        assert user.needs_password_reset is True

    @pytest.mark.asyncio
    async def test_user_empty_roles_list(
        self,
        async_session: AsyncSession,  # noqa: ARG002
        user_factory,  # noqa: ARG002
    ) -> None:
        """User with empty roles list works correctly."""
        # Arrange & Act
        user = await user_factory(email="noroles@example.com", roles=[])

        # Assert
        assert user.roles == []
        assert isinstance(user.roles, list)

    @pytest.mark.asyncio
    async def test_user_nullable_fields(self, async_session: AsyncSession) -> None:
        """User can be created with nullable fields set to None."""
        # Arrange & Act
        user = UserEntity(
            email="minimal@example.com",
            name=None,
            avatar_url=None,
        )
        async_session.add(user)
        await async_session.flush()
        await async_session.refresh(user)

        # Assert
        assert user.email == "minimal@example.com"
        assert user.name is None
        assert user.avatar_url is None

    @pytest.mark.asyncio
    async def test_password_change_updates_hash(
        self, async_session: AsyncSession, user_with_password_factory
    ) -> None:
        """Changing password updates the hash."""
        # Arrange
        user = await user_with_password_factory(password="OldPassword123!")
        old_hash = user._password  # noqa: SLF001

        # Act
        user.password = "NewPassword456!"  # noqa: S105
        await async_session.flush()

        # Assert
        assert user._password != old_hash  # noqa: SLF001
        assert user.check_password("NewPassword456!") is True
        assert user.check_password("OldPassword123!") is False
