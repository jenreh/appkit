# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for MessageProcessingMixin.

Covers prompt parsing, command resolution, processing phases,
chunk buffering, error handling, and cancellation.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.database.models import ThreadStatus
from appkit_assistant.backend.schemas import (
    Chunk,
    ChunkType,
    Message,
    MessageType,
    UploadedFile,
)
from appkit_assistant.state.thread.message_processing import (
    MessageProcessingMixin,
)

_PATCH = "appkit_assistant.state.thread.message_processing"


class _StubMessageProcessing(MessageProcessingMixin):
    """Stub providing expected state vars without Reflex runtime."""

    def __init__(self) -> None:
        self.processing: bool = False
        self.cancellation_requested: bool = False
        self.messages: list[Message] = []
        self.prompt: str = ""
        self.thinking_items: list = []
        self.image_chunks: list = []
        self.show_thinking: bool = False
        self.current_activity: str = ""
        self.uploaded_files: list[UploadedFile] = []
        self.selected_mcp_servers: list = []
        self.selected_skills: list = []
        self.web_search_enabled: bool = False
        self.with_thread_list: bool = False
        self._thread = SimpleNamespace(
            thread_id="t1",
            state=ThreadStatus.NEW,
            title="Neuer Chat",
            ai_model="",
            messages=[],
            mcp_server_ids=[],
            skill_openai_ids=[],
            model_copy=lambda: SimpleNamespace(
                thread_id="t1",
                state=ThreadStatus.ACTIVE,
                title="Test",
            ),
        )
        self._skip_user_message: bool = False
        self._pending_file_cleanup: list[str] = []
        self._cancel_event: asyncio.Event | None = None
        self._current_user_id: str = ""
        self.current_user_id: str = "1"
        self.selected_model: str = "gpt-4o"
        self.get_selected_model: str = "gpt-4o"
        self.selected_model_supports_skills: bool = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get_state(self, cls: type) -> MagicMock:
        if cls.__name__ == "UserSession":
            return MagicMock(
                user=SimpleNamespace(user_id=1),
            )
        if cls.__name__ == "ThreadListState":
            mock = MagicMock()
            mock.add_thread = AsyncMock()
            return mock
        return MagicMock()


def _make_state() -> _StubMessageProcessing:
    return _StubMessageProcessing()


# ============================================================================
# Prompt parsing
# ============================================================================


class TestParsePromptSegments:
    def test_plain_text(self) -> None:
        state = _make_state()
        result = state._parse_prompt_segments("Hello world")
        assert len(result) == 1
        assert result[0] == {"type": "text", "content": "Hello world"}

    def test_single_command(self) -> None:
        state = _make_state()
        result = state._parse_prompt_segments("/summarize")
        assert len(result) == 1
        assert result[0] == {"type": "command", "handle": "summarize"}

    def test_command_with_text(self) -> None:
        state = _make_state()
        result = state._parse_prompt_segments("Hello /translate world")
        assert len(result) == 3
        assert result[0] == {"type": "text", "content": "Hello"}
        assert result[1] == {"type": "command", "handle": "translate"}
        assert result[2] == {"type": "text", "content": "world"}

    def test_multiple_commands(self) -> None:
        state = _make_state()
        result = state._parse_prompt_segments("/cmd1 text /cmd2")
        assert len(result) == 3
        assert result[0] == {"type": "command", "handle": "cmd1"}
        assert result[1] == {"type": "text", "content": "text"}
        assert result[2] == {"type": "command", "handle": "cmd2"}

    def test_empty_string(self) -> None:
        state = _make_state()
        result = state._parse_prompt_segments("")
        assert result == []

    def test_command_with_dash(self) -> None:
        state = _make_state()
        result = state._parse_prompt_segments("/my-command")
        assert result[0] == {"type": "command", "handle": "my-command"}


# ============================================================================
# Create user messages
# ============================================================================


class TestCreateUserMessages:
    def test_no_segments(self) -> None:
        state = _make_state()
        result = state._create_user_messages("Hello", [], [])
        assert len(result) == 1
        assert result[0].text == "Hello"
        assert result[0].type == MessageType.HUMAN

    def test_text_segment(self) -> None:
        state = _make_state()
        segments = [{"type": "text", "content": "Hello"}]
        result = state._create_user_messages("Hello", segments, ["file.txt"])
        assert len(result) == 1
        assert result[0].text == "Hello"
        assert result[0].attachments == ["file.txt"]

    def test_command_segment_resolved(self) -> None:
        state = _make_state()
        segments = [{"type": "command", "handle": "check", "resolved_text": "Review:"}]
        result = state._create_user_messages("/check", segments, [])
        assert len(result) == 1
        assert result[0].text == "Review:"

    def test_command_segment_unresolved(self) -> None:
        state = _make_state()
        segments = [{"type": "command", "handle": "unknown", "resolved_text": None}]
        result = state._create_user_messages("/unknown", segments, [])
        assert len(result) == 0

    def test_mixed_segments(self) -> None:
        state = _make_state()
        segments = [
            {"type": "text", "content": "Hello"},
            {
                "type": "command",
                "handle": "cmd",
                "resolved_text": "Prompt text",
            },
        ]
        result = state._create_user_messages("Hello /cmd", segments, [])
        assert len(result) == 2
        assert result[0].text == "Hello"
        assert result[1].text == "Prompt text"


# ============================================================================
# Load command prompt text
# ============================================================================


class TestLoadCommandPromptText:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        state = _make_state()

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.user_prompt_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_latest_accessible_by_handle = AsyncMock(
                return_value=MagicMock(prompt_text="Loaded prompt")
            )

            result = await state._load_command_prompt_text(1, "/test")

        assert result == "Loaded prompt"

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        state = _make_state()

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.user_prompt_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_latest_accessible_by_handle = AsyncMock(return_value=None)

            result = await state._load_command_prompt_text(1, "/missing")

        assert result is None

    @pytest.mark.asyncio
    async def test_error_returns_none(self) -> None:
        state = _make_state()

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.user_prompt_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_latest_accessible_by_handle = AsyncMock(
                side_effect=RuntimeError("db error")
            )

            result = await state._load_command_prompt_text(1, "/err")

        assert result is None


# ============================================================================
# Request cancellation
# ============================================================================


class TestRequestCancellation:
    def test_sets_flag(self) -> None:
        state = _make_state()
        state._cancel_event = asyncio.Event()

        state.request_cancellation()

        assert state.cancellation_requested is True
        assert state._cancel_event.is_set()

    def test_no_event(self) -> None:
        state = _make_state()
        state._cancel_event = None

        state.request_cancellation()

        assert state.cancellation_requested is True


# ============================================================================
# Error message
# ============================================================================


class TestAddErrorMessage:
    def test_adds_error(self) -> None:
        state = _make_state()
        state._add_error_message("Something failed")
        assert len(state.messages) == 1
        assert state.messages[0].type == MessageType.ERROR
        assert state.messages[0].text == "Something failed"


# ============================================================================
# Stop processing with error
# ============================================================================


class TestStopProcessingWithError:
    @pytest.mark.asyncio
    async def test_stops_and_adds_error(self) -> None:
        state = _make_state()
        state.processing = True

        await state._stop_processing_with_error("Model not found")

        assert state.processing is False
        assert len(state.messages) == 1
        assert state.messages[0].type == MessageType.ERROR


# ============================================================================
# Begin message processing
# ============================================================================


class TestBeginMessageProcessing:
    @pytest.mark.asyncio
    async def test_empty_prompt_returns_none(self) -> None:
        state = _make_state()
        state.prompt = "   "
        result = await state._begin_message_processing()
        assert result is None

    @pytest.mark.asyncio
    async def test_already_processing_returns_none(self) -> None:
        state = _make_state()
        state.prompt = "Hello"
        state.processing = True
        result = await state._begin_message_processing()
        assert result is None

    @pytest.mark.asyncio
    async def test_no_model_returns_none(self) -> None:
        state = _make_state()
        state.prompt = "Hello"
        state.get_selected_model = ""

        result = await state._begin_message_processing()

        assert result is None
        assert state.processing is False

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        state.prompt = "Hello"

        with patch.object(
            state,
            "_resolve_command_segments",
            new_callable=AsyncMock,
        ):
            result = await state._begin_message_processing()

        assert result is not None
        prompt, model, _servers, _files, is_new = result
        assert prompt == "Hello"
        assert model == "gpt-4o"
        assert state.processing is True
        assert is_new is True

    @pytest.mark.asyncio
    async def test_skip_user_message(self) -> None:
        state = _make_state()
        state.prompt = "Hello"
        state._skip_user_message = True

        with patch.object(
            state,
            "_resolve_command_segments",
            new_callable=AsyncMock,
        ):
            result = await state._begin_message_processing()

        assert result is not None
        # skip_user_message should be reset
        assert state._skip_user_message is False
        # Only assistant message (no user message added)
        assert len(state.messages) == 1
        assert state.messages[0].type == MessageType.ASSISTANT


# ============================================================================
# Finalize processing
# ============================================================================


class TestFinalizeProcessing:
    @pytest.mark.asyncio
    async def test_clears_processing_state(self) -> None:
        state = _make_state()
        state.processing = True
        state.cancellation_requested = True
        state.current_activity = "Thinking..."
        state._cancel_event = asyncio.Event()
        state.messages = [Message(text="response", type=MessageType.ASSISTANT)]

        with patch(f"{_PATCH}.file_manager"):
            await state._finalize_processing()

        assert state.processing is False
        assert state.cancellation_requested is False
        assert state.current_activity == ""
        assert state._cancel_event is None
        assert state.messages[0].done is True

    @pytest.mark.asyncio
    async def test_cleans_up_pending_files(self) -> None:
        state = _make_state()
        state._pending_file_cleanup = ["/tmp/f1.txt", "/tmp/f2.txt"]  # noqa: S108

        with patch(f"{_PATCH}.file_manager") as mock_fm:
            await state._finalize_processing()

        mock_fm.cleanup_uploaded_files.assert_called_once_with(
            ["/tmp/f1.txt", "/tmp/f2.txt"]  # noqa: S108
        )
        assert state._pending_file_cleanup == []


# ============================================================================
# Handle process error
# ============================================================================


class TestHandleProcessError:
    @pytest.mark.asyncio
    async def test_sets_error_state(self) -> None:
        state = _make_state()
        state.messages = [Message(text="partial", type=MessageType.ASSISTANT)]
        state._thread.mcp_server_ids = []

        with patch(f"{_PATCH}.ThreadService") as mock_ts_cls:
            mock_ts = AsyncMock()
            mock_ts_cls.return_value = mock_ts
            mock_ts.save_thread = AsyncMock()

            await state._handle_process_error(
                ex=RuntimeError("boom"),
                current_prompt="Hello",
                is_new_thread=False,
                first_response_received=True,
            )

        assert state._thread.state == ThreadStatus.ERROR
        # Last assistant message replaced with error
        assert state.messages[-1].type == MessageType.ERROR
        assert "boom" in state.messages[-1].text

    @pytest.mark.asyncio
    async def test_new_thread_sets_title(self) -> None:
        state = _make_state()
        state.with_thread_list = True
        state._thread.title = "Neuer Chat"
        state.messages = [Message(text="partial", type=MessageType.ASSISTANT)]

        with patch(f"{_PATCH}.ThreadService") as mock_ts_cls:
            mock_ts = AsyncMock()
            mock_ts_cls.return_value = mock_ts
            mock_ts.save_thread = AsyncMock()

            await state._handle_process_error(
                ex=RuntimeError("fail"),
                current_prompt="My long prompt",
                is_new_thread=True,
                first_response_received=False,
            )

        assert state._thread.title == "My long prompt"


# ============================================================================
# Notify thread created
# ============================================================================


class TestNotifyThreadCreated:
    @pytest.mark.asyncio
    async def test_notifies_thread_list(self) -> None:
        state = _make_state()

        await state._notify_thread_created()

        # get_state was called for ThreadListState


# ============================================================================
# Resolve command segments
# ============================================================================


class TestResolveCommandSegments:
    @pytest.mark.asyncio
    async def test_resolves_commands(self) -> None:
        state = _make_state()
        segments = [
            {"type": "text", "content": "Hello"},
            {"type": "command", "handle": "summarize"},
        ]

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.user_prompt_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_latest_accessible_by_handle = AsyncMock(
                return_value=MagicMock(prompt_text="Summary prompt")
            )

            await state._resolve_command_segments(segments, 1)

        assert segments[1]["resolved_text"] == "Summary prompt"

    @pytest.mark.asyncio
    async def test_handles_error(self) -> None:
        state = _make_state()
        segments = [{"type": "command", "handle": "bad"}]

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.user_prompt_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_latest_accessible_by_handle = AsyncMock(
                side_effect=RuntimeError("fail")
            )

            # Should not raise
            await state._resolve_command_segments(segments, 1)


# ============================================================================
# Flush chunk buffer
# ============================================================================


class TestFlushChunkBuffer:
    @pytest.mark.asyncio
    async def test_processes_text_chunk(self) -> None:
        state = _make_state()
        state.messages = [Message(text="", type=MessageType.ASSISTANT)]

        accumulator = MagicMock()
        accumulator.thinking_items = []
        accumulator.current_activity = ""
        accumulator.show_thinking = False
        accumulator.image_chunks = []
        accumulator.auth_required = False
        accumulator.process_chunk = MagicMock()

        chunks = [Chunk(type=ChunkType.TEXT, text="Hello")]

        result = await state._flush_chunk_buffer(
            chunks=chunks,
            accumulator=accumulator,
            current_prompt="Test",
            is_new_thread=False,
            first_response_received=True,
        )

        assert result is True
        accumulator.process_chunk.assert_called_once()

    @pytest.mark.asyncio
    async def test_new_thread_first_text_sets_title(self) -> None:
        state = _make_state()
        state._thread.title = "Neuer Chat"
        state.with_thread_list = True
        state.messages = [Message(text="", type=MessageType.ASSISTANT)]

        accumulator = MagicMock()
        accumulator.thinking_items = []
        accumulator.current_activity = ""
        accumulator.show_thinking = False
        accumulator.image_chunks = []
        accumulator.auth_required = False
        accumulator.process_chunk = MagicMock()

        chunks = [Chunk(type=ChunkType.TEXT, text="Response")]

        result = await state._flush_chunk_buffer(
            chunks=chunks,
            accumulator=accumulator,
            current_prompt="What is AI?",
            is_new_thread=True,
            first_response_received=False,
        )

        assert result is True
        assert state._thread.state == ThreadStatus.ACTIVE
        assert state._thread.title == "What is AI?"
