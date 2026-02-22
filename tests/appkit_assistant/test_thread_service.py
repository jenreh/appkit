"""Tests for ThreadService."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.database.models import AssistantThread
from appkit_assistant.backend.schemas import (
    Message,
    MessageType,
    ThreadModel,
    ThreadStatus,
)
from appkit_assistant.backend.services.thread_service import ThreadService


def mock_async_context_manager(return_value):
    """Create a mock async context manager that returns the given value."""

    @asynccontextmanager
    async def _mock_context():
        yield return_value

    return _mock_context()


class TestThreadService:
    """Test suite for ThreadService."""

    def test_init_creates_model_manager(self) -> None:
        """ThreadService initializes with ModelManager."""
        service = ThreadService()

        assert service.model_manager is not None

    def test_create_new_thread_generates_uuid(self) -> None:
        """create_new_thread generates unique thread_id."""
        service = ThreadService()

        with patch.object(service.model_manager, "get_all_models", return_value=[]):
            with patch.object(
                service.model_manager, "get_default_model", return_value="gpt-4"
            ):
                thread1 = service.create_new_thread("gpt-4")
                thread2 = service.create_new_thread("gpt-4")

        assert thread1.thread_id != thread2.thread_id
        assert len(thread1.thread_id) > 0

    def test_create_new_thread_uses_current_model(self) -> None:
        """create_new_thread uses current_model when accessible."""
        service = ThreadService()
        mock_model = MagicMock(id="gpt-4", requires_role=None)

        with patch.object(
            service.model_manager, "get_all_models", return_value=[mock_model]
        ):
            thread = service.create_new_thread("gpt-4", user_roles=["user"])

        assert thread.ai_model == "gpt-4"

    def test_create_new_thread_respects_role_requirements(self) -> None:
        """create_new_thread filters models by user roles."""
        service = ThreadService()
        admin_model = MagicMock(id="gpt-4-admin", requires_role="admin")
        user_model = MagicMock(id="gpt-3.5", requires_role=None)

        with patch.object(
            service.model_manager,
            "get_all_models",
            return_value=[admin_model, user_model],
        ):
            thread = service.create_new_thread("gpt-4-admin", user_roles=["user"])

        # Should fallback to accessible model
        assert thread.ai_model == "gpt-3.5"

    def test_create_new_thread_allows_role_access(self) -> None:
        """create_new_thread allows model when user has required role."""
        service = ThreadService()
        admin_model = MagicMock(id="gpt-4-admin", requires_role="admin")

        with patch.object(
            service.model_manager, "get_all_models", return_value=[admin_model]
        ):
            thread = service.create_new_thread("gpt-4-admin", user_roles=["admin"])

        assert thread.ai_model == "gpt-4-admin"

    def test_create_new_thread_uses_default_when_invalid(self) -> None:
        """create_new_thread falls back to default model when requested is invalid."""
        service = ThreadService()
        available_model = MagicMock(id="gpt-3.5", requires_role=None)

        with (
            patch.object(
                service.model_manager, "get_all_models", return_value=[available_model]
            ),
            patch.object(
                service.model_manager, "get_default_model", return_value="gpt-3.5"
            ),
        ):
            thread = service.create_new_thread("invalid-model")

        assert thread.ai_model == "gpt-3.5"

    def test_create_new_thread_uses_first_available_when_default_restricted(
        self,
    ) -> None:
        """create_new_thread uses first available when default requires role."""
        service = ThreadService()
        restricted_default = MagicMock(id="gpt-4", requires_role="admin")
        accessible_model = MagicMock(id="gpt-3.5", requires_role=None)

        with (
            patch.object(
                service.model_manager,
                "get_all_models",
                return_value=[restricted_default, accessible_model],
            ),
            patch.object(
                service.model_manager, "get_default_model", return_value="gpt-4"
            ),
        ):
            thread = service.create_new_thread("invalid", user_roles=["user"])

        assert thread.ai_model == "gpt-3.5"

    def test_create_new_thread_sets_initial_state(self) -> None:
        """create_new_thread creates thread with correct initial state."""
        service = ThreadService()

        with patch.object(service.model_manager, "get_all_models", return_value=[]):
            with patch.object(
                service.model_manager, "get_default_model", return_value="gpt-4"
            ):
                thread = service.create_new_thread("gpt-4")

        assert thread.title == "Neuer Chat"
        assert thread.state == ThreadStatus.NEW
        assert thread.messages == []
        assert thread.active is True

    @pytest.mark.asyncio
    async def test_load_thread_returns_none_when_not_found(self) -> None:
        """load_thread returns None when thread doesn't exist."""
        service = ThreadService()
        mock_session = MagicMock()

        with patch(
            "appkit_assistant.backend.services.thread_service.get_asyncdb_session",
            return_value=mock_async_context_manager(mock_session),
        ):
            with patch(
                "appkit_assistant.backend.services.thread_service.thread_repo.find_by_thread_id_and_user",
                new_callable=AsyncMock,
                return_value=None,
            ):
                result = await service.load_thread("nonexistent", user_id=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_load_thread_converts_user_id_from_string(self) -> None:
        """load_thread converts numeric string user_id to int."""
        service = ThreadService()
        mock_session = MagicMock()
        mock_find = AsyncMock(return_value=None)

        with patch(
            "appkit_assistant.backend.services.thread_service.get_asyncdb_session",
            return_value=mock_async_context_manager(mock_session),
        ):
            with patch(
                "appkit_assistant.backend.services.thread_service.thread_repo.find_by_thread_id_and_user",
                mock_find,
            ):
                await service.load_thread("thread-123", user_id="42")

        # Verify it was called with int
        mock_find.assert_called_once()
        assert mock_find.call_args[0][2] == 42

    @pytest.mark.asyncio
    async def test_load_thread_returns_thread_model(self) -> None:
        """load_thread converts database entity to ThreadModel."""
        service = ThreadService()
        mock_session = MagicMock()
        db_thread = AssistantThread(
            thread_id="thread-123",
            user_id=1,
            title="Test Thread",
            state=ThreadStatus.ACTIVE,
            ai_model="gpt-4",
            active=True,
            messages=[
                {
                    "id": "msg-1",
                    "text": "Hello",
                    "type": "human",
                    "done": True,
                    "attachments": [],
                    "annotations": [],
                }
            ],
            mcp_server_ids=[1, 2],
            skill_openai_ids=["skill-1"],
        )

        with patch(
            "appkit_assistant.backend.services.thread_service.get_asyncdb_session",
            return_value=mock_async_context_manager(mock_session),
        ):
            with patch(
                "appkit_assistant.backend.services.thread_service.thread_repo.find_by_thread_id_and_user",
                new_callable=AsyncMock,
                return_value=db_thread,
            ):
                result = await service.load_thread("thread-123", user_id=1)

        assert result is not None
        assert isinstance(result, ThreadModel)
        assert result.thread_id == "thread-123"
        assert result.title == "Test Thread"
        assert result.state == ThreadStatus.ACTIVE
        assert len(result.messages) == 1
        assert result.mcp_server_ids == [1, 2]
        assert result.skill_openai_ids == ["skill-1"]

    @pytest.mark.asyncio
    async def test_load_thread_handles_empty_arrays(self) -> None:
        """load_thread handles None mcp_server_ids and skill_openai_ids."""
        service = ThreadService()
        mock_session = MagicMock()
        db_thread = AssistantThread(
            thread_id="thread-123",
            user_id=1,
            title="Test",
            state=ThreadStatus.NEW,
            ai_model="gpt-4",
            active=True,
            messages=[],
            mcp_server_ids=None,
            skill_openai_ids=None,
        )

        with patch(
            "appkit_assistant.backend.services.thread_service.get_asyncdb_session",
            return_value=mock_async_context_manager(mock_session),
        ):
            with patch(
                "appkit_assistant.backend.services.thread_service.thread_repo.find_by_thread_id_and_user",
                new_callable=AsyncMock,
                return_value=db_thread,
            ):
                result = await service.load_thread("thread-123", user_id=1)

        assert result.mcp_server_ids == []
        assert result.skill_openai_ids == []

    @pytest.mark.asyncio
    async def test_save_thread_skips_when_no_user_id(self) -> None:
        """save_thread returns early when user_id is missing."""
        service = ThreadService()
        thread = ThreadModel(
            thread_id="thread-123",
            title="Test",
            state=ThreadStatus.NEW,
            ai_model="gpt-4",
            active=True,
            messages=[],
        )

        # Should not raise, just log warning
        await service.save_thread(thread, user_id=None)

    @pytest.mark.asyncio
    async def test_save_thread_creates_new_thread(self) -> None:
        """save_thread creates new AssistantThread when not exists."""
        service = ThreadService()
        mock_session = MagicMock()
        thread = ThreadModel(
            thread_id="thread-123",
            title="New Thread",
            state=ThreadStatus.ACTIVE,
            ai_model="gpt-4",
            active=True,
            messages=[Message(text="Hello", type=MessageType.HUMAN)],
            mcp_server_ids=[1],
            skill_openai_ids=["skill-1"],
        )

        mock_save = AsyncMock()
        with patch(
            "appkit_assistant.backend.services.thread_service.get_asyncdb_session",
            return_value=mock_async_context_manager(mock_session),
        ):
            with patch(
                "appkit_assistant.backend.services.thread_service.thread_repo.find_by_thread_id_and_user",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with patch(
                    "appkit_assistant.backend.services.thread_service.thread_repo.save",
                    mock_save,
                ):
                    await service.save_thread(thread, user_id=1)

        # Verify save was called
        mock_save.assert_called_once()
        saved_thread = mock_save.call_args[0][1]
        assert saved_thread.thread_id == "thread-123"
        assert saved_thread.title == "New Thread"
        assert len(saved_thread.messages) == 1

    @pytest.mark.asyncio
    async def test_save_thread_updates_existing_thread(self) -> None:
        """save_thread updates existing AssistantThread."""
        service = ThreadService()
        mock_session = MagicMock()
        existing = AssistantThread(
            thread_id="thread-123",
            user_id=1,
            title="Old Title",
            state=ThreadStatus.NEW,
            ai_model="gpt-3.5",
            active=False,
            messages=[],
            mcp_server_ids=[],
            skill_openai_ids=[],
        )

        thread = ThreadModel(
            thread_id="thread-123",
            title="Updated Title",
            state=ThreadStatus.ACTIVE,
            ai_model="gpt-4",
            active=True,
            messages=[Message(text="New message", type=MessageType.HUMAN)],
            mcp_server_ids=[1, 2],
            skill_openai_ids=["skill-1"],
        )

        mock_save = AsyncMock()
        with patch(
            "appkit_assistant.backend.services.thread_service.get_asyncdb_session",
            return_value=mock_async_context_manager(mock_session),
        ):
            with patch(
                "appkit_assistant.backend.services.thread_service.thread_repo.find_by_thread_id_and_user",
                new_callable=AsyncMock,
                return_value=existing,
            ):
                with patch(
                    "appkit_assistant.backend.services.thread_service.thread_repo.save",
                    mock_save,
                ):
                    await service.save_thread(thread, user_id=1)

        # Verify existing was updated
        assert existing.title == "Updated Title"
        assert existing.state == ThreadStatus.ACTIVE
        assert existing.ai_model == "gpt-4"
        assert existing.active is True
        assert len(existing.messages) == 1
        assert existing.mcp_server_ids == [1, 2]

    @pytest.mark.asyncio
    async def test_save_thread_converts_string_user_id(self) -> None:
        """save_thread converts numeric string user_id to int."""
        service = ThreadService()
        mock_session = MagicMock()
        thread = ThreadModel(
            thread_id="thread-123",
            title="Test",
            state=ThreadStatus.NEW,
            ai_model="gpt-4",
            active=True,
            messages=[],
        )

        mock_find = AsyncMock(return_value=None)
        mock_save = AsyncMock()
        with patch(
            "appkit_assistant.backend.services.thread_service.get_asyncdb_session",
            return_value=mock_async_context_manager(mock_session),
        ):
            with patch(
                "appkit_assistant.backend.services.thread_service.thread_repo.find_by_thread_id_and_user",
                mock_find,
            ):
                with patch(
                    "appkit_assistant.backend.services.thread_service.thread_repo.save",
                    mock_save,
                ):
                    await service.save_thread(thread, user_id="42")

        # Verify user_id was converted to int
        mock_find.assert_called_once()
        assert mock_find.call_args[0][2] == 42

    @pytest.mark.asyncio
    async def test_save_thread_handles_thread_status_enum(self) -> None:
        """save_thread extracts value from ThreadStatus enum."""
        service = ThreadService()
        mock_session = MagicMock()
        thread = ThreadModel(
            thread_id="thread-123",
            title="Test",
            state=ThreadStatus.ACTIVE,  # Enum
            ai_model="gpt-4",
            active=True,
            messages=[],
        )

        mock_save = AsyncMock()
        with patch(
            "appkit_assistant.backend.services.thread_service.get_asyncdb_session",
            return_value=mock_async_context_manager(mock_session),
        ):
            with patch(
                "appkit_assistant.backend.services.thread_service.thread_repo.find_by_thread_id_and_user",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with patch(
                    "appkit_assistant.backend.services.thread_service.thread_repo.save",
                    mock_save,
                ):
                    await service.save_thread(thread, user_id=1)

        saved_thread = mock_save.call_args[0][1]
        # State should be string value, not enum
        assert saved_thread.state == "active"

    @pytest.mark.asyncio
    async def test_save_thread_logs_errors(self) -> None:
        """save_thread logs exceptions without raising."""
        service = ThreadService()
        mock_session = MagicMock()
        thread = ThreadModel(
            thread_id="thread-123",
            title="Test",
            state=ThreadStatus.NEW,
            ai_model="gpt-4",
            active=True,
            messages=[],
        )

        with patch(
            "appkit_assistant.backend.services.thread_service.get_asyncdb_session",
            return_value=mock_async_context_manager(mock_session),
        ):
            with patch(
                "appkit_assistant.backend.services.thread_service.thread_repo.find_by_thread_id_and_user",
                new_callable=AsyncMock,
                side_effect=Exception("DB error"),
            ):
                # Should not raise
                await service.save_thread(thread, user_id=1)
