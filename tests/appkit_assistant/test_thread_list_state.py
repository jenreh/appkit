# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for ThreadListState.

Covers thread list loading, adding, deleting, computed vars,
logout reset, and OpenAI file cleanup.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.database.models import ThreadStatus
from appkit_assistant.backend.schemas import ThreadModel
from appkit_assistant.state.thread_list_state import ThreadListState

_PATCH = "appkit_assistant.state.thread_list_state"

# Access computed-var descriptors via __dict__.
_CV = ThreadListState.__dict__


def _unwrap(name: str):
    """Get the raw function from an EventHandler in __dict__."""
    entry = ThreadListState.__dict__[name]
    return entry.fn if hasattr(entry, "fn") else entry


def _thread_model(
    thread_id: str = "t1",
    title: str = "Thread 1",
    state: ThreadStatus = ThreadStatus.NEW,
    ai_model: str = "gpt-4o",
    active: bool = False,
) -> ThreadModel:
    return ThreadModel(
        thread_id=thread_id,
        title=title,
        state=state,
        ai_model=ai_model,
        active=active,
        messages=[],
    )


class _StubThreadListState:
    """Plain stub providing ThreadListState vars."""

    # Class-level attrs for type(self).method lookups
    cleanup_thread_openai_files = MagicMock()

    def __init__(self) -> None:
        self.threads: list[ThreadModel] = []
        self.active_thread_id: str = ""
        self.loading_thread_id: str = ""
        self.loading: bool = True
        self._initialized: bool = False
        self._current_user_id: str = ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get_state(self, cls: type) -> MagicMock:
        if cls.__name__ == "UserSession":
            user = SimpleNamespace(user_id="user-1")

            async def _is_auth():
                return True

            return MagicMock(
                user=user,
                is_authenticated=_is_auth(),
            )
        # ThreadState
        mock = MagicMock()
        mock.new_thread = AsyncMock()
        return mock

    # Bind unwrapped methods
    _clear_threads = _unwrap("_clear_threads")
    add_thread = _unwrap("add_thread")
    reset_on_logout = _unwrap("reset_on_logout")


def _make_state() -> _StubThreadListState:
    return _StubThreadListState()


# ============================================================================
# Computed vars
# ============================================================================


class TestComputedVars:
    def test_has_threads_empty(self) -> None:
        state = _make_state()
        assert _CV["has_threads"].fget(state) is False

    def test_has_threads_with_threads(self) -> None:
        state = _make_state()
        state.threads = [_thread_model()]
        assert _CV["has_threads"].fget(state) is True


# ============================================================================
# _clear_threads
# ============================================================================


class TestClearThreads:
    def test_clears_all(self) -> None:
        state = _make_state()
        state.threads = [_thread_model()]
        state.active_thread_id = "t1"
        state.loading_thread_id = "t1"

        state._clear_threads()

        assert state.threads == []
        assert state.active_thread_id == ""
        assert state.loading_thread_id == ""


# ============================================================================
# add_thread
# ============================================================================


class TestAddThread:
    @pytest.mark.asyncio
    async def test_add_new_thread(self) -> None:
        state = _make_state()
        t = _thread_model("t1", "New Chat")

        await state.add_thread(t)

        assert len(state.threads) == 1
        assert state.threads[0].thread_id == "t1"
        assert state.threads[0].active is True
        assert state.active_thread_id == "t1"

    @pytest.mark.asyncio
    async def test_add_idempotent(self) -> None:
        state = _make_state()
        t = _thread_model("t1", "Chat")
        state.threads = [t]

        await state.add_thread(_thread_model("t1", "Chat"))

        # Should NOT duplicate
        assert len(state.threads) == 1

    @pytest.mark.asyncio
    async def test_deactivates_others(self) -> None:
        state = _make_state()
        existing = _thread_model("t1", "Old", active=True)
        state.threads = [existing]

        await state.add_thread(_thread_model("t2", "New"))

        assert len(state.threads) == 2
        # New thread is first and active
        assert state.threads[0].thread_id == "t2"
        assert state.threads[0].active is True
        # Old thread is deactivated
        assert state.threads[1].active is False

    @pytest.mark.asyncio
    async def test_add_to_beginning(self) -> None:
        state = _make_state()
        state.threads = [_thread_model("t1")]

        await state.add_thread(_thread_model("t2"))

        assert state.threads[0].thread_id == "t2"
        assert state.threads[1].thread_id == "t1"


# ============================================================================
# reset_on_logout
# ============================================================================


class TestResetOnLogout:
    @pytest.mark.asyncio
    async def test_clears_state(self) -> None:
        state = _make_state()
        state.threads = [_thread_model()]
        state.active_thread_id = "t1"
        state._initialized = True
        state._current_user_id = "user-1"

        await state.reset_on_logout()

        assert state.threads == []
        assert state.active_thread_id == ""
        assert state.loading is False
        assert state._initialized is False
        assert state._current_user_id == ""


# ============================================================================
# delete_thread (background task)
# ============================================================================


class TestDeleteThread:
    @pytest.mark.asyncio
    async def test_not_found_in_list(self) -> None:
        state = _make_state()
        state.threads = []

        fn = _unwrap("delete_thread")
        chunks = [c async for c in fn(state, "unknown")]

        assert any(chunks)  # toast error

    @pytest.mark.asyncio
    async def test_successful_delete(self) -> None:
        state = _make_state()
        t = _thread_model("t1", "Chat 1")
        state.threads = [t]
        state.active_thread_id = "t1"

        fn = _unwrap("delete_thread")

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.thread_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_thread_id_and_user = AsyncMock(
                return_value=MagicMock(id=1, vector_store_id=None)
            )
            mock_repo.delete_by_thread_id_and_user = AsyncMock()

            # file_upload_repo is locally imported inside delete_thread
            with patch(
                "appkit_assistant.backend.database.repositories.file_upload_repo",
            ) as mock_file_repo:
                mock_file_repo.find_by_thread = AsyncMock(return_value=[])
                [c async for c in fn(state, "t1")]

        assert "t1" not in [t.thread_id for t in state.threads]
        assert state.loading_thread_id == ""

    @pytest.mark.asyncio
    async def test_delete_error_handled(self) -> None:
        state = _make_state()
        t = _thread_model("t1", "Chat 1")
        state.threads = [t]

        fn = _unwrap("delete_thread")

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.thread_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_thread_id_and_user = AsyncMock(
                side_effect=RuntimeError("fail")
            )

            chunks = [c async for c in fn(state, "t1")]

        assert state.loading_thread_id == ""
        # toast error yielded
        assert any(chunks)

    @pytest.mark.asyncio
    async def test_not_authenticated(self) -> None:
        state = _make_state()
        t = _thread_model("t1", "Chat")
        state.threads = [t]

        # Override get_state to return unauthenticated user
        async def _unauth_state(_cls):
            async def _not_auth():
                return False

            return MagicMock(
                user=None,
                is_authenticated=_not_auth(),
            )

        state.get_state = _unauth_state

        fn = _unwrap("delete_thread")
        [c async for c in fn(state, "t1")]

        assert state.loading_thread_id == ""


# ============================================================================
# cleanup_thread_openai_files
# ============================================================================


class TestCleanupOpenAIFiles:
    @pytest.mark.asyncio
    async def test_openai_not_available(self) -> None:
        state = _make_state()
        fn = _unwrap("cleanup_thread_openai_files")

        # Locally imported inside cleanup_thread_openai_files
        with patch(
            "appkit_assistant.backend.services.openai_client_service.get_openai_client_service",
        ) as mock_svc:
            mock_svc.return_value.is_available = False
            chunks = [c async for c in fn(state, ["file-1"], None)]

        # Just logs warning, no error
        assert len(chunks) <= 1

    @pytest.mark.asyncio
    async def test_with_files_and_vector_store(self) -> None:
        state = _make_state()
        fn = _unwrap("cleanup_thread_openai_files")

        mock_client = MagicMock()

        # Both are locally imported inside cleanup_thread_openai_files
        with (
            patch(
                "appkit_assistant.backend.services.openai_client_service.get_openai_client_service",
            ) as mock_svc,
            patch(
                "appkit_assistant.backend.services.file_upload_service.FileUploadService",
            ) as mock_fus_cls,
        ):
            mock_svc.return_value.is_available = True
            mock_svc.return_value.create_client.return_value = mock_client
            mock_fus = AsyncMock()
            mock_fus_cls.return_value = mock_fus
            mock_fus.delete_vector_store = AsyncMock()
            mock_fus.delete_files = AsyncMock()

            [c async for c in fn(state, ["file-1", "file-2"], "vs-1")]

        mock_fus.delete_vector_store.assert_awaited_once_with("vs-1")
        mock_fus.delete_files.assert_awaited_once_with(["file-1", "file-2"])
