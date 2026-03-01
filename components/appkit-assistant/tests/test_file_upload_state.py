# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for FileUploadMixin.

Covers file upload, removal, and clearing uploaded files.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.schemas import UploadedFile
from appkit_assistant.state.thread.file_upload import FileUploadMixin

_PATCH = "appkit_assistant.state.thread.file_upload"


class _StubFileUpload(FileUploadMixin):
    """Stub providing expected state vars without Reflex runtime."""

    def __init__(self) -> None:
        self.uploaded_files: list[UploadedFile] = []
        self.max_file_size_mb: int = 10
        self.max_files_per_thread: int = 5

    async def get_state(self, cls: type) -> MagicMock:
        user_session = MagicMock()
        user_session.user = SimpleNamespace(user_id="user-1")
        return user_session


def _make_state() -> _StubFileUpload:
    return _StubFileUpload()


def _uploaded_file(
    name: str = "test.txt",
    path: str = "/tmp/test.txt",  # noqa: S108
) -> UploadedFile:
    return UploadedFile(filename=name, file_path=path, size=100)


def _mock_upload_file(name: str = "test.txt", data: bytes = b"content") -> MagicMock:
    f = AsyncMock()
    f.filename = name
    f.read = AsyncMock(return_value=data)
    return f


def _mock_upload_dir() -> MagicMock:
    """Create a mock upload dir that supports ``/`` (truediv)."""
    mock_dir = MagicMock()
    # rx.get_upload_dir() / filename -> temp_path (mock)
    mock_path = MagicMock()
    mock_path.parent.mkdir = MagicMock()
    mock_path.write_bytes = MagicMock()
    mock_dir.__truediv__ = MagicMock(return_value=mock_path)
    return mock_dir


# ============================================================================
# handle_upload
# ============================================================================


class TestHandleUpload:
    @pytest.mark.asyncio
    async def test_too_many_files(self) -> None:
        state = _make_state()
        state.max_files_per_thread = 2
        files = [_mock_upload_file(f"f{i}.txt") for i in range(3)]

        chunks = [c async for c in state.handle_upload(files)]
        assert len(chunks) == 1  # toast error
        assert state.uploaded_files == []

    @pytest.mark.asyncio
    async def test_successful_upload(self) -> None:
        state = _make_state()
        f = _mock_upload_file("doc.pdf", b"PDF-content")

        mock_dir = _mock_upload_dir()

        with (
            patch(f"{_PATCH}.rx.get_upload_dir", return_value=mock_dir),
            patch(f"{_PATCH}.file_manager") as mock_fm,
        ):
            mock_fm.move_to_user_directory.return_value = "/final/doc.pdf"
            mock_fm.get_file_size.return_value = 1234

            chunks = [c async for c in state.handle_upload([f])]

        assert len(state.uploaded_files) == 1
        assert state.uploaded_files[0].filename == "doc.pdf"
        assert len(chunks) == 0  # no errors

    @pytest.mark.asyncio
    async def test_upload_exception_handled(self) -> None:
        state = _make_state()
        f = _mock_upload_file("bad.txt")
        f.read = AsyncMock(side_effect=RuntimeError("read failed"))

        chunks = [c async for c in state.handle_upload([f])]
        assert state.uploaded_files == []
        assert len(chunks) == 0  # no error yield, just logged

    @pytest.mark.asyncio
    async def test_multiple_files(self) -> None:
        state = _make_state()
        f1 = _mock_upload_file("a.txt", b"A")
        f2 = _mock_upload_file("b.txt", b"B")

        mock_dir = _mock_upload_dir()

        with (
            patch(f"{_PATCH}.rx.get_upload_dir", return_value=mock_dir),
            patch(f"{_PATCH}.file_manager") as mock_fm,
        ):
            mock_fm.move_to_user_directory.return_value = "/final/file.txt"
            mock_fm.get_file_size.return_value = 50

            chunks = [c async for c in state.handle_upload([f1, f2])]

        assert len(state.uploaded_files) == 2
        assert len(chunks) == 0


# ============================================================================
# remove_file_from_prompt
# ============================================================================


class TestRemoveFileFromPrompt:
    def test_removes_file(self) -> None:
        state = _make_state()
        state.uploaded_files = [
            _uploaded_file("a.txt", "/tmp/a.txt"),  # noqa: S108
            _uploaded_file("b.txt", "/tmp/b.txt"),  # noqa: S108
        ]

        with patch(f"{_PATCH}.file_manager") as mock_fm:
            state.remove_file_from_prompt("/tmp/a.txt")  # noqa: S108
            mock_fm.cleanup_uploaded_files.assert_called_once_with(
                ["/tmp/a.txt"]  # noqa: S108
            )

        assert len(state.uploaded_files) == 1
        assert state.uploaded_files[0].filename == "b.txt"

    def test_removes_nonexistent_noop(self) -> None:
        state = _make_state()
        state.uploaded_files = [
            _uploaded_file("a.txt", "/tmp/a.txt")  # noqa: S108
        ]

        with patch(f"{_PATCH}.file_manager"):
            state.remove_file_from_prompt("/tmp/nonexistent.txt")  # noqa: S108

        assert len(state.uploaded_files) == 1


# ============================================================================
# _clear_uploaded_files
# ============================================================================


class TestClearUploadedFiles:
    def test_clears_all(self) -> None:
        state = _make_state()
        state.uploaded_files = [
            _uploaded_file("a.txt", "/tmp/a.txt"),  # noqa: S108
            _uploaded_file("b.txt", "/tmp/b.txt"),  # noqa: S108
        ]

        with patch(f"{_PATCH}.file_manager") as mock_fm:
            state._clear_uploaded_files()
            mock_fm.cleanup_uploaded_files.assert_called_once_with(
                ["/tmp/a.txt", "/tmp/b.txt"]  # noqa: S108
            )

        assert state.uploaded_files == []

    def test_empty_noop(self) -> None:
        state = _make_state()
        with patch(f"{_PATCH}.file_manager") as mock_fm:
            state._clear_uploaded_files()
            mock_fm.cleanup_uploaded_files.assert_not_called()
