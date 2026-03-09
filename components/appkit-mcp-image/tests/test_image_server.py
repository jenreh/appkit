"""Tests for the MCP Image server."""

import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp.client import Client
from fastmcp.exceptions import ToolError


def test_creates_server() -> None:
    """Server instance is created successfully."""
    from appkit_mcp_image.server import create_image_mcp_server

    mcp = create_image_mcp_server(default_model_id="test-model")
    assert mcp is not None


def test_custom_name() -> None:
    """Server respects custom name parameter."""
    from appkit_mcp_image.server import create_image_mcp_server

    mcp = create_image_mcp_server(default_model_id="test-model", name="custom-image")
    assert mcp.name == "custom-image"


async def test_list_tools_registered(image_client: Client) -> None:
    """Server registers generate_image and edit_image tools."""
    tools = await image_client.list_tools()
    tool_names = {t.name for t in tools}
    assert "generate_image" in tool_names
    assert "edit_image" in tool_names


# -- _success_result tests --


class TestSuccessResult:
    def test_basic(self) -> None:
        from appkit_mcp_image.server import _success_result

        result = json.loads(_success_result("http://img/1.png", "a cat"))
        assert result["success"] is True
        assert result["image_url"] == "http://img/1.png"
        assert result["prompt"] == "a cat"

    def test_with_optional_fields(self) -> None:
        from appkit_mcp_image.server import _success_result

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


# -- Tool integration tests --


@pytest.fixture
async def gen_client() -> AsyncIterator[Client]:
    """Client with mocked registry and auth for tool tests."""
    from appkit_mcp_image.server import create_image_mcp_server

    mcp = create_image_mcp_server(default_model_id="test-model")
    async with Client(mcp) as client:
        yield client


class TestGenerateImageTool:
    async def test_success(self, gen_client: Client) -> None:
        """generate_image returns success result."""
        mock_gen = MagicMock()
        mock_gen.model = MagicMock()
        mock_gen.model.model = "test-model"

        with (
            patch(
                "appkit_imagecreator.backend.generator_registry.generator_registry"
            ) as mock_registry,
            patch(
                "appkit_mcp_image.server._get_user_id",
                return_value=1,
            ),
            patch(
                "appkit_mcp_image.server.generate_image_impl",
                new_callable=AsyncMock,
                return_value=(
                    "http://localhost/img.png",
                    "enhanced cat",
                ),
            ),
        ):
            mock_registry.get.return_value = mock_gen
            result = await gen_client.call_tool(
                "generate_image",
                arguments={"prompt": "a cat"},
            )
        data = json.loads(result.content[0].text)
        assert data["success"] is True
        assert data["image_url"] == "http://localhost/img.png"
        assert data["enhanced_prompt"] == "enhanced cat"

    async def test_value_error(self, gen_client: Client) -> None:
        """generate_image sets isError=True on ValueError."""
        mock_gen = MagicMock()
        mock_gen.model = MagicMock()
        mock_gen.model.model = "test-model"

        with (
            patch(
                "appkit_imagecreator.backend.generator_registry.generator_registry"
            ) as mock_registry,
            patch(
                "appkit_mcp_image.server._get_user_id",
                return_value=1,
            ),
            patch(
                "appkit_mcp_image.server.generate_image_impl",
                new_callable=AsyncMock,
                side_effect=ValueError("generation failed"),
            ),
            pytest.raises(ToolError, match="generation failed"),
        ):
            mock_registry.get.return_value = mock_gen
            await gen_client.call_tool(
                "generate_image",
                arguments={"prompt": "bad prompt"},
            )


class TestEditImageTool:
    async def test_success(self, gen_client: Client) -> None:
        """edit_image returns success result."""
        mock_gen = MagicMock()
        mock_gen.model = MagicMock()
        mock_gen.model.model = "test-model"

        with (
            patch(
                "appkit_imagecreator.backend.generator_registry.generator_registry"
            ) as mock_registry,
            patch(
                "appkit_mcp_image.server._get_user_id",
                return_value=1,
            ),
            patch(
                "appkit_mcp_image.server.edit_image_impl",
                new_callable=AsyncMock,
                return_value="http://localhost/edited.png",
            ),
        ):
            mock_registry.get.return_value = mock_gen
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
        """edit_image sets isError=True on ValueError."""
        mock_gen = MagicMock()
        mock_gen.model = MagicMock()
        mock_gen.model.model = "test-model"

        with (
            patch(
                "appkit_imagecreator.backend.generator_registry.generator_registry"
            ) as mock_registry,
            patch(
                "appkit_mcp_image.server._get_user_id",
                return_value=1,
            ),
            patch(
                "appkit_mcp_image.server.edit_image_impl",
                new_callable=AsyncMock,
                side_effect=ValueError("editing not supported"),
            ),
            pytest.raises(ToolError, match="editing not supported"),
        ):
            mock_registry.get.return_value = mock_gen
            await gen_client.call_tool(
                "edit_image",
                arguments={
                    "prompt": "edit this",
                    "image_paths": ["http://img/x.png"],
                },
            )
