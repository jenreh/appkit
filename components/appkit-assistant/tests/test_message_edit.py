# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for MessageEditMixin.

Covers editing, deleting, copying, downloading, expanding, and retrying messages.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from appkit_assistant.backend.database.models import ThreadStatus
from appkit_assistant.state.thread.message_edit import MessageEditMixin

_PATCH = "appkit_assistant.state.thread.message_edit"


def _msg(msg_id: str = "m1", text: str = "Hello") -> SimpleNamespace:
    return SimpleNamespace(
        id=msg_id,
        text=text,
        original_text=None,
    )


class _StubMessageEdit(MessageEditMixin):
    """Stub providing expected state vars without Reflex runtime."""

    def __init__(self) -> None:
        self.editing_message_id: str | None = None
        self.edited_message_content: str = ""
        self.expanded_message_ids: list[str] = []
        self.messages: list = []
        self._thread = SimpleNamespace(
            state=ThreadStatus.NEW,
            messages=[],
        )
        self.prompt: str = ""
        self._skip_user_message: bool = False
        self._current_user_id: int | None = 1
        self.current_user_id: int | None = 1
        self._process_message = AsyncMock()

    # Background tasks use `async with self`. Provide a no-op context.
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _make_state() -> _StubMessageEdit:
    return _StubMessageEdit()


# ============================================================================
# Sync handlers
# ============================================================================


class TestSetEditingMode:
    def test_sets_editing_state(self) -> None:
        state = _make_state()
        state.set_editing_mode("m1", "Hello world")
        assert state.editing_message_id == "m1"
        assert state.edited_message_content == "Hello world"


class TestSetEditedMessageContent:
    def test_updates_content(self) -> None:
        state = _make_state()
        state.set_edited_message_content("Updated text")
        assert state.edited_message_content == "Updated text"


class TestCancelEdit:
    def test_clears_editing_state(self) -> None:
        state = _make_state()
        state.editing_message_id = "m1"
        state.edited_message_content = "something"
        state.cancel_edit()
        assert state.editing_message_id is None
        assert state.edited_message_content == ""


class TestToggleMessageExpanded:
    def test_expand_message(self) -> None:
        state = _make_state()
        state.toggle_message_expanded("m1")
        assert "m1" in state.expanded_message_ids

    def test_collapse_message(self) -> None:
        state = _make_state()
        state.expanded_message_ids = ["m1", "m2"]
        state.toggle_message_expanded("m1")
        assert "m1" not in state.expanded_message_ids
        assert "m2" in state.expanded_message_ids


class TestCopyMessage:
    def test_returns_events(self) -> None:
        state = _make_state()
        result = state.copy_message("Hello")
        assert isinstance(result, list)
        assert len(result) == 2


class TestDownloadMessage:
    def test_returns_call_script(self) -> None:
        state = _make_state()
        result = state.download_message("# Title", "m1")
        assert result is not None

    def test_no_message_id(self) -> None:
        state = _make_state()
        result = state.download_message("Content", "")
        assert result is not None


# ============================================================================
# Background handlers
# ============================================================================


class TestSubmitEditedMessage:
    @pytest.mark.asyncio
    async def test_empty_content_returns_toast(self) -> None:
        state = _make_state()
        state.edited_message_content = "   "

        result = state.submit_edited_message()
        # Background handler is an async generator
        chunks = [c async for c in result]
        # Should yield a toast error
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_message_not_found_cancels(self) -> None:
        state = _make_state()
        state.editing_message_id = "nonexistent"
        state.edited_message_content = "edited text"
        state.messages = [_msg("m1")]

        result = state.submit_edited_message()
        [c async for c in result]  # noqa: C419
        assert state.editing_message_id is None

    @pytest.mark.asyncio
    async def test_successful_edit(self) -> None:
        state = _make_state()
        m1 = _msg("m1", "Original")
        m2 = _msg("m2", "Response")
        state.messages = [m1, m2]
        state.editing_message_id = "m1"
        state.edited_message_content = "Edited text"

        result = state.submit_edited_message()
        [c async for c in result]  # noqa: C419

        # Messages should be truncated to only the edited message
        assert len(state.messages) == 1
        assert state.messages[0].text == "Edited text"
        assert state.prompt == "Edited text"
        assert state._skip_user_message is True
        assert state.editing_message_id is None

    @pytest.mark.asyncio
    async def test_preserves_original_text(self) -> None:
        state = _make_state()
        m1 = _msg("m1", "Original")
        state.messages = [m1]
        state.editing_message_id = "m1"
        state.edited_message_content = "Edited"

        result = state.submit_edited_message()
        [c async for c in result]

        assert state.messages[0].original_text == "Original"

    @pytest.mark.asyncio
    async def test_keeps_original_text_if_already_set(self) -> None:
        state = _make_state()
        m1 = _msg("m1", "V2")
        m1.original_text = "V1"
        state.messages = [m1]
        state.editing_message_id = "m1"
        state.edited_message_content = "V3"

        result = state.submit_edited_message()
        [c async for c in result]

        assert state.messages[0].original_text == "V1"


class TestDeleteMessage:
    @pytest.mark.asyncio
    async def test_removes_message(self) -> None:
        state = _make_state()
        state.messages = [_msg("m1"), _msg("m2")]
        state._thread.state = ThreadStatus.NEW

        await state.delete_message("m1")
        assert len(state.messages) == 1
        assert state.messages[0].id == "m2"

    @pytest.mark.asyncio
    async def test_saves_active_thread(self) -> None:
        state = _make_state()
        state.messages = [_msg("m1")]
        state._thread.state = ThreadStatus.ACTIVE

        with patch(f"{_PATCH}.ThreadService") as mock_svc:
            mock_svc.return_value.save_thread = AsyncMock()
            await state.delete_message("m1")
            mock_svc.return_value.save_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_save_for_new_thread(self) -> None:
        state = _make_state()
        state.messages = [_msg("m1")]
        state._thread.state = ThreadStatus.NEW

        with patch(f"{_PATCH}.ThreadService") as mock_svc:
            mock_svc.return_value.save_thread = AsyncMock()
            await state.delete_message("m1")
            mock_svc.return_value.save_thread.assert_not_called()


class TestRetryMessage:
    @pytest.mark.asyncio
    async def test_truncates_and_retries(self) -> None:
        state = _make_state()
        state.messages = [_msg("m1", "Q"), _msg("m2", "A"), _msg("m3", "Q2")]

        await state.retry_message("m2")

        # Should truncate to messages before index of m2
        assert len(state.messages) == 1
        assert state.messages[0].id == "m1"
        assert state.prompt == "Regenerate"
        assert state._skip_user_message is True

    @pytest.mark.asyncio
    async def test_message_not_found(self) -> None:
        state = _make_state()
        state.messages = [_msg("m1")]

        await state.retry_message("nonexistent")

        # Messages unchanged
        assert len(state.messages) == 1
