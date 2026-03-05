# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for FileManagerState and pure helper functions.

Covers format_file_size_for_display, _format_unix_timestamp,
pydantic models, and FileManagerState methods.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.state.file_manager_state import (
    GB,
    KB,
    MB,
    CleanupStats,
    FileInfo,
    FileManagerState,
    OpenAIFileInfo,
    VectorStoreInfo,
    _format_unix_timestamp,
    format_file_size_for_display,
)

_PATCH = "appkit_assistant.state.file_manager_state"

_CV = FileManagerState.__dict__


def _unwrap(name: str):
    entry = FileManagerState.__dict__[name]
    return entry.fn if hasattr(entry, "fn") else entry


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


def _db_context(session: MagicMock | None = None):
    s = session or _mock_session()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=s)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _mock_model(
    model_id: str = "gpt-4",
    text: str = "GPT-4",
    api_key: str | None = "sk-test",
):
    m = MagicMock()
    m.model_id = model_id
    m.text = text
    m.api_key = api_key
    m.base_url = None
    return m


def _file_info(fid: int = 1) -> FileInfo:
    return FileInfo(
        id=fid,
        filename="test.pdf",
        created_at="01.01.2025 12:00",
        user_name="Alice",
        file_size=1024,
        formatted_size=1.0,
        size_suffix=" KB",
        openai_file_id=f"file-{fid}",
    )


def _openai_file(oid: str = "file-1") -> OpenAIFileInfo:
    return OpenAIFileInfo(
        openai_id=oid,
        filename="test.pdf",
        created_at="01.01.2025",
        expires_at="-",
        purpose="assistants",
        file_size=2048,
        formatted_size=2.0,
        size_suffix=" KB",
    )


# ============================================================================
# Pure functions
# ============================================================================


class TestFormatFileSize:
    def test_bytes(self) -> None:
        val, suffix = format_file_size_for_display(500)
        assert val == 500.0
        assert suffix == " B"

    def test_kb(self) -> None:
        val, suffix = format_file_size_for_display(2048)
        assert suffix == " KB"
        assert abs(val - 2.0) < 0.01

    def test_mb(self) -> None:
        val, suffix = format_file_size_for_display(5 * MB)
        assert suffix == " MB"
        assert abs(val - 5.0) < 0.01

    def test_gb(self) -> None:
        val, suffix = format_file_size_for_display(2 * GB)
        assert suffix == " GB"
        assert abs(val - 2.0) < 0.01

    def test_constants(self) -> None:
        assert KB == 1024
        assert MB == 1024 * 1024
        assert GB == 1024 * 1024 * 1024


class TestFormatUnixTimestamp:
    def test_none(self) -> None:
        assert _format_unix_timestamp(None) == "-"

    def test_valid_timestamp(self) -> None:
        result = _format_unix_timestamp(1706284800)
        assert result != "-"
        assert "." in result  # dd.mm.yyyy format

    def test_invalid_timestamp(self) -> None:
        assert _format_unix_timestamp(-99999999999999) == "-"


# ============================================================================
# Pydantic models
# ============================================================================


class TestPydanticModels:
    def test_file_info(self) -> None:
        fi = _file_info()
        assert fi.filename == "test.pdf"
        assert fi.id == 1

    def test_openai_file_info(self) -> None:
        ofi = _openai_file()
        assert ofi.openai_id == "file-1"

    def test_vector_store_info(self) -> None:
        vs = VectorStoreInfo(store_id="vs-1", name="Store 1")
        assert vs.store_id == "vs-1"

    def test_cleanup_stats_defaults(self) -> None:
        cs = CleanupStats()
        assert cs.status == "idle"
        assert cs.vector_stores_checked == 0
        assert cs.error is None


# ============================================================================
# FileManagerState stub
# ============================================================================


class _StubFileManagerState:
    def __init__(self) -> None:
        self.file_models: list[Any] = []
        self.selected_file_model_id: str = ""
        self.active_tab: str = "vector_stores"
        self.vector_stores: list[VectorStoreInfo] = []
        self.selected_vector_store_id: str = ""
        self.selected_vector_store_name: str = ""
        self.files: list[FileInfo] = []
        self.openai_files: list[OpenAIFileInfo] = []
        self.loading: bool = False
        self.deleting_file_id: int | None = None
        self.deleting_openai_file_id: str | None = None
        self.deleting_vector_store_id: str | None = None
        self.cleanup_modal_open: bool = False
        self.cleanup_running: bool = False
        self.cleanup_stats: CleanupStats = CleanupStats()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a: object):
        pass

    _get_client = _unwrap("_get_client")
    _get_file_by_id = _unwrap("_get_file_by_id")
    _get_openai_file_by_id = _unwrap("_get_openai_file_by_id")
    load_file_models = _unwrap("load_file_models")
    set_selected_file_model = _unwrap("set_selected_file_model")
    on_tab_change = _unwrap("on_tab_change")
    load_vector_stores = _unwrap("load_vector_stores")
    delete_vector_store = _unwrap("delete_vector_store")
    select_vector_store = _unwrap("select_vector_store")
    _cleanup_expired_vector_store = _unwrap("_cleanup_expired_vector_store")
    load_files = _unwrap("load_files")
    load_openai_files = _unwrap("load_openai_files")
    delete_file = _unwrap("delete_file")
    delete_openai_file = _unwrap("delete_openai_file")
    open_cleanup_modal = _unwrap("open_cleanup_modal")
    close_cleanup_modal = _unwrap("close_cleanup_modal")
    set_cleanup_modal_open = _unwrap("set_cleanup_modal_open")
    start_cleanup = _unwrap("start_cleanup")


def _make_state() -> _StubFileManagerState:
    return _StubFileManagerState()


# ============================================================================
# Computed vars
# ============================================================================


class TestComputedVars:
    def test_file_model_options(self) -> None:
        state = _make_state()
        m = _mock_model()
        state.file_models = [m]
        result = _CV["file_model_options"].fget(state)
        assert len(result) == 1
        assert result[0]["value"] == "gpt-4"

    def test_has_file_models_true(self) -> None:
        state = _make_state()
        state.file_models = [_mock_model()]
        assert _CV["has_file_models"].fget(state) is True

    def test_has_file_models_false(self) -> None:
        state = _make_state()
        assert _CV["has_file_models"].fget(state) is False

    def test_selected_file_model_name_found(self) -> None:
        state = _make_state()
        m = _mock_model()
        state.file_models = [m]
        state.selected_file_model_id = "gpt-4"
        assert _CV["selected_file_model_name"].fget(state) == "GPT-4"

    def test_selected_file_model_name_not_found(self) -> None:
        state = _make_state()
        state.file_models = []
        state.selected_file_model_id = "missing"
        assert _CV["selected_file_model_name"].fget(state) == ""


# ============================================================================
# Helpers
# ============================================================================


class TestHelpers:
    def test_get_file_by_id_found(self) -> None:
        state = _make_state()
        state.files = [_file_info(1), _file_info(2)]
        assert state._get_file_by_id(1) is not None
        assert state._get_file_by_id(1).id == 1

    def test_get_file_by_id_not_found(self) -> None:
        state = _make_state()
        state.files = []
        assert state._get_file_by_id(99) is None

    def test_get_openai_file_by_id_found(self) -> None:
        state = _make_state()
        state.openai_files = [_openai_file("file-1")]
        assert state._get_openai_file_by_id("file-1") is not None

    def test_get_openai_file_by_id_not_found(self) -> None:
        state = _make_state()
        state.openai_files = []
        assert state._get_openai_file_by_id("x") is None


# ============================================================================
# Cleanup modal
# ============================================================================


class TestCleanupModal:
    def test_open(self) -> None:
        state = _make_state()
        state.open_cleanup_modal()
        assert state.cleanup_modal_open is True
        assert state.cleanup_stats.status == "idle"

    def test_close(self) -> None:
        state = _make_state()
        state.cleanup_modal_open = True
        state.close_cleanup_modal()
        assert state.cleanup_modal_open is False

    def test_set_open_true(self) -> None:
        state = _make_state()
        state.set_cleanup_modal_open(True)
        assert state.cleanup_modal_open is True

    def test_set_open_false(self) -> None:
        state = _make_state()
        state.cleanup_modal_open = True
        state.set_cleanup_modal_open(False)
        assert state.cleanup_modal_open is False


# ============================================================================
# load_file_models
# ============================================================================


class TestLoadFileModels:
    @pytest.mark.asyncio
    async def test_success_auto_select(self) -> None:
        state = _make_state()
        m = _mock_model()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            session_mock = AsyncMock()
            session_mock.expunge_all = MagicMock()
            repo.find_all_with_attachments = AsyncMock(return_value=[m])
            _ = [c async for c in state.load_file_models()]
        assert len(state.file_models) == 1
        assert state.selected_file_model_id == "gpt-4"

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _make_state()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
        ):
            repo.find_all_with_attachments = AsyncMock(side_effect=RuntimeError("db"))
            _ = [c async for c in state.load_file_models()]
        assert len(state.file_models) == 0


# ============================================================================
# set_selected_file_model
# ============================================================================


class TestSetSelectedFileModel:
    @pytest.mark.asyncio
    async def test_switches_model(self) -> None:
        state = _make_state()
        state.active_tab = "openai_files"
        _ = [c async for c in state.set_selected_file_model("x")]
        assert state.selected_file_model_id == "x"
        assert state.files == []

    @pytest.mark.asyncio
    async def test_vector_stores_tab(self) -> None:
        state = _make_state()
        state.active_tab = "vector_stores"
        _ = [c async for c in state.set_selected_file_model("x")]
        assert state.selected_file_model_id == "x"


# ============================================================================
# on_tab_change
# ============================================================================


class TestOnTabChange:
    @pytest.mark.asyncio
    async def test_openai_files(self) -> None:
        state = _make_state()
        _ = [c async for c in state.on_tab_change("openai_files")]
        assert state.active_tab == "openai_files"

    @pytest.mark.asyncio
    async def test_vector_stores(self) -> None:
        state = _make_state()
        _ = [c async for c in state.on_tab_change("vector_stores")]
        assert state.active_tab == "vector_stores"


# ============================================================================
# load_vector_stores
# ============================================================================


class TestLoadVectorStores:
    @pytest.mark.asyncio
    async def test_no_model_selected(self) -> None:
        state = _make_state()
        _ = [c async for c in state.load_vector_stores()]
        assert state.vector_stores == []

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        state.selected_file_model_id = "gpt-4"
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as repo,
        ):
            repo.find_unique_vector_stores_by_ai_model = AsyncMock(
                return_value=[("vs-1", "Store 1")]
            )
            _ = [c async for c in state.load_vector_stores()]
        assert len(state.vector_stores) == 1
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_empty_clears_selection(self) -> None:
        state = _make_state()
        state.selected_file_model_id = "gpt-4"
        state.selected_vector_store_id = "vs-old"
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as repo,
        ):
            repo.find_unique_vector_stores_by_ai_model = AsyncMock(return_value=[])
            _ = [c async for c in state.load_vector_stores()]
        assert state.selected_vector_store_id == ""
        assert state.files == []

    @pytest.mark.asyncio
    async def test_selected_store_gone(self) -> None:
        state = _make_state()
        state.selected_file_model_id = "gpt-4"
        state.selected_vector_store_id = "vs-gone"
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as repo,
        ):
            repo.find_unique_vector_stores_by_ai_model = AsyncMock(
                return_value=[("vs-1", "Store 1")]
            )
            _ = [c async for c in state.load_vector_stores()]
        assert state.selected_vector_store_id == ""

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _make_state()
        state.selected_file_model_id = "gpt-4"
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as repo,
        ):
            repo.find_unique_vector_stores_by_ai_model = AsyncMock(
                side_effect=RuntimeError("db")
            )
            _ = [c async for c in state.load_vector_stores()]
        assert state.loading is False


# ============================================================================
# load_files
# ============================================================================


class TestLoadFiles:
    @pytest.mark.asyncio
    async def test_no_store_selected(self) -> None:
        state = _make_state()
        _ = [c async for c in state.load_files()]
        assert state.files == []

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        state.selected_vector_store_id = "vs-1"

        upload = MagicMock()
        upload.id = 1
        upload.filename = "test.pdf"
        upload.created_at = MagicMock()
        upload.created_at.strftime.return_value = "01.01.2025 12:00"
        upload.user_id = 42
        upload.file_size = 2048
        upload.openai_file_id = "file-1"

        user = MagicMock()
        user.name = "Alice"
        user.email = "alice@x.com"

        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as fu_repo,
            patch(f"{_PATCH}.user_repo") as u_repo,
        ):
            fu_repo.find_by_vector_store = AsyncMock(return_value=[upload])
            u_repo.find_by_id = AsyncMock(return_value=user)
            _ = [c async for c in state.load_files()]

        assert len(state.files) == 1
        assert state.files[0].user_name == "Alice"

    @pytest.mark.asyncio
    async def test_user_not_found(self) -> None:
        state = _make_state()
        state.selected_vector_store_id = "vs-1"

        upload = MagicMock()
        upload.id = 1
        upload.filename = "test.pdf"
        upload.created_at = MagicMock()
        upload.created_at.strftime.return_value = "01.01.2025"
        upload.user_id = 42
        upload.file_size = 100
        upload.openai_file_id = "file-1"

        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as fu_repo,
            patch(f"{_PATCH}.user_repo") as u_repo,
        ):
            fu_repo.find_by_vector_store = AsyncMock(return_value=[upload])
            u_repo.find_by_id = AsyncMock(return_value=None)
            _ = [c async for c in state.load_files()]
        assert state.files[0].user_name == "Unbekannt"

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _make_state()
        state.selected_vector_store_id = "vs-1"
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as fu_repo,
        ):
            fu_repo.find_by_vector_store = AsyncMock(side_effect=RuntimeError("db"))
            _ = [c async for c in state.load_files()]
        assert state.loading is False


# ============================================================================
# load_openai_files
# ============================================================================


class TestLoadOpenAIFiles:
    @pytest.mark.asyncio
    async def test_no_client(self) -> None:
        state = _make_state()
        with patch.object(
            _StubFileManagerState,
            "_get_client",
            new=AsyncMock(return_value=None),
        ):
            [c async for c in state.load_openai_files()]
        assert state.loading is False

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        oai_file = MagicMock()
        oai_file.id = "file-1"
        oai_file.filename = "test.pdf"
        oai_file.bytes = 2048
        oai_file.created_at = 1706284800
        oai_file.purpose = "assistants"

        response = MagicMock()
        response.data = [oai_file]

        client = AsyncMock()
        client.files.list = AsyncMock(return_value=response)

        with patch.object(
            _StubFileManagerState,
            "_get_client",
            new=AsyncMock(return_value=client),
        ):
            _ = [c async for c in state.load_openai_files()]
        assert len(state.openai_files) == 1

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _make_state()
        client = AsyncMock()
        client.files.list = AsyncMock(side_effect=RuntimeError("api"))
        with patch.object(
            _StubFileManagerState,
            "_get_client",
            new=AsyncMock(return_value=client),
        ):
            _ = [c async for c in state.load_openai_files()]
        assert state.loading is False


# ============================================================================
# delete_file
# ============================================================================


class TestDeleteFile:
    @pytest.mark.asyncio
    async def test_file_not_found(self) -> None:
        state = _make_state()
        state.files = []
        _ = [c async for c in state.delete_file(99)]
        assert state.deleting_file_id is None

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        state.files = [_file_info(1)]
        client = AsyncMock()
        client.files.delete = AsyncMock()

        with (
            patch.object(
                _StubFileManagerState,
                "_get_client",
                new=AsyncMock(return_value=client),
            ),
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as repo,
        ):
            repo.delete_file = AsyncMock(return_value=True)
            [c async for c in state.delete_file(1)]
        assert state.deleting_file_id is None

    @pytest.mark.asyncio
    async def test_delete_fails(self) -> None:
        state = _make_state()
        state.files = [_file_info(1)]
        with (
            patch.object(
                _StubFileManagerState,
                "_get_client",
                new=AsyncMock(return_value=AsyncMock()),
            ),
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as repo,
        ):
            repo.delete_file = AsyncMock(return_value=False)
            _ = [c async for c in state.delete_file(1)]

    @pytest.mark.asyncio
    async def test_no_client_still_deletes(self) -> None:
        state = _make_state()
        state.files = [_file_info(1)]
        with (
            patch.object(
                _StubFileManagerState,
                "_get_client",
                new=AsyncMock(return_value=None),
            ),
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as repo,
        ):
            repo.delete_file = AsyncMock(return_value=True)
            _ = [c async for c in state.delete_file(1)]

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        state = _make_state()
        state.files = [_file_info(1)]
        with patch.object(
            _StubFileManagerState,
            "_get_client",
            new=AsyncMock(side_effect=RuntimeError("x")),
        ):
            _ = [c async for c in state.delete_file(1)]
        assert state.deleting_file_id is None


# ============================================================================
# delete_openai_file
# ============================================================================


class TestDeleteOpenAIFile:
    @pytest.mark.asyncio
    async def test_file_not_found(self) -> None:
        state = _make_state()
        state.openai_files = []
        _ = [c async for c in state.delete_openai_file("x")]
        assert state.deleting_openai_file_id is None

    @pytest.mark.asyncio
    async def test_no_client(self) -> None:
        state = _make_state()
        state.openai_files = [_openai_file("file-1")]
        with patch.object(
            _StubFileManagerState,
            "_get_client",
            new=AsyncMock(return_value=None),
        ):
            _ = [c async for c in state.delete_openai_file("file-1")]

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        state.openai_files = [_openai_file("file-1")]
        client = AsyncMock()
        client.files.delete = AsyncMock()
        with patch.object(
            _StubFileManagerState,
            "_get_client",
            new=AsyncMock(return_value=client),
        ):
            [c async for c in state.delete_openai_file("file-1")]
        assert state.deleting_openai_file_id is None

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _make_state()
        state.openai_files = [_openai_file("file-1")]
        client = AsyncMock()
        client.files.delete = AsyncMock(side_effect=RuntimeError("api"))
        with patch.object(
            _StubFileManagerState,
            "_get_client",
            new=AsyncMock(return_value=client),
        ):
            _ = [c async for c in state.delete_openai_file("file-1")]
        assert state.deleting_openai_file_id is None


# ============================================================================
# start_cleanup (background task)
# ============================================================================


class TestStartCleanup:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        state.selected_file_model_id = "gpt-4"

        async def _gen(**kwargs):
            yield {"status": "checking", "vector_stores_checked": 1}
            yield {"status": "completed"}

        with patch(f"{_PATCH}.run_cleanup", side_effect=_gen):
            _ = [c async for c in state.start_cleanup()]
        assert state.cleanup_running is False

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _make_state()
        state.selected_file_model_id = "gpt-4"

        async def _gen(**kwargs):
            raise RuntimeError("fail")
            yield  # noqa: B027

        with patch(f"{_PATCH}.run_cleanup", side_effect=_gen):
            _ = [c async for c in state.start_cleanup()]
        assert state.cleanup_running is False
        assert state.cleanup_stats.status == "error"


# ============================================================================
# delete_vector_store
# ============================================================================


class TestDeleteVectorStore:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        state = _make_state()
        state.selected_vector_store_id = "vs-1"
        state.vector_stores = [VectorStoreInfo(store_id="vs-1", name="S1")]

        client = AsyncMock()
        client.vector_stores.delete = AsyncMock()
        client.files.delete = AsyncMock()

        file_rec = MagicMock()
        file_rec.openai_file_id = "file-1"

        db = AsyncMock()
        db.commit = AsyncMock()

        with (
            patch.object(
                _StubFileManagerState,
                "_get_client",
                new=AsyncMock(return_value=client),
            ),
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(db),
            ),
            patch(f"{_PATCH}.file_upload_repo") as fu_repo,
            patch(f"{_PATCH}.thread_repo") as t_repo,
        ):
            fu_repo.find_by_vector_store = AsyncMock(return_value=[file_rec])
            fu_repo.delete_by_vector_store = AsyncMock()
            t_repo.clear_vector_store_id = AsyncMock(return_value=1)
            _ = [c async for c in state.delete_vector_store("vs-1")]
        assert state.selected_vector_store_id == ""
        assert state.deleting_vector_store_id is None

    @pytest.mark.asyncio
    async def test_no_client(self) -> None:
        state = _make_state()
        with patch.object(
            _StubFileManagerState,
            "_get_client",
            new=AsyncMock(return_value=None),
        ):
            _ = [c async for c in state.delete_vector_store("vs-1")]

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        state = _make_state()
        with patch.object(
            _StubFileManagerState,
            "_get_client",
            new=AsyncMock(side_effect=RuntimeError("x")),
        ):
            _ = [c async for c in state.delete_vector_store("vs-1")]
        assert state.deleting_vector_store_id is None


# ============================================================================
# select_vector_store
# ============================================================================


class TestSelectVectorStore:
    @pytest.mark.asyncio
    async def test_expired_store(self) -> None:
        state = _make_state()

        vs = MagicMock()
        vs.status = "expired"

        client = AsyncMock()
        client.vector_stores.retrieve = AsyncMock(return_value=vs)

        db = AsyncMock()
        db.commit = AsyncMock()

        with (
            patch.object(
                _StubFileManagerState,
                "_get_client",
                new=AsyncMock(return_value=client),
            ),
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(db),
            ),
            patch(f"{_PATCH}.file_upload_repo") as fu_repo,
            patch(f"{_PATCH}.thread_repo") as t_repo,
        ):
            fu_repo.find_by_vector_store = AsyncMock(return_value=[])
            fu_repo.delete_by_vector_store = AsyncMock()
            t_repo.clear_vector_store_id = AsyncMock(return_value=0)
            _ = [c async for c in state.select_vector_store("vs-1", "S1")]
        assert state.selected_vector_store_id == ""

    @pytest.mark.asyncio
    async def test_not_found_404(self) -> None:
        state = _make_state()

        client = AsyncMock()
        client.vector_stores.retrieve = AsyncMock(side_effect=RuntimeError("not found"))

        db = AsyncMock()
        db.commit = AsyncMock()

        with (
            patch.object(
                _StubFileManagerState,
                "_get_client",
                new=AsyncMock(return_value=client),
            ),
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(db),
            ),
            patch(f"{_PATCH}.file_upload_repo") as fu_repo,
            patch(f"{_PATCH}.thread_repo") as t_repo,
        ):
            fu_repo.find_by_vector_store = AsyncMock(return_value=[])
            fu_repo.delete_by_vector_store = AsyncMock()
            t_repo.clear_vector_store_id = AsyncMock(return_value=0)
            _ = [c async for c in state.select_vector_store("vs-1", "S1")]

    @pytest.mark.asyncio
    async def test_valid_store(self) -> None:
        state = _make_state()

        vs = MagicMock()
        vs.status = "active"

        client = AsyncMock()
        client.vector_stores.retrieve = AsyncMock(return_value=vs)

        with (
            patch.object(
                _StubFileManagerState,
                "_get_client",
                new=AsyncMock(return_value=client),
            ),
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as fu_repo,
            patch(f"{_PATCH}.user_repo"),
        ):
            fu_repo.find_by_vector_store = AsyncMock(return_value=[])
            _ = [c async for c in state.select_vector_store("vs-1", "S1")]
        assert state.selected_vector_store_id == "vs-1"

    @pytest.mark.asyncio
    async def test_no_client(self) -> None:
        state = _make_state()
        with (
            patch.object(
                _StubFileManagerState,
                "_get_client",
                new=AsyncMock(return_value=None),
            ),
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as fu_repo,
            patch(f"{_PATCH}.user_repo"),
        ):
            fu_repo.find_by_vector_store = AsyncMock(return_value=[])
            _ = [c async for c in state.select_vector_store("vs-1", "S1")]
        assert state.selected_vector_store_id == "vs-1"
