# ruff: noqa: ARG002, SLF001, S105, S106, PERF203
"""Tests for SystemPromptState.

Covers load_versions, save_current, delete_version,
set_current_prompt, set_selected_version, and computed vars.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.state.system_prompt_state import (
    MAX_PROMPT_LENGTH,
    SystemPromptState,
)

_PATCH = "appkit_assistant.state.system_prompt_state"
_CV = SystemPromptState.__dict__


def _unwrap(name: str):
    entry = SystemPromptState.__dict__[name]
    return entry.fn if hasattr(entry, "fn") else entry


def _db_context(session: AsyncMock | None = None):
    s = session or AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=s)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _prompt(
    version: int = 1,
    prompt: str = "Hello system",
) -> MagicMock:
    p = MagicMock()
    p.version = version
    p.prompt = prompt
    p.created_at = MagicMock()
    p.created_at.strftime.return_value = "01.01.2025 12:00"
    return p


class _StubSystemPromptState:
    def __init__(self) -> None:
        self.current_prompt: str = ""
        self.last_saved_prompt: str = ""
        self.versions: list = []
        self.prompt_map: dict = {}
        self.selected_version_id: int = 0
        self.is_loading: bool = False
        self.error_message: str = ""
        self.char_count: int = 0
        self.textarea_key: int = 0

    load_versions = _unwrap("load_versions")
    save_current = _unwrap("save_current")
    delete_version = _unwrap("delete_version")
    set_current_prompt = _unwrap("set_current_prompt")
    set_selected_version = _unwrap("set_selected_version")

    async def get_state(self, _cls):  # noqa: ANN001
        user = MagicMock()
        user.user_id = "user-1"
        return user


# ================================================================
# Computed vars
# ================================================================


class TestComputedVars:
    def test_selected_version_str_zero(self) -> None:
        state = _StubSystemPromptState()
        state.selected_version_id = 0
        assert _CV["selected_version_str"].fget(state) == ""

    def test_selected_version_str_nonzero(self) -> None:
        state = _StubSystemPromptState()
        state.selected_version_id = 3
        assert _CV["selected_version_str"].fget(state) == "3"


# ================================================================
# set_current_prompt / set_selected_version
# ================================================================


class TestSetters:
    def test_set_current_prompt(self) -> None:
        state = _StubSystemPromptState()
        state.set_current_prompt("new text")
        assert state.current_prompt == "new text"
        assert state.char_count == 8

    def test_set_selected_version_none(self) -> None:
        state = _StubSystemPromptState()
        state.set_selected_version(None)
        assert state.selected_version_id == 0

    def test_set_selected_version_empty(self) -> None:
        state = _StubSystemPromptState()
        state.set_selected_version("")
        assert state.selected_version_id == 0

    def test_set_selected_version_found(self) -> None:
        state = _StubSystemPromptState()
        state.prompt_map = {"2": "version two prompt"}
        old_key = state.textarea_key
        state.set_selected_version("2")
        assert state.selected_version_id == 2
        assert state.current_prompt == "version two prompt"
        assert state.char_count == len("version two prompt")
        assert state.textarea_key == old_key + 1

    def test_set_selected_version_not_in_map(self) -> None:
        state = _StubSystemPromptState()
        state.prompt_map = {}
        state.set_selected_version("5")
        assert state.selected_version_id == 5
        # prompt unchanged
        assert state.current_prompt == ""


# ================================================================
# load_versions
# ================================================================


class TestLoadVersions:
    @pytest.mark.asyncio
    async def test_success_with_prompts(self) -> None:
        state = _StubSystemPromptState()
        p1 = _prompt(version=2, prompt="v2")
        p2 = _prompt(version=1, prompt="v1")
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.system_prompt_repo") as repo,
        ):
            repo.find_all_ordered_by_version_desc = AsyncMock(return_value=[p1, p2])
            await state.load_versions()

        assert len(state.versions) == 2
        assert state.selected_version_id == 2
        assert state.current_prompt == "v2"
        assert state.last_saved_prompt == "v2"
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_success_empty(self) -> None:
        state = _StubSystemPromptState()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.system_prompt_repo") as repo,
        ):
            repo.find_all_ordered_by_version_desc = AsyncMock(return_value=[])
            await state.load_versions()

        assert state.versions == []
        assert state.selected_version_id == 0
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_preserves_existing_prompt(self) -> None:
        state = _StubSystemPromptState()
        state.current_prompt = "user draft"
        p = _prompt(version=1, prompt="saved")
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.system_prompt_repo") as repo,
        ):
            repo.find_all_ordered_by_version_desc = AsyncMock(return_value=[p])
            await state.load_versions()

        # Should preserve user draft
        assert state.current_prompt == "user draft"
        assert state.last_saved_prompt == "saved"

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _StubSystemPromptState()
        with patch(
            f"{_PATCH}.get_asyncdb_session",
            side_effect=RuntimeError("db fail"),
        ):
            await state.load_versions()

        assert "Fehler" in state.error_message
        assert state.is_loading is False


# ================================================================
# save_current
# ================================================================


class TestSaveCurrent:
    @pytest.mark.asyncio
    async def test_no_change(self) -> None:
        state = _StubSystemPromptState()
        state.current_prompt = "same"
        state.last_saved_prompt = "same"
        results = []
        async for r in state.save_current():
            results.append(r)
        assert len(results) >= 1  # toast.info

    @pytest.mark.asyncio
    async def test_empty_prompt(self) -> None:
        state = _StubSystemPromptState()
        state.current_prompt = "   "
        state.last_saved_prompt = "old"
        results = []
        async for r in state.save_current():
            results.append(r)
        assert state.error_message != ""

    @pytest.mark.asyncio
    async def test_too_long(self) -> None:
        state = _StubSystemPromptState()
        state.current_prompt = "x" * (MAX_PROMPT_LENGTH + 1)
        state.last_saved_prompt = "old"
        results = []
        async for r in state.save_current():
            results.append(r)
        assert state.error_message != ""

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _StubSystemPromptState()
        state.current_prompt = "new prompt"
        state.last_saved_prompt = "old prompt"
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.system_prompt_repo") as repo,
            patch(
                f"{_PATCH}.invalidate_prompt_cache",
                new_callable=AsyncMock,
            ),
        ):
            repo.create_next_version = AsyncMock()
            repo.find_all_ordered_by_version_desc = AsyncMock(return_value=[])
            results = []
            async for r in state.save_current():
                results.append(r)

        assert state.last_saved_prompt == "new prompt"
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _StubSystemPromptState()
        state.current_prompt = "new"
        state.last_saved_prompt = "old"
        with patch(
            f"{_PATCH}.get_asyncdb_session",
            side_effect=RuntimeError("db"),
        ):
            results = []
            async for r in state.save_current():
                results.append(r)

        assert "Fehler" in state.error_message
        assert state.is_loading is False


# ================================================================
# delete_version
# ================================================================


class TestDeleteVersion:
    @pytest.mark.asyncio
    async def test_no_selection(self) -> None:
        state = _StubSystemPromptState()
        state.selected_version_id = 0
        results = []
        async for r in state.delete_version():
            results.append(r)
        assert state.error_message != ""

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _StubSystemPromptState()
        state.selected_version_id = 1
        prompt_mock = MagicMock()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.system_prompt_repo") as repo,
            patch(
                f"{_PATCH}.invalidate_prompt_cache",
                new_callable=AsyncMock,
            ),
        ):
            repo.find_by_id = AsyncMock(return_value=prompt_mock)
            repo.delete = AsyncMock(return_value=True)
            repo.find_all_ordered_by_version_desc = AsyncMock(return_value=[])
            results = []
            async for r in state.delete_version():
                results.append(r)

        assert state.selected_version_id == 0
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        state = _StubSystemPromptState()
        state.selected_version_id = 99
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.system_prompt_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=None)
            results = []
            async for r in state.delete_version():
                results.append(r)

        assert "nicht gefunden" in state.error_message
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_delete_fails(self) -> None:
        state = _StubSystemPromptState()
        state.selected_version_id = 1
        prompt_mock = MagicMock()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.system_prompt_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=prompt_mock)
            repo.delete = AsyncMock(return_value=False)
            results = []
            async for r in state.delete_version():
                results.append(r)

        assert "nicht gefunden" in state.error_message
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        state = _StubSystemPromptState()
        state.selected_version_id = 1
        with patch(
            f"{_PATCH}.get_asyncdb_session",
            side_effect=RuntimeError("db"),
        ):
            results = []
            async for r in state.delete_version():
                results.append(r)

        assert "Fehler" in state.error_message
        assert state.is_loading is False
