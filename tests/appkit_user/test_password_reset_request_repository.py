"""Tests for PasswordResetRequestRepository."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_user.authentication.backend.entities import PasswordResetRequestEntity
from appkit_user.authentication.backend.password_reset_request_repository import (
    PasswordResetRequestRepository,
)


@pytest.fixture
def password_reset_request_repository() -> PasswordResetRequestRepository:
    """Provide PasswordResetRequestRepository instance."""
    return PasswordResetRequestRepository()


class TestPasswordResetRequestRepository:
    """Test suite for PasswordResetRequestRepository."""

    @pytest.mark.asyncio
    async def test_count_recent_requests_no_requests(
        self,
        async_session: AsyncSession,
        password_reset_request_repository: PasswordResetRequestRepository,
    ) -> None:
        """count_recent_requests returns 0 when no requests exist."""
        # Act
        count = await password_reset_request_repository.count_recent_requests(
            async_session, email="nonexistent@example.com", hours=1
        )

        # Assert
        assert count == 0

    @pytest.mark.asyncio
    async def test_count_recent_requests_within_window(
        self,
        async_session: AsyncSession,
        password_reset_request_repository: PasswordResetRequestRepository,
    ) -> None:
        """count_recent_requests counts requests within time window."""
        # Arrange
        email = "test@example.com"  # noqa: S105
        now = datetime.now(UTC).replace(tzinfo=None)

        # Create requests within the last hour
        for i in range(3):
            entity = PasswordResetRequestEntity(
                email=email,
                ip_address="192.168.1.1",
                created=now - timedelta(minutes=i * 10),
            )
            async_session.add(entity)
        await async_session.flush()

        # Act
        count = await password_reset_request_repository.count_recent_requests(
            async_session, email=email, hours=1
        )

        # Assert
        assert count == 3

    @pytest.mark.asyncio
    async def test_count_recent_requests_outside_window(
        self,
        async_session: AsyncSession,
        password_reset_request_repository: PasswordResetRequestRepository,
    ) -> None:
        """count_recent_requests excludes old requests outside time window."""
        # Arrange
        email = "old@example.com"  # noqa: S105
        now = datetime.now(UTC).replace(tzinfo=None)

        # Create request 2 hours ago (outside default 1 hour window)
        old_entity = PasswordResetRequestEntity(
            email=email,
            ip_address="192.168.1.1",
            created=now - timedelta(hours=2),
        )
        async_session.add(old_entity)

        # Create request 30 minutes ago (inside window)
        recent_entity = PasswordResetRequestEntity(
            email=email,
            ip_address="192.168.1.1",
            created=now - timedelta(minutes=30),
        )
        async_session.add(recent_entity)
        await async_session.flush()

        # Act
        count = await password_reset_request_repository.count_recent_requests(
            async_session, email=email, hours=1
        )

        # Assert
        assert count == 1

    @pytest.mark.asyncio
    async def test_count_recent_requests_custom_window(
        self,
        async_session: AsyncSession,
        password_reset_request_repository: PasswordResetRequestRepository,
    ) -> None:
        """count_recent_requests respects custom time window."""
        # Arrange
        email = "window@example.com"  # noqa: S105
        now = datetime.now(UTC).replace(tzinfo=None)

        # Create requests at various times
        for hours in [1, 2, 3, 4]:
            entity = PasswordResetRequestEntity(
                email=email,
                ip_address="192.168.1.1",
                created=now - timedelta(hours=hours),
            )
            async_session.add(entity)
        await async_session.flush()

        # Act - Check within 2.5 hour window
        count = await password_reset_request_repository.count_recent_requests(
            async_session, email=email, hours=2
        )

        # Assert - Should count only requests within 2 hours
        assert count == 1  # Only the 1-hour-old request

    @pytest.mark.asyncio
    async def test_count_recent_requests_different_emails(
        self,
        async_session: AsyncSession,
        password_reset_request_repository: PasswordResetRequestRepository,
    ) -> None:
        """count_recent_requests only counts for specific email."""
        # Arrange
        email1 = "user1@example.com"  # noqa: S105
        email2 = "user2@example.com"  # noqa: S105
        now = datetime.now(UTC).replace(tzinfo=None)

        # Create requests for both emails
        for i in range(2):
            entity1 = PasswordResetRequestEntity(
                email=email1,
                ip_address="192.168.1.1",
                created=now - timedelta(minutes=i * 10),
            )
            entity2 = PasswordResetRequestEntity(
                email=email2,
                ip_address="192.168.1.2",
                created=now - timedelta(minutes=i * 10),
            )
            async_session.add(entity1)
            async_session.add(entity2)
        await async_session.flush()

        # Act
        count1 = await password_reset_request_repository.count_recent_requests(
            async_session, email=email1, hours=1
        )
        count2 = await password_reset_request_repository.count_recent_requests(
            async_session, email=email2, hours=1
        )

        # Assert
        assert count1 == 2
        assert count2 == 2

    @pytest.mark.asyncio
    async def test_log_request_creates_entity(
        self,
        async_session: AsyncSession,
        password_reset_request_repository: PasswordResetRequestRepository,
    ) -> None:
        """log_request creates a new request entity."""
        # Arrange
        email = "log@example.com"  # noqa: S105
        ip_address = "192.168.1.100"

        # Act
        entity = await password_reset_request_repository.log_request(
            async_session, email=email, ip_address=ip_address
        )

        # Assert
        assert entity.id is not None
        assert entity.email == email
        assert entity.ip_address == ip_address
        assert entity.created is not None

    @pytest.mark.asyncio
    async def test_log_request_without_ip_address(
        self,
        async_session: AsyncSession,
        password_reset_request_repository: PasswordResetRequestRepository,
    ) -> None:
        """log_request handles missing IP address."""
        # Arrange
        email = "noip@example.com"  # noqa: S105

        # Act
        entity = await password_reset_request_repository.log_request(
            async_session, email=email, ip_address=None
        )

        # Assert
        assert entity.email == email
        assert entity.ip_address is None

    @pytest.mark.asyncio
    async def test_log_request_sets_timestamp(
        self,
        async_session: AsyncSession,
        password_reset_request_repository: PasswordResetRequestRepository,
    ) -> None:
        """log_request sets created timestamp."""
        # Arrange
        email = "timestamp@example.com"  # noqa: S105
        before = datetime.now(UTC).replace(microsecond=0)

        # Act
        entity = await password_reset_request_repository.log_request(
            async_session, email=email
        )

        # Assert
        after = datetime.now(UTC).replace(microsecond=999999)
        # Convert to UTC for comparison if needed
        created_with_tz = entity.created.replace(tzinfo=UTC)
        assert before <= created_with_tz <= after

    @pytest.mark.asyncio
    async def test_cleanup_old_requests(
        self,
        async_session: AsyncSession,
        password_reset_request_repository: PasswordResetRequestRepository,
    ) -> None:
        """cleanup_old_requests removes old entries."""
        # Arrange
        now = datetime.now(UTC).replace(tzinfo=None)

        # Create old request (8 days ago)
        old_entity = PasswordResetRequestEntity(
            email="old@example.com",  # noqa: S105
            ip_address="192.168.1.1",
            created=now - timedelta(days=8),
        )

        # Create recent request (1 day ago)
        recent_entity = PasswordResetRequestEntity(
            email="recent@example.com",  # noqa: S105
            ip_address="192.168.1.2",
            created=now - timedelta(days=1),
        )

        async_session.add(old_entity)
        async_session.add(recent_entity)
        await async_session.flush()

        # Act
        deleted_count = await password_reset_request_repository.cleanup_old_requests(
            async_session, days=7
        )

        # Assert
        assert deleted_count == 1

        # Verify old request was deleted and recent was kept
        recent_requests = await password_reset_request_repository.count_recent_requests(
            async_session, email="recent@example.com", hours=72
        )
        assert recent_requests == 1

    @pytest.mark.asyncio
    async def test_cleanup_old_requests_custom_days(
        self,
        async_session: AsyncSession,
        password_reset_request_repository: PasswordResetRequestRepository,
    ) -> None:
        """cleanup_old_requests respects custom days threshold."""
        # Arrange
        now = datetime.now(UTC).replace(tzinfo=None)

        # Create requests of various ages
        ages = [1, 10, 20, 30]
        for age in ages:
            entity = PasswordResetRequestEntity(
                email=f"age_{age}@example.com",  # noqa: S105
                ip_address="192.168.1.1",
                created=now - timedelta(days=age),
            )
            async_session.add(entity)
        await async_session.flush()

        # Act - Keep only requests from last 15 days
        deleted_count = await password_reset_request_repository.cleanup_old_requests(
            async_session, days=15
        )

        # Assert
        # Should delete: 20 days old and 30 days old = 2
        assert deleted_count == 2

    @pytest.mark.asyncio
    async def test_cleanup_old_requests_no_old_entries(
        self,
        async_session: AsyncSession,
        password_reset_request_repository: PasswordResetRequestRepository,
    ) -> None:
        """cleanup_old_requests returns 0 when no old entries exist."""
        # Arrange
        now = datetime.now(UTC).replace(tzinfo=None)

        # Create recent requests only
        for i in range(3):
            entity = PasswordResetRequestEntity(
                email=f"recent_{i}@example.com",  # noqa: S105
                ip_address="192.168.1.1",
                created=now - timedelta(days=1),
            )
            async_session.add(entity)
        await async_session.flush()

        # Act
        deleted_count = await password_reset_request_repository.cleanup_old_requests(
            async_session, days=7
        )

        # Assert
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_model_class_property(
        self, password_reset_request_repository: PasswordResetRequestRepository
    ) -> None:
        """model_class property returns PasswordResetRequestEntity."""
        # Act
        model_class = password_reset_request_repository.model_class

        # Assert
        assert model_class == PasswordResetRequestEntity
