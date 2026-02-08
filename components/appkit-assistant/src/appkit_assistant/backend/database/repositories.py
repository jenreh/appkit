"""Repository for MCP server data access operations."""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from appkit_assistant.backend.database.models import (
    AssistantFileUpload,
    AssistantThread,
    MCPServer,
    SystemPrompt,
    UserPrompt,
)
from appkit_commons.database.base_repository import BaseRepository
from appkit_user.authentication.backend.entities import UserEntity

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

    async def find_all_active_ordered_by_name(
        self, session: AsyncSession
    ) -> list[MCPServer]:
        """Retrieve all active MCP servers ordered by name."""
        stmt = (
            select(MCPServer)
            .where(MCPServer.active == True)  # noqa: E712
            .order_by(MCPServer.name)
        )
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

        logger.debug(
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

    async def find_unique_vector_store_ids(self, session: AsyncSession) -> list[str]:
        """Get unique vector store IDs from all threads.

        Returns:
            List of unique vector store IDs (excluding None/empty).
        """
        stmt = select(AssistantThread.vector_store_id).distinct()
        result = await session.execute(stmt)
        return [row[0] for row in result.all() if row[0]]

    async def clear_vector_store_id(
        self, session: AsyncSession, vector_store_id: str
    ) -> int:
        """Clear vector_store_id from all threads referencing the given store.

        Args:
            vector_store_id: The vector store ID to clear from threads.

        Returns:
            Number of threads updated.
        """
        stmt = select(AssistantThread).where(
            AssistantThread.vector_store_id == vector_store_id
        )
        result = await session.execute(stmt)
        threads = list(result.scalars().all())

        for thread in threads:
            thread.vector_store_id = None
            session.add(thread)

        await session.flush()
        return len(threads)


class FileUploadRepository(BaseRepository[AssistantFileUpload, AsyncSession]):
    """Repository class for file upload database operations."""

    @property
    def model_class(self) -> type[AssistantFileUpload]:
        return AssistantFileUpload

    async def find_unique_vector_stores(
        self, session: AsyncSession
    ) -> list[tuple[str, str]]:
        """Get unique vector store IDs with names from all file uploads.

        Returns:
            List of tuples (vector_store_id, vector_store_name).
        """
        stmt = (
            select(
                AssistantFileUpload.vector_store_id,
                AssistantFileUpload.vector_store_name,
            )
            .distinct()
            .order_by(AssistantFileUpload.vector_store_id)
        )
        result = await session.execute(stmt)
        return [(row[0], row[1] or "") for row in result.all()]

    async def find_by_vector_store(
        self, session: AsyncSession, vector_store_id: str
    ) -> list[AssistantFileUpload]:
        """Get all files for a specific vector store."""
        stmt = (
            select(AssistantFileUpload)
            .where(AssistantFileUpload.vector_store_id == vector_store_id)
            .order_by(AssistantFileUpload.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_thread(
        self, session: AsyncSession, thread_id: int
    ) -> list[AssistantFileUpload]:
        """Get all files for a specific thread."""
        stmt = (
            select(AssistantFileUpload)
            .where(AssistantFileUpload.thread_id == thread_id)
            .order_by(AssistantFileUpload.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def delete_file(
        self, session: AsyncSession, file_id: int
    ) -> AssistantFileUpload | None:
        """Delete a file upload by ID and return the deleted record."""
        stmt = select(AssistantFileUpload).where(AssistantFileUpload.id == file_id)
        result = await session.execute(stmt)
        file_upload = result.scalars().first()
        if file_upload:
            await session.delete(file_upload)
            await session.flush()
            return file_upload
        return None

    async def delete_by_vector_store(
        self, session: AsyncSession, vector_store_id: str
    ) -> list[AssistantFileUpload]:
        """Delete all files for a vector store and return the deleted records."""
        stmt = select(AssistantFileUpload).where(
            AssistantFileUpload.vector_store_id == vector_store_id
        )
        result = await session.execute(stmt)
        files = list(result.scalars().all())
        for file_upload in files:
            await session.delete(file_upload)
        await session.flush()
        return files


class UserPromptRepository(BaseRepository[UserPrompt, AsyncSession]):
    """Repository for user prompts (single table design)."""

    @property
    def model_class(self) -> type[UserPrompt]:
        return UserPrompt

    async def find_latest_prompts_by_user(
        self, session: AsyncSession, user_id: int
    ) -> list[UserPrompt]:
        """Find latest versions of prompts owned by the user.

        Used for the sidebar list.
        """
        stmt = (
            select(UserPrompt)
            .where(
                UserPrompt.user_id == user_id,
                UserPrompt.is_latest == True,  # noqa: E712
            )
            .order_by(UserPrompt.handle)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def find_latest_shared_prompts(
        self, session: AsyncSession, user_id: int
    ) -> list[dict[str, Any]]:
        """Find latest shared prompts (excluding own).

        Returns a list of dicts containing the prompt and the creator's name.
        """

        stmt = (
            select(UserPrompt, UserEntity.name)
            .join(UserEntity, UserPrompt.user_id == UserEntity.id)
            .where(
                UserPrompt.is_shared == True,  # noqa: E712
                UserPrompt.user_id != user_id,
                UserPrompt.is_latest == True,  # noqa: E712
            )
            .order_by(UserPrompt.handle)
        )

        result = await session.execute(stmt)
        prompts = []
        for prompt, creator_name in result:
            prompt_dict = prompt.dict()
            prompt_dict["creator_name"] = creator_name or "Unbekannt"
            # Ensure mcp_server_ids is included as a list
            prompt_dict["mcp_server_ids"] = list(prompt.mcp_server_ids)
            prompts.append(prompt_dict)

        return prompts

    async def find_all_versions(
        self, session: AsyncSession, user_id: int, handle: str
    ) -> list[UserPrompt]:
        """Find all versions of a specific prompt (by handle)."""
        stmt = (
            select(UserPrompt)
            .where(UserPrompt.user_id == user_id, UserPrompt.handle == handle)
            .order_by(UserPrompt.version.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def find_latest_by_handle(
        self, session: AsyncSession, user_id: int, handle: str
    ) -> UserPrompt | None:
        """Find the latest version of a prompt by handle."""
        stmt = select(UserPrompt).where(
            UserPrompt.user_id == user_id,
            UserPrompt.handle == handle,
            UserPrompt.is_latest == True,  # noqa: E712
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def find_latest_accessible_by_handle(
        self, session: AsyncSession, user_id: int, handle: str
    ) -> UserPrompt | None:
        """Find the latest version of a prompt accessible to the user.

        Returns the prompt if it's owned by the user OR shared by another user.
        Prefers user's own prompt if both exist with the same handle.
        """
        stmt = (
            select(UserPrompt)
            .where(
                UserPrompt.handle == handle,
                UserPrompt.is_latest == True,  # noqa: E712
                or_(
                    UserPrompt.user_id == user_id,
                    UserPrompt.is_shared == True,  # noqa: E712
                ),
            )
            # Prefer user's own prompt over shared ones
            .order_by((UserPrompt.user_id == user_id).desc())
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def validate_handle_unique(
        self, session: AsyncSession, user_id: int, handle: str
    ) -> bool:
        """Check if a handle is unique for the user.

        Returns True if unique (safe to use), False otherwise.
        """
        existing = await self.find_latest_by_handle(session, user_id, handle)
        return existing is None

    async def create_new_prompt(
        self,
        session: AsyncSession,
        user_id: int,
        handle: str,
        description: str,
        prompt_text: str,
        is_shared: bool = False,
        mcp_server_ids: list[int] | None = None,
    ) -> UserPrompt:
        """Create the first version of a new prompt."""
        prompt = UserPrompt(
            user_id=user_id,
            handle=handle,
            description=description,
            prompt_text=prompt_text,
            version=1,
            is_latest=True,
            is_shared=is_shared,
            mcp_server_ids=mcp_server_ids or [],
            created_at=datetime.now(UTC),
        )
        session.add(prompt)
        await session.flush()
        await session.refresh(prompt)
        return prompt

    async def create_next_version(
        self,
        session: AsyncSession,
        user_id: int,
        handle: str,
        description: str | None = None,
        prompt_text: str | None = None,
        is_shared: bool | None = None,
        mcp_server_ids: list[int] | None = None,
    ) -> UserPrompt:
        """Create a new version for an existing prompt.

        Updates the old latest version's is_latest to False.
        Copies over values from previous version if not provided.
        """
        # 1. Get current latest
        current_latest = await self.find_latest_by_handle(session, user_id, handle)
        if not current_latest:
            raise ValueError(
                f"Prompt with handle '{handle}' not found for user {user_id}"
            )

        # 2. Update metadata on old latest (optional, but 'is_latest' MUST change)
        current_latest.is_latest = False
        session.add(current_latest)

        # 3. Prepare new values (use new if provided, else copy from old)
        new_desc = (
            description if description is not None else current_latest.description
        )
        new_text = (
            prompt_text if prompt_text is not None else current_latest.prompt_text
        )
        new_shared = is_shared if is_shared is not None else current_latest.is_shared
        new_mcp_servers = (
            mcp_server_ids
            if mcp_server_ids is not None
            else list(current_latest.mcp_server_ids)
        )

        # 4. Create new version
        new_version = UserPrompt(
            user_id=user_id,
            handle=handle,
            description=new_desc,
            prompt_text=new_text,
            version=current_latest.version + 1,
            is_latest=True,
            is_shared=new_shared,
            mcp_server_ids=new_mcp_servers,
            created_at=datetime.now(UTC),
        )
        session.add(new_version)
        await session.flush()
        await session.refresh(new_version)

        return new_version

    async def delete_all_versions(
        self, session: AsyncSession, user_id: int, handle: str
    ) -> bool:
        """Delete all versions of a prompt (hard delete)."""
        stmt = select(UserPrompt).where(
            UserPrompt.user_id == user_id, UserPrompt.handle == handle
        )
        result = await session.execute(stmt)
        prompts = result.scalars().all()

        if not prompts:
            return False

        for p in prompts:
            await session.delete(p)

        await session.flush()
        return True

    async def update_handle(
        self, session: AsyncSession, user_id: int, old_handle: str, new_handle: str
    ) -> bool:
        """Update handle for all versions of a prompt.

        Returns True if successful, False if no prompts found.
        """
        stmt = select(UserPrompt).where(
            UserPrompt.user_id == user_id, UserPrompt.handle == old_handle
        )
        result = await session.execute(stmt)
        prompts = list(result.scalars().all())

        if not prompts:
            return False

        for p in prompts:
            p.handle = new_handle
            session.add(p)

        await session.flush()
        return True

    async def find_all_accessible_prompts_filtered(
        self, session: AsyncSession, user_id: int, filter_text: str = ""
    ) -> list[dict[str, Any]]:
        """Find all prompts accessible to the user, filtered by handle.

        Returns user's own prompts and shared prompts from others.
        Filters by handle.startswith(filter_text) if provided.

        Returns list of dicts with handle, description, prompt_text, mcp_server_ids,
        is_own.
        """
        # Query own prompts
        own_stmt = select(UserPrompt).where(
            UserPrompt.user_id == user_id,
            UserPrompt.is_latest == True,  # noqa: E712
        )
        if filter_text:
            own_stmt = own_stmt.where(UserPrompt.handle.startswith(filter_text))
        own_stmt = own_stmt.order_by(UserPrompt.handle)

        own_result = await session.execute(own_stmt)
        own_prompts = own_result.scalars().all()

        # Query shared prompts from others
        shared_stmt = select(UserPrompt).where(
            UserPrompt.is_shared == True,  # noqa: E712
            UserPrompt.user_id != user_id,
            UserPrompt.is_latest == True,  # noqa: E712
        )
        if filter_text:
            shared_stmt = shared_stmt.where(UserPrompt.handle.startswith(filter_text))
        shared_stmt = shared_stmt.order_by(UserPrompt.handle)

        shared_result = await session.execute(shared_stmt)
        shared_prompts = shared_result.scalars().all()

        # Combine and return as dicts
        result: list[dict[str, Any]] = [
            {
                "handle": p.handle,
                "description": p.description,
                "prompt_text": p.prompt_text,
                "mcp_server_ids": list(p.mcp_server_ids),
                "is_own": True,
            }
            for p in own_prompts
        ]

        result.extend(
            {
                "handle": p.handle,
                "description": p.description,
                "prompt_text": p.prompt_text,
                "mcp_server_ids": list(p.mcp_server_ids),
                "is_own": False,
            }
            for p in shared_prompts
        )

        return result


# Export instances
mcp_server_repo = MCPServerRepository()
system_prompt_repo = SystemPromptRepository()
thread_repo = ThreadRepository()
file_upload_repo = FileUploadRepository()
user_prompt_repo = UserPromptRepository()
