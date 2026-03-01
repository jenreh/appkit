# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for AIModelAdminState.

Covers CRUD operations, search filtering, role management,
optimistic toggles, modal management, and computed vars.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.state.ai_model_admin_state import AIModelAdminState

_PATCH = "appkit_assistant.state.ai_model_admin_state"

_CV = AIModelAdminState.__dict__


def _unwrap(name: str):
    entry = AIModelAdminState.__dict__[name]
    return entry.fn if hasattr(entry, "fn") else entry


def _model(
    mid: int = 1,
    model_id: str = "gpt-4",
    text: str = "GPT-4",
    active: bool = True,
    requires_role: str | None = None,
    api_key: str | None = None,
) -> MagicMock:
    m = MagicMock()
    m.id = mid
    m.model_id = model_id
    m.text = text
    m.active = active
    m.requires_role = requires_role
    m.api_key = api_key
    m.model_dump.return_value = {
        "id": mid,
        "model_id": model_id,
        "text": text,
        "active": active,
        "requires_role": requires_role,
        "api_key": api_key,
        "icon": "codesandbox",
        "model": model_id,
        "processor_type": "openai",
        "stream": True,
        "temperature": 0.05,
        "supports_tools": False,
        "supports_attachments": False,
        "supports_search": False,
        "supports_skills": False,
        "base_url": None,
        "on_azure": False,
        "enable_tracking": True,
    }
    m.model_copy.return_value = MagicMock(
        id=mid,
        model_id=model_id,
        text=text,
        active=not active,
        requires_role=requires_role,
    )
    return m


def _db_context(session: AsyncMock | None = None):
    s = session or AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=s)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


class _StubAIModelAdminState:
    def __init__(self) -> None:
        self.models: list[Any] = []
        self.current_model: Any | None = None
        self.loading: bool = False
        self.search_filter: str = ""
        self.updating_active_model_id: int | None = None
        self.updating_role_model_id: int | None = None
        self.available_roles: list[dict[str, str]] = []
        self.role_labels: dict[str, str] = {}
        self.add_modal_open: bool = False
        self.edit_modal_open: bool = False

    set_search_filter = _unwrap("set_search_filter")
    set_available_roles = _unwrap("set_available_roles")
    open_add_modal = _unwrap("open_add_modal")
    close_add_modal = _unwrap("close_add_modal")
    open_edit_modal = _unwrap("open_edit_modal")
    close_edit_modal = _unwrap("close_edit_modal")
    load_models = _unwrap("load_models")
    load_models_with_toast = _unwrap("load_models_with_toast")
    get_model = _unwrap("get_model")
    add_model = _unwrap("add_model")
    modify_model = _unwrap("modify_model")
    delete_model = _unwrap("delete_model")
    toggle_model_active = _unwrap("toggle_model_active")
    update_model_role = _unwrap("update_model_role")


def _make_state() -> _StubAIModelAdminState:
    return _StubAIModelAdminState()


# ============================================================================
# Computed vars
# ============================================================================


class TestComputedVars:
    def test_filtered_models_no_filter(self) -> None:
        state = _make_state()
        m1, m2 = MagicMock(), MagicMock()
        m1.text, m1.model_id = "GPT-4", "gpt-4"
        m2.text, m2.model_id = "Claude", "claude"
        state.models = [m1, m2]
        result = _CV["filtered_models"].fget(state)
        assert len(result) == 2

    def test_filtered_models_by_text(self) -> None:
        state = _make_state()
        m1, m2 = MagicMock(), MagicMock()
        m1.text, m1.model_id = "GPT-4", "gpt-4"
        m2.text, m2.model_id = "Claude", "claude"
        state.models = [m1, m2]
        state.search_filter = "gpt"
        result = _CV["filtered_models"].fget(state)
        assert len(result) == 1

    def test_filtered_models_by_model_id(self) -> None:
        state = _make_state()
        m1, m2 = MagicMock(), MagicMock()
        m1.text, m1.model_id = "GPT-4", "gpt-4"
        m2.text, m2.model_id = "Claude", "claude-3"
        state.models = [m1, m2]
        state.search_filter = "claude-3"
        result = _CV["filtered_models"].fget(state)
        assert len(result) == 1

    def test_model_count(self) -> None:
        state = _make_state()
        state.models = [MagicMock(), MagicMock()]
        assert _CV["model_count"].fget(state) == 2

    def test_has_models_true(self) -> None:
        state = _make_state()
        state.models = [MagicMock()]
        assert _CV["has_models"].fget(state) is True

    def test_has_models_false(self) -> None:
        state = _make_state()
        assert _CV["has_models"].fget(state) is False


# ============================================================================
# Setters & modals
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


class TestModals:
    def test_add_modal(self) -> None:
        state = _make_state()
        state.open_add_modal()
        assert state.add_modal_open is True
        state.close_add_modal()
        assert state.add_modal_open is False

    def test_edit_modal(self) -> None:
        state = _make_state()
        state.open_edit_modal()
        assert state.edit_modal_open is True
        state.close_edit_modal()
        assert state.edit_modal_open is False


# ============================================================================
# load_models
# ============================================================================


class TestLoadModels:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        db_models = [_model(1, "gpt-4", "GPT-4")]
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.find_all_ordered_by_text = AsyncMock(return_value=db_models)
            await state.load_models()
        assert len(state.models) == 1
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_error_raises(self) -> None:
        state = _make_state()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.find_all_ordered_by_text = AsyncMock(side_effect=RuntimeError("db"))
            with pytest.raises(RuntimeError):
                await state.load_models()
        assert state.loading is False


class TestLoadModelsWithToast:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.find_all_ordered_by_text = AsyncMock(return_value=[])
            _ = [c async for c in state.load_models_with_toast()]

    @pytest.mark.asyncio
    async def test_error_toasts(self) -> None:
        state = _make_state()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.find_all_ordered_by_text = AsyncMock(side_effect=RuntimeError("db"))
            results = [c async for c in state.load_models_with_toast()]
        assert len(results) > 0  # toast error


# ============================================================================
# get_model
# ============================================================================


class TestGetModel:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        state = _make_state()
        rec = _model()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=rec)
            await state.get_model(1)
        assert state.current_model is not None

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        state = _make_state()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=None)
            await state.get_model(99)
        assert state.current_model is None

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        state = _make_state()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(side_effect=RuntimeError("db"))
            await state.get_model(1)  # no raise


# ============================================================================
# add_model
# ============================================================================


class TestAddModel:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        state.add_modal_open = True
        form = {
            "model_id": "gpt-4",
            "text": "GPT-4",
            "processor_type": "openai",
        }
        saved = MagicMock()
        saved.text = "GPT-4"
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
            patch(f"{_PATCH}.ai_model_registry") as reg,
        ):
            repo.save = AsyncMock(return_value=saved)
            repo.find_all_ordered_by_text = AsyncMock(return_value=[])
            reg.reload = AsyncMock()
            _ = [c async for c in state.add_model(form)]
        assert state.add_modal_open is False
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_value_error(self) -> None:
        state = _make_state()
        form = {
            "model_id": "x",
            "text": "X",
            "processor_type": "openai",
        }
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.save = AsyncMock(side_effect=ValueError("invalid"))
            _ = [c async for c in state.add_model(form)]
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_generic_error(self) -> None:
        state = _make_state()
        form = {
            "model_id": "x",
            "text": "X",
            "processor_type": "openai",
        }
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.save = AsyncMock(side_effect=RuntimeError("db"))
            _ = [c async for c in state.add_model(form)]
        assert state.loading is False


# ============================================================================
# modify_model
# ============================================================================


class TestModifyModel:
    @pytest.mark.asyncio
    async def test_no_current_model(self) -> None:
        state = _make_state()
        state.current_model = None
        results = [c async for c in state.modify_model({"model_id": "x"})]
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        state.current_model = MagicMock()
        state.current_model.id = 1
        state.edit_modal_open = True

        existing = MagicMock()
        existing.text = "Updated"
        saved = MagicMock()
        saved.text = "Updated"

        form = {
            "model_id": "gpt-4",
            "text": "Updated",
            "processor_type": "openai",
        }
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
            patch(f"{_PATCH}.ai_model_registry") as reg,
        ):
            repo.find_by_id = AsyncMock(return_value=existing)
            repo.save = AsyncMock(return_value=saved)
            repo.find_all_ordered_by_text = AsyncMock(return_value=[])
            reg.reload = AsyncMock()
            _ = [c async for c in state.modify_model(form)]
        assert state.edit_modal_open is False

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        state = _make_state()
        state.current_model = MagicMock()
        state.current_model.id = 99
        form = {
            "model_id": "x",
            "text": "X",
            "processor_type": "openai",
        }
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=None)
            results = [c async for c in state.modify_model(form)]
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_value_error(self) -> None:
        state = _make_state()
        state.current_model = MagicMock()
        state.current_model.id = 1
        form = {
            "model_id": "x",
            "text": "X",
            "processor_type": "openai",
        }
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(side_effect=ValueError("bad"))
            _ = [c async for c in state.modify_model(form)]

    @pytest.mark.asyncio
    async def test_generic_error(self) -> None:
        state = _make_state()
        state.current_model = MagicMock()
        state.current_model.id = 1
        form = {
            "model_id": "x",
            "text": "X",
            "processor_type": "openai",
        }
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(side_effect=RuntimeError("db"))
            _ = [c async for c in state.modify_model(form)]
        assert state.loading is False


# ============================================================================
# delete_model
# ============================================================================


class TestDeleteModel:
    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        state = _make_state()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=None)
            results = [c async for c in state.delete_model(99)]
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_delete_fails(self) -> None:
        state = _make_state()
        rec = MagicMock()
        rec.text = "GPT"
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=rec)
            repo.delete_by_id = AsyncMock(return_value=False)
            _ = [c async for c in state.delete_model(1)]

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        rec = MagicMock()
        rec.text = "GPT"
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
            patch(f"{_PATCH}.ai_model_registry") as reg,
        ):
            repo.find_by_id = AsyncMock(return_value=rec)
            repo.delete_by_id = AsyncMock(return_value=True)
            repo.find_all_ordered_by_text = AsyncMock(return_value=[])
            reg.reload = AsyncMock()
            _ = [c async for c in state.delete_model(1)]

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        state = _make_state()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(side_effect=RuntimeError("db"))
            _ = [c async for c in state.delete_model(1)]


# ============================================================================
# toggle_model_active
# ============================================================================


class TestToggleModelActive:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        m = MagicMock()
        m.id = 1
        m.model_copy.return_value = MagicMock(id=1, active=False)
        state.models = [m]

        rec = MagicMock()
        rec.text = "GPT"
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
            patch(f"{_PATCH}.ai_model_registry") as reg,
        ):
            repo.update_active = AsyncMock(return_value=rec)
            reg.reload = AsyncMock()
            _ = [c async for c in state.toggle_model_active(1, False)]
        assert state.updating_active_model_id is None

    @pytest.mark.asyncio
    async def test_not_found_reverts(self) -> None:
        state = _make_state()
        m = MagicMock()
        m.id = 1
        m.model_copy.return_value = MagicMock(id=1, active=False)
        original = [m]
        state.models = list(original)
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.update_active = AsyncMock(return_value=None)
            _ = [c async for c in state.toggle_model_active(1, False)]
        assert state.updating_active_model_id is None

    @pytest.mark.asyncio
    async def test_error_reverts(self) -> None:
        state = _make_state()
        m = MagicMock()
        m.id = 1
        m.model_copy.return_value = MagicMock(id=1, active=False)
        state.models = [m]
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.update_active = AsyncMock(side_effect=RuntimeError("db"))
            _ = [c async for c in state.toggle_model_active(1, False)]
        assert state.updating_active_model_id is None


# ============================================================================
# update_model_role
# ============================================================================


class TestUpdateModelRole:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        m = MagicMock()
        m.id = 1
        m.requires_role = None
        m.model_copy.return_value = MagicMock(id=1)
        state.models = [m]

        rec = MagicMock()
        rec.text = "GPT"
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
            patch(f"{_PATCH}.ai_model_registry") as reg,
        ):
            repo.update_role = AsyncMock(return_value=rec)
            reg.reload = AsyncMock()
            _ = [c async for c in state.update_model_role(1, "admin")]
        assert state.updating_role_model_id is None

    @pytest.mark.asyncio
    async def test_not_found_reverts(self) -> None:
        state = _make_state()
        m = MagicMock()
        m.id = 1
        m.requires_role = None
        m.model_copy.return_value = MagicMock(id=1)
        state.models = [m]
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.update_role = AsyncMock(return_value=None)
            _ = [c async for c in state.update_model_role(1, "admin")]
        assert state.updating_role_model_id is None

    @pytest.mark.asyncio
    async def test_error_reverts(self) -> None:
        state = _make_state()
        m = MagicMock()
        m.id = 1
        m.requires_role = None
        m.model_copy.return_value = MagicMock(id=1)
        state.models = [m]
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.update_role = AsyncMock(side_effect=RuntimeError("db"))
            _ = [c async for c in state.update_model_role(1, "admin")]
        assert state.updating_role_model_id is None
