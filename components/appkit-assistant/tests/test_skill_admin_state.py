# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for SkillAdminState.

Covers CRUD, sync, upload, toggle, role updates, computed vars,
and model selection helpers.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.database.models import Skill
from appkit_assistant.state.skill_admin_state import SkillAdminState

_PATCH = "appkit_assistant.state.skill_admin_state"

_CV = SkillAdminState.__dict__


def _unwrap(name: str):
    entry = SkillAdminState.__dict__[name]
    return entry.fn if hasattr(entry, "fn") else entry


def _db_context(session: MagicMock | None = None):
    s = session or _mock_session()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=s)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _mock_session(**overrides: object) -> MagicMock:
    """Create a mock session with sync add/expunge_all and async commit/flush."""
    s = MagicMock()
    s.commit = AsyncMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    s.execute = AsyncMock()
    s.expunge_all = MagicMock()
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


def _mock_model(
    model_id: str = "gpt-4",
    text: str = "GPT-4",
    api_key: str | None = "sk-test",
    base_url: str | None = None,
):
    m = MagicMock()
    m.model_id = model_id
    m.text = text
    m.api_key = api_key
    m.base_url = base_url
    m.model_dump.return_value = {
        "model_id": model_id,
        "text": text,
        "api_key": api_key,
        "base_url": base_url,
    }
    return m


def _mock_skill(
    skill_id: int = 1,
    name: str = "Skill1",
    openai_id: str = "sk-1",
    active: bool = True,
    required_role: str | None = None,
):
    s = MagicMock()
    s.id = skill_id
    s.name = name
    s.openai_id = openai_id
    s.active = active
    s.required_role = required_role
    s.model_dump.return_value = {
        "id": skill_id,
        "name": name,
        "openai_id": openai_id,
        "active": active,
        "required_role": required_role,
    }
    s.model_copy.return_value = s
    return s


class _StubSkillAdminState:
    def __init__(self) -> None:
        self.skills: list[Any] = []
        self.available_roles: list[dict[str, str]] = []
        self.role_labels: dict[str, str] = {}
        self.skill_models: list[Any] = []
        self.selected_model_id: str = ""
        self.loading: bool = False
        self.syncing: bool = False
        self.search_filter: str = ""
        self.create_modal_open: bool = False
        self.uploading: bool = False
        self.updating_role_skill_id: int | None = None
        self.updating_active_skill_id: int | None = None

    set_search_filter = _unwrap("set_search_filter")
    set_available_roles = _unwrap("set_available_roles")
    _get_selected_model = _unwrap("_get_selected_model")
    _validate_upload = _unwrap("_validate_upload")
    load_skill_models = _unwrap("load_skill_models")
    set_selected_model = _unwrap("set_selected_model")
    load_skills = _unwrap("load_skills")
    load_skills_with_toast = _unwrap("load_skills_with_toast")
    sync_skills = _unwrap("sync_skills")
    handle_upload = _unwrap("handle_upload")
    update_skill_role = _unwrap("update_skill_role")
    delete_skill = _unwrap("delete_skill")
    toggle_skill_active = _unwrap("toggle_skill_active")
    open_create_modal = _unwrap("open_create_modal")
    close_create_modal = _unwrap("close_create_modal")


def _make_state() -> _StubSkillAdminState:
    return _StubSkillAdminState()


# ============================================================================
# Computed vars
# ============================================================================


class TestComputedVars:
    def test_filtered_skills_no_filter(self) -> None:
        state = _make_state()
        s = _mock_skill()
        state.skills = [s]
        result = _CV["filtered_skills"].fget(state)
        assert len(result) == 1

    def test_filtered_skills_with_filter(self) -> None:
        state = _make_state()
        s1 = _mock_skill(name="Alpha")
        s2 = _mock_skill(name="Beta")
        state.skills = [s1, s2]
        state.search_filter = "alp"
        result = _CV["filtered_skills"].fget(state)
        assert len(result) == 1

    def test_skill_count(self) -> None:
        state = _make_state()
        state.skills = [_mock_skill(), _mock_skill()]
        assert _CV["skill_count"].fget(state) == 2

    def test_has_skills_true(self) -> None:
        state = _make_state()
        state.skills = [_mock_skill()]
        assert _CV["has_skills"].fget(state) is True

    def test_has_skills_false(self) -> None:
        state = _make_state()
        assert _CV["has_skills"].fget(state) is False

    def test_skill_model_options(self) -> None:
        state = _make_state()
        state.skill_models = [_mock_model()]
        result = _CV["skill_model_options"].fget(state)
        assert len(result) == 1
        assert result[0]["value"] == "gpt-4"

    def test_has_skill_models_true(self) -> None:
        state = _make_state()
        state.skill_models = [_mock_model()]
        assert _CV["has_skill_models"].fget(state) is True

    def test_has_skill_models_false(self) -> None:
        state = _make_state()
        assert _CV["has_skill_models"].fget(state) is False


# ============================================================================
# Simple setters
# ============================================================================


class TestSetters:
    def test_set_search_filter(self) -> None:
        state = _make_state()
        state.set_search_filter("test")
        assert state.search_filter == "test"

    def test_set_available_roles(self) -> None:
        state = _make_state()
        roles = [{"value": "admin", "label": "Admin"}]
        labels = {"admin": "Admin"}
        state.set_available_roles(roles, labels)
        assert state.available_roles == roles
        assert state.role_labels == labels


# ============================================================================
# _get_selected_model
# ============================================================================


class TestGetSelectedModel:
    def test_no_selection(self) -> None:
        state = _make_state()
        assert state._get_selected_model() is None

    def test_found(self) -> None:
        state = _make_state()
        m = _mock_model()
        state.skill_models = [m]
        state.selected_model_id = "gpt-4"
        assert state._get_selected_model() is m

    def test_not_found(self) -> None:
        state = _make_state()
        state.skill_models = [_mock_model()]
        state.selected_model_id = "missing"
        assert state._get_selected_model() is None


# ============================================================================
# _validate_upload
# ============================================================================


class TestValidateUpload:
    def test_no_files(self) -> None:
        state = _make_state()
        valid, err = state._validate_upload([])
        assert valid is False
        assert "ZIP" in err

    def test_wrong_extension(self) -> None:
        state = _make_state()
        f = MagicMock()
        f.filename = "test.txt"
        valid, err = state._validate_upload([f])
        assert valid is False
        assert "ZIP" in err

    def test_valid_zip(self) -> None:
        state = _make_state()
        f = MagicMock()
        f.filename = "skill.zip"
        valid, err = state._validate_upload([f])
        assert valid is True
        assert err is None


# ============================================================================
# load_skill_models
# ============================================================================


class TestLoadSkillModels:
    @pytest.mark.asyncio
    async def test_auto_select_first(self) -> None:
        state = _make_state()
        m = _mock_model()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
            patch(
                f"{_PATCH}.AssistantAIModel",
                side_effect=lambda **_kw: m,
            ),
        ):
            repo.find_all_skill_capable = AsyncMock(return_value=[m])
            await state.load_skill_models()
        assert state.selected_model_id == "gpt-4"

    @pytest.mark.asyncio
    async def test_keeps_existing_selection(self) -> None:
        state = _make_state()
        state.selected_model_id = "existing"
        m = _mock_model()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
            patch(
                f"{_PATCH}.AssistantAIModel",
                side_effect=lambda **_kw: m,
            ),
        ):
            repo.find_all_skill_capable = AsyncMock(return_value=[m])
            await state.load_skill_models()
        assert state.selected_model_id == "existing"


# ============================================================================
# load_skills
# ============================================================================


class TestLoadSkills:
    @pytest.mark.asyncio
    async def test_with_model(self) -> None:
        state = _make_state()
        m = _mock_model()
        state.skill_models = [m]
        state.selected_model_id = "gpt-4"
        s = _mock_skill()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.skill_repo") as repo,
            patch(
                f"{_PATCH}.compute_api_key_hash",
                return_value="h",
            ),
            patch(
                f"{_PATCH}.Skill",
                side_effect=lambda **_kw: s,
            ),
        ):
            repo.find_all_by_api_key_hash = AsyncMock(return_value=[s])
            await state.load_skills()
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_without_model(self) -> None:
        state = _make_state()
        s = _mock_skill()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.skill_repo") as repo,
            patch(
                f"{_PATCH}.Skill",
                side_effect=lambda **_kw: s,
            ),
        ):
            repo.find_all_ordered_by_name = AsyncMock(return_value=[s])
            await state.load_skills()
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _make_state()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.skill_repo") as repo,
        ):
            repo.find_all_ordered_by_name = AsyncMock(side_effect=RuntimeError("db"))
            with pytest.raises(RuntimeError):
                await state.load_skills()
        assert state.loading is False


# ============================================================================
# load_skills_with_toast
# ============================================================================


class TestLoadSkillsWithToast:
    @pytest.mark.asyncio
    async def test_error_yields_toast(self) -> None:
        state = _make_state()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.skill_repo") as repo,
        ):
            repo.find_all_ordered_by_name = AsyncMock(side_effect=RuntimeError("db"))
            _ = [c async for c in state.load_skills_with_toast()]


# ============================================================================
# sync_skills
# ============================================================================


class TestSyncSkills:
    @pytest.mark.asyncio
    async def test_no_model(self) -> None:
        state = _make_state()
        _ = [c async for c in state.sync_skills()]
        assert state.syncing is False

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        m = _mock_model()
        state.skill_models = [m]
        state.selected_model_id = "gpt-4"

        service = AsyncMock()
        service.sync_all_skills = AsyncMock(return_value=3)

        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(
                f"{_PATCH}.get_skill_service",
                return_value=service,
            ),
            patch(f"{_PATCH}.skill_repo") as repo,
        ):
            repo.find_all_by_api_key_hash = AsyncMock(return_value=[])
            with (
                patch(
                    f"{_PATCH}.compute_api_key_hash",
                    return_value="h",
                ),
                patch.object(
                    Skill,
                    "__init__",
                    lambda _self, **_kw: None,
                ),
            ):
                _ = [c async for c in state.sync_skills()]
        assert state.syncing is False

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _make_state()
        m = _mock_model()
        state.skill_models = [m]
        state.selected_model_id = "gpt-4"

        service = AsyncMock()
        service.sync_all_skills = AsyncMock(side_effect=RuntimeError("api"))

        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(
                f"{_PATCH}.get_skill_service",
                return_value=service,
            ),
        ):
            _ = [c async for c in state.sync_skills()]
        assert state.syncing is False


# ============================================================================
# handle_upload
# ============================================================================


class TestHandleUpload:
    @pytest.mark.asyncio
    async def test_no_model(self) -> None:
        state = _make_state()
        _ = [c async for c in state.handle_upload([])]

    @pytest.mark.asyncio
    async def test_invalid_file(self) -> None:
        state = _make_state()
        m = _mock_model()
        state.skill_models = [m]
        state.selected_model_id = "gpt-4"
        _ = [c async for c in state.handle_upload([])]

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        m = _mock_model()
        state.skill_models = [m]
        state.selected_model_id = "gpt-4"

        upload = AsyncMock()
        upload.filename = "skill.zip"
        upload.read = AsyncMock(return_value=b"zipdata")

        service = AsyncMock()
        service.create_or_update_skill = AsyncMock(
            return_value={"id": "sk-1", "name": "MySkill"}
        )
        service.sync_skill = AsyncMock()

        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(
                f"{_PATCH}.get_skill_service",
                return_value=service,
            ),
            patch(f"{_PATCH}.skill_repo") as repo,
        ):
            repo.find_all_by_api_key_hash = AsyncMock(return_value=[])
            with (
                patch(
                    f"{_PATCH}.compute_api_key_hash",
                    return_value="h",
                ),
                patch.object(
                    Skill,
                    "__init__",
                    lambda _self, **_kw: None,
                ),
            ):
                _ = [c async for c in state.handle_upload([upload])]
        assert state.uploading is False
        assert state.create_modal_open is False

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _make_state()
        m = _mock_model()
        state.skill_models = [m]
        state.selected_model_id = "gpt-4"

        upload = AsyncMock()
        upload.filename = "skill.zip"
        upload.read = AsyncMock(side_effect=RuntimeError("read fail"))

        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.get_skill_service"),
        ):
            _ = [c async for c in state.handle_upload([upload])]
        assert state.uploading is False


# ============================================================================
# update_skill_role
# ============================================================================


class TestUpdateSkillRole:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        state.role_labels = {"admin": "Admin"}
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.skill_repo") as repo,
        ):
            repo.update_required_role = AsyncMock()
            repo.find_all_ordered_by_name = AsyncMock(return_value=[])
            with patch.object(
                Skill,
                "__init__",
                lambda _self, **_kw: None,
            ):
                _ = [c async for c in state.update_skill_role(1, "admin")]
        assert state.updating_role_skill_id is None

    @pytest.mark.asyncio
    async def test_none_role(self) -> None:
        state = _make_state()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.skill_repo") as repo,
        ):
            repo.update_required_role = AsyncMock()
            repo.find_all_ordered_by_name = AsyncMock(return_value=[])
            with patch.object(
                Skill,
                "__init__",
                lambda _self, **_kw: None,
            ):
                _ = [c async for c in state.update_skill_role(1, "None")]
        repo.update_required_role.assert_called_once()
        call_args = repo.update_required_role.call_args
        assert call_args[0][1] == 1
        assert call_args[0][2] is None

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _make_state()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.skill_repo") as repo,
        ):
            repo.update_required_role = AsyncMock(side_effect=RuntimeError("db"))
            _ = [c async for c in state.update_skill_role(1, "admin")]
        assert state.updating_role_skill_id is None


# ============================================================================
# delete_skill
# ============================================================================


class TestDeleteSkill:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        m = _mock_model()
        state.skill_models = [m]
        state.selected_model_id = "gpt-4"

        service = AsyncMock()
        service.delete_skill_full = AsyncMock(return_value="SkillX")

        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(
                f"{_PATCH}.get_skill_service",
                return_value=service,
            ),
            patch(f"{_PATCH}.skill_repo") as repo,
        ):
            repo.find_all_by_api_key_hash = AsyncMock(return_value=[])
            with (
                patch(
                    f"{_PATCH}.compute_api_key_hash",
                    return_value="h",
                ),
                patch.object(
                    Skill,
                    "__init__",
                    lambda _self, **_kw: None,
                ),
            ):
                _ = [c async for c in state.delete_skill(1)]

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _make_state()
        service = AsyncMock()
        service.delete_skill_full = AsyncMock(side_effect=RuntimeError("api"))
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(
                f"{_PATCH}.get_skill_service",
                return_value=service,
            ),
        ):
            _ = [c async for c in state.delete_skill(1)]


# ============================================================================
# toggle_skill_active
# ============================================================================


class TestToggleSkillActive:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        s = _mock_skill(skill_id=1, active=True)
        state.skills = [s]
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.skill_repo") as repo,
        ):
            found = MagicMock()
            found.active = True
            repo.find_by_id = AsyncMock(return_value=found)
            repo.save = AsyncMock()
            _ = [c async for c in state.toggle_skill_active(1, False)]
        assert state.updating_active_skill_id is None

    @pytest.mark.asyncio
    async def test_not_found_reverts(self) -> None:
        state = _make_state()
        s = _mock_skill(skill_id=1, active=True)
        original = [s]
        state.skills = original
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.skill_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=None)
            _ = [c async for c in state.toggle_skill_active(1, False)]
        assert state.skills == original

    @pytest.mark.asyncio
    async def test_error_reverts(self) -> None:
        state = _make_state()
        s = _mock_skill(skill_id=1, active=True)
        original = [s]
        state.skills = original
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.skill_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(side_effect=RuntimeError("db"))
            _ = [c async for c in state.toggle_skill_active(1, False)]
        assert state.skills == original
        assert state.updating_active_skill_id is None


# ============================================================================
# Modals
# ============================================================================


class TestModals:
    @pytest.mark.asyncio
    async def test_open_create_modal(self) -> None:
        state = _make_state()
        _ = [c async for c in state.open_create_modal()]
        assert state.create_modal_open is True

    @pytest.mark.asyncio
    async def test_close_create_modal(self) -> None:
        state = _make_state()
        state.create_modal_open = True
        _ = [c async for c in state.close_create_modal()]
        assert state.create_modal_open is False
