"""Tests for the MCP Image server."""

import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp.client import Client
from pydantic import SecretStr

from appkit_mcp_image.backend.models import ImageGenerator
from appkit_mcp_image.configuration import MCPImageGeneratorConfig
from appkit_mcp_image.server import (
    _error_result,
    _generators,
    _success_result,
    create_image_mcp_server,
    init_generators,
)


def test_creates_server() -> None:
    """Server instance is created successfully."""
    mcp = create_image_mcp_server(generator=None)
    assert mcp is not None


def test_custom_name() -> None:
    """Server respects custom name parameter."""
    mcp = create_image_mcp_server(generator=None, name="custom-image")
    assert mcp.name == "custom-image"


async def test_list_tools_registered(image_client: Client) -> None:
    """Server registers generate_image and edit_image tools."""
    tools = await image_client.list_tools()
    tool_names = {t.name for t in tools}
    assert "generate_image" in tool_names
    assert "edit_image" in tool_names


# -- _success_result / _error_result tests --


class TestSuccessResult:
    def test_basic(self) -> None:
        result = json.loads(_success_result("http://img/1.png", "a cat"))
        assert result["success"] is True
        assert result["image_url"] == "http://img/1.png"
        assert result["prompt"] == "a cat"

    def test_with_optional_fields(self) -> None:
        result = json.loads(
            _success_result(
                "http://img/1.png",
                "prompt",
                enhanced_prompt="enhanced",
                model="gpt-image-1",
                size="1024x1024",
            )
        )
        assert result["enhanced_prompt"] == "enhanced"
        assert result["model"] == "gpt-image-1"
        assert result["size"] == "1024x1024"


class TestErrorResult:
    def test_basic(self) -> None:
        result = json.loads(_error_result("something broke"))
        assert result["success"] is False
        assert result["error"] == "something broke"

    def test_no_image_url(self) -> None:
        result = json.loads(_error_result("err"))
        assert result.get("image_url") is None


# -- init_generators tests --


class TestInitGenerators:
    def test_no_keys_returns_empty(self) -> None:
        _generators.clear()
        config = MCPImageGeneratorConfig()
        result = init_generators(config)
        assert isinstance(result, dict)

    def test_returns_cached(self) -> None:
        _generators.clear()
        sentinel = MagicMock(spec=ImageGenerator)
        _generators["test"] = sentinel
        config = MCPImageGeneratorConfig()
        result = init_generators(config)
        assert "test" in result
        _generators.clear()

    def test_azure_generator(self) -> None:
        """Azure generator is created when keys are provided."""
        _generators.clear()
        config = MCPImageGeneratorConfig(
            azure_api_key=SecretStr("test-key"),
            azure_base_url=SecretStr("https://test.openai.azure.com"),
            azure_image_model="gpt-image-1",
            azure_prompt_optimizer="gpt-5-mini",
        )
        result = init_generators(config)
        assert "azure" in result
        assert "google" not in result
        _generators.clear()

    def test_google_generator(self) -> None:
        """Google generator is created when key is provided."""
        _generators.clear()
        config = MCPImageGeneratorConfig(
            google_api_key=SecretStr("test-google-key"),
            google_image_model="imagen-4",
            google_prompt_optimizer="gemini-flash",
        )
        result = init_generators(config)
        assert "google" in result
        assert "azure" not in result
        _generators.clear()

    def test_both_generators(self) -> None:
        """Both generators created when all keys provided."""
        _generators.clear()
        config = MCPImageGeneratorConfig(
            azure_api_key=SecretStr("azure-key"),
            azure_base_url=SecretStr("https://test.azure.com"),
            google_api_key=SecretStr("google-key"),
        )
        result = init_generators(config)
        assert "azure" in result
        assert "google" in result
        _generators.clear()


# -- Tool integration tests --


@pytest.fixture
async def gen_client() -> AsyncIterator[Client]:
    """Client with a mock generator for tool tests."""
    mock_gen = MagicMock(spec=ImageGenerator)
    mock_gen.model = "test-model"
    mcp = create_image_mcp_server(generator=mock_gen)
    async with Client(mcp) as client:
        yield client


class TestGenerateImageTool:
    async def test_success(self, gen_client: Client) -> None:
        """generate_image returns success result."""
        with patch(
            "appkit_mcp_image.server.generate_image_impl",
            new_callable=AsyncMock,
            return_value=(
                "http://localhost/img.png",
                "enhanced cat",
            ),
        ):
            result = await gen_client.call_tool(
                "generate_image",
                arguments={"prompt": "a cat"},
            )
        data = json.loads(result.content[0].text)
        assert data["success"] is True
        assert data["image_url"] == "http://localhost/img.png"
        assert data["enhanced_prompt"] == "enhanced cat"

    async def test_value_error(self, gen_client: Client) -> None:
        """generate_image returns error on ValueError."""
        with patch(
            "appkit_mcp_image.server.generate_image_impl",
            new_callable=AsyncMock,
            side_effect=ValueError("generation failed"),
        ):
            result = await gen_client.call_tool(
                "generate_image",
                arguments={"prompt": "bad prompt"},
            )
        data = json.loads(result.content[0].text)
        assert data["success"] is False
        assert "generation failed" in data["error"]


class TestEditImageTool:
    async def test_success(self, gen_client: Client) -> None:
        """edit_image returns success result."""
        with patch(
            "appkit_mcp_image.server.edit_image_impl",
            new_callable=AsyncMock,
            return_value="http://localhost/edited.png",
        ):
            result = await gen_client.call_tool(
                "edit_image",
                arguments={
                    "prompt": "make it blue",
                    "image_paths": ["http://img/orig.png"],
                },
            )
        data = json.loads(result.content[0].text)
        assert data["success"] is True
        assert data["image_url"] == "http://localhost/edited.png"

    async def test_value_error(self, gen_client: Client) -> None:
        """edit_image returns error on ValueError."""
        with patch(
            "appkit_mcp_image.server.edit_image_impl",
            new_callable=AsyncMock,
            side_effect=ValueError("editing not supported"),
        ):
            result = await gen_client.call_tool(
                "edit_image",
                arguments={
                    "prompt": "edit this",
                    "image_paths": ["http://img/x.png"],
                },
            )
        data = json.loads(result.content[0].text)
        assert data["success"] is False
        assert "editing not supported" in data["error"]
