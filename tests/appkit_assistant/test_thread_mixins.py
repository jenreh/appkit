"""Tests for ThreadState mixin classes.

Tests the mixin logic by creating lightweight stub classes that simulate
the state variables expected by each mixin. This avoids the heavy Reflex
state machinery while exercising all business logic paths.
"""

# ruff: noqa: SLF001, N806, S108, ARG001, ARG002, PERF401

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.database.models import MCPServer, Skill
from appkit_assistant.backend.schemas import (
    AIModel,
    CommandDefinition,
    Message,
    MessageType,
    ThreadModel,
    UploadedFile,
)
from appkit_assistant.backend.services.response_accumulator import (
    ResponseAccumulator,
)
from appkit_assistant.state.thread.command_palette import (
    CommandPaletteMixin,
)
from appkit_assistant.state.thread.file_upload import FileUploadMixin
from appkit_assistant.state.thread.mcp_tools import McpToolsMixin
from appkit_assistant.state.thread.message_edit import MessageEditMixin
from appkit_assistant.state.thread.message_processing import (
    MessageProcessingMixin,
)
from appkit_assistant.state.thread.model_selection import (
    ModelSelectionMixin,
)
from appkit_assistant.state.thread.oauth import OAuthMixin
from appkit_assistant.state.thread.skills import SkillsMixin

# =====================================================================
# Helper factories
# =====================================================================


def _cmd(
    id: str,  # noqa: A002
    *,
    editable: bool = False,
    mcp_server_ids: list[int] | None = None,
) -> CommandDefinition:
    return CommandDefinition(
        id=id,
        label=f"/{id}",
        description=f"Desc of {id}",
        is_editable=editable,
        mcp_server_ids=mcp_server_ids or [],
    )


def _model(
    id: str,  # noqa: A002
    *,
    supports_tools: bool = False,
    supports_attachments: bool = False,
    supports_search: bool = False,
    supports_skills: bool = False,
    requires_role: str | None = None,
    active: bool = True,
) -> AIModel:
    return AIModel(
        id=id,
        text=id,
        supports_tools=supports_tools,
        supports_attachments=supports_attachments,
        supports_search=supports_search,
        supports_skills=supports_skills,
        requires_role=requires_role,
        active=active,
    )


def _message(text: str, type_: MessageType = MessageType.HUMAN, **kw: Any) -> Message:
    return Message(text=text, type=type_, **kw)


def _mcp_server(
    id: int,  # noqa: A002
    name: str = "srv",
    **kw: Any,
) -> MCPServer:
    defaults: dict[str, Any] = {
        "name": name,
        "url": f"https://{name}.example.com",
        "active": True,
    }
    defaults.update(kw)
    server = MCPServer(**defaults)
    server.id = id
    return server


def _skill(
    openai_id: str,
    name: str = "skill",
    *,
    required_role: str | None = None,
    api_key_hash: str = "abc",
) -> Skill:
    return Skill(
        openai_id=openai_id,
        name=name,
        description="Test skill",
        default_version="1",
        latest_version="1",
        active=True,
        required_role=required_role,
        api_key_hash=api_key_hash,
        last_synced=datetime.now(UTC),
    )


# =====================================================================
# ModelSelectionMixin
# =====================================================================


class _ModelState(ModelSelectionMixin):
    """Stub owning the state vars needed by ModelSelectionMixin."""

    ai_models: list[AIModel] = []
    selected_model: str = ""
    web_search_enabled: bool = False
    selected_mcp_servers: list[MCPServer] = []
    temp_selected_mcp_servers: list[int] = []
    server_selection_state: dict[int, bool] = {}
    uploaded_files: list[UploadedFile] = []
    selected_skills: list[Skill] = []
    temp_selected_skill_ids: list[str] = []
    skill_selection_state: dict[str, bool] = {}
    modal_active_tab: str = "tools"
    _thread: ThreadModel = ThreadModel(thread_id="t1")
    _current_user_id: str = "1"

    # stubs for methods called by the mixin
    def _restore_mcp_selection(self, ids: list[int]) -> None:
        self.selected_mcp_servers = []
        self.temp_selected_mcp_servers = []
        self.server_selection_state = {}

    def _clear_uploaded_files(self) -> None:
        self.uploaded_files = []

    def _restore_skill_selection(self, ids: list[str]) -> None:
        self.selected_skills = []
        self.temp_selected_skill_ids = []
        self.skill_selection_state = {}

    # Cross-mixin method references used by set_selected_model
    @staticmethod
    async def load_available_skills_for_user() -> None:
        pass

    @staticmethod
    async def persist_current_thread() -> None:
        pass


class TestModelSelectionMixin:
    """Tests for ModelSelectionMixin."""

    def _state(self, **overrides: Any) -> _ModelState:
        s = _ModelState()
        for k, v in overrides.items():
            setattr(s, k, v)
        return s

    # -- _setup_models --------------------------------------------------

    def test_setup_models_filters_by_role(self) -> None:
        """Models requiring a role the user doesn't have are excluded."""
        st = self._state()
        user = MagicMock(roles=["user"])

        models = [_model("m1"), _model("m2", requires_role="admin")]
        with (
            patch.object(ModelSelectionMixin, "_setup_models", wraps=st._setup_models),
            patch("appkit_assistant.state.thread.model_selection.ModelManager") as MM,
        ):
            mm = MM.return_value
            mm.get_all_models.return_value = models
            mm.get_default_model.return_value = "m1"
            st._setup_models(user)

        assert len(st.ai_models) == 1
        assert st.ai_models[0].id == "m1"

    def test_setup_models_allows_matching_role(self) -> None:
        """Models accessible when user has the required role."""
        st = self._state()
        user = MagicMock(roles=["admin"])

        models = [_model("m1", requires_role="admin")]
        with patch("appkit_assistant.state.thread.model_selection.ModelManager") as MM:
            mm = MM.return_value
            mm.get_all_models.return_value = models
            mm.get_default_model.return_value = "m1"
            st._setup_models(user)

        assert len(st.ai_models) == 1
        assert st.selected_model == "m1"

    def test_setup_models_fallback_to_default(self) -> None:
        """Selected model falls back to default when current is invalid."""
        st = self._state(selected_model="old")
        user = MagicMock(roles=[])

        models = [_model("m1"), _model("m2")]
        with patch("appkit_assistant.state.thread.model_selection.ModelManager") as MM:
            mm = MM.return_value
            mm.get_all_models.return_value = models
            mm.get_default_model.return_value = "m2"
            st._setup_models(user)

        assert st.selected_model == "m2"

    def test_setup_models_fallback_to_first(self) -> None:
        """Falls back to first model when default is not available."""
        st = self._state(selected_model="old")
        user = MagicMock(roles=[])

        models = [_model("m1")]
        with patch("appkit_assistant.state.thread.model_selection.ModelManager") as MM:
            mm = MM.return_value
            mm.get_all_models.return_value = models
            mm.get_default_model.return_value = "nonexistent"
            st._setup_models(user)

        assert st.selected_model == "m1"

    def test_setup_models_no_models_available(self) -> None:
        """Warning logged and empty model when no models match."""
        st = self._state(selected_model="old")
        user = MagicMock(roles=[])

        with patch("appkit_assistant.state.thread.model_selection.ModelManager") as MM:
            mm = MM.return_value
            mm.get_all_models.return_value = []
            mm.get_default_model.return_value = ""
            st._setup_models(user)

        assert st.selected_model == ""
        assert st.ai_models == []

    def test_setup_models_keeps_current_selection(self) -> None:
        """Keeps current selection when it's still available."""
        st = self._state(selected_model="m2")
        user = MagicMock(roles=[])

        models = [_model("m1"), _model("m2")]
        with patch("appkit_assistant.state.thread.model_selection.ModelManager") as MM:
            mm = MM.return_value
            mm.get_all_models.return_value = models
            mm.get_default_model.return_value = "m1"
            st._setup_models(user)

        assert st.selected_model == "m2"

    # -- set_selected_model ---------------------------------------------

    def test_set_selected_model_deactivates_search(self) -> None:
        """Web search is disabled when model doesn't support it."""
        st = self._state(web_search_enabled=True)
        model = _model("m1", supports_search=False)

        with patch("appkit_assistant.state.thread.model_selection.ModelManager") as MM:
            MM.return_value.get_model.return_value = model
            st.set_selected_model("m1")

        assert st.web_search_enabled is False

    def test_set_selected_model_deactivates_tools(self) -> None:
        """MCP servers cleared when model doesn't support tools."""
        srv = _mcp_server(1, "s1")
        st = self._state(selected_mcp_servers=[srv])
        model = _model("m1", supports_tools=False)

        with patch("appkit_assistant.state.thread.model_selection.ModelManager") as MM:
            MM.return_value.get_model.return_value = model
            st.set_selected_model("m1")

        assert st.selected_mcp_servers == []

    def test_set_selected_model_clears_files(self) -> None:
        """Uploaded files cleared when model doesn't support attachments."""
        f = UploadedFile(filename="a.pdf", file_path="/tmp/a.pdf", size=100)
        st = self._state(uploaded_files=[f])
        model = _model("m1", supports_attachments=False)

        with patch("appkit_assistant.state.thread.model_selection.ModelManager") as MM:
            MM.return_value.get_model.return_value = model
            st.set_selected_model("m1")

        assert st.uploaded_files == []

    def test_set_selected_model_clears_skills(self) -> None:
        """Skills cleared when model doesn't support skills."""
        sk = _skill("sk1")
        st = self._state(selected_skills=[sk])
        model = _model("m1", supports_skills=False)

        with patch("appkit_assistant.state.thread.model_selection.ModelManager") as MM:
            MM.return_value.get_model.return_value = model
            st.set_selected_model("m1")

        assert st.selected_skills == []

    def test_set_selected_model_unknown_model(self) -> None:
        """Returns None when model is not found."""
        st = self._state()

        with patch("appkit_assistant.state.thread.model_selection.ModelManager") as MM:
            MM.return_value.get_model.return_value = None
            result = st.set_selected_model("unknown")

        assert result is None

    def test_set_selected_model_resets_modal_tab(self) -> None:
        """Modal tab is reset to 'tools' when model changes."""
        st = self._state(modal_active_tab="skills")
        model = _model("m1")

        with patch("appkit_assistant.state.thread.model_selection.ModelManager") as MM:
            MM.return_value.get_model.return_value = model
            st.set_selected_model("m1")

        assert st.modal_active_tab == "tools"


# =====================================================================
# CommandPaletteMixin
# =====================================================================


class _CmdState(CommandPaletteMixin):
    """Stub owning the state vars needed by CommandPaletteMixin."""

    show_command_palette: bool = False
    filtered_commands: list[CommandDefinition] = []
    selected_command_index: int = 0
    command_search_prefix: str = ""
    command_trigger_position: int = 0
    available_commands: list[CommandDefinition] = []
    prompt: str = ""
    available_mcp_servers: list[MCPServer] = []
    selected_mcp_servers: list[MCPServer] = []
    temp_selected_mcp_servers: list[int] = []
    server_selection_state: dict[int, bool] = {}
    _current_user_id: str = ""


class TestCommandPaletteMixin:
    """Tests for CommandPaletteMixin."""

    def _state(self, **overrides: Any) -> _CmdState:
        s = _CmdState()
        for k, v in overrides.items():
            setattr(s, k, v)
        return s

    # -- _update_command_palette ----------------------------------------

    def test_update_shows_palette_on_slash(self) -> None:
        """Palette appears when prompt ends with '/'."""
        cmds = [_cmd("teach"), _cmd("brainstorm")]
        st = self._state(available_commands=cmds, prompt="/")
        st._update_command_palette("/")

        assert st.show_command_palette is True
        assert len(st.filtered_commands) == 2

    def test_update_filters_by_prefix(self) -> None:
        """Only matching commands appear for typed prefix."""
        cmds = [_cmd("teach"), _cmd("brainstorm")]
        st = self._state(available_commands=cmds, prompt="/te")
        st._update_command_palette("/te")

        assert len(st.filtered_commands) == 1
        assert st.filtered_commands[0].id == "teach"

    def test_update_hides_palette_no_slash(self) -> None:
        """Palette hidden when no slash pattern."""
        st = self._state(show_command_palette=True, prompt="hello")
        st._update_command_palette("hello")

        assert st.show_command_palette is False
        assert st.filtered_commands == []

    def test_update_slash_mid_prompt(self) -> None:
        """Slash preceded by space triggers palette."""
        cmds = [_cmd("teach")]
        st = self._state(available_commands=cmds, prompt="hello /te")
        st._update_command_palette("hello /te")

        assert st.show_command_palette is True
        assert len(st.filtered_commands) == 1

    def test_update_slash_no_match(self) -> None:
        """Palette shown but empty when no commands match."""
        cmds = [_cmd("teach")]
        st = self._state(available_commands=cmds, prompt="/xyz")
        st._update_command_palette("/xyz")

        assert st.show_command_palette is True
        assert len(st.filtered_commands) == 0

    # -- _hide_command_palette ------------------------------------------

    def test_hide_resets_state(self) -> None:
        """All palette state is reset on hide."""
        st = self._state(
            show_command_palette=True,
            filtered_commands=[_cmd("a")],
            selected_command_index=2,
            command_search_prefix="abc",
            command_trigger_position=5,
        )
        st._hide_command_palette()

        assert st.show_command_palette is False
        assert st.filtered_commands == []
        assert st.selected_command_index == 0
        assert st.command_search_prefix == ""
        assert st.command_trigger_position == 0

    # -- navigate_command_palette ---------------------------------------

    def test_navigate_down(self) -> None:
        """Navigation wraps from last to first."""
        cmds = [_cmd("a"), _cmd("b"), _cmd("c")]
        st = self._state(
            show_command_palette=True,
            filtered_commands=cmds,
            selected_command_index=2,
        )
        st.navigate_command_palette("down")
        assert st.selected_command_index == 0

    def test_navigate_up(self) -> None:
        """Navigation wraps from first to last."""
        cmds = [_cmd("a"), _cmd("b"), _cmd("c")]
        st = self._state(
            show_command_palette=True,
            filtered_commands=cmds,
            selected_command_index=0,
        )
        st.navigate_command_palette("up")
        assert st.selected_command_index == 2

    def test_navigate_noop_when_hidden(self) -> None:
        """No-op when palette is not shown."""
        st = self._state(
            show_command_palette=False,
            filtered_commands=[_cmd("a")],
            selected_command_index=0,
        )
        st.navigate_command_palette("down")
        assert st.selected_command_index == 0

    def test_navigate_noop_when_empty(self) -> None:
        """No-op when no commands are available."""
        st = self._state(
            show_command_palette=True,
            filtered_commands=[],
            selected_command_index=0,
        )
        st.navigate_command_palette("down")
        assert st.selected_command_index == 0

    # -- select_command -------------------------------------------------

    def test_select_command_inserts_label(self) -> None:
        """Command label replaces slash prefix in prompt."""
        cmd = _cmd("teach")
        st = self._state(
            filtered_commands=[cmd],
            prompt="/te",
            command_trigger_position=0,
        )
        st.select_command("teach")

        assert st.prompt == "/teach "
        assert st.show_command_palette is False

    def test_select_command_mid_prompt(self) -> None:
        """Command inserted mid-prompt preserves prefix text."""
        cmd = _cmd("teach")
        st = self._state(
            filtered_commands=[cmd],
            prompt="hello /te",
            command_trigger_position=6,
        )
        st.select_command("teach")

        assert st.prompt == "hello /teach "

    def test_select_command_not_found(self) -> None:
        """If command not found, palette is hidden."""
        st = self._state(
            filtered_commands=[_cmd("a")],
            prompt="/b",
            command_trigger_position=0,
        )
        st.select_command("b")

        assert st.show_command_palette is False

    def test_select_command_activates_mcp_servers(self) -> None:
        """Selecting a command auto-activates its MCP servers."""
        srv1 = _mcp_server(1, "srv1")
        srv2 = _mcp_server(2, "srv2")
        cmd = _cmd("teach", mcp_server_ids=[1, 2])
        st = self._state(
            filtered_commands=[cmd],
            prompt="/te",
            command_trigger_position=0,
            available_mcp_servers=[srv1, srv2],
            selected_mcp_servers=[],
            temp_selected_mcp_servers=[],
            server_selection_state={},
        )
        st.select_command("teach")

        assert len(st.selected_mcp_servers) == 2
        assert 1 in st.temp_selected_mcp_servers
        assert 2 in st.temp_selected_mcp_servers
        assert st.server_selection_state[1] is True

    def test_select_command_no_duplicate_mcp(self) -> None:
        """Already-selected MCP servers are not duplicated."""
        srv1 = _mcp_server(1, "srv1")
        cmd = _cmd("teach", mcp_server_ids=[1])
        st = self._state(
            filtered_commands=[cmd],
            prompt="/te",
            command_trigger_position=0,
            available_mcp_servers=[srv1],
            selected_mcp_servers=[srv1],
            temp_selected_mcp_servers=[1],
            server_selection_state={1: True},
        )
        st.select_command("teach")

        # Should still be just 1 server
        assert len(st.selected_mcp_servers) == 1

    # -- select_current_command -----------------------------------------

    def test_select_current_command(self) -> None:
        """Selects the highlighted command."""
        cmd = _cmd("teach")
        st = self._state(
            show_command_palette=True,
            filtered_commands=[cmd],
            selected_command_index=0,
            prompt="/te",
            command_trigger_position=0,
        )
        st.select_current_command()

        assert st.prompt == "/teach "

    def test_select_current_command_noop_hidden(self) -> None:
        """No-op when palette is hidden."""
        st = self._state(
            show_command_palette=False,
            filtered_commands=[_cmd("a")],
            prompt="/a",
        )
        st.select_current_command()
        assert st.prompt == "/a"  # unchanged

    def test_select_current_command_noop_empty(self) -> None:
        """No-op when no commands available."""
        st = self._state(
            show_command_palette=True,
            filtered_commands=[],
            prompt="/",
        )
        st.select_current_command()
        assert st.prompt == "/"  # unchanged

    # -- dismiss_command_palette ----------------------------------------

    def test_dismiss_hides_palette(self) -> None:
        """Dismissal resets palette state."""
        st = self._state(
            show_command_palette=True,
            filtered_commands=[_cmd("a")],
        )
        st.dismiss_command_palette()

        assert st.show_command_palette is False
        assert st.filtered_commands == []

    # -- computed vars helpers ------------------------------------------

    def test_filtered_user_prompts(self) -> None:
        """User prompts (editable) sorted alphabetically."""
        cmds = [
            _cmd("beta", editable=True),
            _cmd("alpha", editable=True),
            _cmd("shared", editable=False),
        ]
        st = self._state(filtered_commands=cmds)

        result = st.filtered_user_prompts
        assert len(result) == 2
        assert result[0].id == "alpha"
        assert result[1].id == "beta"

    def test_filtered_shared_prompts(self) -> None:
        """Shared prompts (not editable) sorted alphabetically."""
        cmds = [
            _cmd("zbeta", editable=False),
            _cmd("alpha", editable=False),
            _cmd("mine", editable=True),
        ]
        st = self._state(filtered_commands=cmds)

        result = st.filtered_shared_prompts
        assert len(result) == 2
        assert result[0].id == "alpha"
        assert result[1].id == "zbeta"

    def test_has_filtered_user_prompts_true(self) -> None:
        st = self._state(filtered_commands=[_cmd("a", editable=True)])
        assert st.has_filtered_user_prompts is True

    def test_has_filtered_user_prompts_false(self) -> None:
        st = self._state(filtered_commands=[_cmd("a", editable=False)])
        assert st.has_filtered_user_prompts is False

    def test_has_filtered_shared_prompts_true(self) -> None:
        st = self._state(filtered_commands=[_cmd("a", editable=False)])
        assert st.has_filtered_shared_prompts is True

    def test_has_filtered_shared_prompts_false(self) -> None:
        st = self._state(filtered_commands=[_cmd("a", editable=True)])
        assert st.has_filtered_shared_prompts is False

    # -- reload_commands (async) ----------------------------------------

    @pytest.mark.asyncio
    async def test_reload_commands_loads_and_updates(self) -> None:
        """reload_commands loads prompts and refreshes palette."""
        st = self._state(_current_user_id="42", prompt="/")
        st.available_commands = []

        with patch.object(
            st, "_load_user_prompts_as_commands", new_callable=AsyncMock
        ) as mock_load:
            await st.reload_commands()
            mock_load.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_reload_commands_noop_no_user(self) -> None:
        """reload_commands does nothing when no user is set."""
        st = self._state(_current_user_id="")

        with patch.object(
            st, "_load_user_prompts_as_commands", new_callable=AsyncMock
        ) as mock_load:
            await st.reload_commands()
            mock_load.assert_not_called()

    # -- _load_user_prompts_as_commands ---------------------------------

    @pytest.mark.asyncio
    async def test_load_user_prompts_builds_commands(self) -> None:
        """Loads own + shared prompts and builds CommandDefinitions."""
        st = self._state()

        own = MagicMock(
            handle="translate",
            description="Translate text",
            mcp_server_ids=[1],
        )
        shared = {
            "handle": "review",
            "description": "Code review",
            "user_id": 99,
            "mcp_server_ids": [],
        }

        mock_session = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.find_latest_prompts_by_user = AsyncMock(return_value=[own])
        mock_repo.find_latest_shared_prompts = AsyncMock(return_value=[shared])

        @asynccontextmanager
        async def _mock_session():
            yield mock_session

        with (
            patch(
                "appkit_assistant.state.thread.command_palette.get_asyncdb_session",
                _mock_session,
            ),
            patch(
                "appkit_assistant.state.thread.command_palette.user_prompt_repo",
                mock_repo,
            ),
        ):
            await st._load_user_prompts_as_commands(1)

        assert len(st.available_commands) == 2
        assert st.available_commands[0].id == "translate"
        assert st.available_commands[0].is_editable is True
        assert st.available_commands[1].id == "review"
        assert st.available_commands[1].is_editable is False

    @pytest.mark.asyncio
    async def test_load_user_prompts_error_clears(self) -> None:
        """On error, available_commands is set to empty list."""
        st = self._state(available_commands=[_cmd("old")])

        @asynccontextmanager
        async def _mock_session():
            raise RuntimeError("db error")
            yield  # pragma: no cover

        with patch(
            "appkit_assistant.state.thread.command_palette.get_asyncdb_session",
            _mock_session,
        ):
            await st._load_user_prompts_as_commands(1)

        assert st.available_commands == []


# =====================================================================
# McpToolsMixin
# =====================================================================


class _McpState(McpToolsMixin):
    """Stub owning the state vars needed by McpToolsMixin."""

    selected_mcp_servers: list[MCPServer] = []
    show_tools_modal: bool = False
    available_mcp_servers: list[MCPServer] = []
    temp_selected_mcp_servers: list[int] = []
    server_selection_state: dict[int, bool] = {}


class TestMcpToolsMixin:
    """Tests for McpToolsMixin."""

    def _state(self, **overrides: Any) -> _McpState:
        s = _McpState()
        for k, v in overrides.items():
            setattr(s, k, v)
        return s

    # -- toggle_tools_modal ---------------------------------------------

    def test_toggle_tools_modal_show(self) -> None:
        st = self._state()
        st.toggle_tools_modal(True)
        assert st.show_tools_modal is True

    def test_toggle_tools_modal_hide(self) -> None:
        st = self._state(show_tools_modal=True)
        st.toggle_tools_modal(False)
        assert st.show_tools_modal is False

    # -- toggle_mcp_server_selection ------------------------------------

    def test_toggle_select(self) -> None:
        st = self._state()
        st.toggle_mcp_server_selection(5, True)

        assert 5 in st.temp_selected_mcp_servers
        assert st.server_selection_state[5] is True

    def test_toggle_deselect(self) -> None:
        st = self._state(
            temp_selected_mcp_servers=[5],
            server_selection_state={5: True},
        )
        st.toggle_mcp_server_selection(5, False)

        assert 5 not in st.temp_selected_mcp_servers
        assert st.server_selection_state[5] is False

    def test_toggle_select_idempotent(self) -> None:
        """Selecting the same server twice doesn't duplicate."""
        st = self._state(
            temp_selected_mcp_servers=[5],
            server_selection_state={5: True},
        )
        st.toggle_mcp_server_selection(5, True)
        assert st.temp_selected_mcp_servers.count(5) == 1

    def test_toggle_deselect_not_present(self) -> None:
        """Deselecting a non-present server doesn't error."""
        st = self._state()
        st.toggle_mcp_server_selection(99, False)
        assert 99 not in st.temp_selected_mcp_servers

    # -- apply_mcp_server_selection -------------------------------------

    def test_apply_builds_from_temp(self) -> None:
        srv1 = _mcp_server(1, "s1")
        srv2 = _mcp_server(2, "s2")
        st = self._state(
            available_mcp_servers=[srv1, srv2],
            temp_selected_mcp_servers=[2],
        )
        st.apply_mcp_server_selection()

        assert len(st.selected_mcp_servers) == 1
        assert st.selected_mcp_servers[0].id == 2
        assert st.show_tools_modal is False

    # -- deselect_all_mcp_servers ---------------------------------------

    def test_deselect_all(self) -> None:
        st = self._state(
            temp_selected_mcp_servers=[1, 2, 3],
            server_selection_state={1: True, 2: True, 3: True},
        )
        st.deselect_all_mcp_servers()

        assert st.temp_selected_mcp_servers == []
        assert st.server_selection_state == {}

    # -- is_mcp_server_selected -----------------------------------------

    def test_is_selected_true(self) -> None:
        st = self._state(temp_selected_mcp_servers=[5])
        assert st.is_mcp_server_selected(5) is True

    def test_is_selected_false(self) -> None:
        st = self._state(temp_selected_mcp_servers=[])
        assert st.is_mcp_server_selected(5) is False

    # -- _restore_mcp_selection -----------------------------------------

    def test_restore_selection(self) -> None:
        srv1 = _mcp_server(1, "s1")
        srv2 = _mcp_server(2, "s2")
        st = self._state(available_mcp_servers=[srv1, srv2])
        st._restore_mcp_selection([2])

        assert len(st.selected_mcp_servers) == 1
        assert st.selected_mcp_servers[0].id == 2
        assert st.temp_selected_mcp_servers == [2]
        assert st.server_selection_state == {2: True}

    def test_restore_selection_empty(self) -> None:
        srv1 = _mcp_server(1, "s1")
        st = self._state(
            available_mcp_servers=[srv1],
            selected_mcp_servers=[srv1],
            temp_selected_mcp_servers=[1],
            server_selection_state={1: True},
        )
        st._restore_mcp_selection([])

        assert st.selected_mcp_servers == []
        assert st.temp_selected_mcp_servers == []
        assert st.server_selection_state == {}

    # -- load_mcp_servers (async) ---------------------------------------

    @pytest.mark.asyncio
    async def test_load_mcp_servers_filters_by_role(self) -> None:
        """Only servers matching user roles are loaded."""
        st = self._state()

        user = MagicMock(roles=["user"])
        user_session = MagicMock()
        # authenticated_user is awaited in the source
        user_session.authenticated_user = AsyncMock(return_value=user)()

        async def _fake_get_state(cls: Any) -> Any:
            return user_session

        st.get_state = _fake_get_state

        srv_no_role = MagicMock()
        srv_no_role.model_dump.return_value = {
            "name": "s1",
            "url": "https://s1.com",
            "active": True,
            "required_role": None,
        }
        srv_no_role.required_role = None

        srv_admin = MagicMock()
        srv_admin.model_dump.return_value = {
            "name": "s2",
            "url": "https://s2.com",
            "active": True,
            "required_role": "admin",
        }
        srv_admin.required_role = "admin"

        mock_repo = MagicMock()
        mock_repo.find_all_active_ordered_by_name = AsyncMock(
            return_value=[srv_no_role, srv_admin]
        )

        mock_session = AsyncMock()

        @asynccontextmanager
        async def _mock_session():
            yield mock_session

        with (
            patch(
                "appkit_assistant.state.thread.mcp_tools.get_asyncdb_session",
                _mock_session,
            ),
            patch(
                "appkit_assistant.state.thread.mcp_tools.mcp_server_repo",
                mock_repo,
            ),
        ):
            await st.load_mcp_servers()

        assert len(st.available_mcp_servers) == 1
        assert st.available_mcp_servers[0].name == "s1"


# =====================================================================
# SkillsMixin
# =====================================================================


class _SkillState(SkillsMixin):
    """Stub owning the state vars needed by SkillsMixin."""

    selected_skills: list[Skill] = []
    available_skills_for_selection: list[Skill] = []
    temp_selected_skill_ids: list[str] = []
    skill_selection_state: dict[str, bool] = {}
    modal_active_tab: str = "tools"
    selected_model: str = ""


class TestSkillsMixin:
    """Tests for SkillsMixin."""

    def _state(self, **overrides: Any) -> _SkillState:
        s = _SkillState()
        for k, v in overrides.items():
            setattr(s, k, v)
        return s

    # -- set_modal_active_tab -------------------------------------------

    def test_set_tab_string(self) -> None:
        st = self._state()
        st.set_modal_active_tab("skills")
        assert st.modal_active_tab == "skills"

    def test_set_tab_list(self) -> None:
        st = self._state()
        st.set_modal_active_tab(["skills", "tools"])
        assert st.modal_active_tab == "skills"

    def test_set_tab_empty_list(self) -> None:
        st = self._state()
        st.set_modal_active_tab([])
        assert st.modal_active_tab == "tools"

    # -- toggle_skill_selection -----------------------------------------

    def test_toggle_skill_select(self) -> None:
        st = self._state()
        st.toggle_skill_selection("sk1", True)

        assert "sk1" in st.temp_selected_skill_ids
        assert st.skill_selection_state["sk1"] is True

    def test_toggle_skill_deselect(self) -> None:
        st = self._state(
            temp_selected_skill_ids=["sk1"],
            skill_selection_state={"sk1": True},
        )
        st.toggle_skill_selection("sk1", False)

        assert "sk1" not in st.temp_selected_skill_ids
        assert st.skill_selection_state["sk1"] is False

    def test_toggle_skill_idempotent(self) -> None:
        st = self._state(
            temp_selected_skill_ids=["sk1"],
            skill_selection_state={"sk1": True},
        )
        st.toggle_skill_selection("sk1", True)
        assert st.temp_selected_skill_ids.count("sk1") == 1

    def test_toggle_skill_deselect_not_present(self) -> None:
        st = self._state()
        st.toggle_skill_selection("sk99", False)
        assert "sk99" not in st.temp_selected_skill_ids

    # -- apply_skill_selection ------------------------------------------

    def test_apply_skill_selection(self) -> None:
        sk = _skill("sk1", "Skill1")
        st = self._state(
            available_skills_for_selection=[sk],
            temp_selected_skill_ids=["sk1"],
        )
        st.apply_skill_selection()

        assert len(st.selected_skills) == 1
        assert st.selected_skills[0].openai_id == "sk1"

    # -- deselect_all_skills --------------------------------------------

    def test_deselect_all_skills(self) -> None:
        st = self._state(
            temp_selected_skill_ids=["sk1", "sk2"],
            skill_selection_state={"sk1": True, "sk2": True},
        )
        st.deselect_all_skills()

        assert st.temp_selected_skill_ids == []
        assert st.skill_selection_state == {}

    # -- _restore_skill_selection ---------------------------------------

    def test_restore_skill_selection(self) -> None:
        sk = _skill("sk1", "Skill1")
        st = self._state(available_skills_for_selection=[sk])
        st._restore_skill_selection(["sk1"])

        assert len(st.selected_skills) == 1
        assert st.temp_selected_skill_ids == ["sk1"]
        assert st.skill_selection_state == {"sk1": True}

    def test_restore_skill_selection_empty(self) -> None:
        sk = _skill("sk1", "Skill1")
        st = self._state(
            available_skills_for_selection=[sk],
            selected_skills=[sk],
            temp_selected_skill_ids=["sk1"],
            skill_selection_state={"sk1": True},
        )
        st._restore_skill_selection([])

        assert st.selected_skills == []
        assert st.temp_selected_skill_ids == []
        assert st.skill_selection_state == {}

    # -- load_available_skills_for_user (async) -------------------------

    @pytest.mark.asyncio
    async def test_load_skills_filters_by_role(self) -> None:
        """Only skills matching user roles are loaded."""
        st = self._state(selected_model="m1")

        user = MagicMock(roles=["user"])
        user_session = MagicMock()
        user_session.authenticated_user = AsyncMock(return_value=user)()

        async def _fake_get_state(cls: Any) -> Any:
            return user_session

        st.get_state = _fake_get_state

        sk_no_role = MagicMock()
        sk_no_role.model_dump.return_value = {
            "openai_id": "sk1",
            "name": "Skill1",
            "description": "d",
            "default_version": "1",
            "latest_version": "1",
            "active": True,
            "required_role": None,
            "api_key_hash": "h",
            "last_synced": datetime.now(UTC),
        }
        sk_no_role.required_role = None

        sk_admin = MagicMock()
        sk_admin.model_dump.return_value = {
            "openai_id": "sk2",
            "name": "Skill2",
            "description": "d",
            "default_version": "1",
            "latest_version": "1",
            "active": True,
            "required_role": "admin",
            "api_key_hash": "h",
            "last_synced": datetime.now(UTC),
        }
        sk_admin.required_role = "admin"

        mock_skill_repo = MagicMock()
        mock_skill_repo.find_all_active_by_api_key_hash = AsyncMock(
            return_value=[sk_no_role, sk_admin]
        )
        mock_ai_model_repo = MagicMock()
        mock_model = MagicMock(api_key="key123")
        mock_ai_model_repo.find_by_model_id = AsyncMock(return_value=mock_model)

        mock_session = AsyncMock()

        @asynccontextmanager
        async def _mock_session():
            yield mock_session

        with (
            patch(
                "appkit_assistant.state.thread.skills.get_asyncdb_session",
                _mock_session,
            ),
            patch(
                "appkit_assistant.state.thread.skills.skill_repo",
                mock_skill_repo,
            ),
            patch(
                "appkit_assistant.state.thread.skills.ai_model_repo",
                mock_ai_model_repo,
            ),
            patch(
                "appkit_assistant.state.thread.skills.compute_api_key_hash",
                return_value="hash123",
            ),
        ):
            await st.load_available_skills_for_user()

        assert len(st.available_skills_for_selection) == 1
        assert st.available_skills_for_selection[0].openai_id == "sk1"


# =====================================================================
# FileUploadMixin
# =====================================================================


class _FileState(FileUploadMixin):
    """Stub owning the state vars needed by FileUploadMixin."""

    uploaded_files: list[UploadedFile] = []
    max_file_size_mb: int = 50
    max_files_per_thread: int = 10


class TestFileUploadMixin:
    """Tests for FileUploadMixin."""

    def _state(self, **overrides: Any) -> _FileState:
        s = _FileState()
        for k, v in overrides.items():
            setattr(s, k, v)
        return s

    # -- remove_file_from_prompt ----------------------------------------

    def test_remove_file(self) -> None:
        """Removes specified file and cleans up disk."""
        f1 = UploadedFile(filename="a.pdf", file_path="/tmp/a.pdf")
        f2 = UploadedFile(filename="b.pdf", file_path="/tmp/b.pdf")
        st = self._state(uploaded_files=[f1, f2])

        with patch("appkit_assistant.state.thread.file_upload.file_manager") as fm:
            st.remove_file_from_prompt("/tmp/a.pdf")
            fm.cleanup_uploaded_files.assert_called_once_with(["/tmp/a.pdf"])

        assert len(st.uploaded_files) == 1
        assert st.uploaded_files[0].filename == "b.pdf"

    # -- _clear_uploaded_files ------------------------------------------

    def test_clear_uploaded_files(self) -> None:
        """All files cleared from state and disk."""
        f1 = UploadedFile(filename="a.pdf", file_path="/tmp/a.pdf")
        f2 = UploadedFile(filename="b.pdf", file_path="/tmp/b.pdf")
        st = self._state(uploaded_files=[f1, f2])

        with patch("appkit_assistant.state.thread.file_upload.file_manager") as fm:
            st._clear_uploaded_files()
            fm.cleanup_uploaded_files.assert_called_once_with(
                ["/tmp/a.pdf", "/tmp/b.pdf"]
            )

        assert st.uploaded_files == []

    def test_clear_uploaded_files_noop_empty(self) -> None:
        """No-op when no files are uploaded."""
        st = self._state()

        with patch("appkit_assistant.state.thread.file_upload.file_manager") as fm:
            st._clear_uploaded_files()
            fm.cleanup_uploaded_files.assert_not_called()


# =====================================================================
# MessageEditMixin
# =====================================================================


class _EditState(MessageEditMixin):
    """Stub owning the state vars needed by MessageEditMixin."""

    editing_message_id: str | None = None
    edited_message_content: str = ""
    expanded_message_ids: list[str] = []
    messages: list[Message] = []
    _thread: ThreadModel = ThreadModel(thread_id="t1")
    prompt: str = ""
    _skip_user_message: bool = False
    _current_user_id: str = "1"

    @property
    def current_user_id(self) -> str:
        return self._current_user_id


class TestMessageEditMixin:
    """Tests for MessageEditMixin."""

    def _state(self, **overrides: Any) -> _EditState:
        s = _EditState()
        for k, v in overrides.items():
            setattr(s, k, v)
        return s

    # -- set_editing_mode / cancel_edit ---------------------------------

    def test_set_editing_mode(self) -> None:
        st = self._state()
        st.set_editing_mode("msg-1", "Hello")

        assert st.editing_message_id == "msg-1"
        assert st.edited_message_content == "Hello"

    def test_set_edited_message_content(self) -> None:
        st = self._state(editing_message_id="msg-1")
        st.set_edited_message_content("Updated")
        assert st.edited_message_content == "Updated"

    def test_cancel_edit(self) -> None:
        st = self._state(
            editing_message_id="msg-1",
            edited_message_content="Draft",
        )
        st.cancel_edit()

        assert st.editing_message_id is None
        assert st.edited_message_content == ""

    # -- toggle_message_expanded ----------------------------------------

    def test_toggle_expand(self) -> None:
        st = self._state(expanded_message_ids=[])
        st.toggle_message_expanded("msg-1")

        assert "msg-1" in st.expanded_message_ids

    def test_toggle_collapse(self) -> None:
        st = self._state(expanded_message_ids=["msg-1"])
        st.toggle_message_expanded("msg-1")

        assert "msg-1" not in st.expanded_message_ids

    # -- copy_message ---------------------------------------------------

    def test_copy_message_returns_events(self) -> None:
        """copy_message returns clipboard + toast events."""
        st = self._state()
        result = st.copy_message("Hello")

        assert isinstance(result, list)
        assert len(result) == 2

    # -- download_message -----------------------------------------------

    def test_download_message_returns_script(self) -> None:
        """download_message returns a JS call_script."""
        st = self._state()
        result = st.download_message("# Hello", "msg-1")

        # Should return a call_script event spec
        assert result is not None

    def test_download_message_no_id(self) -> None:
        """download_message works without message_id."""
        st = self._state()
        result = st.download_message("# Hello", "")

        assert result is not None


# =====================================================================
# OAuthMixin
# =====================================================================


class _OAuthState(OAuthMixin):
    """Stub owning the state vars needed by OAuthMixin."""

    pending_auth_server_id: str = ""
    pending_auth_server_name: str = ""
    pending_auth_url: str = ""
    show_auth_card: bool = False
    pending_oauth_message: str = ""
    oauth_result: str = ""
    messages: list[Message]
    _current_user_id: str = "1"
    _skip_user_message: bool = False
    prompt: str = ""

    def __init__(self) -> None:
        self.messages = []

    @staticmethod
    async def submit_message() -> None:
        """Stub for cross-mixin reference."""


class TestOAuthMixin:
    """Tests for OAuthMixin."""

    def _state(self, **overrides: Any) -> _OAuthState:
        s = _OAuthState()
        for k, v in overrides.items():
            setattr(s, k, v)
        return s

    # -- start_mcp_oauth ------------------------------------------------

    def test_start_oauth_no_url(self) -> None:
        """Returns error toast when no auth URL is set."""
        st = self._state(pending_auth_url="")
        result = st.start_mcp_oauth()
        assert result is not None  # toast error event

    def test_start_oauth_with_url(self) -> None:
        """Returns call_script to open popup when URL is set."""
        st = self._state(pending_auth_url="https://auth.example.com")
        result = st.start_mcp_oauth()
        assert result is not None

    # -- dismiss_auth_card ----------------------------------------------

    def test_dismiss_auth_card(self) -> None:
        st = self._state(show_auth_card=True)
        st.dismiss_auth_card()
        assert st.show_auth_card is False

    # -- _handle_auth_required_from_accumulator -------------------------

    def test_handle_auth_required(self) -> None:
        """Auth card state populated from accumulator data."""
        acc = MagicMock(spec=ResponseAccumulator)
        acc.auth_required = True
        acc.auth_required_data = {
            "server_id": "srv-1",
            "server_name": "My Server",
            "auth_url": "https://auth.example.com",
        }

        msg = _message("Help me", MessageType.HUMAN)
        st = self._state(messages=[msg])
        st._handle_auth_required_from_accumulator(acc)

        assert st.pending_auth_server_id == "srv-1"
        assert st.pending_auth_server_name == "My Server"
        assert st.pending_auth_url == "https://auth.example.com"
        assert st.show_auth_card is True
        assert st.pending_oauth_message == "Help me"
        assert acc.auth_required is False

    def test_handle_auth_required_no_human_msg(self) -> None:
        """pending_oauth_message stays empty when no human message."""
        acc = MagicMock(spec=ResponseAccumulator)
        acc.auth_required = True
        acc.auth_required_data = {
            "server_id": "s",
            "server_name": "S",
            "auth_url": "u",
        }
        st = self._state(messages=[])
        st._handle_auth_required_from_accumulator(acc)

        assert st.pending_oauth_message == ""

    # -- handle_mcp_oauth_success ---------------------------------------

    @pytest.mark.asyncio
    async def test_oauth_success_resends_message(self) -> None:
        """Successful OAuth retries pending message."""
        human_msg = _message("Help me", MessageType.HUMAN)
        assistant_msg = _message("Auth needed", MessageType.ASSISTANT)
        st = self._state(
            pending_oauth_message="Help me",
            messages=[human_msg, assistant_msg],
        )

        events: list[Any] = []
        async for event in st.handle_mcp_oauth_success("srv-1", "Server"):
            events.append(event)

        assert st.show_auth_card is False
        assert st.pending_oauth_message == ""
        assert st.prompt == "Help me"
        assert st._skip_user_message is True
        # Last assistant msg should be removed
        assert len(st.messages) == 1

    @pytest.mark.asyncio
    async def test_oauth_success_no_pending(self) -> None:
        """Successful OAuth without pending message just toasts."""
        st = self._state(pending_oauth_message="")

        events: list[Any] = []
        async for event in st.handle_mcp_oauth_success("srv-1", "Server"):
            events.append(event)

        assert st.show_auth_card is False
        assert st.prompt == ""

    # -- process_oauth_result -------------------------------------------

    @pytest.mark.asyncio
    async def test_process_oauth_result_success(self) -> None:
        """Processes valid OAuth result from localStorage."""
        data = {
            "type": "mcp-oauth-success",
            "serverId": "srv-1",
            "serverName": "Server",
            "userId": "1",
        }
        st = self._state(
            oauth_result=json.dumps(data),
            _current_user_id="1",
            pending_oauth_message="",
        )

        # Patch handle_mcp_oauth_success as an async generator
        async def _fake_oauth_success(*args: Any, **kwargs: Any):
            return
            yield  # pragma: no cover

        st.handle_mcp_oauth_success = _fake_oauth_success

        events: list[Any] = []
        async for event in st.process_oauth_result():
            events.append(event)

        assert st.oauth_result == ""

    @pytest.mark.asyncio
    async def test_process_oauth_result_empty(self) -> None:
        """No-op when oauth_result is empty."""
        st = self._state(oauth_result="")

        events: list[Any] = []
        async for event in st.process_oauth_result():
            events.append(event)

        # Should be empty, no events yielded
        assert events == []

    @pytest.mark.asyncio
    async def test_process_oauth_result_wrong_type(self) -> None:
        """Ignores non-success event types."""
        data = {"type": "other-event"}
        st = self._state(oauth_result=json.dumps(data))

        events: list[Any] = []
        async for event in st.process_oauth_result():
            events.append(event)

        # Nothing should happen

    @pytest.mark.asyncio
    async def test_process_oauth_result_user_mismatch(self) -> None:
        """Clears result on user ID mismatch."""
        data = {
            "type": "mcp-oauth-success",
            "serverId": "s",
            "serverName": "S",
            "userId": "999",
        }
        st = self._state(
            oauth_result=json.dumps(data),
            _current_user_id="1",
        )

        events: list[Any] = []
        async for event in st.process_oauth_result():
            events.append(event)

        assert st.oauth_result == ""

    @pytest.mark.asyncio
    async def test_process_oauth_result_invalid_json(self) -> None:
        """Handles invalid JSON gracefully."""
        st = self._state(oauth_result="not-json{")

        events: list[Any] = []
        async for event in st.process_oauth_result():
            events.append(event)

        assert st.oauth_result == ""


# =====================================================================
# MessageProcessingMixin
# =====================================================================


class _ProcessState(MessageProcessingMixin):
    """Stub owning the state vars needed by MessageProcessingMixin."""

    processing: bool = False
    cancellation_requested: bool = False
    messages: list[Message]
    prompt: str = ""
    thinking_items: list
    image_chunks: list
    show_thinking: bool = False
    current_activity: str = ""
    uploaded_files: list[UploadedFile]
    selected_mcp_servers: list[MCPServer]
    selected_skills: list[Skill]
    web_search_enabled: bool = False
    with_thread_list: bool = False
    _thread: ThreadModel = ThreadModel(thread_id="t1")
    _skip_user_message: bool = False
    _pending_file_cleanup: list[str]
    _cancel_event: asyncio.Event | None = None
    _current_user_id: str = "1"
    selected_model: str = "gpt-4"

    def __init__(self) -> None:
        self.messages = []
        self.thinking_items = []
        self.image_chunks = []
        self.uploaded_files = []
        self.selected_mcp_servers = []
        self.selected_skills = []
        self._pending_file_cleanup = []

    @property
    def get_selected_model(self) -> str:
        return self.selected_model

    @property
    def current_user_id(self) -> str:
        return self._current_user_id

    @property
    def selected_model_supports_skills(self) -> bool:
        return True

    def _handle_auth_required_from_accumulator(self, acc: ResponseAccumulator) -> None:
        pass

    async def get_state(self, cls: Any) -> Any:
        mock = MagicMock()
        mock.user = MagicMock(user_id=1)
        return mock


class TestMessageProcessingMixin:
    """Tests for MessageProcessingMixin."""

    def _state(self, **overrides: Any) -> _ProcessState:
        s = _ProcessState()
        for k, v in overrides.items():
            setattr(s, k, v)
        return s

    # -- _parse_prompt_segments -----------------------------------------

    def test_parse_simple_text(self) -> None:
        st = self._state()
        result = st._parse_prompt_segments("Hello world")

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert result[0]["content"] == "Hello world"

    def test_parse_single_command(self) -> None:
        st = self._state()
        result = st._parse_prompt_segments("/translate")

        assert len(result) == 1
        assert result[0]["type"] == "command"
        assert result[0]["handle"] == "translate"

    def test_parse_command_with_text(self) -> None:
        st = self._state()
        result = st._parse_prompt_segments("/translate Hello world")

        assert len(result) == 2
        assert result[0]["type"] == "command"
        assert result[0]["handle"] == "translate"
        assert result[1]["type"] == "text"
        assert result[1]["content"] == "Hello world"

    def test_parse_text_before_command(self) -> None:
        st = self._state()
        result = st._parse_prompt_segments("Please /translate this")

        assert len(result) == 3
        assert result[0]["type"] == "text"
        assert result[0]["content"] == "Please"
        assert result[1]["type"] == "command"
        assert result[1]["handle"] == "translate"
        assert result[2]["type"] == "text"
        assert result[2]["content"] == "this"

    def test_parse_multiple_commands(self) -> None:
        st = self._state()
        result = st._parse_prompt_segments("/translate /review code")

        commands = [s for s in result if s["type"] == "command"]
        assert len(commands) == 2

    def test_parse_empty_prompt(self) -> None:
        st = self._state()
        result = st._parse_prompt_segments("")
        assert result == []

    def test_parse_command_with_hyphens(self) -> None:
        st = self._state()
        result = st._parse_prompt_segments("/my-command")

        assert len(result) == 1
        assert result[0]["handle"] == "my-command"

    # -- _create_user_messages ------------------------------------------

    def test_create_user_messages_no_segments(self) -> None:
        """Falls back to single message from prompt when no segments."""
        st = self._state()
        result = st._create_user_messages("Hello", [], ["file.pdf"])

        assert len(result) == 1
        assert result[0].text == "Hello"
        assert result[0].type == MessageType.HUMAN
        assert "file.pdf" in result[0].attachments

    def test_create_user_messages_text_segment(self) -> None:
        """Creates message from text segment."""
        st = self._state()
        segments = [{"type": "text", "content": "Hello"}]
        result = st._create_user_messages("Hello", segments, ["f.pdf"])

        assert len(result) == 1
        assert result[0].text == "Hello"
        assert "f.pdf" in result[0].attachments

    def test_create_user_messages_command_resolved(self) -> None:
        """Creates message from resolved command."""
        st = self._state()
        segments = [{"type": "command", "handle": "translate", "resolved_text": "T"}]
        result = st._create_user_messages("/translate", segments, [])

        assert len(result) == 1
        assert result[0].text == "T"

    def test_create_user_messages_command_unresolved(self) -> None:
        """Skips commands that failed to resolve."""
        st = self._state()
        segments = [{"type": "command", "handle": "unknown", "resolved_text": None}]
        result = st._create_user_messages("/unknown", segments, [])
        assert len(result) == 0

    def test_create_user_messages_mixed(self) -> None:
        """Mixed text and command segments produce correct messages."""
        st = self._state()
        segments = [
            {"type": "text", "content": "Hello"},
            {
                "type": "command",
                "handle": "translate",
                "resolved_text": "Translated",
            },
        ]
        result = st._create_user_messages("Hello /translate", segments, ["f.pdf"])

        assert len(result) == 2
        assert result[0].attachments == ["f.pdf"]
        assert result[1].attachments == []  # only first gets attachments

    # -- _add_error_message ---------------------------------------------

    def test_add_error_message(self) -> None:
        st = self._state()
        st._add_error_message("Something broke")

        assert len(st.messages) == 1
        assert st.messages[0].type == MessageType.ERROR
        assert st.messages[0].text == "Something broke"

    # -- request_cancellation -------------------------------------------

    def test_request_cancellation_sets_flag(self) -> None:
        st = self._state()
        st.request_cancellation()

        assert st.cancellation_requested is True

    def test_request_cancellation_sets_event(self) -> None:
        evt = asyncio.Event()
        st = self._state(_cancel_event=evt)
        st.request_cancellation()

        assert evt.is_set()

    def test_request_cancellation_no_event(self) -> None:
        """Does not error when cancel event is None."""
        st = self._state(_cancel_event=None)
        st.request_cancellation()
        assert st.cancellation_requested is True

    # -- _stop_processing_with_error ------------------------------------

    @pytest.mark.asyncio
    async def test_stop_processing_with_error(self) -> None:
        """Error message appended and processing flag cleared."""

        class NoLockState(_ProcessState):
            """State without async context manager for testing."""

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        st = NoLockState()
        st.processing = True
        await st._stop_processing_with_error("Model not found")

        assert st.processing is False
        assert len(st.messages) == 1
        assert st.messages[0].type == MessageType.ERROR

    # -- _finalize_processing -------------------------------------------

    @pytest.mark.asyncio
    async def test_finalize_processing(self) -> None:
        """State is cleaned up and pending files are cleaned."""
        msg = _message("done", MessageType.ASSISTANT, done=False)

        class NoLockState(_ProcessState):
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        st = NoLockState()
        st.messages = [msg]
        st.processing = True
        st.cancellation_requested = True
        st.current_activity = "Working..."
        st._pending_file_cleanup = ["/tmp/a.pdf"]

        with patch(
            "appkit_assistant.state.thread.message_processing.file_manager"
        ) as fm:
            await st._finalize_processing()
            fm.cleanup_uploaded_files.assert_called_once_with(["/tmp/a.pdf"])

        assert st.processing is False
        assert st.cancellation_requested is False
        assert st.current_activity == ""
        assert st._cancel_event is None
        assert st._pending_file_cleanup == []
        assert st.messages[0].done is True

    @pytest.mark.asyncio
    async def test_finalize_processing_no_pending_files(self) -> None:
        """No cleanup call when no pending files."""

        class NoLockState(_ProcessState):
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        st = NoLockState()
        st.processing = True
        st._pending_file_cleanup = []

        with patch(
            "appkit_assistant.state.thread.message_processing.file_manager"
        ) as fm:
            await st._finalize_processing()
            fm.cleanup_uploaded_files.assert_not_called()

    # -- _load_command_prompt_text --------------------------------------

    @pytest.mark.asyncio
    async def test_load_command_prompt_text_found(self) -> None:
        """Returns prompt text for a valid command handle."""
        st = self._state()

        mock_prompt = MagicMock(prompt_text="You are a translator")
        mock_repo = MagicMock()
        mock_repo.find_latest_accessible_by_handle = AsyncMock(return_value=mock_prompt)
        mock_session = AsyncMock()

        @asynccontextmanager
        async def _mock_session():
            yield mock_session

        with (
            patch(
                "appkit_assistant.state.thread.message_processing.get_asyncdb_session",
                _mock_session,
            ),
            patch(
                "appkit_assistant.state.thread.message_processing.user_prompt_repo",
                mock_repo,
            ),
        ):
            result = await st._load_command_prompt_text(1, "/translate")

        assert result == "You are a translator"
        mock_repo.find_latest_accessible_by_handle.assert_called_once_with(
            mock_session, 1, "translate"
        )

    @pytest.mark.asyncio
    async def test_load_command_prompt_text_not_found(self) -> None:
        """Returns None when prompt not found."""
        st = self._state()

        mock_repo = MagicMock()
        mock_repo.find_latest_accessible_by_handle = AsyncMock(return_value=None)
        mock_session = AsyncMock()

        @asynccontextmanager
        async def _mock_session():
            yield mock_session

        with (
            patch(
                "appkit_assistant.state.thread.message_processing.get_asyncdb_session",
                _mock_session,
            ),
            patch(
                "appkit_assistant.state.thread.message_processing.user_prompt_repo",
                mock_repo,
            ),
        ):
            result = await st._load_command_prompt_text(1, "unknown")

        assert result is None

    @pytest.mark.asyncio
    async def test_load_command_prompt_text_error(self) -> None:
        """Returns None on database error."""
        st = self._state()

        @asynccontextmanager
        async def _mock_session():
            raise RuntimeError("db error")
            yield  # pragma: no cover

        with patch(
            "appkit_assistant.state.thread.message_processing.get_asyncdb_session",
            _mock_session,
        ):
            result = await st._load_command_prompt_text(1, "test")

        assert result is None

    # -- _resolve_command_segments --------------------------------------

    @pytest.mark.asyncio
    async def test_resolve_command_segments(self) -> None:
        """Command segments get resolved_text populated."""
        st = self._state()
        segments = [
            {"type": "command", "handle": "translate"},
            {"type": "text", "content": "hello"},
        ]

        with patch.object(
            st,
            "_load_command_prompt_text",
            new_callable=AsyncMock,
            return_value="Translated text",
        ):
            await st._resolve_command_segments(segments, 1)

        assert segments[0]["resolved_text"] == "Translated text"
        # Text segments are unchanged
        assert "resolved_text" not in segments[1]

    @pytest.mark.asyncio
    async def test_resolve_command_segments_error(self) -> None:
        """Errors during resolution are caught and logged."""
        st = self._state()
        segments = [{"type": "command", "handle": "fail"}]

        with patch.object(
            st,
            "_load_command_prompt_text",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db error"),
        ):
            await st._resolve_command_segments(segments, 1)

        # Should not crash, resolved_text absent
        assert "resolved_text" not in segments[0]
