# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for ImageGeneratorAdminState.

Covers CRUD operations, computed vars, modal controls, search filtering,
optimistic updates, and error handling for the image generator admin UI.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from appkit_imagecreator.admin_state import ImageGeneratorAdminState
from appkit_imagecreator.backend.models import ImageGeneratorModel

_PATCH = "appkit_imagecreator.admin_state"

# Access computed-var descriptors via __dict__ to bypass Reflex __get__.
_CV = ImageGeneratorAdminState.__dict__


def _gen_model(
    gen_id: int = 1,
    model_id: str = "dall-e-3",
    label: str = "DALL-E 3",
    processor_type: str = "openai",
    active: bool = True,
    required_role: str | None = None,
) -> ImageGeneratorModel:
    return ImageGeneratorModel(
        id=gen_id,
        model_id=model_id,
        model=model_id,
        label=label,
        processor_type=processor_type,
        api_key="secret",
        active=active,
        required_role=required_role,
    )


_REAL = ImageGeneratorAdminState


def _unwrap(name: str):
    """Get the raw function from an EventHandler in __dict__."""
    entry = _REAL.__dict__[name]
    return entry.fn if hasattr(entry, "fn") else entry


class _StubAdminState:
    """Plain stub providing the same attrs as ImageGeneratorAdminState.

    We cannot subclass rx.State because its __setattr__ delegates
    to parent_state which is None in tests. Instead we create a
    plain object and call the unwrapped functions via EventHandler.fn.
    """

    def __init__(self) -> None:
        self.generators: list[ImageGeneratorModel] = []
        self.current_generator: ImageGeneratorModel | None = None
        self.loading: bool = False
        self.search_filter: str = ""
        self.updating_active_generator_id: int | None = None
        self.updating_role_generator_id: int | None = None
        self.available_roles: list[dict[str, str]] = []
        self.role_labels: dict[str, str] = {}
        self.add_modal_open: bool = False
        self.edit_modal_open: bool = False

    # Unwrap EventHandler → raw function for each method.
    set_search_filter = _unwrap("set_search_filter")
    set_available_roles = _unwrap("set_available_roles")
    open_add_modal = _unwrap("open_add_modal")
    close_add_modal = _unwrap("close_add_modal")
    open_edit_modal = _unwrap("open_edit_modal")
    close_edit_modal = _unwrap("close_edit_modal")
    load_generators = _unwrap("load_generators")
    load_generators_with_toast = _unwrap("load_generators_with_toast")
    get_generator = _unwrap("get_generator")
    add_generator = _unwrap("add_generator")
    modify_generator = _unwrap("modify_generator")
    delete_generator = _unwrap("delete_generator")
    toggle_generator_active = _unwrap("toggle_generator_active")
    update_generator_role = _unwrap("update_generator_role")


def _make_state() -> _StubAdminState:
    return _StubAdminState()


# ============================================================================
# Sync handlers
# ============================================================================


class TestSyncHandlers:
    def test_set_search_filter(self) -> None:
        state = _make_state()
        state.set_search_filter("dalle")
        assert state.search_filter == "dalle"

    def test_set_available_roles(self) -> None:
        state = _make_state()
        roles = [{"value": "admin", "label": "Admin"}]
        labels = {"admin": "Admin"}
        state.set_available_roles(roles, labels)
        assert state.available_roles == roles
        assert state.role_labels == labels

    def test_open_add_modal(self) -> None:
        state = _make_state()
        state.open_add_modal()
        assert state.add_modal_open is True

    def test_close_add_modal(self) -> None:
        state = _make_state()
        state.add_modal_open = True
        state.close_add_modal()
        assert state.add_modal_open is False

    def test_open_edit_modal(self) -> None:
        state = _make_state()
        state.open_edit_modal()
        assert state.edit_modal_open is True

    def test_close_edit_modal(self) -> None:
        state = _make_state()
        state.edit_modal_open = True
        state.close_edit_modal()
        assert state.edit_modal_open is False


# ============================================================================
# Computed vars
# ============================================================================


class TestComputedVars:
    def test_filtered_generators_no_filter(self) -> None:
        state = _make_state()
        state.generators = [_gen_model(1, "m1", "Model 1")]
        result = _CV["filtered_generators"].fget(state)
        assert len(result) == 1

    def test_filtered_generators_by_label(self) -> None:
        state = _make_state()
        state.generators = [
            _gen_model(1, "m1", "DALL-E 3"),
            _gen_model(2, "m2", "Stable Diffusion"),
        ]
        state.search_filter = "dall"
        result = _CV["filtered_generators"].fget(state)
        assert len(result) == 1
        assert result[0].label == "DALL-E 3"

    def test_filtered_generators_by_model_id(self) -> None:
        state = _make_state()
        state.generators = [
            _gen_model(1, "dall-e-3", "DE3"),
            _gen_model(2, "flux-1", "Flux"),
        ]
        state.search_filter = "flux"
        result = _CV["filtered_generators"].fget(state)
        assert len(result) == 1
        assert result[0].model_id == "flux-1"

    def test_filtered_generators_case_insensitive(self) -> None:
        state = _make_state()
        state.generators = [_gen_model(1, "test", "UPPERCASE")]
        state.search_filter = "uppercase"
        result = _CV["filtered_generators"].fget(state)
        assert len(result) == 1

    def test_generator_count(self) -> None:
        state = _make_state()
        state.generators = [_gen_model(1), _gen_model(2)]
        assert _CV["generator_count"].fget(state) == 2

    def test_generator_count_empty(self) -> None:
        state = _make_state()
        assert _CV["generator_count"].fget(state) == 0

    def test_has_generators_true(self) -> None:
        state = _make_state()
        state.generators = [_gen_model()]
        assert _CV["has_generators"].fget(state) is True

    def test_has_generators_false(self) -> None:
        state = _make_state()
        assert _CV["has_generators"].fget(state) is False


# ============================================================================
# _parse_extra_config (static)
# ============================================================================


class TestParseExtraConfig:
    def test_empty_string(self) -> None:
        assert ImageGeneratorAdminState._parse_extra_config({}) is None

    def test_whitespace(self) -> None:
        assert (
            ImageGeneratorAdminState._parse_extra_config({"extra_config": "   "})
            is None
        )

    def test_valid_json_object(self) -> None:
        result = ImageGeneratorAdminState._parse_extra_config(
            {"extra_config": '{"key": "value"}'}
        )
        assert result == {"key": "value"}

    def test_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="JSON"):
            ImageGeneratorAdminState._parse_extra_config({"extra_config": "not json"})

    def test_non_dict_json(self) -> None:
        with pytest.raises(ValueError, match="JSON-Objekt"):
            ImageGeneratorAdminState._parse_extra_config({"extra_config": "[1, 2, 3]"})


# ============================================================================
# load_generators
# ============================================================================


class TestLoadGenerators:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        mock_models = [_gen_model(1), _gen_model(2)]

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_all_ordered_by_name = AsyncMock(return_value=mock_models)

            await state.load_generators()

        assert len(state.generators) == 2
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_error_raises(self) -> None:
        state = _make_state()

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_all_ordered_by_name = AsyncMock(
                side_effect=RuntimeError("db error")
            )

            with pytest.raises(RuntimeError, match="db error"):
                await state.load_generators()

        assert state.loading is False


# ============================================================================
# load_generators_with_toast
# ============================================================================


class TestLoadGeneratorsWithToast:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_all_ordered_by_name = AsyncMock(return_value=[])

            chunks = [c async for c in state.load_generators_with_toast()]

        assert state.loading is False
        # No error toast on success
        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_error_yields_toast(self) -> None:
        state = _make_state()

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_all_ordered_by_name = AsyncMock(
                side_effect=RuntimeError("fail")
            )

            chunks = [c async for c in state.load_generators_with_toast()]

        assert len(chunks) >= 1  # toast error


# ============================================================================
# get_generator
# ============================================================================


class TestGetGenerator:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        state = _make_state()
        gen = _gen_model(1)

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_id = AsyncMock(return_value=gen)

            await state.get_generator(1)

        assert state.current_generator is not None
        assert state.current_generator.id == 1

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        state = _make_state()

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_id = AsyncMock(return_value=None)

            await state.get_generator(999)

        assert state.current_generator is None

    @pytest.mark.asyncio
    async def test_error_handled(self) -> None:
        state = _make_state()

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_id = AsyncMock(side_effect=RuntimeError("fail"))

            # Should not raise
            await state.get_generator(1)

        assert state.current_generator is None


# ============================================================================
# add_generator
# ============================================================================


class TestAddGenerator:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        form_data = {
            "model_id": "flux-1",
            "label": "Flux 1",
            "processor_type": "bfl",
        }
        saved_gen = _gen_model(1, "flux-1", "Flux 1", "bfl")

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
            patch(f"{_PATCH}.generator_registry") as mock_registry,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.save = AsyncMock(return_value=saved_gen)
            mock_repo.find_all_ordered_by_name = AsyncMock(return_value=[saved_gen])
            mock_registry.reload = AsyncMock()

            chunks = [c async for c in state.add_generator(form_data)]

        assert state.add_modal_open is False
        assert state.loading is False
        assert len(chunks) >= 1  # toast info

    @pytest.mark.asyncio
    async def test_value_error(self) -> None:
        state = _make_state()
        form_data = {
            "model_id": "test",
            "label": "Test",
            "processor_type": "x",
            "extra_config": "invalid json",
        }

        chunks = [c async for c in state.add_generator(form_data)]
        assert state.loading is False
        assert len(chunks) >= 1  # toast error

    @pytest.mark.asyncio
    async def test_db_error(self) -> None:
        state = _make_state()
        form_data = {
            "model_id": "test",
            "label": "Test",
            "processor_type": "x",
        }

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.save = AsyncMock(side_effect=RuntimeError("db error"))

            chunks = [c async for c in state.add_generator(form_data)]

        assert state.loading is False
        assert len(chunks) >= 1  # toast error


# ============================================================================
# modify_generator
# ============================================================================


class TestModifyGenerator:
    @pytest.mark.asyncio
    async def test_no_current_generator(self) -> None:
        state = _make_state()

        chunks = [c async for c in state.modify_generator({})]
        assert len(chunks) >= 1  # toast error

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        state.current_generator = _gen_model(1)
        existing = _gen_model(1)
        saved = _gen_model(1, "dall-e-3", "Updated DALL-E")
        form_data = {
            "model_id": "dall-e-3",
            "label": "Updated DALL-E",
            "processor_type": "openai",
        }

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
            patch(f"{_PATCH}.generator_registry") as mock_registry,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_id = AsyncMock(return_value=existing)
            mock_repo.save = AsyncMock(return_value=saved)
            mock_repo.find_all_ordered_by_name = AsyncMock(return_value=[saved])
            mock_registry.reload = AsyncMock()

            chunks = [c async for c in state.modify_generator(form_data)]

        assert state.edit_modal_open is False
        assert state.loading is False
        assert len(chunks) >= 1  # toast info

    @pytest.mark.asyncio
    async def test_not_found_in_db(self) -> None:
        state = _make_state()
        state.current_generator = _gen_model(1)
        form_data = {
            "model_id": "x",
            "label": "X",
            "processor_type": "x",
        }

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_id = AsyncMock(return_value=None)

            chunks = [c async for c in state.modify_generator(form_data)]

        assert len(chunks) >= 1  # toast error
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_api_key_only_updated_when_provided(self) -> None:
        state = _make_state()
        state.current_generator = _gen_model(1)
        existing = _gen_model(1)
        existing.api_key = "old-key"
        form_data = {
            "model_id": "dall-e-3",
            "label": "DALL-E",
            "processor_type": "openai",
            "api_key": "",  # empty = should keep old key
        }

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
            patch(f"{_PATCH}.generator_registry") as mock_registry,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_id = AsyncMock(return_value=existing)
            mock_repo.save = AsyncMock(return_value=existing)
            mock_repo.find_all_ordered_by_name = AsyncMock(return_value=[existing])
            mock_registry.reload = AsyncMock()

            [c async for c in state.modify_generator(form_data)]

        assert existing.api_key == "old-key"


# ============================================================================
# delete_generator
# ============================================================================


class TestDeleteGenerator:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        gen = _gen_model(1)

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
            patch(f"{_PATCH}.generator_registry") as mock_registry,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_id = AsyncMock(return_value=gen)
            mock_repo.delete_by_id = AsyncMock(return_value=True)
            mock_repo.find_all_ordered_by_name = AsyncMock(return_value=[])
            mock_registry.reload = AsyncMock()

            chunks = [c async for c in state.delete_generator(1)]

        assert len(chunks) >= 1  # toast info

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        state = _make_state()

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_id = AsyncMock(return_value=None)

            chunks = [c async for c in state.delete_generator(999)]

        assert len(chunks) >= 1  # toast error

    @pytest.mark.asyncio
    async def test_delete_failed(self) -> None:
        state = _make_state()
        gen = _gen_model(1)

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_id = AsyncMock(return_value=gen)
            mock_repo.delete_by_id = AsyncMock(return_value=False)

            chunks = [c async for c in state.delete_generator(1)]

        assert len(chunks) >= 1  # toast error

    @pytest.mark.asyncio
    async def test_db_exception(self) -> None:
        state = _make_state()

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_id = AsyncMock(side_effect=RuntimeError("fail"))

            chunks = [c async for c in state.delete_generator(1)]

        assert len(chunks) >= 1  # toast error


# ============================================================================
# toggle_generator_active
# ============================================================================


class TestToggleGeneratorActive:
    @pytest.mark.asyncio
    async def test_activate(self) -> None:
        state = _make_state()
        gen = _gen_model(1, active=False)
        state.generators = [gen]

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
            patch(f"{_PATCH}.generator_registry") as mock_registry,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            db_gen = _gen_model(1, active=False)
            mock_repo.find_by_id = AsyncMock(return_value=db_gen)
            mock_repo.save = AsyncMock(return_value=db_gen)
            mock_registry.reload = AsyncMock()

            chunks = [c async for c in state.toggle_generator_active(1, True)]

        assert state.updating_active_generator_id is None
        # Optimistic update + DB update
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_not_found_reverts(self) -> None:
        state = _make_state()
        original = _gen_model(1, active=True)
        state.generators = [original]

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_id = AsyncMock(return_value=None)

            chunks = [c async for c in state.toggle_generator_active(1, False)]

        assert state.updating_active_generator_id is None
        assert len(chunks) >= 1  # toast error

    @pytest.mark.asyncio
    async def test_error_reverts(self) -> None:
        state = _make_state()
        original = _gen_model(1, active=True)
        state.generators = [original]

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_id = AsyncMock(side_effect=RuntimeError("fail"))

            chunks = [c async for c in state.toggle_generator_active(1, False)]

        assert state.updating_active_generator_id is None
        assert len(chunks) >= 1  # toast error


# ============================================================================
# update_generator_role
# ============================================================================


class TestUpdateGeneratorRole:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        gen = _gen_model(1)
        state.generators = [gen]

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            db_gen = _gen_model(1)
            mock_repo.find_by_id = AsyncMock(return_value=db_gen)
            mock_repo.save = AsyncMock(return_value=db_gen)

            chunks = [c async for c in state.update_generator_role(1, "admin")]

        assert state.updating_role_generator_id is None
        assert len(chunks) >= 1  # toast info

    @pytest.mark.asyncio
    async def test_not_found_reverts(self) -> None:
        state = _make_state()
        gen = _gen_model(1)
        state.generators = [gen]

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_id = AsyncMock(return_value=None)

            chunks = [c async for c in state.update_generator_role(1, "admin")]

        assert state.updating_role_generator_id is None
        assert len(chunks) >= 1  # toast error

    @pytest.mark.asyncio
    async def test_error_reverts(self) -> None:
        state = _make_state()
        gen = _gen_model(1)
        state.generators = [gen]

        with (
            patch(f"{_PATCH}.get_asyncdb_session") as mock_session,
            patch(f"{_PATCH}.generator_model_repo") as mock_repo,
        ):
            session = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_id = AsyncMock(side_effect=RuntimeError("fail"))

            chunks = [c async for c in state.update_generator_role(1, "admin")]

        assert state.updating_role_generator_id is None
        assert len(chunks) >= 1  # toast error
