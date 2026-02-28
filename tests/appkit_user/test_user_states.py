# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for UserState.

Covers user CRUD, search filtering, role extraction,
modal management, pagination, and auth-decorated flows.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_commons.roles import Role
from appkit_user.authentication.backend.models import User
from appkit_user.user_management.states.user_states import UserState

_PATCH = "appkit_user.user_management.states.user_states"

_CV = UserState.__dict__


def _unwrap(name: str):
    entry = UserState.__dict__[name]
    return entry.fn if hasattr(entry, "fn") else entry


def _user(user_id: int = 1, name: str = "Alice", email: str = "alice@x.com") -> User:
    return User(user_id=user_id, name=name, email=email, is_active=True)


def _user_entity(
    user_id: int = 1, name: str = "Alice", email: str = "alice@x.com"
) -> MagicMock:
    entity = MagicMock()
    entity.id = user_id
    entity.to_dict.return_value = {
        "user_id": user_id,
        "name": name,
        "email": email,
        "is_active": True,
        "is_verified": True,
    }
    return entity


class _StubUserState:
    """Plain stub for UserState."""

    def __init__(self, *, authenticated: bool = True) -> None:
        self.users: list[User] = []
        self.selected_user: User | None = None
        self.is_loading: bool = False
        self.available_roles: list[dict[str, str]] = []
        self.grouped_roles: dict[str, list[dict[str, str]]] = {}
        self.sorted_group_names: list[str] = []
        self.add_modal_open: bool = False
        self.edit_modal_open: bool = False
        self.search_filter: str = ""
        self._authenticated = authenticated

    async def get_state(self, cls: type) -> MagicMock:
        mock = MagicMock()
        mock.is_authenticated = AsyncMock(return_value=self._authenticated)()
        mock.redir = AsyncMock(return_value=None)
        return mock

    set_search_filter = _unwrap("set_search_filter")
    open_add_modal = _unwrap("open_add_modal")
    close_add_modal = _unwrap("close_add_modal")
    open_edit_modal = _unwrap("open_edit_modal")
    close_edit_modal = _unwrap("close_edit_modal")
    select_user_and_open_edit = _unwrap("select_user_and_open_edit")
    set_available_roles = _unwrap("set_available_roles")
    _get_selected_roles = _unwrap("_get_selected_roles")
    _load_users = _unwrap("_load_users")
    load_users = _unwrap("load_users")
    create_user = _unwrap("create_user")
    update_user = _unwrap("update_user")
    delete_user = _unwrap("delete_user")
    select_user = _unwrap("select_user")
    user_has_role = _unwrap("user_has_role")


def _make_state(*, authenticated: bool = True) -> _StubUserState:
    return _StubUserState(authenticated=authenticated)


def _db_context():
    session = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


class TestFilteredUsers:
    def test_no_filter(self) -> None:
        state = _make_state()
        state.users = [_user(), _user(2, "Bob", "bob@x.com")]
        assert len(_CV["filtered_users"].fget(state)) == 2

    def test_filter_by_name(self) -> None:
        state = _make_state()
        state.users = [_user(), _user(2, "Bob", "bob@x.com")]
        state.search_filter = "alice"
        result = _CV["filtered_users"].fget(state)
        assert len(result) == 1
        assert result[0].name == "Alice"

    def test_filter_by_email(self) -> None:
        state = _make_state()
        state.users = [_user(), _user(2, "Bob", "bob@x.com")]
        state.search_filter = "bob@"
        assert len(_CV["filtered_users"].fget(state)) == 1

    def test_no_match(self) -> None:
        state = _make_state()
        state.users = [_user()]
        state.search_filter = "zzz"
        assert len(_CV["filtered_users"].fget(state)) == 0


class TestModals:
    def test_add_modal(self) -> None:
        state = _make_state()
        state.open_add_modal()
        assert state.add_modal_open is True
        state.close_add_modal()
        assert state.add_modal_open is False

    def test_edit_modal_clears_selection(self) -> None:
        state = _make_state()
        state.selected_user = _user()
        state.open_edit_modal()
        assert state.edit_modal_open is True
        state.close_edit_modal()
        assert state.edit_modal_open is False
        assert state.selected_user is None


class TestSetSearchFilter:
    def test_updates(self) -> None:
        state = _make_state()
        state.set_search_filter("test")
        assert state.search_filter == "test"


class TestSetAvailableRoles:
    def test_role_objects(self) -> None:
        state = _make_state()
        roles = [
            Role(name="admin", label="Admin", group="sys"),
            Role(name="user", label="User", group="app"),
        ]
        state.set_available_roles(roles)
        assert len(state.available_roles) == 2
        assert "sys" in state.sorted_group_names
        assert len(state.grouped_roles) == 2

    def test_dict_roles(self) -> None:
        state = _make_state()
        state.set_available_roles([{"name": "admin", "label": "Admin", "group": "g1"}])
        assert len(state.available_roles) == 1


class TestGetSelectedRoles:
    def test_extracts(self) -> None:
        state = _make_state()
        result = state._get_selected_roles(
            {"role_admin": "on", "role_user": "on", "name": "X", "role_off": "off"}
        )
        assert sorted(result) == ["admin", "user"]

    def test_no_roles(self) -> None:
        state = _make_state()
        assert state._get_selected_roles({"name": "X"}) == []


class TestLoadUsersInternal:
    @pytest.mark.asyncio
    async def test_loads(self) -> None:
        state = _make_state()
        entities = [_user_entity(1, "Alice"), _user_entity(2, "Bob")]
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.user_repo") as mock_repo,
        ):
            mock_repo.find_all_paginated = AsyncMock(return_value=entities)
            await state._load_users()
        assert len(state.users) == 2


class TestLoadUsers:
    @pytest.mark.asyncio
    async def test_loading_flag(self) -> None:
        state = _make_state()
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.user_repo") as mock_repo,
        ):
            mock_repo.find_all_paginated = AsyncMock(return_value=[])
            _ = [c async for c in state.load_users()]
        assert state.is_loading is False


class TestCreateUser:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        state.add_modal_open = True
        form_data = {
            "name": "Bob",
            "email": "bob@x.com",
            "password": "X",
            "role_admin": "on",
        }
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.user_repo") as mock_repo,
        ):
            mock_repo.create_new_user = AsyncMock()
            mock_repo.find_all_paginated = AsyncMock(return_value=[])
            _ = [c async for c in state.create_user(form_data)]
        assert state.add_modal_open is False

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _make_state()
        form_data = {"name": "B", "email": "b@x.com", "password": "X"}
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.user_repo") as mock_repo,
        ):
            mock_repo.create_new_user = AsyncMock(side_effect=RuntimeError("dup"))
            results = [c async for c in state.create_user(form_data)]
        assert state.is_loading is False
        assert len(results) > 0


class TestUpdateUser:
    @pytest.mark.asyncio
    async def test_no_selected_user(self) -> None:
        state = _make_state()
        _ = [c async for c in state.update_user({"email": "x@y.com"})]
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        state.selected_user = _user()
        state.edit_modal_open = True
        form_data = {
            "name": "A",
            "email": "a@x.com",
            "password": "",
            "is_active": True,
            "is_admin": False,
            "is_verified": True,
            "role_admin": "on",
        }
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.user_repo") as mock_repo,
        ):
            mock_repo.update_from_model = AsyncMock()
            mock_repo.find_all_paginated = AsyncMock(return_value=[])
            _ = [c async for c in state.update_user(form_data)]
        assert state.edit_modal_open is False

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _make_state()
        state.selected_user = _user()
        form_data = {
            "name": "X",
            "email": "x@y.com",
            "password": "",
            "is_active": True,
            "is_admin": False,
            "is_verified": True,
        }
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.user_repo") as mock_repo,
        ):
            mock_repo.update_from_model = AsyncMock(side_effect=RuntimeError("f"))
            _ = [c async for c in state.update_user(form_data)]
        assert state.is_loading is False


class TestDeleteUser:
    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        state = _make_state()
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.user_repo") as mock_repo,
        ):
            mock_repo.find_by_id = AsyncMock(return_value=None)
            _ = [c async for c in state.delete_user(99)]
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_delete_fails(self) -> None:
        state = _make_state()
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.user_repo") as mock_repo,
        ):
            mock_repo.find_by_id = AsyncMock(return_value=_user_entity())
            mock_repo.delete_by_id = AsyncMock(return_value=False)
            _ = [c async for c in state.delete_user(1)]
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.user_repo") as mock_repo,
        ):
            mock_repo.find_by_id = AsyncMock(return_value=_user_entity())
            mock_repo.delete_by_id = AsyncMock(return_value=True)
            mock_repo.find_all_paginated = AsyncMock(return_value=[])
            _ = [c async for c in state.delete_user(1)]
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        state = _make_state()
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.user_repo") as mock_repo,
        ):
            mock_repo.find_by_id = AsyncMock(side_effect=RuntimeError("db"))
            _ = [c async for c in state.delete_user(1)]
        assert state.is_loading is False


class TestSelectUser:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        state = _make_state()
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.user_repo") as mock_repo,
        ):
            mock_repo.find_by_id = AsyncMock(return_value=_user_entity(1, "Alice"))
            await state.select_user(1)
        assert state.selected_user is not None

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        state = _make_state()
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.user_repo") as mock_repo,
        ):
            mock_repo.find_by_id = AsyncMock(return_value=None)
            await state.select_user(99)
        assert state.selected_user is None


class TestUserHasRole:
    @pytest.mark.asyncio
    async def test_no_user(self) -> None:
        state = _make_state()
        assert await state.user_has_role("admin") is False

    @pytest.mark.asyncio
    async def test_has_role(self) -> None:
        state = _make_state()
        state.selected_user = User(
            user_id=1, name="A", email="a@x.com", roles=["admin"]
        )
        assert await state.user_has_role("admin") is True
        assert await state.user_has_role("user") is False


class TestSelectUserAndOpenEdit:
    @pytest.mark.asyncio
    async def test_opens_modal(self) -> None:
        state = _make_state()
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.user_repo") as mock_repo,
        ):
            mock_repo.find_by_id = AsyncMock(return_value=_user_entity())
            await state.select_user_and_open_edit(1)
        assert state.edit_modal_open is True
        assert state.selected_user is not None
