# ruff: noqa: ARG002, SLF001, S105, S106, PERF203
"""Tests for MCPServerState.

Covers load, add, modify, delete, toggle, role update,
header parsing, and computed vars.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.state.mcp_server_state import MCPServerState

_PATCH = "appkit_assistant.state.mcp_server_state"
_CV = MCPServerState.__dict__


def _unwrap(name: str):
    entry = MCPServerState.__dict__[name]
    return entry.fn if hasattr(entry, "fn") else entry


def _db_context(session: AsyncMock | None = None):
    s = session or AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=s)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _server(
    server_id: int = 1,
    name: str = "test",
    url: str = "https://mcp.test",
    active: bool = True,
    required_role: str | None = None,
) -> MagicMock:
    s = MagicMock()
    s.id = server_id
    s.name = name
    s.url = url
    s.active = active
    s.required_role = required_role
    s.model_dump.return_value = {
        "id": server_id,
        "name": name,
        "url": url,
        "active": active,
        "required_role": required_role,
    }
    s.model_copy.return_value = MagicMock(
        id=server_id,
        name=name,
        url=url,
        active=not active,
        required_role=required_role,
    )
    return s


class _StubMCPServerState:
    def __init__(self) -> None:
        self.servers: list = []
        self.current_server = None
        self.loading = False
        self.updating_active_server_id: int | None = None
        self.updating_role_server_id: int | None = None
        self.add_modal_open = False
        self.opening_add_modal = False
        self.edit_modal_open = False
        self.opening_edit_server_id: int | None = None
        self.search_filter = ""
        self.available_roles: list = []
        self.role_labels: dict = {}

    load_servers = _unwrap("load_servers")
    load_servers_with_toast = _unwrap("load_servers_with_toast")
    get_server = _unwrap("get_server")
    add_server = _unwrap("add_server")
    modify_server = _unwrap("modify_server")
    delete_server = _unwrap("delete_server")
    toggle_server_active = _unwrap("toggle_server_active")
    update_server_role = _unwrap("update_server_role")
    _parse_headers_from_form = _unwrap("_parse_headers_from_form")
    set_search_filter = _unwrap("set_search_filter")
    open_add_modal = _unwrap("open_add_modal")
    close_add_modal = _unwrap("close_add_modal")
    open_edit_modal = _unwrap("open_edit_modal")
    close_edit_modal = _unwrap("close_edit_modal")
    set_available_roles = _unwrap("set_available_roles")
    set_current_server = _unwrap("set_current_server")


# ================================================================
# Computed vars
# ================================================================


class TestComputedVars:
    def test_server_count(self) -> None:
        state = _StubMCPServerState()
        state.servers = [_server(), _server(2)]
        assert _CV["server_count"].fget(state) == 2

    def test_has_servers_true(self) -> None:
        state = _StubMCPServerState()
        state.servers = [_server()]
        assert _CV["has_servers"].fget(state) is True

    def test_has_servers_false(self) -> None:
        state = _StubMCPServerState()
        state.servers = []
        assert _CV["has_servers"].fget(state) is False

    def test_filtered_servers_no_filter(self) -> None:
        state = _StubMCPServerState()
        s = MagicMock()
        s.name = "Alpha"
        state.servers = [s]
        state.search_filter = ""
        result = _CV["filtered_servers"].fget(state)
        assert len(result) == 1

    def test_filtered_servers_with_filter(self) -> None:
        state = _StubMCPServerState()
        s1 = MagicMock()
        s1.name = "Alpha"
        s2 = MagicMock()
        s2.name = "Beta"
        state.servers = [s1, s2]
        state.search_filter = "alp"
        result = _CV["filtered_servers"].fget(state)
        assert len(result) == 1
        assert result[0].name == "Alpha"


# ================================================================
# Simple methods
# ================================================================


class TestSimpleMethods:
    def test_set_search_filter(self) -> None:
        state = _StubMCPServerState()
        state.set_search_filter("test")
        assert state.search_filter == "test"

    def test_close_add_modal(self) -> None:
        state = _StubMCPServerState()
        state.add_modal_open = True
        state.close_add_modal()
        assert state.add_modal_open is False

    def test_close_edit_modal(self) -> None:
        state = _StubMCPServerState()
        state.edit_modal_open = True
        state.current_server = _server()
        state.close_edit_modal()
        assert state.edit_modal_open is False
        assert state.current_server is None

    def test_set_available_roles(self) -> None:
        state = _StubMCPServerState()
        roles = [{"value": "admin", "label": "Admin"}]
        labels = {"admin": "Admin"}
        state.set_available_roles(roles, labels)
        assert state.available_roles == roles
        assert state.role_labels == labels

    @pytest.mark.asyncio
    async def test_set_current_server(self) -> None:
        state = _StubMCPServerState()
        s = _server()
        await state.set_current_server(s)
        assert state.current_server is s

    @pytest.mark.asyncio
    async def test_open_add_modal(self) -> None:
        state = _StubMCPServerState()
        [r async for r in state.open_add_modal()]
        assert state.add_modal_open is True

    @pytest.mark.asyncio
    async def test_open_edit_modal_found(self) -> None:
        state = _StubMCPServerState()
        s = MagicMock()
        s.id = 1
        state.servers = [s]
        [r async for r in state.open_edit_modal(1)]
        assert state.edit_modal_open is True
        assert state.current_server is s


# ================================================================
# Parse headers
# ================================================================


class TestParseHeaders:
    def test_empty(self) -> None:
        state = _StubMCPServerState()
        result = state._parse_headers_from_form({})
        assert result == "{}"

    def test_blank(self) -> None:
        state = _StubMCPServerState()
        result = state._parse_headers_from_form({"headers_json": "  "})
        assert result == "{}"

    def test_valid_json(self) -> None:
        state = _StubMCPServerState()
        result = state._parse_headers_from_form(
            {"headers_json": '{"Authorization": "Bearer x"}'}
        )
        assert "Authorization" in result

    def test_invalid_json(self) -> None:
        state = _StubMCPServerState()
        with pytest.raises(ValueError, match="JSON"):
            state._parse_headers_from_form({"headers_json": "not json"})

    def test_non_dict_json(self) -> None:
        state = _StubMCPServerState()
        with pytest.raises(ValueError, match="dictionary"):
            state._parse_headers_from_form({"headers_json": '["list"]'})

    def test_non_string_values(self) -> None:
        state = _StubMCPServerState()
        with pytest.raises(ValueError, match="Invalid"):
            state._parse_headers_from_form({"headers_json": '{"key": 123}'})


# ================================================================
# Load servers
# ================================================================


class TestLoadServers:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _StubMCPServerState()
        s = _server()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.mcp_server_repo") as repo,
        ):
            repo.find_all_ordered_by_name = AsyncMock(return_value=[s])
            await state.load_servers()
        assert len(state.servers) == 1
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_error_raises(self) -> None:
        state = _StubMCPServerState()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                side_effect=RuntimeError("db"),
            ),
            pytest.raises(RuntimeError),
        ):
            await state.load_servers()
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_with_toast_success(self) -> None:
        state = _StubMCPServerState()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.mcp_server_repo") as repo,
        ):
            repo.find_all_ordered_by_name = AsyncMock(return_value=[])
            [r async for r in state.load_servers_with_toast()]
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_with_toast_error(self) -> None:
        state = _StubMCPServerState()
        with patch(
            f"{_PATCH}.get_asyncdb_session",
            side_effect=RuntimeError("db"),
        ):
            results = [r async for r in state.load_servers_with_toast()]
        # Should yield toast error
        assert len(results) >= 1


# ================================================================
# Get server
# ================================================================


class TestGetServer:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        state = _StubMCPServerState()
        s = _server()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.mcp_server_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=s)
            await state.get_server(1)
        assert state.current_server is not None

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        state = _StubMCPServerState()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.mcp_server_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=None)
            await state.get_server(999)
        assert state.current_server is None

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _StubMCPServerState()
        with patch(
            f"{_PATCH}.get_asyncdb_session",
            side_effect=RuntimeError("db"),
        ):
            await state.get_server(1)
        # Should not raise


# ================================================================
# Add server
# ================================================================


class TestAddServer:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _StubMCPServerState()
        saved = _server()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.mcp_server_repo") as repo,
        ):
            repo.save = AsyncMock(return_value=saved)
            repo.find_all_ordered_by_name = AsyncMock(return_value=[saved])
            [
                r
                async for r in state.add_server(
                    {"name": "New", "url": "https://new.test"}
                )
            ]
        assert state.add_modal_open is False
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_value_error(self) -> None:
        state = _StubMCPServerState()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.mcp_server_repo") as repo,
        ):
            repo.save = AsyncMock(side_effect=ValueError("bad data"))
            [
                r
                async for r in state.add_server(
                    {"name": "X", "url": "x", "headers_json": "{}"}
                )
            ]
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        state = _StubMCPServerState()
        with patch(
            f"{_PATCH}.get_asyncdb_session",
            side_effect=RuntimeError("db"),
        ):
            [r async for r in state.add_server({"name": "X", "url": "x"})]
        assert state.loading is False


# ================================================================
# Modify server
# ================================================================


class TestModifyServer:
    @pytest.mark.asyncio
    async def test_no_current_server(self) -> None:
        state = _StubMCPServerState()
        state.current_server = None
        [r async for r in state.modify_server({"name": "X", "url": "x"})]
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _StubMCPServerState()
        s = _server()
        state.current_server = s
        updated = _server(name="Updated")
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.mcp_server_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=s)
            repo.save = AsyncMock(return_value=updated)
            repo.find_all_ordered_by_name = AsyncMock(return_value=[updated])
            [
                r
                async for r in state.modify_server(
                    {"name": "Updated", "url": "https://new.test"}
                )
            ]
        assert state.edit_modal_open is False
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_server_not_found(self) -> None:
        state = _StubMCPServerState()
        state.current_server = _server()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.mcp_server_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=None)
            [r async for r in state.modify_server({"name": "X", "url": "x"})]
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_value_error(self) -> None:
        state = _StubMCPServerState()
        state.current_server = _server()
        [
            r
            async for r in state.modify_server(
                {"name": "X", "url": "x", "headers_json": "bad"}
            )
        ]
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        state = _StubMCPServerState()
        state.current_server = _server()
        with patch(
            f"{_PATCH}.get_asyncdb_session",
            side_effect=RuntimeError("db"),
        ):
            [r async for r in state.modify_server({"name": "X", "url": "x"})]
        assert state.loading is False


# ================================================================
# Delete server
# ================================================================


class TestDeleteServer:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _StubMCPServerState()
        s = _server()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.mcp_server_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=s)
            repo.delete_by_id = AsyncMock(return_value=True)
            repo.find_all_ordered_by_name = AsyncMock(return_value=[])
            [r async for r in state.delete_server(1)]
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        state = _StubMCPServerState()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.mcp_server_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=None)
            [r async for r in state.delete_server(999)]
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_delete_fails(self) -> None:
        state = _StubMCPServerState()
        s = _server()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.mcp_server_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=s)
            repo.delete_by_id = AsyncMock(return_value=False)
            [r async for r in state.delete_server(1)]
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        state = _StubMCPServerState()
        with patch(
            f"{_PATCH}.get_asyncdb_session",
            side_effect=RuntimeError("db"),
        ):
            [r async for r in state.delete_server(1)]
        assert state.loading is False


# ================================================================
# Toggle active
# ================================================================


class TestToggleActive:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _StubMCPServerState()
        s = MagicMock()
        s.id = 1
        s.name = "test"
        s.model_copy.return_value = MagicMock(id=1, name="test", active=False)
        state.servers = [s]
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.mcp_server_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=s)
            repo.save = AsyncMock(return_value=s)
            [r async for r in state.toggle_server_active(1, False)]
        assert state.updating_active_server_id is None

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        state = _StubMCPServerState()
        s = MagicMock()
        s.id = 1
        s.model_copy.return_value = MagicMock(id=1, active=False)
        state.servers = [s]
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.mcp_server_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=None)
            [r async for r in state.toggle_server_active(1, False)]
        assert state.updating_active_server_id is None

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        state = _StubMCPServerState()
        s = MagicMock()
        s.id = 1
        s.model_copy.return_value = MagicMock(id=1, active=False)
        state.servers = [s]
        with patch(
            f"{_PATCH}.get_asyncdb_session",
            side_effect=RuntimeError("db"),
        ):
            [r async for r in state.toggle_server_active(1, False)]
        assert state.updating_active_server_id is None


# ================================================================
# Update role
# ================================================================


class TestUpdateRole:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _StubMCPServerState()
        s = MagicMock()
        s.id = 1
        s.name = "test"
        s.required_role = None
        s.model_copy.return_value = MagicMock(id=1, required_role=None)
        state.servers = [s]
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.mcp_server_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=s)
            repo.save = AsyncMock(return_value=s)
            [r async for r in state.update_server_role(1, "admin")]
        assert state.updating_role_server_id is None

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        state = _StubMCPServerState()
        s = MagicMock()
        s.id = 1
        s.required_role = None
        s.model_copy.return_value = MagicMock(id=1, required_role=None)
        state.servers = [s]
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.mcp_server_repo") as repo,
        ):
            repo.find_by_id = AsyncMock(return_value=None)
            [r async for r in state.update_server_role(1, "admin")]
        assert state.updating_role_server_id is None

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        state = _StubMCPServerState()
        s = MagicMock()
        s.id = 1
        s.required_role = None
        s.model_copy.return_value = MagicMock(id=1, required_role=None)
        state.servers = [s]
        with patch(
            f"{_PATCH}.get_asyncdb_session",
            side_effect=RuntimeError("db"),
        ):
            [r async for r in state.update_server_role(1, "admin")]
        assert state.updating_role_server_id is None
