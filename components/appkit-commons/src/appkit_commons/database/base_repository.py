"""Abstract base repository with generic CRUD operations.

Inspired by org.springframework.data.repository.CrudRepository
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol, TypeVar, cast

from sqlmodel import select


class HasId(Protocol):
    """Protocol for entities with an id attribute."""

    id: int | None


T = TypeVar("T", bound=HasId)
S = TypeVar("S")


class BaseRepository[T, S](ABC):
    """Generic asynchronous repository base class for CRUD operations.

    This abstract base class provides a set of common Create/Read/Update/Delete
    operations for working with SQLModel/SQLAlchemy model objects in an
    asynchronous context. It is intended to be subclassed for concrete model
    repositories.

    Type parameters
    - T: The model/entity type managed by the repository. The model is expected
        to have an integer "id" attribute (or a comparable primary key).
    - S: The asynchronous session type (e.g., SQLAlchemy AsyncSession or a
        compatible wrapper). The session must implement async methods used
        below: add(), flush(), refresh(), execute(), get(), delete().

    Design and behavior
    - This class does NOT commit transactions. Methods call session.flush() and
      session.refresh() where appropriate to synchronize in-memory objects with
      the database session, but the caller is responsible for transaction
      boundaries (commit/rollback) and session lifecycle.
    - Methods operate asynchronously and must be awaited.
    - Methods use SQLAlchemy select() and session.get() under the hood. The
      session must support SQLAlchemy Core/ORM patterns for execution and retrieval.
    - The default implementations favor correctness and clarity over bulk
      performance: bulk operations (save_all, delete_all, etc.) iterate and
      perform individual operations; subclasses should override these methods
      to implement more efficient bulk SQL if needed.

    Error handling
    - ValueError is raised for invalid or missing IDs in update-like operations
      and when an expected existing entity cannot be found during update.
    - Other exceptions raised by the underlying session/engine (e.g., integrity
      errors) are not swallowed—callers should handle DB errors and transaction
      rollback as appropriate.

    Subclassing example
    class MyModelRepository(BaseRepository[MyModel, AsyncSession]):
        def model_class(self) -> type[MyModel]:
           return MyModel

    Notes and recommendations
    - For models with relationships or complex state, prefer using dedicated
      merge/copy patterns or explicit field mapping rather than the simple
      attribute copy used in update().
    - For large batches or high-performance use cases, override save_all,
      count, delete_all, and other methods to use efficient SQL bulk operations
      (e.g., INSERT ... ON CONFLICT, bulk DELETE, or SELECT COUNT()).
    - Keep transaction boundaries (commit/rollback) at a higher level (service
      layer) rather than inside repository methods to allow grouping multiple
      operations into a single transaction."""

    @property
    @abstractmethod
    def model_class(self) -> type[T]:
        """Return the model class this repository manages."""

    # Create/Update operations
    async def create(self, session: S, entity: T) -> T:
        """Create a new entity."""
        session.add(entity)
        await session.flush()
        await session.refresh(entity)
        return entity

    async def update(self, session: S, entity: T) -> T:
        """Update an existing entity."""
        entity_id = getattr(entity, "id", None)
        if entity_id is None:
            raise ValueError("Entity must have an ID to be updated")

        existing = await session.get(self.model_class, entity_id)
        if not existing:
            # For update, we expect the entity to exist
            raise ValueError(f"Entity with id {entity_id} not found")

        # Update existing - merge entity data into existing
        for key, value in vars(entity).items():
            if not key.startswith("_"):
                setattr(existing, key, value)
        session.add(existing)
        await session.flush()
        await session.refresh(existing)
        return existing

    async def save(self, session: S, entity: T) -> T:
        """Save (create or update) an entity.

        If entity has an ID and exists, updates it.
        Otherwise, creates a new entity.
        """
        entity_id = getattr(entity, "id", None)
        # Check if entity exists
        if entity_id is not None and await self.exists_by_id(session, entity_id):
            return await self.update(session, entity)

        return await self.create(session, entity)

    async def save_all(self, session: S, entities: list[T]) -> list[T]:
        """Save (create or update) multiple entities.

        For each entity: if it has an ID and exists, updates it.
        Otherwise, creates a new entity.
        """
        return [await self.save(session, entity) for entity in entities]

    # Read operations
    async def find_by_id(self, session: S, item_id: int) -> T | None:
        """Find an instance by ID."""
        model_with_id = cast(Any, self.model_class)
        result = await session.execute(
            select(self.model_class).where(model_with_id.id == item_id)
        )
        return result.scalars().first()

    async def find_all(self, session: S) -> list[T]:
        """Find all instances."""
        result = await session.execute(select(self.model_class))
        return list(result.scalars().all())

    async def find_all_by_ids(self, session: S, ids: list[int]) -> list[T]:
        """Find all instances by IDs."""
        model_with_id = cast(Any, self.model_class)
        result = await session.execute(
            select(self.model_class).where(model_with_id.id.in_(ids))
        )
        return list(result.scalars().all())

    async def exists_by_id(self, session: S, item_id: int) -> bool:
        """Check if an instance exists by ID."""
        model_with_id = cast(Any, self.model_class)
        result = await session.execute(
            select(self.model_class).where(model_with_id.id == item_id)
        )
        return result.scalars().first() is not None

    async def count(self, session: S) -> int:
        """Count all instances."""
        result = await session.execute(select(self.model_class))
        return len(list(result.scalars().all()))

    # Delete operations
    async def delete_by_id(self, session: S, item_id: int) -> bool:
        """Delete an instance by ID."""
        instance = await session.get(self.model_class, item_id)
        if not instance:
            return False
        await session.delete(instance)
        await session.flush()
        return True

    async def delete(self, session: S, entity: T) -> bool:
        """Delete an entity."""
        # Re-fetch to ensure we have the right instance in this session
        item_id = getattr(entity, "id", None)
        if item_id is None:
            return False
        instance = await session.get(self.model_class, item_id)
        if not instance:
            return False
        await session.delete(instance)
        await session.flush()
        return True

    async def delete_all(self, session: S) -> int:
        """Delete all instances. Returns count of deleted items."""
        instances = await self.find_all(session)
        count = len(instances)
        for instance in instances:
            await session.delete(instance)
        await session.flush()
        return count

    async def delete_all_by_ids(self, session: S, ids: list[int]) -> int:
        """Delete all instances by IDs. Returns count of deleted items."""
        instances = await self.find_all_by_ids(session, ids)
        count = len(instances)
        for instance in instances:
            await session.delete(instance)
        await session.flush()
        return count
