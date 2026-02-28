# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for SkillState.

Covers load_user_skills, toggle_skill_enabled,
and computed vars (has_skills, enabled_skill_ids).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.state.skill_state import SkillState

_PATCH = "appkit_assistant.state.skill_state"

_CV = SkillState.__dict__


def _unwrap(name: str):
    entry = SkillState.__dict__[name]
    return entry.fn if hasattr(entry, "fn") else entry


def _db_context(session: AsyncMock | None = None):
    s = session or AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=s)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


class _StubSkillState:
    def __init__(self) -> None:
        self.available_skills: list[dict[str, Any]] = []
        self.loading: bool = False
        self._mock_user_session: MagicMock | None = None

    async def get_state(self, cls: type) -> Any:
        return self._mock_user_session

    load_user_skills = _unwrap("load_user_skills")
    toggle_skill_enabled = _unwrap("toggle_skill_enabled")


def _make_state(
    user_id: int | None = 42,
) -> _StubSkillState:
    s = _StubSkillState()
    user_session = MagicMock()
    user_session.user_id = user_id
    s._mock_user_session = user_session
    return s


def _mock_skill(
    openai_id: str = "sk-1",
    name: str = "Skill1",
    description: str = "Desc",
    active: bool = True,
):
    s = MagicMock()
    s.openai_id = openai_id
    s.name = name
    s.description = description
    s.active = active
    return s


def _mock_selection(openai_id: str = "sk-1", enabled: bool = True):
    sel = MagicMock()
    sel.skill_openai_id = openai_id
    sel.enabled = enabled
    return sel


# ============================================================================
# Computed vars
# ============================================================================


class TestComputedVars:
    def test_has_skills_true(self) -> None:
        state = _make_state()
        state.available_skills = [{"openai_id": "sk-1"}]
        assert _CV["has_skills"].fget(state) is True

    def test_has_skills_false(self) -> None:
        state = _make_state()
        assert _CV["has_skills"].fget(state) is False

    def test_enabled_skill_ids_empty(self) -> None:
        state = _make_state()
        assert _CV["enabled_skill_ids"].fget(state) == []

    def test_enabled_skill_ids_mixed(self) -> None:
        state = _make_state()
        state.available_skills = [
            {"openai_id": "sk-1", "enabled": True},
            {"openai_id": "sk-2", "enabled": False},
            {"openai_id": "sk-3", "enabled": True},
        ]
        result = _CV["enabled_skill_ids"].fget(state)
        assert result == ["sk-1", "sk-3"]


# ============================================================================
# load_user_skills
# ============================================================================


class TestLoadUserSkills:
    @pytest.mark.asyncio
    async def test_no_user(self) -> None:
        state = _make_state(user_id=None)
        _ = [c async for c in state.load_user_skills()]
        assert state.available_skills == []
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_zero_user_id(self) -> None:
        state = _make_state(user_id=0)
        _ = [c async for c in state.load_user_skills()]
        assert state.available_skills == []

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        skill = _mock_skill("sk-1", "SkillA", "A desc")
        sel = _mock_selection("sk-1", enabled=True)

        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.skill_repo") as sr,
            patch(f"{_PATCH}.user_skill_repo") as usr,
        ):
            sr.find_all_active_ordered_by_name = AsyncMock(return_value=[skill])
            usr.find_by_user_id = AsyncMock(return_value=[sel])
            _ = [c async for c in state.load_user_skills()]

        assert len(state.available_skills) == 1
        assert state.available_skills[0]["name"] == "SkillA"
        assert state.available_skills[0]["enabled"] is True
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_no_selection_defaults_false(self) -> None:
        state = _make_state()
        skill = _mock_skill("sk-1")

        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.skill_repo") as sr,
            patch(f"{_PATCH}.user_skill_repo") as usr,
        ):
            sr.find_all_active_ordered_by_name = AsyncMock(return_value=[skill])
            usr.find_by_user_id = AsyncMock(return_value=[])
            _ = [c async for c in state.load_user_skills()]

        assert state.available_skills[0]["enabled"] is False

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _make_state()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.skill_repo") as sr,
        ):
            sr.find_all_active_ordered_by_name = AsyncMock(
                side_effect=RuntimeError("db")
            )
            _ = [c async for c in state.load_user_skills()]
        assert state.loading is False


# ============================================================================
# toggle_skill_enabled
# ============================================================================


class TestToggleSkillEnabled:
    @pytest.mark.asyncio
    async def test_optimistic_update(self) -> None:
        state = _make_state()
        state.available_skills = [
            {
                "openai_id": "sk-1",
                "name": "S",
                "enabled": False,
            },
        ]
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.user_skill_repo") as usr,
        ):
            usr.upsert = AsyncMock()
            _ = [c async for c in state.toggle_skill_enabled("sk-1", True)]
        assert state.available_skills[0]["enabled"] is True

    @pytest.mark.asyncio
    async def test_error_reverts(self) -> None:
        state = _make_state()
        state.available_skills = [
            {
                "openai_id": "sk-1",
                "name": "S",
                "enabled": False,
            },
        ]
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.user_skill_repo") as usr,
        ):
            usr.upsert = AsyncMock(side_effect=RuntimeError("db"))
            _ = [c async for c in state.toggle_skill_enabled("sk-1", True)]
        # Should be reverted back to False
        assert state.available_skills[0]["enabled"] is False

    @pytest.mark.asyncio
    async def test_no_user(self) -> None:
        state = _make_state(user_id=None)
        state.available_skills = [
            {
                "openai_id": "sk-1",
                "name": "S",
                "enabled": False,
            },
        ]
        _ = [c async for c in state.toggle_skill_enabled("sk-1", True)]
        # Optimistic update happens, but no DB call
        assert state.available_skills[0]["enabled"] is True

    @pytest.mark.asyncio
    async def test_disable(self) -> None:
        state = _make_state()
        state.available_skills = [
            {
                "openai_id": "sk-1",
                "name": "S",
                "enabled": True,
            },
        ]
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.user_skill_repo") as usr,
        ):
            usr.upsert = AsyncMock()
            _ = [c async for c in state.toggle_skill_enabled("sk-1", False)]
        assert state.available_skills[0]["enabled"] is False
