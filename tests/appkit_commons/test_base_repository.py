"""Tests for BaseRepository generic CRUD operations."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel

from appkit_commons.database.base_repository import BaseRepository


# Test models
class TestEntity(SQLModel, table=True):
    """Test entity for repository testing."""

    __tablename__ = "test_entities"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    name: str
    value: int = 0
    description: str | None = None


class TestEntityRepository(BaseRepository[TestEntity, AsyncSession]):
    """Repository for TestEntity."""

    @property
    def model_class(self) -> type[TestEntity]:
        """Return the TestEntity model class."""
        return TestEntity


@pytest.fixture
def test_repository() -> TestEntityRepository:
    """Provide a TestEntityRepository instance."""
    return TestEntityRepository()


class TestBaseRepository:
    """Test suite for BaseRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_entity_success(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Creating a new entity succeeds and assigns an ID."""
        # Arrange
        entity = TestEntity(name="test-entity", value=42)

        # Act
        created = await test_repository.create(async_session, entity)

        # Assert
        assert created.id is not None
        assert created.name == "test-entity"
        assert created.value == 42

    @pytest.mark.asyncio
    async def test_create_multiple_entities(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Creating multiple entities assigns unique IDs."""
        # Arrange
        entity1 = TestEntity(name="entity-1", value=1)
        entity2 = TestEntity(name="entity-2", value=2)

        # Act
        created1 = await test_repository.create(async_session, entity1)
        created2 = await test_repository.create(async_session, entity2)

        # Assert
        assert created1.id != created2.id
        assert created1.name == "entity-1"
        assert created2.name == "entity-2"

    @pytest.mark.asyncio
    async def test_find_by_id_exists(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Finding an existing entity by ID returns the entity."""
        # Arrange
        entity = TestEntity(name="findable", value=100)
        created = await test_repository.create(async_session, entity)

        # Act
        found = await test_repository.find_by_id(async_session, created.id)  # type: ignore

        # Assert
        assert found is not None
        assert found.id == created.id
        assert found.name == "findable"

    @pytest.mark.asyncio
    async def test_find_by_id_not_exists(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Finding a non-existent entity by ID returns None."""
        # Act
        found = await test_repository.find_by_id(async_session, 99999)

        # Assert
        assert found is None

    @pytest.mark.asyncio
    async def test_find_all_empty(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Finding all entities when none exist returns empty list."""
        # Act
        all_entities = await test_repository.find_all(async_session)

        # Assert
        assert all_entities == []

    @pytest.mark.asyncio
    async def test_find_all_returns_all(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Finding all entities returns all created entities."""
        # Arrange
        entity1 = TestEntity(name="entity-1", value=1)
        entity2 = TestEntity(name="entity-2", value=2)
        entity3 = TestEntity(name="entity-3", value=3)

        await test_repository.create(async_session, entity1)
        await test_repository.create(async_session, entity2)
        await test_repository.create(async_session, entity3)

        # Act
        all_entities = await test_repository.find_all(async_session)

        # Assert
        assert len(all_entities) == 3
        names = [e.name for e in all_entities]
        assert "entity-1" in names
        assert "entity-2" in names
        assert "entity-3" in names

    @pytest.mark.asyncio
    async def test_find_all_by_ids(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Finding entities by list of IDs returns matching entities."""
        # Arrange
        entity1 = TestEntity(name="entity-1", value=1)
        entity2 = TestEntity(name="entity-2", value=2)
        entity3 = TestEntity(name="entity-3", value=3)

        created1 = await test_repository.create(async_session, entity1)
        created2 = await test_repository.create(async_session, entity2)
        await test_repository.create(async_session, entity3)

        # Act
        found = await test_repository.find_all_by_ids(
            async_session, [created1.id, created2.id]  # type: ignore
        )

        # Assert
        assert len(found) == 2
        names = [e.name for e in found]
        assert "entity-1" in names
        assert "entity-2" in names

    @pytest.mark.asyncio
    async def test_find_all_by_ids_empty_list(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Finding entities with empty ID list returns empty list."""
        # Act
        found = await test_repository.find_all_by_ids(async_session, [])

        # Assert
        assert found == []

    @pytest.mark.asyncio
    async def test_exists_by_id_true(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """exists_by_id returns True for existing entity."""
        # Arrange
        entity = TestEntity(name="exists", value=1)
        created = await test_repository.create(async_session, entity)

        # Act
        exists = await test_repository.exists_by_id(async_session, created.id)  # type: ignore

        # Assert
        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_by_id_false(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """exists_by_id returns False for non-existent entity."""
        # Act
        exists = await test_repository.exists_by_id(async_session, 99999)

        # Assert
        assert exists is False

    @pytest.mark.asyncio
    async def test_count_empty(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Counting entities when none exist returns 0."""
        # Act
        count = await test_repository.count(async_session)

        # Assert
        assert count == 0

    @pytest.mark.asyncio
    async def test_count_returns_correct_count(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Counting entities returns correct count."""
        # Arrange
        for i in range(5):
            entity = TestEntity(name=f"entity-{i}", value=i)
            await test_repository.create(async_session, entity)

        # Act
        count = await test_repository.count(async_session)

        # Assert
        assert count == 5

    @pytest.mark.asyncio
    async def test_update_existing_entity(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Updating an existing entity succeeds."""
        # Arrange
        entity = TestEntity(name="original", value=1)
        created = await test_repository.create(async_session, entity)

        # Act
        created.name = "updated"
        created.value = 99
        updated = await test_repository.update(async_session, created)

        # Assert
        assert updated.id == created.id
        assert updated.name == "updated"
        assert updated.value == 99

    @pytest.mark.asyncio
    async def test_update_without_id_raises(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Updating an entity without ID raises ValueError."""
        # Arrange
        entity = TestEntity(name="no-id", value=1)
        entity.id = None

        # Act & Assert
        with pytest.raises(ValueError, match="Entity must have an ID"):
            await test_repository.update(async_session, entity)

    @pytest.mark.asyncio
    async def test_update_nonexistent_entity_raises(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Updating a non-existent entity raises ValueError."""
        # Arrange
        entity = TestEntity(name="ghost", value=1)
        entity.id = 99999

        # Act & Assert
        with pytest.raises(ValueError, match="not found"):
            await test_repository.update(async_session, entity)

    @pytest.mark.asyncio
    async def test_save_creates_new_entity(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """save() creates a new entity when ID is None."""
        # Arrange
        entity = TestEntity(name="new-via-save", value=10)

        # Act
        saved = await test_repository.save(async_session, entity)

        # Assert
        assert saved.id is not None
        assert saved.name == "new-via-save"

    @pytest.mark.asyncio
    async def test_save_updates_existing_entity(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """save() updates an existing entity when ID exists."""
        # Arrange
        entity = TestEntity(name="original", value=1)
        created = await test_repository.create(async_session, entity)

        # Act
        created.value = 50
        saved = await test_repository.save(async_session, created)

        # Assert
        assert saved.id == created.id
        assert saved.value == 50

    @pytest.mark.asyncio
    async def test_save_all_mixed_create_update(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """save_all() handles both new and existing entities."""
        # Arrange
        existing = TestEntity(name="existing", value=1)
        created = await test_repository.create(async_session, existing)

        new_entity = TestEntity(name="new", value=2)
        created.value = 100

        # Act
        saved = await test_repository.save_all(async_session, [created, new_entity])

        # Assert
        assert len(saved) == 2
        # Find the updated entity
        updated = next(e for e in saved if e.name == "existing")
        assert updated.value == 100
        # Find the new entity
        new = next(e for e in saved if e.name == "new")
        assert new.id is not None

    @pytest.mark.asyncio
    async def test_delete_by_id_success(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Deleting an existing entity by ID succeeds."""
        # Arrange
        entity = TestEntity(name="to-delete", value=1)
        created = await test_repository.create(async_session, entity)

        # Act
        deleted = await test_repository.delete_by_id(async_session, created.id)  # type: ignore

        # Assert
        assert deleted is True
        found = await test_repository.find_by_id(async_session, created.id)  # type: ignore
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_by_id_nonexistent_returns_false(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Deleting a non-existent entity by ID returns False."""
        # Act
        deleted = await test_repository.delete_by_id(async_session, 99999)

        # Assert
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_entity_success(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Deleting an existing entity succeeds."""
        # Arrange
        entity = TestEntity(name="to-delete", value=1)
        created = await test_repository.create(async_session, entity)

        # Act
        deleted = await test_repository.delete(async_session, created)

        # Assert
        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_entity_without_id_returns_false(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """Deleting an entity without ID returns False."""
        # Arrange
        entity = TestEntity(name="no-id", value=1)
        entity.id = None

        # Act
        deleted = await test_repository.delete(async_session, entity)

        # Assert
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_all_removes_all_entities(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """delete_all() removes all entities."""
        # Arrange
        for i in range(3):
            entity = TestEntity(name=f"entity-{i}", value=i)
            await test_repository.create(async_session, entity)

        # Act
        deleted_count = await test_repository.delete_all(async_session)

        # Assert
        assert deleted_count == 3
        remaining = await test_repository.find_all(async_session)
        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_delete_all_empty_table(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """delete_all() on empty table returns 0."""
        # Act
        deleted_count = await test_repository.delete_all(async_session)

        # Assert
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_delete_all_by_ids(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """delete_all_by_ids() deletes only specified entities."""
        # Arrange
        entity1 = TestEntity(name="entity-1", value=1)
        entity2 = TestEntity(name="entity-2", value=2)
        entity3 = TestEntity(name="entity-3", value=3)

        created1 = await test_repository.create(async_session, entity1)
        created2 = await test_repository.create(async_session, entity2)
        created3 = await test_repository.create(async_session, entity3)

        # Act
        deleted_count = await test_repository.delete_all_by_ids(
            async_session, [created1.id, created2.id]  # type: ignore
        )

        # Assert
        assert deleted_count == 2
        remaining = await test_repository.find_all(async_session)
        assert len(remaining) == 1
        assert remaining[0].name == "entity-3"

    @pytest.mark.asyncio
    async def test_delete_all_by_ids_empty_list(
        self,
        async_session: AsyncSession,
        test_repository: TestEntityRepository,
    ) -> None:
        """delete_all_by_ids() with empty list returns 0."""
        # Act
        deleted_count = await test_repository.delete_all_by_ids(async_session, [])

        # Assert
        assert deleted_count == 0
