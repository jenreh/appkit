# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for BlackForestLabsImageGenerator.

Covers init, API param construction, payload building, response parsing,
polling, prompt enhancement, and the generate/edit flows.
"""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_imagecreator.backend.generators.black_forest_labs import (
    BlackForestLabsImageGenerator,
)
from appkit_imagecreator.backend.models import (
    GenerationInput,
    ImageModel,
    ImageResponseState,
)


def _model(model_id: str = "flux-2-pro") -> ImageModel:
    return ImageModel(id=model_id, model=model_id, label="Flux 2 Pro")


def _gen(
    api_key: str = "bfl-key",
    on_azure: bool = False,
    base_url: str = "https://api.bfl.ai/v1/",
) -> BlackForestLabsImageGenerator:
    return BlackForestLabsImageGenerator(
        model=_model(),
        api_key=api_key,
        base_url=base_url,
        on_azure=on_azure,
    )


# ============================================================================
# Initialization
# ============================================================================


class TestInit:
    def test_defaults(self) -> None:
        gen = _gen()
        assert gen.model.model == "flux-2-pro"
        assert gen.api_key == "bfl-key"
        assert gen._base_url == "https://api.bfl.ai/v1/"
        assert gen._on_azure is False

    def test_azure(self) -> None:
        gen = _gen(on_azure=True, base_url="https://azure.test")
        assert gen._on_azure is True


# ============================================================================
# _get_api_params
# ============================================================================


class TestGetApiParams:
    def test_native(self) -> None:
        gen = _gen()
        url, headers = gen._get_api_params()
        assert "flux-2-pro" in url
        assert headers["x-key"] == "bfl-key"

    def test_azure(self) -> None:
        gen = _gen(on_azure=True, base_url="https://azure.test")
        url, headers = gen._get_api_params()
        assert "providers/blackforestlabs" in url
        assert "Bearer bfl-key" in headers["Authorization"]


# ============================================================================
# _build_payload
# ============================================================================


class TestBuildPayload:
    def test_basic(self) -> None:
        gen = _gen()
        inp = GenerationInput(prompt="sunset", width=1024, height=768)
        payload = gen._build_payload(inp, "sunset")
        assert payload["prompt"] == "sunset"
        assert payload["width"] == 1024
        assert payload["height"] == 768

    def test_azure_model_name(self) -> None:
        gen = _gen(on_azure=True)
        inp = GenerationInput(prompt="test")
        payload = gen._build_payload(inp, "test")
        # "flux-2-pro" → "flux.2-pro"
        assert payload["model"] == "flux.2-pro"

    def test_model_config_merged(self) -> None:
        model = ImageModel(
            id="flux",
            model="flux",
            label="Flux",
            config={"steps": 30},
        )
        gen = BlackForestLabsImageGenerator(model=model, api_key="key")
        inp = GenerationInput(prompt="test")
        payload = gen._build_payload(inp, "test")
        assert payload["steps"] == 30


# ============================================================================
# _parse_response
# ============================================================================


class TestParseResponse:
    def test_native_response(self) -> None:
        gen = _gen()
        data = {"result": {"sample": "https://img.test/a.png"}}
        resp = gen._parse_response(data, "sunset")
        assert resp.state == ImageResponseState.SUCCEEDED
        assert len(resp.generated_images) == 1
        assert resp.generated_images[0].external_url == "https://img.test/a.png"

    def test_azure_response(self) -> None:
        gen = _gen(on_azure=True)
        b64_data = base64.b64encode(b"fake-image").decode()
        data = {"data": [{"b64_json": b64_data}]}
        resp = gen._parse_response(data, "sunset")
        assert resp.state == ImageResponseState.SUCCEEDED
        assert resp.generated_images[0].image_bytes == b"fake-image"

    def test_native_missing_url(self) -> None:
        gen = _gen()
        with pytest.raises(ValueError, match="No image URL"):
            gen._parse_response({"result": {}}, "test")

    def test_azure_missing_data(self) -> None:
        gen = _gen(on_azure=True)
        with pytest.raises(ValueError, match="No image data"):
            gen._parse_response({"data": []}, "test")


# ============================================================================
# _poll_result
# ============================================================================


class TestPollResult:
    @pytest.mark.asyncio
    async def test_ready(self) -> None:
        gen = _gen()
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": "Ready",
            "result": {"sample": "url"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await gen._poll_result(mock_client, "https://poll")

        assert result["status"] == "Ready"

    @pytest.mark.asyncio
    async def test_unexpected_status(self) -> None:
        gen = _gen()
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "Failed"}
        mock_resp.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(ValueError, match="Unexpected status"),
        ):
            await gen._poll_result(mock_client, "https://poll")


# ============================================================================
# _make_request
# ============================================================================


class TestMakeRequest:
    @pytest.mark.asyncio
    async def test_azure_returns_directly(self) -> None:
        gen = _gen(on_azure=True, base_url="https://azure.test")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": [{"b64_json": "abc"}]}
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            ctx = AsyncMock()
            ctx.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=ctx)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await gen._make_request({"prompt": "test"})

        assert "data" in result

    @pytest.mark.asyncio
    async def test_native_polls(self) -> None:
        gen = _gen()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"polling_url": "https://poll/abc"}
        mock_resp.raise_for_status = MagicMock()

        with (
            patch("httpx.AsyncClient") as mock_client_cls,
            patch.object(
                gen,
                "_poll_result",
                new_callable=AsyncMock,
                return_value={"status": "Ready", "result": {"sample": "url"}},
            ),
        ):
            ctx = AsyncMock()
            ctx.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=ctx)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await gen._make_request({"prompt": "test"})

        assert result["status"] == "Ready"


# ============================================================================
# _enhance_prompt
# ============================================================================


class TestEnhancePrompt:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        gen = _gen()
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content="Enhanced"))]
            )
        )
        mock_config = MagicMock()
        mock_config.openai_model = "gpt-4.1-mini"
        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_config
        with (
            patch.object(
                gen,
                "_create_openai_client",
                new_callable=AsyncMock,
                return_value=mock_client,
            ),
            patch(
                "appkit_imagecreator.backend.generators.black_forest_labs.service_registry",
                return_value=mock_registry,
            ),
        ):
            result = await gen._enhance_prompt("test prompt")
        assert result == "Enhanced"

    @pytest.mark.asyncio
    async def test_no_client(self) -> None:
        gen = _gen()
        with patch.object(
            gen,
            "_create_openai_client",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await gen._enhance_prompt("test prompt")
        assert result == "test prompt"

    @pytest.mark.asyncio
    async def test_error_fallback(self) -> None:
        gen = _gen()
        with patch.object(
            gen,
            "_create_openai_client",
            new_callable=AsyncMock,
            side_effect=RuntimeError("fail"),
        ):
            result = await gen._enhance_prompt("original")
        assert result == "original"


# ============================================================================
# _execute (central error handler)
# ============================================================================


class TestExecute:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        gen = _gen()
        with (
            patch.object(
                gen,
                "_make_request",
                new_callable=AsyncMock,
                return_value={"result": {"sample": "https://img/a.png"}},
            ),
        ):
            result = await gen._execute({"prompt": "test"}, "test")
        assert result.state == ImageResponseState.SUCCEEDED

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        gen = _gen()
        with patch.object(
            gen,
            "_make_request",
            new_callable=AsyncMock,
            side_effect=RuntimeError("API error"),
        ):
            result = await gen._execute({"prompt": "test"}, "test")
        assert result.state == ImageResponseState.FAILED
        assert "API error" in result.error


# ============================================================================
# _perform_generation
# ============================================================================


class TestPerformGeneration:
    @pytest.mark.asyncio
    async def test_basic(self) -> None:
        gen = _gen()
        inp = GenerationInput(prompt="a sunset", enhance_prompt=False)
        with patch.object(
            gen,
            "_execute",
            new_callable=AsyncMock,
            return_value=MagicMock(state=ImageResponseState.SUCCEEDED),
        ) as mock_exec:
            result = await gen._perform_generation(inp)
        assert result.state == ImageResponseState.SUCCEEDED
        mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_enhancement(self) -> None:
        gen = _gen()
        inp = GenerationInput(prompt="a sunset", enhance_prompt=True)
        with (
            patch.object(
                gen,
                "_enhance_prompt",
                new_callable=AsyncMock,
                return_value="enhanced sunset",
            ),
            patch.object(
                gen,
                "_execute",
                new_callable=AsyncMock,
                return_value=MagicMock(state=ImageResponseState.SUCCEEDED),
            ) as mock_exec,
        ):
            await gen._perform_generation(inp)
        # The enhanced prompt should be passed to _execute
        args = mock_exec.call_args[0]
        assert args[1] == "enhanced sunset"


# ============================================================================
# _perform_edit
# ============================================================================


class TestPerformEdit:
    @pytest.mark.asyncio
    async def test_appends_images(self) -> None:
        gen = _gen()
        inp = GenerationInput(prompt="edit this")
        ref_images = [(b"img1", "image/png"), (b"img2", "image/png")]
        with patch.object(
            gen,
            "_execute",
            new_callable=AsyncMock,
            return_value=MagicMock(state=ImageResponseState.SUCCEEDED),
        ) as mock_exec:
            await gen._perform_edit(inp, ref_images)

        payload = mock_exec.call_args[0][0]
        assert "input_image" in payload
        assert "input_image_2" in payload
