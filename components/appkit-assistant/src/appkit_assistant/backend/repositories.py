"""Repository for MCP server data access operations."""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from appkit_assistant.backend.models import (
    AssistantThread,
    MCPServer,
    SystemPrompt,
)
from appkit_commons.database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class MCPServerRepository(BaseRepository[MCPServer, AsyncSession]):
    """Repository class for MCP server database operations."""

    @property
    def model_class(self) -> type[MCPServer]:
        return MCPServer

    async def find_all_ordered_by_name(self, session: AsyncSession) -> list[MCPServer]:
        """Retrieve all MCP servers ordered by name."""
        stmt = select(MCPServer).order_by(MCPServer.name)
        result = await session.execute(stmt)
        return list(result.scalars().all())


class SystemPromptRepository(BaseRepository[SystemPrompt, AsyncSession]):
    """Repository class for system prompt database operations.

    Implements append-only versioning with full CRUD capabilities.
    """

    @property
    def model_class(self) -> type[SystemPrompt]:
        return SystemPrompt

    async def find_all_ordered_by_version_desc(
        self, session: AsyncSession
    ) -> list[SystemPrompt]:
        """Retrieve all system prompt versions ordered by version descending."""
        stmt = select(SystemPrompt).order_by(SystemPrompt.version.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def find_latest(self, session: AsyncSession) -> SystemPrompt | None:
        """Retrieve the latest system prompt version."""
        stmt = select(SystemPrompt).order_by(SystemPrompt.version.desc()).limit(1)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def create_next_version(
        self, session: AsyncSession, prompt: str, user_id: int
    ) -> SystemPrompt:
        """Neue System Prompt Version anlegen.

        Version ist fortlaufende Ganzzahl, beginnend bei 1.
        """
        stmt = select(SystemPrompt).order_by(SystemPrompt.version.desc()).limit(1)
        result = await session.execute(stmt)
        latest = result.scalars().first()
        next_version = (latest.version + 1) if latest else 1

        name = f"Version {next_version}"

        system_prompt = SystemPrompt(
            name=name,
            prompt=prompt,
            version=next_version,
            user_id=user_id,
            created_at=datetime.now(UTC),
        )
        session.add(system_prompt)
        await session.flush()
        await session.refresh(system_prompt)

        logger.info(
            "Created system prompt version %s for user %s",
            next_version,
            user_id,
        )
        return system_prompt


class ThreadRepository(BaseRepository[AssistantThread, AsyncSession]):
    """Repository class for Thread database operations."""

    @property
    def model_class(self) -> type[AssistantThread]:
        return AssistantThread

    async def find_by_user(
        self, session: AsyncSession, user_id: int
    ) -> list[AssistantThread]:
        """Retrieve all threads for a user."""
        stmt = (
            select(AssistantThread)
            .where(AssistantThread.user_id == user_id)
            .order_by(AssistantThread.updated_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_thread_id(
        self, session: AsyncSession, thread_id: str
    ) -> AssistantThread | None:
        """Retrieve a thread by its thread_id."""
        stmt = select(AssistantThread).where(AssistantThread.thread_id == thread_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def find_by_thread_id_and_user(
        self, session: AsyncSession, thread_id: str, user_id: int
    ) -> AssistantThread | None:
        """Retrieve a thread by thread_id and user_id."""
        stmt = select(AssistantThread).where(
            AssistantThread.thread_id == thread_id,
            AssistantThread.user_id == user_id,
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def delete_by_thread_id_and_user(
        self, session: AsyncSession, thread_id: str, user_id: int
    ) -> bool:
        """Delete a thread by thread_id and user_id."""
        stmt = select(AssistantThread).where(
            AssistantThread.thread_id == thread_id,
            AssistantThread.user_id == user_id,
        )
        result = await session.execute(stmt)
        thread = result.scalars().first()
        if thread:
            await session.delete(thread)
            await session.flush()
            return True
        return False

    async def find_summaries_by_user(
        self, session: AsyncSession, user_id: int
    ) -> list[AssistantThread]:
        """Retrieve thread summaries (no messages) for a user."""
        stmt = (
            select(AssistantThread)
            .where(AssistantThread.user_id == user_id)
            .options(defer(AssistantThread.messages))
            .order_by(AssistantThread.updated_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


# Export instances
mcp_server_repo = MCPServerRepository()
system_prompt_repo = SystemPromptRepository()
thread_repo = ThreadRepository()
