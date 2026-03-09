"""Tests for image service (adapter layer between MCP and imagecreator)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_imagecreator.backend.models import (
    GeneratedImageData,
    ImageGeneratorResponse,
    ImageResponseState,
)
from appkit_mcp_image.backend.image_service import (
    _parse_size,
    _to_ic_input,
    edit_image_impl,
    generate_image_impl,
)
from appkit_mcp_image.backend.models import EditImageInput, GenerationInput


class TestParseSize:
    """Test _parse_size helper."""

    def test_standard_sizes(self) -> None:
        assert _parse_size("1024x1024") == (1024, 1024)
        assert _parse_size("1536x1024") == (1536, 1024)
        assert _parse_size("1024x1536") == (1024, 1536)

    def test_auto_defaults_to_square(self) -> None:
        assert _parse_size("auto") == (1024, 1024)


class TestToIcInput:
    """Test _to_ic_input conversion."""

    def test_generation_input_conversion(self) -> None:
        mcp_input = GenerationInput(
            prompt="a cat",
            size="1536x1024",
            seed=42,
            enhance_prompt=False,
        )
        ic_input = _to_ic_input(mcp_input)

        assert ic_input.prompt == "a cat"
        assert ic_input.width == 1536
        assert ic_input.height == 1024
        assert ic_input.seed == 42
        assert ic_input.enhance_prompt is False

    def test_edit_input_conversion(self) -> None:
        mcp_input = EditImageInput(
            prompt="make it blue",
            size="1024x1536",
            image_paths=["http://img/1.png"],
        )
        ic_input = _to_ic_input(mcp_input)

        assert ic_input.prompt == "make it blue"
        assert ic_input.width == 1024
        assert ic_input.height == 1536
        assert ic_input.seed == 0
        assert ic_input.enhance_prompt is True


def _mock_generator() -> MagicMock:
    """Create a mock imagecreator generator."""
    gen = AsyncMock()
    gen.model = MagicMock()
    gen.model.model = "test-model"
    return gen


def _mock_session_context(saved_id: int = 42) -> MagicMock:
    """Create a mock for get_asyncdb_session context manager."""
    mock_session = AsyncMock()
    mock_entity = MagicMock()
    mock_entity.id = saved_id

    async def mock_create(session, entity):  # noqa: ARG001
        entity.id = saved_id
        return entity

    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    return mock_session, mock_create


class TestGenerateImageImpl:
    """Test generate_image_impl function."""

    @pytest.mark.asyncio
    async def test_success_returns_url_and_enhanced_prompt(self) -> None:
        """Successful generation persists image and returns API URL."""
        generator = _mock_generator()
        generator.generate.return_value = ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            generated_images=[
                GeneratedImageData(
                    image_bytes=b"fake-image-bytes",
                    content_type="image/png",
                )
            ],
            enhanced_prompt="Refined cat prompt",
        )

        mock_session, mock_create = _mock_session_context(saved_id=99)

        with (
            patch(
                "appkit_mcp_image.backend.image_service.get_asyncdb_session",
                return_value=mock_session,
            ),
            patch("appkit_mcp_image.backend.image_service.image_repo") as mock_repo,
            patch(
                "appkit_mcp_image.backend.image_service.get_image_api_base_url",
                return_value="http://localhost:3031",
            ),
        ):
            mock_repo.create = AsyncMock(side_effect=mock_create)

            input_data = GenerationInput(prompt="a cat", size="1024x1024")
            image_url, enhanced_prompt = await generate_image_impl(
                input_data, generator, user_id=5
            )

        assert image_url == "http://localhost:3031/api/images/99"
        assert enhanced_prompt == "Refined cat prompt"

    @pytest.mark.asyncio
    async def test_failure_raises_value_error(self) -> None:
        """Generation failure raises ValueError."""
        generator = _mock_generator()
        generator.generate.return_value = ImageGeneratorResponse(
            state=ImageResponseState.FAILED,
            error="API connection failed",
        )

        input_data = GenerationInput(prompt="a cat")

        with pytest.raises(ValueError, match="Image generation failed"):
            await generate_image_impl(input_data, generator, user_id=5)

    @pytest.mark.asyncio
    async def test_no_images_raises_value_error(self) -> None:
        """Empty generated_images list raises ValueError."""
        generator = _mock_generator()
        generator.generate.return_value = ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            generated_images=[],
        )

        input_data = GenerationInput(prompt="a cat")

        with pytest.raises(ValueError, match="No images generated"):
            await generate_image_impl(input_data, generator, user_id=5)

    @pytest.mark.asyncio
    async def test_none_enhanced_prompt(self) -> None:
        """None enhanced_prompt is passed through."""
        generator = _mock_generator()
        generator.generate.return_value = ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            generated_images=[
                GeneratedImageData(image_bytes=b"img", content_type="image/png")
            ],
            enhanced_prompt="",
        )

        mock_session, mock_create = _mock_session_context()

        with (
            patch(
                "appkit_mcp_image.backend.image_service.get_asyncdb_session",
                return_value=mock_session,
            ),
            patch("appkit_mcp_image.backend.image_service.image_repo") as mock_repo,
            patch(
                "appkit_mcp_image.backend.image_service.get_image_api_base_url",
                return_value="http://localhost:3031",
            ),
        ):
            mock_repo.create = AsyncMock(side_effect=mock_create)
            input_data = GenerationInput(prompt="simple", enhance_prompt=False)
            _, enhanced_prompt = await generate_image_impl(
                input_data, generator, user_id=1
            )

        assert enhanced_prompt is None


class TestEditImageImpl:
    """Test edit_image_impl function."""

    @pytest.mark.asyncio
    async def test_success_returns_url(self) -> None:
        """Successful edit persists image and returns API URL."""
        generator = _mock_generator()
        generator.edit.return_value = ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            generated_images=[
                GeneratedImageData(
                    image_bytes=b"edited-bytes",
                    content_type="image/jpeg",
                )
            ],
        )

        mock_session, mock_create = _mock_session_context(saved_id=77)

        with (
            patch(
                "appkit_mcp_image.backend.image_service.get_asyncdb_session",
                return_value=mock_session,
            ),
            patch("appkit_mcp_image.backend.image_service.image_repo") as mock_repo,
            patch(
                "appkit_mcp_image.backend.image_service.get_image_api_base_url",
                return_value="http://localhost:3031",
            ),
            patch(
                "appkit_mcp_image.backend.image_service.ImageProcessor"
            ) as mock_proc_cls,
        ):
            mock_proc = AsyncMock()
            mock_proc.prepare_images_for_editing.return_value = [
                (b"ref-bytes", "image/jpeg")
            ]
            mock_proc.load_image = AsyncMock()
            mock_proc_cls.return_value = mock_proc
            mock_repo.create = AsyncMock(side_effect=mock_create)

            input_data = EditImageInput(
                prompt="make it blue",
                image_paths=["http://example.com/img.png"],
            )
            image_url = await edit_image_impl(input_data, generator, user_id=3)

        assert image_url == "http://localhost:3031/api/images/77"

    @pytest.mark.asyncio
    async def test_failure_raises_value_error(self) -> None:
        """Edit failure raises ValueError."""
        generator = _mock_generator()
        generator.edit.return_value = ImageGeneratorResponse(
            state=ImageResponseState.FAILED,
            error="Unsupported format",
        )

        with patch(
            "appkit_mcp_image.backend.image_service.ImageProcessor"
        ) as mock_proc_cls:
            mock_proc = AsyncMock()
            mock_proc.prepare_images_for_editing.return_value = [(b"data", "image/png")]
            mock_proc_cls.return_value = mock_proc

            input_data = EditImageInput(
                prompt="fix it",
                image_paths=["http://example.com/img.png"],
            )

            with pytest.raises(ValueError, match="Image editing failed"):
                await edit_image_impl(input_data, generator, user_id=1)
