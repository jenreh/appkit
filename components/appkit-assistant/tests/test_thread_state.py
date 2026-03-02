# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for ThreadState.

Covers computed vars, initialization, thread management,
setters, toggles, clear, persistence, and load_thread.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.database.models import ThreadStatus
from appkit_assistant.backend.schemas import (
    AIModel,
    Message,
    MessageType,
    Suggestion,
    Thinking,
    ThinkingType,
    ThreadModel,
)
from appkit_assistant.state.thread_state import ThreadState

_PATCH = "appkit_assistant.state.thread_state"

# Access computed-var descriptors via __dict__.
_CV = ThreadState.__dict__


def _unwrap(name: str):
    """Get the raw function from an EventHandler in __dict__."""
    entry = ThreadState.__dict__[name]
    return entry.fn if hasattr(entry, "fn") else entry


def _thread_model(
    thread_id: str = "t1",
    state: ThreadStatus = ThreadStatus.NEW,
    ai_model: str = "gpt-4o",
    prompt: str = "",
    messages: list[Message] | None = None,
    mcp_server_ids: list[int] | None = None,
    skill_openai_ids: list[str] | None = None,
) -> ThreadModel:
    return ThreadModel(
        thread_id=thread_id,
        title="Chat",
        state=state,
        ai_model=ai_model,
        prompt=prompt,
        messages=messages or [],
        mcp_server_ids=mcp_server_ids or [],
        skill_openai_ids=skill_openai_ids or [],
    )


def _message(
    msg_type: MessageType = MessageType.HUMAN,
    text: str = "Hello",
    msg_id: str | None = None,
) -> Message:
    return Message(
        id=msg_id or str(uuid.uuid4()),
        type=msg_type,
        text=text,
        done=True,
    )


def _ai_model(
    model_id: str = "gpt-4o",
    text: str = "GPT-4o",
    supports_tools: bool = True,
    supports_attachments: bool = True,
    supports_search: bool = False,
    supports_skills: bool = True,
) -> AIModel:
    return AIModel(
        id=model_id,
        text=text,
        supports_tools=supports_tools,
        supports_attachments=supports_attachments,
        supports_search=supports_search,
        supports_skills=supports_skills,
    )


def _thinking(
    thinking_type: ThinkingType = ThinkingType.REASONING,
    thinking_id: str = "r1",
) -> Thinking:
    return Thinking(id=thinking_id, type=thinking_type, text="thinking...")


class _StubThreadState:
    """Plain stub providing ThreadState vars for testing.

    Does NOT inherit from rx.State to avoid __setattr__ issues.
    """

    def __init__(
        self,
        *,
        authenticated: bool = True,
        user_id: str = "42",
    ) -> None:
        self._thread = _thread_model()
        self.ai_models: list[AIModel] = []
        self.selected_model: str = ""
        self.processing: bool = False
        self.cancellation_requested: bool = False
        self.messages: list[Message] = []
        self.prompt: str = ""
        self.suggestions: list[Suggestion] = []

        self.thinking_items: list[Thinking] = []
        self.image_chunks: list = []
        self.show_thinking: bool = False
        self.thinking_expanded: bool = False
        self.current_activity: str = ""

        self.uploaded_files: list = []
        self.max_file_size_mb: int = 50
        self.max_files_per_thread: int = 10

        self.editing_message_id: str | None = None
        self.edited_message_content: str = ""
        self.expanded_message_ids: list[str] = []

        self.selected_mcp_servers: list = []
        self.show_tools_modal: bool = False
        self.available_mcp_servers: list = []
        self.temp_selected_mcp_servers: list[int] = []
        self.server_selection_state: dict[int, bool] = {}

        self.selected_skills: list = []
        self.available_skills_for_selection: list = []
        self.temp_selected_skill_ids: list[str] = []
        self.skill_selection_state: dict[str, bool] = {}
        self.modal_active_tab: str = "tools"

        self.web_search_enabled: bool = False

        self.show_command_palette: bool = False
        self.filtered_commands: list = []
        self.selected_command_index: int = 0
        self.command_search_prefix: str = ""
        self.command_trigger_position: int = 0
        self.available_commands: list = []

        self.with_thread_list: bool = False

        self._initialized: bool = False
        self._current_user_id: str = ""
        self._skip_user_message: bool = False
        self._pending_file_cleanup: list[str] = []
        self._cancel_event = None

        # Test config
        self._authenticated = authenticated
        self._user_id = user_id

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get_state(self, cls: type) -> MagicMock:
        name = cls.__name__
        if name == "UserSession":
            user = (
                SimpleNamespace(
                    user_id=self._user_id,
                    roles=["admin"],
                )
                if self._authenticated
                else None
            )

            async def _is_auth():
                return self._authenticated

            async def _auth_user():
                return user

            mock = MagicMock()
            mock.user = user
            mock.is_authenticated = _is_auth()
            mock.authenticated_user = _auth_user()
            return mock
        if name == "ThreadListState":
            mock = MagicMock()
            mock.threads = []
            mock.loading_thread_id = ""
            mock.active_thread_id = ""
            return mock
        return MagicMock()

    # Bind methods that are needed for testing
    def _setup_models(self, user) -> None:  # noqa: ARG002
        """Stub _setup_models from ModelSelectionMixin."""

    def _reset_ui_state(self) -> None:
        _unwrap("_reset_ui_state")(self)

    def _restore_mcp_selection(self, server_ids: list[int]) -> None:
        """Stub _restore_mcp_selection."""
        self.selected_mcp_servers = []
        self.temp_selected_mcp_servers = []
        self.server_selection_state = {}

    def _restore_skill_selection(self, skill_ids: list[str]) -> None:
        """Stub _restore_skill_selection."""
        self.selected_skills = []
        self.temp_selected_skill_ids = []
        self.skill_selection_state = {}

    def _clear_uploaded_files(self) -> None:
        """Stub _clear_uploaded_files."""
        self.uploaded_files = []

    def _update_command_palette(self, prompt: str) -> None:  # noqa: ARG002
        """Stub _update_command_palette."""

    async def _load_user_prompts_as_commands(self, user_id: int) -> None:  # noqa: ARG002
        """Stub _load_user_prompts_as_commands."""

    async def _stop_loading_state(self) -> None:
        """Stub _stop_loading_state."""

    def _load_config(self) -> None:
        """Stub _load_config."""

    async def initialize(self) -> None:
        """Stub initialize for patch.object compatibility."""

    @property
    def _thread_service(self) -> MagicMock:
        return self._mock_thread_service


def _make_state(*, authenticated: bool = True, user_id: str = "42") -> _StubThreadState:
    s = _StubThreadState(authenticated=authenticated, user_id=user_id)
    s._mock_thread_service = MagicMock()
    return s


# ============================================================================
# Computed vars
# ============================================================================


class TestComputedVars:
    def test_current_user_id(self) -> None:
        state = _make_state()
        state._current_user_id = "u123"
        assert _CV["current_user_id"].fget(state) == "u123"

    def test_current_user_id_empty(self) -> None:
        state = _make_state()
        assert _CV["current_user_id"].fget(state) == ""

    def test_has_suggestions_false(self) -> None:
        state = _make_state()
        assert _CV["has_suggestions"].fget(state) is False

    def test_has_suggestions_true(self) -> None:
        state = _make_state()
        state.suggestions = [Suggestion(prompt="test prompt")]
        assert _CV["has_suggestions"].fget(state) is True

    def test_has_thinking_content_false(self) -> None:
        state = _make_state()
        assert _CV["has_thinking_content"].fget(state) is False

    def test_has_thinking_content_true(self) -> None:
        state = _make_state()
        state.thinking_items = [_thinking()]
        assert _CV["has_thinking_content"].fget(state) is True

    def test_get_unique_reasoning_sessions(self) -> None:
        state = _make_state()
        state.thinking_items = [
            _thinking(ThinkingType.REASONING, "r1"),
            _thinking(ThinkingType.TOOL_CALL, "tc1"),
            _thinking(ThinkingType.REASONING, "r2"),
        ]
        result = _CV["get_unique_reasoning_sessions"].fget(state)
        assert result == ["r1", "r2"]

    def test_get_unique_tool_calls(self) -> None:
        state = _make_state()
        state.thinking_items = [
            _thinking(ThinkingType.REASONING, "r1"),
            _thinking(ThinkingType.TOOL_CALL, "tc1"),
            _thinking(ThinkingType.TOOL_CALL, "tc2"),
        ]
        result = _CV["get_unique_tool_calls"].fget(state)
        assert result == ["tc1", "tc2"]

    def test_get_unique_reasoning_sessions_empty(self) -> None:
        state = _make_state()
        assert _CV["get_unique_reasoning_sessions"].fget(state) == []

    def test_get_unique_tool_calls_empty(self) -> None:
        state = _make_state()
        assert _CV["get_unique_tool_calls"].fget(state) == []

    def test_get_last_assistant_message_text(self) -> None:
        state = _make_state()
        state.messages = [
            _message(MessageType.HUMAN, "hi"),
            _message(MessageType.ASSISTANT, "hello"),
            _message(MessageType.HUMAN, "bye"),
        ]
        result = _CV["get_last_assistant_message_text"].fget(state)
        assert result == "hello"

    def test_get_last_assistant_message_text_empty(self) -> None:
        state = _make_state()
        result = _CV["get_last_assistant_message_text"].fget(state)
        assert result == ""

    def test_get_last_assistant_message_picks_last(self) -> None:
        state = _make_state()
        state.messages = [
            _message(MessageType.ASSISTANT, "first"),
            _message(MessageType.ASSISTANT, "second"),
        ]
        result = _CV["get_last_assistant_message_text"].fget(state)
        assert result == "second"


# ============================================================================
# _reset_ui_state
# ============================================================================


class TestResetUIState:
    def test_clears_all(self) -> None:
        state = _make_state()
        state.messages = [_message()]
        state.thinking_items = [_thinking()]
        state.image_chunks = [MagicMock()]
        state.prompt = "some prompt"
        state.show_thinking = True
        state.available_commands = [MagicMock()]

        state._reset_ui_state()

        assert state.messages == []
        assert state.thinking_items == []
        assert state.image_chunks == []
        assert state.prompt == ""
        assert state.show_thinking is False
        assert state.available_commands == []


# ============================================================================
# _load_config
# ============================================================================


class TestLoadConfig:
    def test_loads_from_registry(self) -> None:
        state = _make_state()
        fn = _unwrap("_load_config")

        mock_config = MagicMock()
        mock_config.file_upload.max_file_size_mb = 25
        mock_config.file_upload.max_files_per_thread = 5

        with patch(f"{_PATCH}.service_registry") as mock_reg:
            mock_reg.return_value.get.return_value = mock_config
            fn(state)

        assert state.max_file_size_mb == 25
        assert state.max_files_per_thread == 5

    def test_no_config_keeps_defaults(self) -> None:
        state = _make_state()
        fn = _unwrap("_load_config")

        with patch(f"{_PATCH}.service_registry") as mock_reg:
            mock_reg.return_value.get.return_value = None
            fn(state)

        assert state.max_file_size_mb == 50
        assert state.max_files_per_thread == 10


# ============================================================================
# initialize
# ============================================================================


class TestInitialize:
    @pytest.mark.asyncio
    async def test_first_init(self) -> None:
        state = _make_state()
        fn = _unwrap("initialize")

        mock_svc = MagicMock()
        mock_svc.create_new_thread.return_value = _thread_model("new-t")
        state._mock_thread_service = mock_svc

        with patch(f"{_PATCH}.service_registry") as mock_reg:
            mock_reg.return_value.get.return_value = None
            await fn(state)

        assert state._initialized is True
        assert state._current_user_id == "42"
        assert state._thread.thread_id == "new-t"

    @pytest.mark.asyncio
    async def test_already_initialized_same_user(self) -> None:
        state = _make_state()
        state._initialized = True
        state._current_user_id = "42"

        fn = _unwrap("initialize")
        await fn(state)

        # Should not reinitialize
        assert state._initialized is True

    @pytest.mark.asyncio
    async def test_different_user_reinitializes(self) -> None:
        state = _make_state(user_id="99")
        state._initialized = True
        state._current_user_id = "42"  # Different from "99"

        fn = _unwrap("initialize")

        mock_svc = MagicMock()
        mock_svc.create_new_thread.return_value = _thread_model("new-t")
        state._mock_thread_service = mock_svc

        with patch(f"{_PATCH}.service_registry") as mock_reg:
            mock_reg.return_value.get.return_value = None
            await fn(state)

        assert state._current_user_id == "99"
        assert state._initialized is True

    @pytest.mark.asyncio
    async def test_unauthenticated_user(self) -> None:
        state = _make_state(authenticated=False)
        fn = _unwrap("initialize")

        mock_svc = MagicMock()
        mock_svc.create_new_thread.return_value = _thread_model("empty")
        state._mock_thread_service = mock_svc

        with patch(f"{_PATCH}.service_registry") as mock_reg:
            mock_reg.return_value.get.return_value = None
            await fn(state)

        assert state._initialized is True
        assert state._current_user_id == ""

    @pytest.mark.asyncio
    async def test_load_user_prompts_error_handled(self) -> None:
        state = _make_state()
        fn = _unwrap("initialize")

        mock_svc = MagicMock()
        mock_svc.create_new_thread.return_value = _thread_model("new-t")
        state._mock_thread_service = mock_svc

        async def _fail_prompts(user_id: int) -> None:  # noqa: ARG001
            raise RuntimeError("prompt load failed")

        state._load_user_prompts_as_commands = _fail_prompts

        with patch(f"{_PATCH}.service_registry") as mock_reg:
            mock_reg.return_value.get.return_value = None
            # Should not raise, error is caught
            await fn(state)

        assert state._initialized is True


# ============================================================================
# new_thread
# ============================================================================


class TestNewThread:
    @pytest.mark.asyncio
    async def test_creates_new_thread(self) -> None:
        state = _make_state()
        state._initialized = True
        state._thread = _thread_model("old", state=ThreadStatus.ACTIVE)
        state.messages = [_message()]

        fn = _unwrap("new_thread")

        mock_svc = MagicMock()
        mock_svc.create_new_thread.return_value = _thread_model("new-t")
        state._mock_thread_service = mock_svc

        await fn(state)

        assert state._thread.thread_id == "new-t"
        assert state.messages == []
        assert state.thinking_items == []
        assert state.prompt == ""

    @pytest.mark.asyncio
    async def test_skips_if_already_empty(self) -> None:
        state = _make_state()
        state._initialized = True
        state._thread = _thread_model("current", state=ThreadStatus.NEW)
        state.messages = []

        fn = _unwrap("new_thread")
        await fn(state)

        # Thread ID unchanged
        assert state._thread.thread_id == "current"

    @pytest.mark.asyncio
    async def test_calls_initialize_if_not_initialized(self) -> None:
        state = _make_state()
        state._initialized = False

        fn = _unwrap("new_thread")

        # Mock initialize to set _initialized
        async def _mock_init(self_):
            self_._initialized = True
            self_._thread = _thread_model("init-t", state=ThreadStatus.NEW)

        with patch.object(type(state), "initialize", _mock_init):
            await fn(state)

        # Since thread is NEW with no messages, it should skip creating another
        assert state._initialized is True


# ============================================================================
# set_thread
# ============================================================================


class TestSetThread:
    def test_sets_thread_data(self) -> None:
        state = _make_state()
        fn = _unwrap("set_thread")

        msgs = [_message(MessageType.ASSISTANT, "hi")]
        thread = _thread_model("t2", ai_model="claude-3", messages=msgs)

        fn(state, thread)

        assert state._thread.thread_id == "t2"
        assert state.messages == msgs
        assert state.selected_model == "claude-3"
        assert state.thinking_items == []
        assert state.prompt == ""


# ============================================================================
# set_prompt
# ============================================================================


class TestSetPrompt:
    def test_sets_prompt(self) -> None:
        state = _make_state()
        fn = _unwrap("set_prompt")

        fn(state, "hello world")

        assert state.prompt == "hello world"

    def test_empty_prompt(self) -> None:
        state = _make_state()
        fn = _unwrap("set_prompt")

        fn(state, "")

        assert state.prompt == ""


# ============================================================================
# set_suggestions
# ============================================================================


class TestSetSuggestions:
    def test_dict_input(self) -> None:
        state = _make_state()
        fn = _unwrap("set_suggestions")

        fn(state, [{"prompt": "test prompt", "icon": "star"}])

        assert len(state.suggestions) == 1
        assert state.suggestions[0].prompt == "test prompt"

    def test_model_input(self) -> None:
        state = _make_state()
        fn = _unwrap("set_suggestions")

        s = Suggestion(prompt="p1")
        fn(state, [s])

        assert len(state.suggestions) == 1
        assert state.suggestions[0] is s

    def test_empty_list(self) -> None:
        state = _make_state()
        fn = _unwrap("set_suggestions")

        fn(state, [])

        assert state.suggestions == []


# ============================================================================
# set_with_thread_list
# ============================================================================


class TestSetWithThreadList:
    def test_sets_flag(self) -> None:
        state = _make_state()
        fn = _unwrap("set_with_thread_list")

        fn(state, True)
        assert state.with_thread_list is True

        fn(state, False)
        assert state.with_thread_list is False


# ============================================================================
# toggle_thinking_expanded
# ============================================================================


class TestToggleThinkingExpanded:
    def test_toggles(self) -> None:
        state = _make_state()
        fn = _unwrap("toggle_thinking_expanded")

        assert state.thinking_expanded is False
        fn(state)
        assert state.thinking_expanded is True
        fn(state)
        assert state.thinking_expanded is False


# ============================================================================
# toggle_web_search
# ============================================================================


class TestToggleWebSearch:
    def test_toggles(self) -> None:
        state = _make_state()
        fn = _unwrap("toggle_web_search")

        assert state.web_search_enabled is False
        fn(state)
        assert state.web_search_enabled is True
        fn(state)
        assert state.web_search_enabled is False


# ============================================================================
# clear
# ============================================================================


class TestClear:
    def test_clears_thread(self) -> None:
        state = _make_state()
        state._thread = _thread_model(
            "t1",
            state=ThreadStatus.ACTIVE,
            messages=[_message()],
        )
        state.messages = [_message()]
        state.prompt = "test"
        state.thinking_items = [_thinking()]
        state.image_chunks = [MagicMock()]
        state.show_thinking = True
        state.uploaded_files = [MagicMock()]

        fn = _unwrap("clear")

        with patch(f"{_PATCH}.ModelManager") as mock_mm:
            mock_mm.return_value.get_default_model.return_value = "gpt-5-mini"
            fn(state)

        assert state._thread.messages == []
        assert state._thread.state == ThreadStatus.NEW
        assert state._thread.ai_model == "gpt-5-mini"
        assert state._thread.active is True
        assert state._thread.prompt == ""
        assert state._thread.mcp_server_ids == []
        assert state.prompt == ""
        assert state.messages == []
        assert state.thinking_items == []
        assert state.image_chunks == []
        assert state.show_thinking is False
        assert state.uploaded_files == []


# ============================================================================
# persist_current_thread (background task)
# ============================================================================


class TestPersistCurrentThread:
    @pytest.mark.asyncio
    async def test_new_thread_skips(self) -> None:
        state = _make_state()
        state._thread = _thread_model(state=ThreadStatus.NEW)

        fn = _unwrap("persist_current_thread")
        [c async for c in fn(state)]

        # No save should happen

    @pytest.mark.asyncio
    async def test_no_user_skips(self) -> None:
        state = _make_state(authenticated=False)
        state._thread = _thread_model(state=ThreadStatus.ACTIVE)

        fn = _unwrap("persist_current_thread")
        [c async for c in fn(state)]

        # No save should happen

    @pytest.mark.asyncio
    async def test_saves_thread(self) -> None:
        state = _make_state()
        state._thread = _thread_model(state=ThreadStatus.ACTIVE)

        mock_svc = MagicMock()
        mock_svc.save_thread = AsyncMock()
        state._mock_thread_service = mock_svc

        fn = _unwrap("persist_current_thread")
        [c async for c in fn(state)]

        mock_svc.save_thread.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_error_handled(self) -> None:
        state = _make_state()
        state._thread = _thread_model(state=ThreadStatus.ACTIVE)

        mock_svc = MagicMock()
        mock_svc.save_thread = AsyncMock(side_effect=RuntimeError("DB error"))
        state._mock_thread_service = mock_svc

        fn = _unwrap("persist_current_thread")
        # Should not raise
        [c async for c in fn(state)]


# ============================================================================
# load_thread (background task)
# ============================================================================


class TestLoadThread:
    @pytest.mark.asyncio
    async def test_unauthenticated_returns(self) -> None:
        state = _make_state(authenticated=False)
        fn = _unwrap("load_thread")

        [c async for c in fn(state, "t1")]

        # No crash, just returns

    @pytest.mark.asyncio
    async def test_thread_not_found(self) -> None:
        state = _make_state()
        fn = _unwrap("load_thread")

        mock_svc = MagicMock()
        mock_svc.load_thread = AsyncMock(return_value=None)
        state._mock_thread_service = mock_svc

        [c async for c in fn(state, "t1")]

        # Thread not loaded, no crash

    @pytest.mark.asyncio
    async def test_successful_load(self) -> None:
        state = _make_state()
        fn = _unwrap("load_thread")

        msgs = [_message(MessageType.ASSISTANT, "Hello")]
        thread = _thread_model(
            "t2",
            state=ThreadStatus.ACTIVE,
            ai_model="claude-3",
            messages=msgs,
        )

        mock_svc = MagicMock()
        mock_svc.load_thread = AsyncMock(return_value=thread)
        state._mock_thread_service = mock_svc

        with patch(f"{_PATCH}.ModelManager") as mock_mm:
            model = MagicMock(supports_tools=True, supports_skills=True)
            mock_mm.return_value.get_model.return_value = model

            [c async for c in fn(state, "t2")]

        assert state._thread.thread_id == "t2"
        assert state.selected_model == "claude-3"
        assert state.messages[0].done is True

    @pytest.mark.asyncio
    async def test_load_error_handled(self) -> None:
        state = _make_state()
        fn = _unwrap("load_thread")

        mock_svc = MagicMock()
        mock_svc.load_thread = AsyncMock(side_effect=RuntimeError("DB error"))
        state._mock_thread_service = mock_svc

        # Should not raise
        [c async for c in fn(state, "t1")]

    @pytest.mark.asyncio
    async def test_load_model_no_tools(self) -> None:
        state = _make_state()
        fn = _unwrap("load_thread")

        thread = _thread_model(
            "t3",
            state=ThreadStatus.ACTIVE,
            ai_model="simple-model",
            mcp_server_ids=[1, 2],
            skill_openai_ids=["sk1"],
        )

        mock_svc = MagicMock()
        mock_svc.load_thread = AsyncMock(return_value=thread)
        state._mock_thread_service = mock_svc

        with patch(f"{_PATCH}.ModelManager") as mock_mm:
            model = MagicMock(supports_tools=False, supports_skills=False)
            mock_mm.return_value.get_model.return_value = model

            [c async for c in fn(state, "t3")]

        # MCP and skills should be cleared
        assert state.selected_mcp_servers == []
        assert state.selected_skills == []

    @pytest.mark.asyncio
    async def test_load_model_none(self) -> None:
        """Model not found in ModelManager."""
        state = _make_state()
        fn = _unwrap("load_thread")

        thread = _thread_model(
            "t4",
            state=ThreadStatus.ACTIVE,
            ai_model="unknown-model",
        )

        mock_svc = MagicMock()
        mock_svc.load_thread = AsyncMock(return_value=thread)
        state._mock_thread_service = mock_svc

        with patch(f"{_PATCH}.ModelManager") as mock_mm:
            mock_mm.return_value.get_model.return_value = None

            [c async for c in fn(state, "t4")]

        assert state.selected_mcp_servers == []
        assert state.selected_skills == []


# ============================================================================
# _stop_loading_state
# ============================================================================


class TestStopLoadingState:
    @pytest.mark.asyncio
    async def test_clears_loading(self) -> None:
        state = _make_state()
        fn = _unwrap("_stop_loading_state")

        await fn(state)
        # Just verifies no crash — actual assertion needs
        # get_state(ThreadListState) mock which our stub provides
