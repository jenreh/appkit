# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for OpenAIImageGenerator.

Covers init, API param building, content type mapping, response
processing, prompt enhancement, generation, image editing, and file prep.
"""

from __future__ import annotations

import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_imagecreator.backend.generators.openai import (
    OpenAIImageGenerator,
)
from appkit_imagecreator.backend.models import (
    GenerationInput,
    ImageModel,
    ImageResponseState,
)

_PATCH = "appkit_imagecreator.backend.generators.openai"


def _model(model_id: str = "gpt-image-1") -> ImageModel:
    return ImageModel(
        id=model_id,
        model=model_id,
        label="GPT Image",
        config={"output_format": "png", "moderation": "low"},
    )


def _gen(
    api_key: str = "sk-test",
    on_azure: bool = False,
    base_url: str | None = None,
) -> OpenAIImageGenerator:
    with patch(f"{_PATCH}.AsyncOpenAI") as mock_cls:
        mock_cls.return_value = MagicMock()
        return OpenAIImageGenerator(
            model=_model(),
            api_key=api_key,
            base_url=base_url,
            on_azure=on_azure,
        )


# ============================================================================
# Initialization
# ============================================================================


class TestInit:
    def test_standard_client(self) -> None:
        gen = _gen()
        assert gen.client is not None
        assert gen._on_azure is False

    def test_azure_client(self) -> None:
        with patch(f"{_PATCH}.AsyncAzureOpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            gen = OpenAIImageGenerator(
                model=_model(),
                api_key="key",
                base_url="https://azure.test",
                on_azure=True,
            )
        assert gen._on_azure is True
        assert gen.client is not None


# ============================================================================
# _build_api_params
# ============================================================================


class TestBuildApiParams:
    def test_generate_endpoint(self) -> None:
        gen = _gen()
        params = gen._build_api_params(prompt="test", n=1)
        assert params["prompt"] == "test"
        assert params["output_format"] == "png"
        # input_fidelity should be filtered for generate
        assert "input_fidelity" not in params

    def test_edit_endpoint(self) -> None:
        gen = _gen()
        params = gen._build_api_params(endpoint="edit", prompt="edit")
        assert params["prompt"] == "edit"
        # moderation should be filtered for edit
        assert "moderation" not in params

    def test_overrides(self) -> None:
        gen = _gen()
        params = gen._build_api_params(model="dall-e-3", n=2)
        assert params["model"] == "dall-e-3"
        assert params["n"] == 2

    def test_no_config(self) -> None:
        model = ImageModel(id="m", model="m", label="M", config=None)
        with patch(f"{_PATCH}.AsyncOpenAI"):
            gen = OpenAIImageGenerator(model=model, api_key="k")
        params = gen._build_api_params(prompt="t")
        assert params["prompt"] == "t"


# ============================================================================
# _get_content_type
# ============================================================================


class TestGetContentType:
    def test_jpeg(self) -> None:
        gen = _gen()
        assert gen._get_content_type({"output_format": "jpeg"}) == "image/jpeg"

    def test_png(self) -> None:
        gen = _gen()
        assert gen._get_content_type({"output_format": "png"}) == "image/png"

    def test_default(self) -> None:
        gen = _gen()
        assert gen._get_content_type({}) == "image/jpeg"


# ============================================================================
# _process_response_images
# ============================================================================


class TestProcessResponseImages:
    @pytest.mark.asyncio
    async def test_b64_json(self) -> None:
        gen = _gen()

        b64 = base64.b64encode(b"fake-image").decode()
        img = SimpleNamespace(b64_json=b64, url=None)
        result = await gen._process_response_images([img], "image/png")
        assert len(result) == 1
        assert result[0].image_bytes == b"fake-image"

    @pytest.mark.asyncio
    async def test_url_fetch(self) -> None:
        gen = _gen()
        img = SimpleNamespace(b64_json=None, url="https://img.test/a.png")

        mock_resp = MagicMock()
        mock_resp.content = b"downloaded"
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            ctx = AsyncMock()
            ctx.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=ctx)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await gen._process_response_images([img], "image/png")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_no_data(self) -> None:
        gen = _gen()
        img = SimpleNamespace(b64_json=None, url=None)
        result = await gen._process_response_images([img], "image/png")
        assert len(result) == 0


# ============================================================================
# _enhance_prompt
# ============================================================================


class TestEnhancePrompt:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        gen = _gen()
        gen.client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content="Enhanced"))]
            )
        )
        result = await gen._enhance_prompt("test")
        assert result == "Enhanced"

    @pytest.mark.asyncio
    async def test_error_fallback(self) -> None:
        gen = _gen()
        gen.client.chat.completions.create = AsyncMock(side_effect=RuntimeError("fail"))
        result = await gen._enhance_prompt("original")
        assert result == "original"


# ============================================================================
# _prepare_image_files
# ============================================================================


class TestPrepareImageFiles:
    def test_known_types(self) -> None:
        gen = _gen()
        refs = [
            (b"img1", "image/png"),
            (b"img2", "image/jpeg"),
            (b"img3", "image/webp"),
        ]
        result = gen._prepare_image_files(refs)
        assert len(result) == 3
        assert result[0][0] == "reference_0.png"
        assert result[1][0] == "reference_1.jpg"
        assert result[2][0] == "reference_2.webp"

    def test_unknown_type_defaults_jpg(self) -> None:
        gen = _gen()
        refs = [(b"img", "image/bmp")]
        result = gen._prepare_image_files(refs)
        assert result[0][0] == "reference_0.jpg"


# ============================================================================
# _perform_generation
# ============================================================================


class TestPerformGeneration:
    @pytest.mark.asyncio
    async def test_basic(self) -> None:
        gen = _gen()

        b64 = base64.b64encode(b"img").decode()
        gen.client.images.generate = AsyncMock(
            return_value=MagicMock(data=[SimpleNamespace(b64_json=b64, url=None)])
        )
        inp = GenerationInput(prompt="sunset", enhance_prompt=False)
        result = await gen._perform_generation(inp)
        assert result.state == ImageResponseState.SUCCEEDED
        assert len(result.generated_images) == 1

    @pytest.mark.asyncio
    async def test_no_images(self) -> None:
        gen = _gen()
        gen.client.images.generate = AsyncMock(return_value=MagicMock(data=[]))
        inp = GenerationInput(prompt="sunset", enhance_prompt=False)
        result = await gen._perform_generation(inp)
        assert result.state == ImageResponseState.FAILED

    @pytest.mark.asyncio
    async def test_with_enhancement(self) -> None:
        gen = _gen()

        b64 = base64.b64encode(b"img").decode()
        gen.client.images.generate = AsyncMock(
            return_value=MagicMock(data=[SimpleNamespace(b64_json=b64, url=None)])
        )
        gen.client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content="Better sunset"))]
            )
        )
        inp = GenerationInput(prompt="sunset", enhance_prompt=True)
        result = await gen._perform_generation(inp)
        assert result.enhanced_prompt == "Better sunset"


# ============================================================================
# _perform_edit
# ============================================================================


class TestPerformEdit:
    @pytest.mark.asyncio
    async def test_basic(self) -> None:
        gen = _gen()

        b64 = base64.b64encode(b"edited").decode()
        gen.client.images.edit = AsyncMock(
            return_value=MagicMock(data=[SimpleNamespace(b64_json=b64, url=None)])
        )
        inp = GenerationInput(prompt="edit this", enhance_prompt=False)
        refs = [(b"src", "image/png")]
        result = await gen._perform_edit(inp, refs)
        assert result.state == ImageResponseState.SUCCEEDED

    @pytest.mark.asyncio
    async def test_no_results(self) -> None:
        gen = _gen()
        gen.client.images.edit = AsyncMock(return_value=MagicMock(data=[]))
        inp = GenerationInput(prompt="edit", enhance_prompt=False)
        refs = [(b"src", "image/png")]
        result = await gen._perform_edit(inp, refs)
        assert result.state == ImageResponseState.FAILED
