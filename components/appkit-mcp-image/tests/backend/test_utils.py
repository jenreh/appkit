"""Tests for backend utility functions."""

import base64
from pathlib import Path

import httpx
import pytest
import respx
from httpx import Response

import appkit_mcp_image.backend.utils as utils_module
from appkit_mcp_image.backend.utils import (
    url_to_base64,
    url_to_bytes,
)


class TestUrlToBytes:
    """Test url_to_bytes function."""

    @pytest.mark.asyncio
    async def test_url_to_bytes_data_url(self, sample_base64_image: str) -> None:
        """Test loading image from data URL."""
        result = await url_to_bytes(sample_base64_image)

        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_url_to_bytes_http_url(self, sample_image_bytes: bytes) -> None:
        """Test downloading image from HTTP URL."""
        url = "https://example.com/image.png"
        respx.get(url).mock(return_value=Response(200, content=sample_image_bytes))

        result = await url_to_bytes(url)

        assert result == sample_image_bytes

    @pytest.mark.asyncio
    @respx.mock
    async def test_url_to_bytes_https_url(self, sample_image_bytes: bytes) -> None:
        """Test downloading image from HTTPS URL."""
        url = "https://secure.example.com/image.png"
        respx.get(url).mock(return_value=Response(200, content=sample_image_bytes))

        result = await url_to_bytes(url)

        assert result == sample_image_bytes

    @pytest.mark.asyncio
    async def test_url_to_bytes_local_file(
        self, temp_image_file: str, sample_image_bytes: bytes
    ) -> None:
        """Test reading image from local file path."""
        result = await url_to_bytes(temp_image_file)

        assert result == sample_image_bytes

    @pytest.mark.asyncio
    @respx.mock
    async def test_url_to_bytes_backend_upload_url(
        self,
        tmp_path: Path,
        sample_image_bytes: bytes,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test reading from backend upload directory."""
        # Create a temp file
        temp_file = tmp_path / "generated.png"
        temp_file.write_bytes(sample_image_bytes)

        # Mock TMP_PATH to point to temp directory
        monkeypatch.setattr(utils_module, "TMP_PATH", str(tmp_path))

        url = "http://localhost:8000/_upload/generated.png"
        result = await url_to_bytes(url)

        assert result == sample_image_bytes

    @pytest.mark.asyncio
    @respx.mock
    async def test_url_to_bytes_backend_upload_url_fallback_to_remote(
        self,
        sample_image_bytes: bytes,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test falling back to remote download when local file doesn't exist."""
        # Mock TMP_PATH but don't create the file
        monkeypatch.setattr(utils_module, "TMP_PATH", "/nonexistent/tmp")

        url = "http://localhost:8000/_upload/missing.png"
        remote_url = "http://localhost:8000/_upload/missing.png"
        respx.get(remote_url).mock(
            return_value=Response(200, content=sample_image_bytes)
        )

        result = await url_to_bytes(url)

        # Should fall back to remote download
        assert result == sample_image_bytes

    @pytest.mark.asyncio
    @respx.mock
    async def test_url_to_bytes_http_error(self) -> None:
        """Test handling HTTP error responses."""
        url = "https://example.com/notfound.png"
        respx.get(url).mock(return_value=Response(404))

        with pytest.raises(httpx.HTTPStatusError):
            await url_to_bytes(url)

    @pytest.mark.asyncio
    @respx.mock
    async def test_url_to_bytes_http_500_error(self) -> None:
        """Test handling HTTP 500 error."""
        url = "https://example.com/error.png"
        respx.get(url).mock(return_value=Response(500))

        with pytest.raises(httpx.HTTPStatusError):
            await url_to_bytes(url)

    @pytest.mark.asyncio
    async def test_url_to_bytes_empty_data_url(self) -> None:
        """Test handling malformed data URL without comma separator."""
        malformed_url = "data:image/png;base64"  # Missing comma and data

        with pytest.raises(IndexError):
            await url_to_bytes(malformed_url)


class TestUrlToBase64:
    """Test url_to_base64 function."""

    @pytest.mark.asyncio
    async def test_url_to_base64_data_url(self, sample_base64_image: str) -> None:
        """Test converting data URL to base64."""
        result = await url_to_base64(sample_base64_image)

        assert isinstance(result, str)
        # Should be valid base64
        decoded = base64.b64decode(result)
        assert isinstance(decoded, bytes)

    @pytest.mark.asyncio
    @respx.mock
    async def test_url_to_base64_http_url(self, sample_image_bytes: bytes) -> None:
        """Test downloading and converting HTTP URL to base64."""
        url = "https://example.com/image.png"
        respx.get(url).mock(return_value=Response(200, content=sample_image_bytes))

        result = await url_to_base64(url)

        assert isinstance(result, str)
        decoded = base64.b64decode(result)
        assert decoded == sample_image_bytes

    @pytest.mark.asyncio
    async def test_url_to_base64_local_file(
        self, temp_image_file: str, sample_image_bytes: bytes
    ) -> None:
        """Test reading and converting local file to base64."""
        result = await url_to_base64(temp_image_file)

        assert isinstance(result, str)
        decoded = base64.b64decode(result)
        assert decoded == sample_image_bytes

    @pytest.mark.asyncio
    async def test_url_to_base64_file_not_found(self) -> None:
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            await url_to_base64("/nonexistent/file.png")

    @pytest.mark.asyncio
    @respx.mock
    async def test_url_to_base64_http_error(self) -> None:
        """Test handling HTTP errors."""
        url = "https://example.com/notfound.png"
        respx.get(url).mock(return_value=Response(404))

        with pytest.raises(httpx.HTTPStatusError):
            await url_to_base64(url)
