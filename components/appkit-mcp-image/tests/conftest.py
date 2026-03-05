"""Pytest fixtures for appkit-mcp-image tests."""

import base64
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp.client import Client

from appkit_commons.registry import service_registry
from appkit_mcp_image.configuration import MCPImageGeneratorConfig
from appkit_mcp_image.server import create_image_mcp_server

pytest_plugins = ["appkit_commons.testing"]

# Minimal valid 1x1 PNG image
_SAMPLE_IMAGE_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
    b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
    b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture(autouse=True)
def setup_config() -> None:
    """Configure registry with default config for tests."""
    config = MCPImageGeneratorConfig()
    service_registry().register_as(MCPImageGeneratorConfig, config)


@pytest.fixture
async def image_client() -> AsyncIterator[Client]:
    """Fixture providing a FastMCP Client for the Image server."""

    mcp = create_image_mcp_server(generator=None)
    async with Client(mcp) as client:
        yield client


# ---------------------------------------------------------------------------
# Shared fixtures for generator and utils tests
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_image_bytes() -> bytes:
    """Minimal PNG image bytes for testing."""
    return _SAMPLE_IMAGE_BYTES


@pytest.fixture
def sample_base64_image() -> str:
    """Base64-encoded data URL of a minimal PNG image."""
    b64 = base64.b64encode(_SAMPLE_IMAGE_BYTES).decode()
    return f"data:image/png;base64,{b64}"


@pytest.fixture
def temp_image_file(tmp_path: object) -> str:
    """Write sample image bytes to a temporary file and return the path."""
    p = Path(str(tmp_path)) / "test_image.png"
    p.write_bytes(_SAMPLE_IMAGE_BYTES)
    return str(p)


# --- Google generator fixtures ---


@pytest.fixture
def google_api_key() -> str:
    """Fake Google API key for testing."""
    return "test-google-api-key"


@pytest.fixture
def mock_google_client() -> MagicMock:
    """Mock google.genai.Client for testing."""
    client = MagicMock()
    client.models.generate_images.return_value = MagicMock(generated_images=[])
    client.models.generate_content.return_value = MagicMock(text="enhanced prompt")
    return client


# --- OpenAI generator fixtures ---


@pytest.fixture
def openai_api_key() -> str:
    """Fake OpenAI API key for testing."""
    return "test-openai-api-key"


@pytest.fixture
def openai_base_url() -> str:
    """Fake OpenAI base URL for testing."""
    return "https://test.openai.azure.com"


@pytest.fixture
def mock_openai_client() -> MagicMock:
    """Mock AsyncAzureOpenAI client for testing."""
    client = MagicMock()
    client.images = MagicMock()
    client.images.generate = AsyncMock()
    client.images.edit = AsyncMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock()
    return client
