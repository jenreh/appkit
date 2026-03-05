"""Unit tests for image loading strategies."""

import base64
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_mcp_image.backend.image_loaders import (
    Base64ImageLoader,
    FileImageLoader,
    ImageLoaderFactory,
    URLImageLoader,
)

logger = logging.getLogger(__name__)


# Fixtures
@pytest.fixture
def sample_image_bytes() -> bytes:
    """Sample image bytes for testing."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


@pytest.fixture
def sample_base64_data_url(sample_image_bytes: bytes) -> str:
    """Sample base64 data URL."""
    b64_data = base64.b64encode(sample_image_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64_data}"


@pytest.fixture
def caplog_handler(caplog) -> object:
    """Enable caplog at INFO level."""
    caplog.set_level(logging.INFO)
    return caplog


# URLImageLoader Tests
class TestURLImageLoader:
    """Tests for URLImageLoader strategy."""

    @pytest.mark.asyncio
    async def test_load_success(self, sample_image_bytes: bytes) -> None:
        """Test successful image download from URL."""
        loader = URLImageLoader()
        url = "https://d8iqbmvu05s9c.cloudfront.net/ajprhqgqg1otf7d5sm7u3brf27gv"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.content = sample_image_bytes
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await loader.load(url)

            assert result == sample_image_bytes
            mock_client.get.assert_called_once_with(url)

    @pytest.mark.asyncio
    async def test_load_http_status_error(self) -> None:
        """Test handling of HTTP error status."""
        loader = URLImageLoader()
        url = "https://d8iqbmvu05s9c.cloudfront.net/ajprhqgqg1otf7d5sm7u3brf27gvf"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = Exception("404 Not Found")
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(Exception):  # noqa: B017
                await loader.load(url)

    @pytest.mark.asyncio
    async def test_load_network_error(self) -> None:
        """Test handling of network errors."""
        loader = URLImageLoader()
        url = "https://invalid-domain-12345.com/image.png"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(Exception):  # noqa: B017
                await loader.load(url)

    @pytest.mark.asyncio
    async def test_load_logs_success(
        self, sample_image_bytes: bytes, caplog_handler
    ) -> None:
        """Test that successful load is logged."""
        loader = URLImageLoader()
        url = "https://d8iqbmvu05s9c.cloudfront.net/ajprhqgqg1otf7d5sm7u3brf27gv"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.content = sample_image_bytes
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await loader.load(url)

            assert "Downloading image from URL" in caplog_handler.text
            assert "Successfully downloaded image" in caplog_handler.text


# FileImageLoader Tests
class TestFileImageLoader:
    """Tests for FileImageLoader strategy."""

    @pytest.mark.asyncio
    async def test_load_success(self, sample_image_bytes: bytes) -> None:
        """Test successful image load from file."""
        loader = FileImageLoader()
        path = "../gpt-image-b9d516885410416bbc41383494ef04e7.png"  # noqa: S108

        with patch("anyio.open_file") as mock_open_file:
            mock_file = AsyncMock()
            mock_file.read = AsyncMock(return_value=sample_image_bytes)
            mock_open_file.return_value.__aenter__.return_value = mock_file
            mock_open_file.return_value.__aexit__.return_value = None

            result = await loader.load(path)

            assert result == sample_image_bytes
            mock_open_file.assert_called_once_with(path, "rb")

    @pytest.mark.asyncio
    async def test_load_file_not_found(self) -> None:
        """Test handling of missing file."""
        loader = FileImageLoader()
        path = "/nonexistent/image.png"

        with patch("anyio.open_file") as mock_open_file:
            mock_open_file.side_effect = FileNotFoundError("File not found")

            with pytest.raises(FileNotFoundError):
                await loader.load(path)

    @pytest.mark.asyncio
    async def test_load_permission_error(self) -> None:
        """Test handling of permission errors."""
        loader = FileImageLoader()
        path = "/restricted/image.png"

        with patch("anyio.open_file") as mock_open_file:
            mock_open_file.side_effect = PermissionError("Access denied")

            with pytest.raises(PermissionError):
                await loader.load(path)

    @pytest.mark.asyncio
    async def test_load_logs_success(
        self, sample_image_bytes: bytes, caplog_handler
    ) -> None:
        """Test that successful load is logged."""
        loader = FileImageLoader()
        path = "/tmp/test_image.png"  # noqa: S108

        with patch("anyio.open_file") as mock_open_file:
            mock_file = AsyncMock()
            mock_file.read = AsyncMock(return_value=sample_image_bytes)
            mock_open_file.return_value.__aenter__.return_value = mock_file
            mock_open_file.return_value.__aexit__.return_value = None

            await loader.load(path)

            assert "Reading image from local file" in caplog_handler.text
            assert "Successfully read image" in caplog_handler.text


# Base64ImageLoader Tests
class TestBase64ImageLoader:
    """Tests for Base64ImageLoader strategy."""

    @pytest.mark.asyncio
    async def test_load_success(
        self, sample_base64_data_url: str, sample_image_bytes: bytes
    ) -> None:
        """Test successful base64 decoding."""
        loader = Base64ImageLoader()

        result = await loader.load(sample_base64_data_url)

        assert result == sample_image_bytes

    @pytest.mark.asyncio
    async def test_load_invalid_base64(self) -> None:
        """Test handling of invalid base64 data."""
        loader = Base64ImageLoader()
        invalid_data_url = "data:image/png;base64,!!!invalid!!!"

        with pytest.raises(Exception):  # noqa: B017
            await loader.load(invalid_data_url)

    @pytest.mark.asyncio
    async def test_load_malformed_data_url(self) -> None:
        """Test handling of malformed data URL."""
        loader = Base64ImageLoader()
        malformed_url = "data:image/png;base64"  # Missing comma and data

        with pytest.raises(IndexError):
            await loader.load(malformed_url)

    @pytest.mark.asyncio
    async def test_load_logs_success(
        self, sample_base64_data_url: str, caplog_handler
    ) -> None:
        """Test that successful decode is logged."""
        loader = Base64ImageLoader()

        await loader.load(sample_base64_data_url)

        assert "Successfully decoded base64 image" in caplog_handler.text


# ImageLoaderFactory Tests
class TestImageLoaderFactory:
    """Tests for ImageLoaderFactory."""

    def test_create_for_https_url(self) -> None:
        """Test factory returns URLImageLoader for HTTPS URLs."""
        loader = ImageLoaderFactory.create("https://example.com/image.png")

        assert isinstance(loader, URLImageLoader)

    def test_create_for_http_url(self) -> None:
        """Test factory returns URLImageLoader for HTTP URLs."""
        loader = ImageLoaderFactory.create("http://example.com/image.png")

        assert isinstance(loader, URLImageLoader)

    def test_create_for_base64_data_url(self) -> None:
        """Test factory returns Base64ImageLoader for data URLs."""
        loader = ImageLoaderFactory.create("data:image/png;base64,abc123")

        assert isinstance(loader, Base64ImageLoader)

    def test_create_for_local_file_path(self) -> None:
        """Test factory returns FileImageLoader for local paths."""
        loader = ImageLoaderFactory.create("/tmp/test_image.png")  # noqa: S108

        assert isinstance(loader, FileImageLoader)

    def test_create_for_relative_path(self) -> None:
        """Test factory returns FileImageLoader for relative paths."""
        loader = ImageLoaderFactory.create("./images/photo.jpg")

        assert isinstance(loader, FileImageLoader)

    def test_create_for_windows_path(self) -> None:
        """Test factory returns FileImageLoader for Windows paths."""
        loader = ImageLoaderFactory.create("C:\\Users\\image.png")

        assert isinstance(loader, FileImageLoader)

    def test_factory_returns_singleton_instances(self) -> None:
        """Test that factory returns the same loader instance for same type."""
        loader1 = ImageLoaderFactory.create("https://example.com/1.png")
        loader2 = ImageLoaderFactory.create("https://example.com/2.png")

        assert loader1 is loader2

    def test_factory_precedence_data_url_over_http(self) -> None:
        """Test that data: prefix takes precedence."""
        # Edge case: URL starting with "data:" should use Base64ImageLoader
        loader = ImageLoaderFactory.create("data:image/png;base64,abc")

        assert isinstance(loader, Base64ImageLoader)
