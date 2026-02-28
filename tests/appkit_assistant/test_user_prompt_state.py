# ruff: noqa: ARG002, SLF001, S105, S106, PERF203
"""Tests for UserPromptState.

Covers modal CRUD, versioning, MCP server selection,
validation helpers, and computed vars.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.state.user_prompt_state import (
    MAX_DESCRIPTION_LENGTH,
    MAX_PROMPT_LENGTH,
    UserPromptState,
)

_PATCH = "appkit_assistant.state.user_prompt_state"
_CV = UserPromptState.__dict__


def _unwrap(name: str):
    entry = UserPromptState.__dict__[name]
    return entry.fn if hasattr(entry, "fn") else entry


def _db_context(session: AsyncMock | None = None):
    s = session or AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=s)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _version(
    vid: int = 1,
    version: int = 1,
    prompt_text: str = "prompt",
    description: str = "desc",
    is_latest: bool = True,
    is_shared: bool = False,
    mcp_server_ids: list[int] | None = None,
) -> MagicMock:
    v = MagicMock()
    v.id = vid
    v.version = version
    v.prompt_text = prompt_text
    v.description = description
    v.is_latest = is_latest
    v.is_shared = is_shared
    v.mcp_server_ids = mcp_server_ids or []
    v.created_at = MagicMock()
    v.created_at.strftime.return_value = "01.01.2025 12:00"
    return v


def _mcp_server(server_id: int = 1, name: str = "srv") -> MagicMock:
    s = MagicMock()
    s.id = server_id
    s.name = name
    s.active = True
    s.required_role = None
    s.model_dump.return_value = {
        "id": server_id,
        "name": name,
        "active": True,
        "required_role": None,
    }
    return s


class _StubUserPromptState:
    def __init__(self) -> None:
        self.is_loading: bool = False
        self.modal_open: bool = False
        self.modal_is_new: bool = False
        self.modal_handle: str = ""
        self.modal_original_handle: str = ""
        self.modal_description: str = ""
        self.modal_prompt: str = ""
        self.modal_is_shared: bool = False
        self.modal_char_count: int = 0
        self.modal_error: str = ""
        self.modal_textarea_key: int = 0
        self.modal_handle_error: str = ""
        self.modal_description_error: str = ""
        self.modal_prompt_error: str = ""
        self.modal_versions: list = []
        self.modal_prompt_map: dict = {}
        self.modal_selected_version_id: int = 0
        self.modal_available_mcp_servers: list = []
        self.modal_selected_mcp_server_ids: list = []
        self.modal_mcp_server_map: dict = {}

    _reset_modal = _unwrap("_reset_modal")
    set_modal_selected_version_id = _unwrap("set_modal_selected_version_id")
    set_modal_selected_mcp_servers = _unwrap("set_modal_selected_mcp_servers")
    open_edit_modal = _unwrap("open_edit_modal")
    open_new_modal = _unwrap("open_new_modal")
    close_modal = _unwrap("close_modal")
    handle_modal_open_change = _unwrap("handle_modal_open_change")
    set_modal_handle = _unwrap("set_modal_handle")
    _get_description_error = _unwrap("_get_description_error")
    _get_prompt_error = _unwrap("_get_prompt_error")
    set_modal_description = _unwrap("set_modal_description")
    set_modal_description_and_validate = _unwrap("set_modal_description_and_validate")
    set_modal_prompt = _unwrap("set_modal_prompt")
    set_modal_prompt_and_validate = _unwrap("set_modal_prompt_and_validate")
    set_modal_is_shared = _unwrap("set_modal_is_shared")
    save_from_modal = _unwrap("save_from_modal")
    delete_from_modal = _unwrap("delete_from_modal")
    _load_modal_available_mcp_servers = _unwrap("_load_modal_available_mcp_servers")

    async def get_state(self, _cls):  # noqa: ANN001
        user_obj = MagicMock()
        user_obj.roles = ["admin"]

        class _Session:
            user_id = "user-1"

            @property
            def authenticated_user(self):  # noqa: ANN202
                async def _get():  # noqa: ANN202
                    return user_obj

                return _get()

        return _Session()


# ================================================================
# Computed vars
# ================================================================


class TestComputedVars:
    def test_modal_title_new(self) -> None:
        state = _StubUserPromptState()
        state.modal_is_new = True
        assert _CV["modal_title"].fget(state) == "Neuer Prompt"

    def test_modal_title_edit(self) -> None:
        state = _StubUserPromptState()
        state.modal_is_new = False
        assert _CV["modal_title"].fget(state) == "Prompt bearbeiten"

    def test_modal_save_button_text_new(self) -> None:
        state = _StubUserPromptState()
        state.modal_is_new = True
        assert _CV["modal_save_button_text"].fget(state) == "Erstellen"

    def test_modal_save_button_text_edit(self) -> None:
        state = _StubUserPromptState()
        state.modal_is_new = False
        result = _CV["modal_save_button_text"].fget(state)
        assert result == "Neue Version speichern"

    def test_has_modal_validation_errors_false(self) -> None:
        state = _StubUserPromptState()
        assert _CV["has_modal_validation_errors"].fget(state) is False

    def test_has_modal_validation_errors_true(self) -> None:
        state = _StubUserPromptState()
        state.modal_handle_error = "bad"
        assert _CV["has_modal_validation_errors"].fget(state) is True

    def test_modal_selected_version_str_zero(self) -> None:
        state = _StubUserPromptState()
        state.modal_selected_version_id = 0
        assert _CV["modal_selected_version_str"].fget(state) == ""

    def test_modal_selected_version_str(self) -> None:
        state = _StubUserPromptState()
        state.modal_selected_version_id = 5
        assert _CV["modal_selected_version_str"].fget(state) == "5"

    def test_modal_mcp_server_options(self) -> None:
        state = _StubUserPromptState()
        srv = MagicMock()
        srv.id = 1
        srv.name = "MyServer"
        state.modal_available_mcp_servers = [srv]
        result = _CV["modal_mcp_server_options"].fget(state)
        assert result == [{"value": "1", "label": "MyServer"}]


# ================================================================
# Reset / close / open
# ================================================================


class TestResetAndModals:
    def test_reset_modal(self) -> None:
        state = _StubUserPromptState()
        state.modal_open = True
        state.modal_handle = "test"
        state.modal_error = "err"
        state._reset_modal()
        assert state.modal_open is False
        assert state.modal_handle == ""
        assert state.modal_error == ""

    def test_close_modal(self) -> None:
        state = _StubUserPromptState()
        state.modal_open = True
        state.close_modal()
        assert state.modal_open is False

    def test_handle_modal_open_change_close(self) -> None:
        state = _StubUserPromptState()
        state.modal_open = True
        state.handle_modal_open_change(False)
        assert state.modal_open is False

    def test_handle_modal_open_change_open(self) -> None:
        state = _StubUserPromptState()
        state.handle_modal_open_change(True)
        # No reset happens on open
        assert state.modal_open is False  # Not set by this method


# ================================================================
# Setters
# ================================================================


class TestSetters:
    def test_set_modal_description(self) -> None:
        state = _StubUserPromptState()
        state.set_modal_description("desc")
        assert state.modal_description == "desc"

    def test_set_modal_prompt(self) -> None:
        state = _StubUserPromptState()
        state.set_modal_prompt("text")
        assert state.modal_prompt == "text"
        assert state.modal_char_count == 4

    def test_set_modal_is_shared_true(self) -> None:
        state = _StubUserPromptState()
        state.set_modal_is_shared(True)
        assert state.modal_is_shared is True

    def test_set_modal_is_shared_false(self) -> None:
        state = _StubUserPromptState()
        state.set_modal_is_shared(False)
        assert state.modal_is_shared is False

    def test_set_modal_handle(self) -> None:
        state = _StubUserPromptState()
        with patch(
            f"{_PATCH}.validate_handle",
            return_value=(True, ""),
        ):
            state.set_modal_handle("test")
        assert state.modal_handle == "test"
        assert state.modal_handle_error == ""

    def test_set_modal_handle_invalid(self) -> None:
        state = _StubUserPromptState()
        with patch(
            f"{_PATCH}.validate_handle",
            return_value=(False, "bad handle"),
        ):
            state.set_modal_handle("!!!")
        assert state.modal_handle_error == "bad handle"

    def test_set_modal_selected_mcp_servers_none(self) -> None:
        state = _StubUserPromptState()
        state.set_modal_selected_mcp_servers(None)
        assert state.modal_selected_mcp_server_ids == []

    def test_set_modal_selected_mcp_servers_list(self) -> None:
        state = _StubUserPromptState()
        state.set_modal_selected_mcp_servers([1, 2])
        assert state.modal_selected_mcp_server_ids == ["1", "2"]

    def test_set_modal_selected_mcp_servers_other(self) -> None:
        state = _StubUserPromptState()
        state.set_modal_selected_mcp_servers("not a list")
        assert state.modal_selected_mcp_server_ids == []


# ================================================================
# Version selection
# ================================================================


class TestVersionSelection:
    def test_empty_value(self) -> None:
        state = _StubUserPromptState()
        state.set_modal_selected_version_id("")
        assert state.modal_selected_version_id == 0

    def test_none_value(self) -> None:
        state = _StubUserPromptState()
        state.set_modal_selected_version_id(None)
        assert state.modal_selected_version_id == 0

    def test_selects_prompt_from_map(self) -> None:
        state = _StubUserPromptState()
        state.modal_prompt_map = {"3": "prompt v3"}
        old_key = state.modal_textarea_key
        state.set_modal_selected_version_id("3")
        assert state.modal_selected_version_id == 3
        assert state.modal_prompt == "prompt v3"
        assert state.modal_textarea_key == old_key + 1

    def test_selects_mcp_servers_from_map(self) -> None:
        state = _StubUserPromptState()
        state.modal_prompt_map = {"3": "prompt v3"}
        srv = MagicMock()
        srv.id = 10
        state.modal_available_mcp_servers = [srv]
        state.modal_mcp_server_map = {"3": ["10", "99"]}
        state.set_modal_selected_version_id("3")
        # Only "10" available, "99" filtered out
        assert state.modal_selected_mcp_server_ids == ["10"]


# ================================================================
# Validation helpers
# ================================================================


class TestValidation:
    def test_description_ok(self) -> None:
        state = _StubUserPromptState()
        assert state._get_description_error("ok") == ""

    def test_description_too_long(self) -> None:
        state = _StubUserPromptState()
        err = state._get_description_error("x" * (MAX_DESCRIPTION_LENGTH + 1))
        assert "max" in err.lower()

    def test_prompt_ok(self) -> None:
        state = _StubUserPromptState()
        assert state._get_prompt_error("valid prompt") == ""

    def test_prompt_empty(self) -> None:
        state = _StubUserPromptState()
        assert state._get_prompt_error("") != ""

    def test_prompt_too_long(self) -> None:
        state = _StubUserPromptState()
        err = state._get_prompt_error("x" * (MAX_PROMPT_LENGTH + 1))
        assert "max" in err.lower()

    def test_set_modal_description_and_validate(self) -> None:
        state = _StubUserPromptState()
        state.set_modal_description_and_validate("x" * (MAX_DESCRIPTION_LENGTH + 1))
        assert state.modal_description_error != ""

    def test_set_modal_prompt_and_validate(self) -> None:
        state = _StubUserPromptState()
        state.set_modal_prompt_and_validate("")
        assert state.modal_prompt_error != ""

    def test_set_modal_prompt_and_validate_ok(self) -> None:
        state = _StubUserPromptState()
        state.set_modal_prompt_and_validate("valid")
        assert state.modal_prompt_error == ""


# ================================================================
# open_edit_modal
# ================================================================


class TestOpenEditModal:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _StubUserPromptState()
        v = _version(
            vid=10,
            version=1,
            prompt_text="hello",
            mcp_server_ids=[1],
        )
        srv = _mcp_server(server_id=1, name="Srv1")
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.user_prompt_repo") as repo,
            patch(f"{_PATCH}.mcp_server_repo") as mcp_repo,
        ):
            repo.find_all_versions = AsyncMock(return_value=[v])
            mcp_repo.find_all_active_ordered_by_name = AsyncMock(return_value=[srv])
            await state.open_edit_modal("test-handle")

        assert state.modal_open is True
        assert state.modal_handle == "test-handle"
        assert state.modal_prompt == "hello"
        assert state.modal_selected_version_id == 10

    @pytest.mark.asyncio
    async def test_no_versions(self) -> None:
        state = _StubUserPromptState()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.user_prompt_repo") as repo,
            patch(f"{_PATCH}.mcp_server_repo") as mcp_repo,
        ):
            repo.find_all_versions = AsyncMock(return_value=[])
            mcp_repo.find_all_active_ordered_by_name = AsyncMock(return_value=[])
            await state.open_edit_modal("missing")

        assert state.modal_open is False
        assert "nicht gefunden" in state.modal_error

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        state = _StubUserPromptState()
        with patch(
            f"{_PATCH}.get_asyncdb_session",
            side_effect=RuntimeError("db"),
        ):
            await state.open_edit_modal("err")

        assert "Fehler" in state.modal_error


# ================================================================
# open_new_modal
# ================================================================


class TestOpenNewModal:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _StubUserPromptState()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.mcp_server_repo") as mcp_repo,
        ):
            mcp_repo.find_all_active_ordered_by_name = AsyncMock(return_value=[])
            await state.open_new_modal()

        assert state.modal_open is True
        assert state.modal_is_new is True


# ================================================================
# save_from_modal
# ================================================================


class TestSaveFromModal:
    @pytest.mark.asyncio
    async def test_invalid_handle(self) -> None:
        state = _StubUserPromptState()
        state.modal_handle = "!!!"
        state.modal_prompt = "prompt"
        with patch(
            f"{_PATCH}.validate_handle",
            return_value=(False, "bad"),
        ):
            results = []
            async for r in state.save_from_modal():
                results.append(r)
        assert state.modal_error == "bad"

    @pytest.mark.asyncio
    async def test_empty_prompt(self) -> None:
        state = _StubUserPromptState()
        state.modal_handle = "test"
        state.modal_prompt = ""
        with patch(
            f"{_PATCH}.validate_handle",
            return_value=(True, ""),
        ):
            results = []
            async for r in state.save_from_modal():
                results.append(r)
        assert state.modal_error != ""

    @pytest.mark.asyncio
    async def test_description_too_long(self) -> None:
        state = _StubUserPromptState()
        state.modal_handle = "test"
        state.modal_prompt = "valid"
        state.modal_description = "x" * (MAX_DESCRIPTION_LENGTH + 1)
        with patch(
            f"{_PATCH}.validate_handle",
            return_value=(True, ""),
        ):
            results = []
            async for r in state.save_from_modal():
                results.append(r)
        assert state.modal_error != ""

    @pytest.mark.asyncio
    async def test_create_new_success(self) -> None:
        state = _StubUserPromptState()
        state.modal_is_new = True
        state.modal_handle = "newcmd"
        state.modal_prompt = "prompt text"
        state.modal_description = "desc"
        with (
            patch(
                f"{_PATCH}.validate_handle",
                return_value=(True, ""),
            ),
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.user_prompt_repo") as repo,
            patch(f"{_PATCH}.ThreadState") as ts,
        ):
            repo.validate_handle_unique = AsyncMock(return_value=True)
            repo.create_new_prompt = AsyncMock()
            ts.reload_commands = MagicMock()
            results = []
            async for r in state.save_from_modal():
                results.append(r)

        assert state.modal_open is False
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_create_duplicate_handle(self) -> None:
        state = _StubUserPromptState()
        state.modal_is_new = True
        state.modal_handle = "dup"
        state.modal_prompt = "text"
        with (
            patch(
                f"{_PATCH}.validate_handle",
                return_value=(True, ""),
            ),
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.user_prompt_repo") as repo,
        ):
            repo.validate_handle_unique = AsyncMock(return_value=False)
            results = []
            async for r in state.save_from_modal():
                results.append(r)

        assert "existiert" in state.modal_error

    @pytest.mark.asyncio
    async def test_update_existing_success(self) -> None:
        state = _StubUserPromptState()
        state.modal_is_new = False
        state.modal_handle = "cmd"
        state.modal_original_handle = "cmd"
        state.modal_prompt = "updated prompt"
        state.modal_description = "desc"
        with (
            patch(
                f"{_PATCH}.validate_handle",
                return_value=(True, ""),
            ),
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.user_prompt_repo") as repo,
            patch(f"{_PATCH}.ThreadState") as ts,
        ):
            repo.create_next_version = AsyncMock()
            ts.reload_commands = MagicMock()
            results = []
            async for r in state.save_from_modal():
                results.append(r)

        assert state.modal_open is False
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_update_with_rename(self) -> None:
        state = _StubUserPromptState()
        state.modal_is_new = False
        state.modal_handle = "new-name"
        state.modal_original_handle = "old-name"
        state.modal_prompt = "text"
        with (
            patch(
                f"{_PATCH}.validate_handle",
                return_value=(True, ""),
            ),
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.user_prompt_repo") as repo,
            patch(f"{_PATCH}.ThreadState") as ts,
        ):
            repo.validate_handle_unique = AsyncMock(return_value=True)
            repo.update_handle = AsyncMock()
            repo.create_next_version = AsyncMock()
            ts.reload_commands = MagicMock()
            results = []
            async for r in state.save_from_modal():
                results.append(r)

        assert state.modal_open is False
        repo.update_handle.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rename_duplicate(self) -> None:
        state = _StubUserPromptState()
        state.modal_is_new = False
        state.modal_handle = "taken"
        state.modal_original_handle = "old"
        state.modal_prompt = "text"
        with (
            patch(
                f"{_PATCH}.validate_handle",
                return_value=(True, ""),
            ),
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.user_prompt_repo") as repo,
        ):
            repo.validate_handle_unique = AsyncMock(return_value=False)
            results = []
            async for r in state.save_from_modal():
                results.append(r)

        assert "existiert" in state.modal_error

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        state = _StubUserPromptState()
        state.modal_handle = "test"
        state.modal_prompt = "text"
        with (
            patch(
                f"{_PATCH}.validate_handle",
                return_value=(True, ""),
            ),
            patch(
                f"{_PATCH}.get_asyncdb_session",
                side_effect=RuntimeError("db"),
            ),
        ):
            results = []
            async for r in state.save_from_modal():
                results.append(r)

        assert "fehlgeschlagen" in state.modal_error.lower()
        assert state.is_loading is False


# ================================================================
# delete_from_modal
# ================================================================


class TestDeleteFromModal:
    @pytest.mark.asyncio
    async def test_new_prompt_just_resets(self) -> None:
        state = _StubUserPromptState()
        state.modal_is_new = True
        state.modal_open = True
        results = []
        async for r in state.delete_from_modal():
            results.append(r)
        assert state.modal_open is False

    @pytest.mark.asyncio
    async def test_no_handle(self) -> None:
        state = _StubUserPromptState()
        state.modal_is_new = False
        state.modal_handle = ""
        results = []
        async for r in state.delete_from_modal():
            results.append(r)
        # Should return early
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _StubUserPromptState()
        state.modal_is_new = False
        state.modal_handle = "to-delete"
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.user_prompt_repo") as repo,
            patch(f"{_PATCH}.ThreadState") as ts,
        ):
            repo.delete_all_versions = AsyncMock()
            ts.reload_commands = MagicMock()
            results = []
            async for r in state.delete_from_modal():
                results.append(r)

        assert state.modal_open is False
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        state = _StubUserPromptState()
        state.modal_is_new = False
        state.modal_handle = "to-delete"
        with patch(
            f"{_PATCH}.get_asyncdb_session",
            side_effect=RuntimeError("db"),
        ):
            results = []
            async for r in state.delete_from_modal():
                results.append(r)

        assert "fehlgeschlagen" in state.modal_error.lower()
        assert state.is_loading is False
