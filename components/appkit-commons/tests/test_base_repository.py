"""Tests for BaseRepository generic CRUD operations."""

import pytest
from sqlalchemy import Integer, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from appkit_commons.database.base_repository import BaseRepository
from appkit_commons.database.entities import Base


class SampleEntity(Base):
    """Test entity for repository testing."""

    __tablename__ = "test_sample_entity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    value: Mapped[int] = mapped_column(Integer, default=0)


class SampleEntityRepository(BaseRepository[SampleEntity, AsyncSession]):
    """Repository for SampleEntity."""

    @property
    def model_class(self) -> type[SampleEntity]:
        return SampleEntity


@pytest.fixture
def test_repository() -> SampleEntityRepository:
    """Provide a SampleEntityRepository instance."""
    return SampleEntityRepository()


class TestBaseRepository:
    """Test suite for BaseRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_and_find_by_id(
        self, async_session: AsyncSession, test_repository: SampleEntityRepository
    ) -> None:
        # Arrange
        entity = SampleEntity(name="Test Item 1", value=42)

        # Act
        created = await test_repository.create(async_session, entity)

        found = await test_repository.find_by_id(async_session, created.id)

        # Assert
        assert found is not None
        assert found.id == created.id
        assert found.name == "Test Item 1"
        assert found.value == 42

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(
        self, async_session: AsyncSession, test_repository: SampleEntityRepository
    ) -> None:
        # Act
        found = await test_repository.find_by_id(async_session, 999)

        # Assert
        assert found is None
