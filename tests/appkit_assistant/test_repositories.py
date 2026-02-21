"""Tests for core repository classes."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_assistant.backend.database.repositories import (
    ThreadRepository,
    MCPServerRepository,
    SystemPromptRepository,
    FileUploadRepository,
)
from appkit_assistant.backend.schemas import ThreadStatus


class TestThreadRepository:
    """Test suite for ThreadRepository."""

    @pytest.mark.asyncio
    async def test_find_by_user_returns_user_threads(
        self, async_session: AsyncSession, thread_factory, thread_repo
    ) -> None:
        """find_by_user returns all threads for specific user."""
        user1_thread1 = await thread_factory(user_id=1, title="User 1 Thread 1")
        user1_thread2 = await thread_factory(user_id=1, title="User 1 Thread 2")
        user2_thread = await thread_factory(user_id=2, title="User 2 Thread")

        results = await thread_repo.find_by_user(async_session, user_id=1)

        assert len(results) == 2
        thread_ids = {t.id for t in results}
        assert user1_thread1.id in thread_ids
        assert user1_thread2.id in thread_ids
        assert user2_thread.id not in thread_ids

    @pytest.mark.asyncio
    async def test_find_by_user_orders_by_updated_desc(
        self, async_session: AsyncSession, thread_factory, thread_repo, faker_instance
    ) -> None:
        """find_by_user returns threads ordered by updated_at descending."""
        from datetime import UTC, datetime, timedelta

        old_thread = await thread_factory(user_id=1)
        old_thread.updated_at = datetime.now(UTC) - timedelta(days=2)

        new_thread = await thread_factory(user_id=1)
        new_thread.updated_at = datetime.now(UTC)
        await async_session.flush()

        results = await thread_repo.find_by_user(async_session, user_id=1)

        assert results[0].id == new_thread.id  # Newest first
        assert results[1].id == old_thread.id

    @pytest.mark.asyncio
    async def test_find_by_thread_id_existing(
        self, async_session: AsyncSession, thread_factory, thread_repo
    ) -> None:
        """find_by_thread_id returns thread by thread_id string."""
        thread = await thread_factory(thread_id="thread-abc123")

        result = await thread_repo.find_by_thread_id(async_session, "thread-abc123")

        assert result is not None
        assert result.id == thread.id
        assert result.thread_id == "thread-abc123"

    @pytest.mark.asyncio
    async def test_find_by_thread_id_nonexistent(
        self, async_session: AsyncSession, thread_repo
    ) -> None:
        """find_by_thread_id returns None for nonexistent thread_id."""
        result = await thread_repo.find_by_thread_id(
            async_session, "nonexistent-thread"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_thread_id_and_user_valid(
        self, async_session: AsyncSession, thread_factory, thread_repo
    ) -> None:
        """find_by_thread_id_and_user returns thread for correct user."""
        thread = await thread_factory(thread_id="thread-123", user_id=1)

        result = await thread_repo.find_by_thread_id_and_user(
            async_session, "thread-123", user_id=1
        )

        assert result is not None
        assert result.id == thread.id

    @pytest.mark.asyncio
    async def test_find_by_thread_id_and_user_wrong_user(
        self, async_session: AsyncSession, thread_factory, thread_repo
    ) -> None:
        """find_by_thread_id_and_user returns None for wrong user."""
        await thread_factory(thread_id="thread-123", user_id=1)

        result = await thread_repo.find_by_thread_id_and_user(
            async_session, "thread-123", user_id=2
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_by_thread_id_and_user_success(
        self, async_session: AsyncSession, thread_factory, thread_repo
    ) -> None:
        """delete_by_thread_id_and_user deletes thread for correct user."""
        thread = await thread_factory(thread_id="thread-123", user_id=1)

        success = await thread_repo.delete_by_thread_id_and_user(
            async_session, "thread-123", user_id=1
        )

        assert success is True
        # Verify deletion
        result = await thread_repo.find_by_thread_id(async_session, "thread-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_by_thread_id_and_user_wrong_user(
        self, async_session: AsyncSession, thread_factory, thread_repo
    ) -> None:
        """delete_by_thread_id_and_user fails for wrong user."""
        await thread_factory(thread_id="thread-123", user_id=1)

        success = await thread_repo.delete_by_thread_id_and_user(
            async_session, "thread-123", user_id=2
        )

        assert success is False
        # Thread should still exist
        result = await thread_repo.find_by_thread_id(async_session, "thread-123")
        assert result is not None

    @pytest.mark.asyncio
    async def test_find_summaries_by_user_defers_messages(
        self, async_session: AsyncSession, thread_factory, thread_repo, sample_messages
    ) -> None:
        """find_summaries_by_user defers loading messages BLOB."""
        await thread_factory(user_id=1, messages=sample_messages)

        results = await thread_repo.find_summaries_by_user(async_session, user_id=1)

        assert len(results) == 1
        # messages should be deferred (not loaded)

    @pytest.mark.asyncio
    async def test_find_unique_vector_store_ids(
        self, async_session: AsyncSession, thread_factory, thread_repo
    ) -> None:
        """find_unique_vector_store_ids returns distinct non-null store IDs."""
        await thread_factory(vector_store_id="vs-123")
        await thread_factory(vector_store_id="vs-456")
        await thread_factory(vector_store_id="vs-123")  # Duplicate
        await thread_factory(vector_store_id=None)  # Null

        results = await thread_repo.find_unique_vector_store_ids(async_session)

        assert len(results) == 2
        assert "vs-123" in results
        assert "vs-456" in results
        assert None not in results

    @pytest.mark.asyncio
    async def test_clear_vector_store_id(
        self, async_session: AsyncSession, thread_factory, thread_repo
    ) -> None:
        """clear_vector_store_id clears vector_store_id from matching threads."""
        thread1 = await thread_factory(vector_store_id="vs-clear")
        thread2 = await thread_factory(vector_store_id="vs-clear")
        thread3 = await thread_factory(vector_store_id="vs-keep")

        count = await thread_repo.clear_vector_store_id(async_session, "vs-clear")

        assert count == 2
        await async_session.refresh(thread1)
        await async_session.refresh(thread2)
        await async_session.refresh(thread3)
        assert thread1.vector_store_id is None
        assert thread2.vector_store_id is None
        assert thread3.vector_store_id == "vs-keep"


class TestMCPServerRepository:
    """Test suite for MCPServerRepository."""

    @pytest.mark.asyncio
    async def test_find_all_ordered_by_name(
        self, async_session: AsyncSession, mcp_server_factory, mcp_server_repo
    ) -> None:
        """find_all_ordered_by_name returns all servers sorted by name."""
        server_b = await mcp_server_factory(name="B Server")
        server_a = await mcp_server_factory(name="A Server")
        server_c = await mcp_server_factory(name="C Server")

        results = await mcp_server_repo.find_all_ordered_by_name(async_session)

        assert len(results) == 3
        assert results[0].id == server_a.id
        assert results[1].id == server_b.id
        assert results[2].id == server_c.id

    @pytest.mark.asyncio
    async def test_find_all_ordered_by_name_includes_inactive(
        self, async_session: AsyncSession, mcp_server_factory, mcp_server_repo
    ) -> None:
        """find_all_ordered_by_name includes inactive servers."""
        active = await mcp_server_factory(active=True)
        inactive = await mcp_server_factory(active=False)

        results = await mcp_server_repo.find_all_ordered_by_name(async_session)

        assert len(results) == 2
        server_ids = {s.id for s in results}
        assert active.id in server_ids
        assert inactive.id in server_ids

    @pytest.mark.asyncio
    async def test_find_all_active_ordered_by_name(
        self, async_session: AsyncSession, mcp_server_factory, mcp_server_repo
    ) -> None:
        """find_all_active_ordered_by_name returns only active servers."""
        active1 = await mcp_server_factory(name="Active 1", active=True)
        active2 = await mcp_server_factory(name="Active 2", active=True)
        inactive = await mcp_server_factory(name="Inactive", active=False)

        results = await mcp_server_repo.find_all_active_ordered_by_name(async_session)

        assert len(results) == 2
        server_ids = {s.id for s in results}
        assert active1.id in server_ids
        assert active2.id in server_ids
        assert inactive.id not in server_ids

    @pytest.mark.asyncio
    async def test_find_all_active_ordered_alphabetically(
        self, async_session: AsyncSession, mcp_server_factory, mcp_server_repo
    ) -> None:
        """find_all_active_ordered_by_name sorts alphabetically."""
        server_z = await mcp_server_factory(name="Z Server", active=True)
        server_a = await mcp_server_factory(name="A Server", active=True)

        results = await mcp_server_repo.find_all_active_ordered_by_name(async_session)

        assert results[0].id == server_a.id
        assert results[1].id == server_z.id


class TestSystemPromptRepository:
    """Test suite for SystemPromptRepository."""

    @pytest.mark.asyncio
    async def test_find_all_ordered_by_version_desc(
        self, async_session: AsyncSession, system_prompt_factory, system_prompt_repo
    ) -> None:
        """find_all_ordered_by_version_desc returns prompts newest first."""
        v1 = await system_prompt_factory(version=1)
        v3 = await system_prompt_factory(version=3)
        v2 = await system_prompt_factory(version=2)

        results = await system_prompt_repo.find_all_ordered_by_version_desc(
            async_session
        )

        assert len(results) == 3
        assert results[0].id == v3.id  # Version 3 first
        assert results[1].id == v2.id
        assert results[2].id == v1.id

    @pytest.mark.asyncio
    async def test_find_latest(
        self, async_session: AsyncSession, system_prompt_factory, system_prompt_repo
    ) -> None:
        """find_latest returns highest version number."""
        await system_prompt_factory(version=1)
        await system_prompt_factory(version=2)
        v3 = await system_prompt_factory(version=3)

        result = await system_prompt_repo.find_latest(async_session)

        assert result is not None
        assert result.id == v3.id
        assert result.version == 3

    @pytest.mark.asyncio
    async def test_find_latest_no_prompts(
        self, async_session: AsyncSession, system_prompt_repo
    ) -> None:
        """find_latest returns None when no prompts exist."""
        result = await system_prompt_repo.find_latest(async_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_create_next_version_first_version(
        self, async_session: AsyncSession, system_prompt_repo
    ) -> None:
        """create_next_version creates version 1 when no prompts exist."""
        prompt = await system_prompt_repo.create_next_version(
            async_session, prompt="First version", user_id=1
        )

        assert prompt.version == 1
        assert prompt.prompt == "First version"
        assert prompt.name == "Version 1"

    @pytest.mark.asyncio
    async def test_create_next_version_increments(
        self, async_session: AsyncSession, system_prompt_factory, system_prompt_repo
    ) -> None:
        """create_next_version increments version number."""
        await system_prompt_factory(version=1)
        await system_prompt_factory(version=2)

        new_prompt = await system_prompt_repo.create_next_version(
            async_session, prompt="Third version", user_id=1
        )

        assert new_prompt.version == 3
        assert new_prompt.name == "Version 3"
        assert new_prompt.prompt == "Third version"


class TestFileUploadRepository:
    """Test suite for FileUploadRepository."""

    @pytest.mark.asyncio
    async def test_find_unique_vector_stores(
        self, async_session: AsyncSession, file_upload_factory, file_upload_repo
    ) -> None:
        """find_unique_vector_stores returns distinct vector stores."""
        await file_upload_factory(vector_store_id="vs-1", vector_store_name="Store 1")
        await file_upload_factory(vector_store_id="vs-2", vector_store_name="Store 2")
        await file_upload_factory(
            vector_store_id="vs-1", vector_store_name="Store 1"
        )  # Duplicate

        results = await file_upload_repo.find_unique_vector_stores(async_session)

        assert len(results) == 2
        store_ids = {vs_id for vs_id, _ in results}
        assert "vs-1" in store_ids
        assert "vs-2" in store_ids

    @pytest.mark.asyncio
    async def test_find_by_vector_store(
        self, async_session: AsyncSession, file_upload_factory, file_upload_repo
    ) -> None:
        """find_by_vector_store returns files for specific store."""
        file1 = await file_upload_factory(vector_store_id="vs-123")
        file2 = await file_upload_factory(vector_store_id="vs-123")
        file3 = await file_upload_factory(vector_store_id="vs-456")

        results = await file_upload_repo.find_by_vector_store(async_session, "vs-123")

        assert len(results) == 2
        file_ids = {f.id for f in results}
        assert file1.id in file_ids
        assert file2.id in file_ids
        assert file3.id not in file_ids

    @pytest.mark.asyncio
    async def test_find_by_vector_store_orders_by_created_desc(
        self, async_session: AsyncSession, file_upload_factory, file_upload_repo
    ) -> None:
        """find_by_vector_store orders by created_at descending."""
        from datetime import UTC, datetime, timedelta

        old_file = await file_upload_factory(vector_store_id="vs-123")
        old_file.created_at = datetime.now(UTC) - timedelta(days=1)

        new_file = await file_upload_factory(vector_store_id="vs-123")
        new_file.created_at = datetime.now(UTC)
        await async_session.flush()

        results = await file_upload_repo.find_by_vector_store(async_session, "vs-123")

        assert results[0].id == new_file.id  # Newest first
        assert results[1].id == old_file.id

    @pytest.mark.asyncio
    async def test_find_by_thread(
        self, async_session: AsyncSession, file_upload_factory, file_upload_repo
    ) -> None:
        """find_by_thread returns files for specific thread."""
        # Create files with same thread_id
        file1 = await file_upload_factory()
        thread_id = file1.thread_id
        file2 = await file_upload_factory(thread_id=thread_id)
        file3 = await file_upload_factory()  # Different thread

        results = await file_upload_repo.find_by_thread(async_session, thread_id)

        assert len(results) == 2
        file_ids = {f.id for f in results}
        assert file1.id in file_ids
        assert file2.id in file_ids
        assert file3.id not in file_ids

    @pytest.mark.asyncio
    async def test_delete_file_success(
        self, async_session: AsyncSession, file_upload_factory, file_upload_repo
    ) -> None:
        """delete_file deletes file and returns deleted record."""
        file_upload = await file_upload_factory()

        deleted = await file_upload_repo.delete_file(async_session, file_upload.id)

        assert deleted is not None
        assert deleted.id == file_upload.id

    @pytest.mark.asyncio
    async def test_delete_file_nonexistent(
        self, async_session: AsyncSession, file_upload_repo
    ) -> None:
        """delete_file returns None for nonexistent file."""
        deleted = await file_upload_repo.delete_file(async_session, file_id=99999)

        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_by_vector_store(
        self, async_session: AsyncSession, file_upload_factory, file_upload_repo
    ) -> None:
        """delete_by_vector_store deletes all files for a store."""
        file1 = await file_upload_factory(vector_store_id="vs-delete")
        file2 = await file_upload_factory(vector_store_id="vs-delete")
        file3 = await file_upload_factory(vector_store_id="vs-keep")

        deleted_files = await file_upload_repo.delete_by_vector_store(
            async_session, "vs-delete"
        )

        assert len(deleted_files) == 2
        deleted_ids = {f.id for f in deleted_files}
        assert file1.id in deleted_ids
        assert file2.id in deleted_ids

        # Verify vs-keep still exists
        remaining = await file_upload_repo.find_by_vector_store(async_session, "vs-keep")
        assert len(remaining) == 1
