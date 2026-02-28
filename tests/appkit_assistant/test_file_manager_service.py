"""Tests for file_manager utilities.

Covers get_user_upload_directory, _make_unique_filename,
move_to_user_directory, and cleanup_uploaded_files.
"""

from pathlib import Path

import pytest

from appkit_assistant.backend.services.file_manager import (
    _make_unique_filename,
    cleanup_uploaded_files,
    get_user_upload_directory,
    move_to_user_directory,
)


class TestGetUserUploadDirectory:
    def test_creates_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "appkit_assistant.backend.services.file_manager.UPLOAD_BASE_DIR",
            tmp_path / "uploads",
        )
        result = get_user_upload_directory("user123")
        assert result.exists()
        assert result == tmp_path / "uploads" / "user123"

    def test_idempotent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "appkit_assistant.backend.services.file_manager.UPLOAD_BASE_DIR",
            tmp_path / "uploads",
        )
        d1 = get_user_upload_directory("u1")
        d2 = get_user_upload_directory("u1")
        assert d1 == d2


class TestMakeUniqueFilename:
    def test_no_conflict(self, tmp_path: Path) -> None:
        target = tmp_path / "file.txt"
        assert _make_unique_filename(target) == target

    def test_conflict_appends_counter(self, tmp_path: Path) -> None:
        target = tmp_path / "file.txt"
        target.write_text("existing")
        result = _make_unique_filename(target)
        assert result == tmp_path / "file_1.txt"

    def test_multiple_conflicts(self, tmp_path: Path) -> None:
        for name in ["file.txt", "file_1.txt", "file_2.txt"]:
            (tmp_path / name).write_text("x")
        result = _make_unique_filename(tmp_path / "file.txt")
        assert result == tmp_path / "file_3.txt"


class TestMoveToUserDirectory:
    def test_moves_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "appkit_assistant.backend.services.file_manager.UPLOAD_BASE_DIR",
            tmp_path / "uploads",
        )
        src = tmp_path / "temp.pdf"
        src.write_text("content")
        result = move_to_user_directory(str(src), "user1")
        assert Path(result).exists()
        assert not src.exists()
        assert "user1" in result

    def test_source_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            move_to_user_directory(str(tmp_path / "nonexistent.pdf"), "u1")

    def test_unique_filename_on_conflict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "appkit_assistant.backend.services.file_manager.UPLOAD_BASE_DIR",
            tmp_path / "uploads",
        )
        # Create existing file in user dir
        user_dir = tmp_path / "uploads" / "user1"
        user_dir.mkdir(parents=True)
        (user_dir / "file.txt").write_text("existing")

        src = tmp_path / "file.txt"
        src.write_text("new content")
        result = move_to_user_directory(str(src), "user1")
        assert "file_1.txt" in result


class TestCleanupUploadedFiles:
    def test_deletes_files(self, tmp_path: Path) -> None:
        files = []
        for i in range(3):
            f = tmp_path / f"file{i}.txt"
            f.write_text("x")
            files.append(str(f))
        cleanup_uploaded_files(files)
        for f in files:
            assert not Path(f).exists()

    def test_missing_file_no_error(self, tmp_path: Path) -> None:
        cleanup_uploaded_files([str(tmp_path / "nonexistent.txt")])
        # Should not raise

    def test_empty_list(self) -> None:
        cleanup_uploaded_files([])
        # Should not raise
