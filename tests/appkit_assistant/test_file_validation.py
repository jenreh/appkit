"""Tests for FileValidationService."""

import tempfile
from pathlib import Path

import pytest

from appkit_assistant.backend.services.file_validation import (
    FileValidationService,
    get_file_validation_service,
)


class TestFileValidationService:
    """Test suite for FileValidationService."""

    def test_get_file_extension_extracts_lowercase(self) -> None:
        """get_file_extension returns lowercase extension."""
        service = FileValidationService()

        assert service.get_file_extension("file.PDF") == "pdf"
        assert service.get_file_extension("document.DOCX") == "docx"

    def test_get_file_extension_handles_multiple_dots(self) -> None:
        """get_file_extension returns last extension only."""
        service = FileValidationService()

        assert service.get_file_extension("archive.tar.gz") == "gz"
        assert service.get_file_extension("file.backup.pdf") == "pdf"

    def test_get_file_extension_returns_empty_when_no_extension(self) -> None:
        """get_file_extension returns empty string for no extension."""
        service = FileValidationService()

        assert service.get_file_extension("README") == ""
        assert service.get_file_extension("file_without_ext") == ""

    def test_is_image_file_detects_image_extensions(self) -> None:
        """is_image_file returns True for image files."""
        service = FileValidationService()

        assert service.is_image_file("photo.png") is True
        assert service.is_image_file("image.JPG") is True
        assert service.is_image_file("picture.jpeg") is True
        assert service.is_image_file("graphic.gif") is True
        assert service.is_image_file("modern.webp") is True

    def test_is_image_file_rejects_non_images(self) -> None:
        """is_image_file returns False for non-image files."""
        service = FileValidationService()

        assert service.is_image_file("document.pdf") is False
        assert service.is_image_file("data.csv") is False
        assert service.is_image_file("text.md") is False

    def test_get_media_type_returns_correct_mime(self) -> None:
        """get_media_type returns correct MIME type for known extensions."""
        service = FileValidationService()

        assert service.get_media_type("file.pdf") == "application/pdf"
        assert service.get_media_type("image.png") == "image/png"
        assert service.get_media_type("photo.jpg") == "image/jpeg"
        assert service.get_media_type("data.csv") == "text/csv"
        assert (
            service.get_media_type("doc.docx")
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def test_get_media_type_defaults_for_unknown(self) -> None:
        """get_media_type returns default for unknown extensions."""
        service = FileValidationService()

        assert service.get_media_type("file.xyz") == "application/octet-stream"
        assert service.get_media_type("unknown.bin") == "application/octet-stream"

    def test_validate_file_fails_when_not_exists(self) -> None:
        """validate_file returns False when file doesn't exist."""
        service = FileValidationService()

        valid, error = service.validate_file("/nonexistent/file.pdf")

        assert valid is False
        assert "not found" in error.lower()

    def test_validate_file_fails_for_unsupported_extension(self) -> None:
        """validate_file returns False for unsupported file types."""
        service = FileValidationService()

        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"test data")
            temp_path = f.name

        try:
            valid, error = service.validate_file(temp_path)

            assert valid is False
            assert "unsupported" in error.lower()
            assert "exe" in error.lower()
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_validate_file_fails_when_too_large(self) -> None:
        """validate_file returns False when file exceeds size limit."""
        service = FileValidationService()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            # Write > 5MB
            f.write(b"x" * (6 * 1024 * 1024))
            temp_path = f.name

        try:
            valid, error = service.validate_file(temp_path)

            assert valid is False
            assert "too large" in error.lower()
            assert "max 5mb" in error.lower()
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_validate_file_succeeds_for_valid_file(self) -> None:
        """validate_file returns True for valid file."""
        service = FileValidationService()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"test pdf content")
            temp_path = f.name

        try:
            valid, error = service.validate_file(temp_path)

            assert valid is True
            assert error == ""
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_validate_file_allows_all_supported_extensions(self) -> None:
        """validate_file accepts all ALLOWED_EXTENSIONS."""
        service = FileValidationService()

        for ext in service.ALLOWED_EXTENSIONS:
            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
                f.write(b"test data")
                temp_path = f.name

            try:
                valid, _ = service.validate_file(temp_path)
                assert valid is True, f"Extension {ext} should be allowed"
            finally:
                Path(temp_path).unlink(missing_ok=True)

    def test_validate_file_at_size_limit(self) -> None:
        """validate_file accepts files at exactly 5MB."""
        service = FileValidationService()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            # Write exactly 5MB
            f.write(b"x" * (5 * 1024 * 1024))
            temp_path = f.name

        try:
            valid, error = service.validate_file(temp_path)

            assert valid is True
            assert error == ""
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestFileValidationServiceSingleton:
    """Test suite for singleton pattern."""

    def test_get_file_validation_service_returns_instance(self) -> None:
        """get_file_validation_service returns FileValidationService."""
        service = get_file_validation_service()

        assert isinstance(service, FileValidationService)

    def test_get_file_validation_service_returns_same_instance(self) -> None:
        """get_file_validation_service returns singleton."""
        service1 = get_file_validation_service()
        service2 = get_file_validation_service()

        assert service1 is service2
