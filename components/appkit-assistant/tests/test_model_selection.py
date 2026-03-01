# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for ModelSelectionMixin.

Covers model setup, selection, computed capability checks,
and event dispatching on model change.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from appkit_assistant.backend.database.models import ThreadStatus
from appkit_assistant.backend.schemas import AIModel
from appkit_assistant.state.thread.model_selection import ModelSelectionMixin

_PATCH = "appkit_assistant.state.thread.model_selection"

# Access computed-var descriptors via __dict__ to avoid triggering
# the Reflex __get__ descriptor protocol (which needs inherited_vars).
_CV = ModelSelectionMixin.__dict__


def _ai_model(
    model_id: str = "gpt-4o",
    *,
    supports_tools: bool = True,
    supports_attachments: bool = True,
    supports_search: bool = True,
    supports_skills: bool = True,
    requires_role: str | None = None,
) -> AIModel:
    return AIModel(
        id=model_id,
        text=model_id,
        model=model_id,
        supports_tools=supports_tools,
        supports_attachments=supports_attachments,
        supports_search=supports_search,
        supports_skills=supports_skills,
        requires_role=requires_role,
    )


class _StubModelSelection(ModelSelectionMixin):
    """Stub providing expected state vars without Reflex runtime."""

    # Class-level attributes for type(self).xxx lookups in set_selected_model
    load_available_skills_for_user = MagicMock()
    persist_current_thread = MagicMock()

    def __init__(self) -> None:
        self.ai_models: list[AIModel] = []
        self.selected_model: str = ""
        self._thread = SimpleNamespace(state=ThreadStatus.NEW, ai_model="")
        self.web_search_enabled = False
        self._restore_mcp_selection = MagicMock()
        self._clear_uploaded_files = MagicMock()
        self._restore_skill_selection = MagicMock()
        self.modal_active_tab = "tools"
        self._current_user_id: int | None = None


def _make_state() -> _StubModelSelection:
    return _StubModelSelection()


# ============================================================================
# Computed vars
# ============================================================================


class TestComputedVars:
    def test_get_selected_model(self) -> None:
        state = _make_state()
        state.selected_model = "gpt-4o"
        assert _CV["get_selected_model"].fget(state) == "gpt-4o"

    def test_has_ai_models_empty(self) -> None:
        state = _make_state()
        assert _CV["has_ai_models"].fget(state) is False

    def test_has_ai_models_with_models(self) -> None:
        state = _make_state()
        state.ai_models = [_ai_model()]
        assert _CV["has_ai_models"].fget(state) is True

    def test_supports_tools_no_model(self) -> None:
        state = _make_state()
        state.selected_model = ""
        assert _CV["selected_model_supports_tools"].fget(state) is False

    def test_supports_tools_true(self) -> None:
        state = _make_state()
        state.selected_model = "gpt-4o"
        mock_mgr = MagicMock()
        mock_mgr.get_model.return_value = _ai_model(supports_tools=True)
        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            result = _CV["selected_model_supports_tools"].fget(state)
        assert result is True

    def test_supports_tools_false(self) -> None:
        state = _make_state()
        state.selected_model = "basic"
        mock_mgr = MagicMock()
        mock_mgr.get_model.return_value = _ai_model(supports_tools=False)
        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            result = _CV["selected_model_supports_tools"].fget(state)
        assert result is False

    def test_supports_tools_model_not_found(self) -> None:
        state = _make_state()
        state.selected_model = "unknown"
        mock_mgr = MagicMock()
        mock_mgr.get_model.return_value = None
        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            result = _CV["selected_model_supports_tools"].fget(state)
        assert result is False

    def test_supports_attachments_no_model(self) -> None:
        state = _make_state()
        state.selected_model = ""
        assert _CV["selected_model_supports_attachments"].fget(state) is False

    def test_supports_attachments_true(self) -> None:
        state = _make_state()
        state.selected_model = "gpt-4o"
        mock_mgr = MagicMock()
        mock_mgr.get_model.return_value = _ai_model(supports_attachments=True)
        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            result = _CV["selected_model_supports_attachments"].fget(state)
        assert result is True

    def test_supports_search_no_model(self) -> None:
        state = _make_state()
        state.selected_model = ""
        assert _CV["selected_model_supports_search"].fget(state) is False

    def test_supports_search_true(self) -> None:
        state = _make_state()
        state.selected_model = "gpt-4o"
        mock_mgr = MagicMock()
        mock_mgr.get_model.return_value = _ai_model(supports_search=True)
        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            result = _CV["selected_model_supports_search"].fget(state)
        assert result is True

    def test_supports_skills_no_model(self) -> None:
        state = _make_state()
        state.selected_model = ""
        assert _CV["selected_model_supports_skills"].fget(state) is False

    def test_supports_skills_true(self) -> None:
        state = _make_state()
        state.selected_model = "gpt-4o"
        mock_mgr = MagicMock()
        mock_mgr.get_model.return_value = _ai_model(supports_skills=True)
        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            result = _CV["selected_model_supports_skills"].fget(state)
        assert result is True


# ============================================================================
# _setup_models
# ============================================================================


class TestSetupModels:
    def test_all_models_loaded(self) -> None:
        state = _make_state()
        models = [_ai_model("m1"), _ai_model("m2")]
        mock_mgr = MagicMock()
        mock_mgr.get_all_models.return_value = models
        mock_mgr.get_default_model.return_value = "m1"

        user = SimpleNamespace(roles=[])
        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            state._setup_models(user)

        assert len(state.ai_models) == 2
        assert state.selected_model == "m1"

    def test_role_filtering(self) -> None:
        state = _make_state()
        models = [
            _ai_model("public"),
            _ai_model("premium", requires_role="admin"),
        ]
        mock_mgr = MagicMock()
        mock_mgr.get_all_models.return_value = models
        mock_mgr.get_default_model.return_value = "public"

        user = SimpleNamespace(roles=[])
        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            state._setup_models(user)

        assert len(state.ai_models) == 1
        assert state.ai_models[0].id == "public"

    def test_role_matching(self) -> None:
        state = _make_state()
        models = [
            _ai_model("public"),
            _ai_model("premium", requires_role="admin"),
        ]
        mock_mgr = MagicMock()
        mock_mgr.get_all_models.return_value = models
        mock_mgr.get_default_model.return_value = "public"

        user = SimpleNamespace(roles=["admin"])
        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            state._setup_models(user)

        assert len(state.ai_models) == 2

    def test_keeps_current_selection(self) -> None:
        state = _make_state()
        state.selected_model = "m2"
        models = [_ai_model("m1"), _ai_model("m2")]
        mock_mgr = MagicMock()
        mock_mgr.get_all_models.return_value = models
        mock_mgr.get_default_model.return_value = "m1"

        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            state._setup_models(SimpleNamespace(roles=[]))

        assert state.selected_model == "m2"

    def test_fallback_to_default(self) -> None:
        state = _make_state()
        state.selected_model = "removed"
        models = [_ai_model("m1"), _ai_model("m2")]
        mock_mgr = MagicMock()
        mock_mgr.get_all_models.return_value = models
        mock_mgr.get_default_model.return_value = "m1"

        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            state._setup_models(SimpleNamespace(roles=[]))

        assert state.selected_model == "m1"

    def test_fallback_to_first(self) -> None:
        state = _make_state()
        state.selected_model = "removed"
        models = [_ai_model("m1")]
        mock_mgr = MagicMock()
        mock_mgr.get_all_models.return_value = models
        mock_mgr.get_default_model.return_value = "nonexistent"

        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            state._setup_models(SimpleNamespace(roles=[]))

        assert state.selected_model == "m1"

    def test_no_models_available(self) -> None:
        state = _make_state()
        state.selected_model = "old"
        mock_mgr = MagicMock()
        mock_mgr.get_all_models.return_value = []
        mock_mgr.get_default_model.return_value = ""

        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            state._setup_models(SimpleNamespace(roles=[]))

        assert state.selected_model == ""
        assert state.ai_models == []

    def test_none_user(self) -> None:
        state = _make_state()
        models = [_ai_model("m1"), _ai_model("m2", requires_role="admin")]
        mock_mgr = MagicMock()
        mock_mgr.get_all_models.return_value = models
        mock_mgr.get_default_model.return_value = "m1"

        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            state._setup_models(None)

        # Only models without requires_role should be available
        assert len(state.ai_models) == 1


# ============================================================================
# set_selected_model
# ============================================================================


class TestSetSelectedModel:
    def test_basic_selection(self) -> None:
        state = _make_state()
        mock_mgr = MagicMock()
        mock_model = _ai_model(
            "gpt-4o",
            supports_search=True,
            supports_tools=True,
            supports_attachments=True,
            supports_skills=True,
        )
        mock_mgr.get_model.return_value = mock_model

        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            result = state.set_selected_model("gpt-4o")

        assert state.selected_model == "gpt-4o"
        assert state._thread.ai_model == "gpt-4o"
        assert state.modal_active_tab == "tools"
        assert result is not None

    def test_model_not_found(self) -> None:
        state = _make_state()
        mock_mgr = MagicMock()
        mock_mgr.get_model.return_value = None

        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            result = state.set_selected_model("unknown")

        assert state.selected_model == "unknown"
        assert result is None

    def test_disables_search(self) -> None:
        state = _make_state()
        state.web_search_enabled = True
        mock_mgr = MagicMock()
        mock_mgr.get_model.return_value = _ai_model(supports_search=False)

        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            state.set_selected_model("basic")

        assert state.web_search_enabled is False

    def test_disables_tools(self) -> None:
        state = _make_state()
        mock_mgr = MagicMock()
        mock_mgr.get_model.return_value = _ai_model(supports_tools=False)

        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            state.set_selected_model("basic")

        state._restore_mcp_selection.assert_called_once_with([])

    def test_disables_attachments(self) -> None:
        state = _make_state()
        mock_mgr = MagicMock()
        mock_mgr.get_model.return_value = _ai_model(supports_attachments=False)

        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            state.set_selected_model("basic")

        state._clear_uploaded_files.assert_called_once()

    def test_disables_skills(self) -> None:
        state = _make_state()
        mock_mgr = MagicMock()
        mock_mgr.get_model.return_value = _ai_model(supports_skills=False)

        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            state.set_selected_model("basic")

        state._restore_skill_selection.assert_called_once_with([])

    def test_persists_for_active_thread(self) -> None:
        state = _make_state()
        state._thread.state = ThreadStatus.ACTIVE
        state._current_user_id = 1
        mock_mgr = MagicMock()
        mock_mgr.get_model.return_value = _ai_model()

        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            result = state.set_selected_model("gpt-4o")

        assert len(result) == 2  # load_skills + persist

    def test_no_persist_for_new_thread(self) -> None:
        state = _make_state()
        state._thread.state = ThreadStatus.NEW
        state._current_user_id = 1
        mock_mgr = MagicMock()
        mock_mgr.get_model.return_value = _ai_model()

        with patch(f"{_PATCH}.ModelManager", return_value=mock_mgr):
            result = state.set_selected_model("gpt-4o")

        assert len(result) == 1  # only load_skills
